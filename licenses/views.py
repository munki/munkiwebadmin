from django.http import HttpResponse, HttpRequest, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.http import Http404
from django.contrib.auth.decorators import login_required, permission_required

import plistlib
import json

from models import License

def index(request):
    '''MWA index page for licenses.'''
    all_licenses = License.objects.all()
    return render_to_response('licenses/index.html', 
        {'licenses': all_licenses,
         'user': request.user,
         'page': 'licenses'})


def available(request, item_name=''):
    '''Returns license seat availability for item_name in plist format.
    Key is item_name, value is boolean.
    For use by Munki client to determine if a given item should be made
    available for optional install.'''
    output_style = request.GET.get('output_style', 'plist')
    item_names = []
    if item_name:
        item_names.append(item_name)
    additional_names = request.GET.getlist('name')
    item_names.extend(additional_names)
    info = {}
    if item_names:
        for name in item_names:
            try:
                license = License.objects.get(item_name=name)
                info[name] = (license.available() > 0)
            except (License.DoesNotExist):
                pass
    else:
        # return everything
        licenses = License.objects.all()
        for license in licenses:
            info[license.item_name] = license.available()
            
    if output_style == 'json':
        return HttpResponse(json.dumps(info), mimetype='application/json')
    else:
        return HttpResponse(plistlib.writePlistToString(info),
                            mimetype='application/xml')


def usage(request, item_name=''):
    '''Returns license info for item_name in plist or json format.'''
    output_style = request.GET.get('output_style', 'plist')
    item_names = []
    if item_name:
        item_names.append(item_name)
    additional_names = request.GET.getlist('name')
    item_names.extend(additional_names)
    info = {}
    for name in item_names:
        try:
            license = License.objects.get(item_name=name)
            info[name] = {'total': license.total,
                          'used': license.used()}
            # calculate available instead of hitting the db a second time
            info[name]['available'] = (
                info[name]['total'] - info[name]['used'])
        except (License.DoesNotExist):
            info[name] = {}
    if output_style == 'json':
        return HttpResponse(json.dumps(info), mimetype='application/json')
    else:
        return HttpResponse(plistlib.writePlistToString(info),
                            mimetype='application/xml')