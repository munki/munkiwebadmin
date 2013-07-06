from django.http import HttpResponse, HttpRequest, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.core.context_processors import csrf
from django.views.decorators.csrf import csrf_exempt
from django.core.urlresolvers import reverse
from django.http import Http404
#from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.conf import settings
from django import forms
from django.db.models import Q
from django.db.models import Count

import plistlib
import base64
import bz2
import hashlib
import json

from datetime import datetime
import urllib2
from xml.etree import ElementTree

from models import Inventory, InventoryItem
from reports.models import Machine

def decode_to_string(base64bz2data):
    '''Decodes an inventory submission, which is a plist-encoded
    list, compressed via bz2 and base64 encoded.'''
    try:
        bz2data = base64.b64decode(base64bz2data)
        return bz2.decompress(bz2data)
    except Exception:
        return ''


@csrf_exempt
def submit(request):
    if request.method != 'POST':
        raise Http404
    
    # list of bundleids to ignore
    bundleid_ignorelist = [
        'com.apple.print.PrinterProxy'
    ]
    submission = request.POST
    mac = submission.get('mac')
    machine = None
    if mac:
        try:
            machine = Machine.objects.get(mac=mac)
        except Machine.DoesNotExist:
            machine = Machine(mac=mac)
    if machine:
        if 'hostname' in submission:
            machine.hostname = submission.get('hostname')
        if 'username' in submission:
            machine.username = submission.get('username')
        if 'location' in submission:
            machine.location = submission.get('location')
        machine.remote_ip = request.META['REMOTE_ADDR']
        compressed_inventory = submission.get('base64bz2inventory')
        if compressed_inventory:
            compressed_inventory = compressed_inventory.replace(" ", "+")
            inventory_str = decode_to_string(compressed_inventory)
            try:
                inventory_list = plistlib.readPlistFromString(inventory_str)
            except Exception:
                inventory_list = None
            if inventory_list:
                try:
                    inventory_meta = Inventory.objects.get(machine=machine)
                except Inventory.DoesNotExist:
                    inventory_meta = Inventory(machine=machine)
                inventory_meta.sha256hash = \
                    hashlib.sha256(inventory_str).hexdigest()
                # clear existing inventoryitems
                machine.inventoryitem_set.all().delete()
                # insert current inventory items
                for item in inventory_list:
                    # skip items in bundleid_ignorelist.
                    if not item.get('bundleid') in bundleid_ignorelist:
                        i_item = machine.inventoryitem_set.create(
                            name=item.get('name', ''),
                            version=item.get('version', ''),
                            bundleid=item.get('bundleid', ''),
                            bundlename=item.get('CFBundleName', ''),
                            path=item.get('path', '')
                            )
                machine.last_inventory_update = datetime.now()
                inventory_meta.save()
            machine.save()
            return HttpResponse(
                "Inventory submmitted for %s.\n" %
                submission.get('hostname'))
    
    return HttpResponse("No inventory submitted.\n")


def inventory_hash(request, mac):
    sha256hash = ''
    machine = None
    if mac:
        try:
            machine = Machine.objects.get(mac=mac)
            inventory_meta = Inventory.objects.get(machine=machine)
            sha256hash = inventory_meta.sha256hash
        except (Machine.DoesNotExist, Inventory.DoesNotExist):
            pass
    else:
        raise Http404
    return HttpResponse(sha256hash)


@login_required
def index(request):
    all_machines = Machine.objects.all()
    return render_to_response('inventory/index.html',
                              {'machines': all_machines,
                               'user': request.user,
                               'page': 'inventory'})


@login_required
def detail(request, mac):
    machine = None
    if mac:
        try:
            machine = Machine.objects.get(mac=mac)
        except Machine.DoesNotExist:
            raise Http404
    else:
        raise Http404

    machine = None
    try:
        machine = Machine.objects.get(mac=mac)
    except Machine.DoesNotExist:
        pass
        
    inventory_items = machine.inventoryitem_set.all()
    
    # determine if the model description information should be shown
    try:
        MODEL_LOOKUP_ENABLED = settings.MODEL_LOOKUP_ENABLED
    except:
        MODEL_LOOKUP_ENABLED = False

    # If enabled lookup the model description
    additional_info = {}
    if MODEL_LOOKUP_ENABLED and machine.serial_number:
        additional_info['model_description'] = \
            model_description_lookup(machine.serial_number)
    
    return render_to_response('inventory/detail.html',
                             {'machine': machine,
                              'inventory_items': inventory_items,
                              'user': request.user,
                              'additional_info': additional_info,
                              'model_lookup_enabled': MODEL_LOOKUP_ENABLED,
                              'page': 'inventory'})


@login_required
def items(request):
    name = request.GET.get('name')
    version = request.GET.get('version')
    bundleid = request.GET.get('bundleid')
    bundlename = request.GET.get('bundlename')
    path = request.GET.get('path')
    
    if name or bundleid or bundlename or path:
        item_detail = {}
        item_detail['name'] = name or bundleid or bundlename or path
        
        items = InventoryItem.objects.all()
        if name:
            items = items.filter(name__exact=name)
        if version:
            if version.endswith('*'):
                items = items.filter(
                    version__startswith=version[0:-1])
            else:
                items = items.filter(version__exact=version)
        if bundleid:
            items = items.filter(bundleid__exact=bundleid)
        if bundlename:
            items = items.filter(bundlename__exact=bundlename)
        if path:
            items = items.filter(path__exact=path)
    
        item_detail['instances'] = []
        for item in items:
            instance = {}
            instance['mac'] = item.machine.mac
            instance['hostname'] = item.machine.hostname
            instance['username'] = item.machine.username
            instance['version'] = item.version
            instance['bundleid'] = item.bundleid
            instance['bundlename'] = item.bundlename
            instance['path'] = item.path
            item_detail['instances'].append(instance)
        
        return render_to_response(
            'inventory/item_detail.html',
            {'item_detail': item_detail,
             'user': request.user,
             'page': 'inventory'})
    else:
        return render_to_response('inventory/items.html',
                                  {'user': request.user,
                                   'page': 'inventory'})


def items_json(request):
    inventory_items = InventoryItem.objects.values(
        'name', 'version').annotate(num_machines=Count('machine'))

    # build a dict so we can group by name
    inventory_dict = {}
    for item in inventory_items:
        name = item['name']
        version = item['version']
        machine_count = item['num_machines']
        if not name in inventory_dict:
            inventory_dict[name] = []
        inventory_dict[name].append({'version': version, 
                                     'count': machine_count})

    # convert to an array for use by DataTables
    rows = []
    for name, versions in inventory_dict.items():
        rows.append({'name': name,
                     'versions': versions})

    # send it back in JSON format
    return HttpResponse(json.dumps(rows),
                        mimetype='application/json')


def model_description_lookup(serial):
    """Determines the models human readable description based off the serial
    number"""
    # Based off https://github.com/MagerValp/MacModelShelf/		
    
    snippet = serial[-3:]
    if (len(serial) == 12):
        snippet = serial[-4:]
    try:
        response = urllib2.urlopen(
            "http://support-sp.apple.com/sp/product?cc=%s&lang=en_US" 
            % snippet, timeout=2)
        et = ElementTree.parse(response)
        return et.findtext("configCode").decode("utf-8")
    except:
        return ''
