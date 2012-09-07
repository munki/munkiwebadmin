from django.http import HttpResponse, HttpRequest, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.core.context_processors import csrf
from django.core.urlresolvers import reverse
#from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.conf import settings
from django import forms

from models import Manifest
from catalogs.models import Catalog

import fnmatch
import json
import os

MANIFEST_USERNAME_IS_EDITABLE = settings.MANIFEST_USERNAME_IS_EDITABLE
MANIFEST_USERNAME_KEY = settings.MANIFEST_USERNAME_KEY


class NewManifestForm(forms.Form):
    manifest_name = forms.CharField(max_length=120)
    user_name = forms.CharField(max_length=120, required=False)
    
    error_css_class = 'error'
    required_css_class = 'required'
    
    def clean_manifest_name(self):
        manifest_names = Manifest.list()
        if self.cleaned_data['manifest_name'] in manifest_names:
            raise forms.ValidationError('Manifest name already exists!')
        return self.cleaned_data['manifest_name']
        
    
@login_required
@permission_required('reports.change_machine', login_url='/login/')
def new(request):
    if request.method == 'POST': # If the form has been submitted...
        form = NewManifestForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data
            # ...
            # Redirect after POST
            manifest = Manifest.new()
            manifest_name = form.cleaned_data['manifest_name']
            user_name = form.cleaned_data.get('user_name','')
            manifest[MANIFEST_USERNAME_KEY] = user_name
            Manifest.write(manifest_name, manifest,
                           request.user)
            return HttpResponseRedirect(
                '/manifest/view/%s' % manifest_name)
        else:
            # form not valid, try again
            c = RequestContext(request, {'form': form})
    else:
        form = NewManifestForm() # An unbound form
        c = RequestContext(request, {'form': form})
        c.update(csrf(request))
        
    return render_to_response('manifests/new.html', c)
    

@login_required
@permission_required('reports.change_machine', login_url='/login/')
def delete(request, manifest_name=None):
    if request.method == 'POST':
        Manifest.delete(manifest_name, request.user)
        return HttpResponseRedirect('/manifest/')
    else:
        c = RequestContext(request, {'manifest_name': manifest_name})
        c.update(csrf(request))
        return render_to_response('manifests/delete.html', c)


def getManifestInfo(manifest_names):
    manifest_list = []
    for name in manifest_names:
        m_dict = {}
        m_dict['name'] = name
        manifest = Manifest.read(name)
        m_dict['user'] = manifest.get(MANIFEST_USERNAME_KEY, '')
        manifest_list.append(m_dict) 
    return manifest_list


@login_required
def index(request, manifest_name=None):
    if request.method == 'GET':
        manifest_names = Manifest.list()
        available_sections =   ['catalogs',
                                'included_manifests',
                                'managed_installs',
                                'managed_uninstalls',
                                'managed_updates',
                                'optional_installs']
        section = request.GET.get('section', 'manifest_name')
        findtext = request.GET.get('findtext', '')
        #sort = request.GET.get('sort', 'name')
        if findtext:
            filtered_names = []
            if section == 'manifest_name':
                for name in manifest_names:
                    basename = os.path.basename(name)
                    if fnmatch.fnmatch(basename, findtext):
                        filtered_names.append(name)
            elif section == 'user_name':
                for name in manifest_names:
                    manifest = Manifest.read(name)
                    if manifest:
                        username = manifest.get(MANIFEST_USERNAME_KEY, '')
                        if fnmatch.fnmatch(username, findtext):
                            filtered_names.append(name)
            else:
                for name in manifest_names:
                    manifest = Manifest.read(name)
                    if manifest:
                        for item in manifest.get(section, []):
                            if fnmatch.fnmatch(item, findtext):
                                filtered_names.append(name)
                                break
        
            manifest_names = filtered_names
        
        manifest_list = getManifestInfo(manifest_names)
        username = None
        manifest = None
        
        if manifest_name:
            manifest = Manifest.read(manifest_name)
            username = manifest.get(MANIFEST_USERNAME_KEY)
            manifest_name = manifest_name.replace(':', '/')
        c = RequestContext(request,     
            {'manifest_list': manifest_list,
             'section': section,
             'findtext': findtext,
             'available_sections': available_sections,
             'manifest_name': manifest_name,
             'manifest_user': username,
             'manifest': manifest,
             'show_edit_controls':
                 request.user.has_perm('reports.change_machine'),
             'user': request.user,
             'page': 'manifests'})
        
        return render_to_response('manifests/index.html', c)
        

@login_required
def view(request, manifest_name=None):
    return index(request, manifest_name)


def get_suggestions(request, item_list):
    suggestions = []
    if item_list:
        term = request.GET.get('term', '').lower()
        if term:
            suggestions = [ item for item in item_list 
                            if term in item.lower() ]
        suggestions.sort()
    return HttpResponse(json.dumps(suggestions),
                        mimetype='application/json')


def json_suggested_items(request, manifest_name):
    valid_install_items = Manifest.getSuggestedInstallItems(manifest_name)
    return get_suggestions(request, valid_install_items)


def json_catalog_names(request):
    valid_catalogs = Catalog.list()
    valid_catalogs.sort()
    term = request.GET.get('term', '').lower()
    if term:
        suggestions = [ item for item in valid_catalogs 
                        if term in item.lower() ]
    else:
        suggestions = valid_catalogs
    return HttpResponse(json.dumps(suggestions),
                        mimetype='application/json')


def old_json_catalog_names(request):
    valid_catalogs = Catalog.list()
    valid_catalogs.sort()
    return HttpResponse(json.dumps(valid_catalogs),
                        mimetype='application/json')


def json_manifest_names(request):
    valid_manifest_names = Manifest.list()
    valid_manifest_names.sort()
    term = request.GET.get('term', '').lower()
    if term:
        suggestions = [ item for item in valid_manifest_names
                        if term in item.lower() ]
    else:
        suggestions = valid_manifest_names
    return HttpResponse(json.dumps(suggestions),
                        mimetype='application/json')


def old_json_manifest_names(request):
    valid_manifest_names = Manifest.list()
    valid_manifest_names.sort()
    return HttpResponse(json.dumps(valid_manifest_names),
                        mimetype='application/json')


@login_required
def detail(request, manifest_name):
    if request.method == 'POST':
        if request.is_ajax():
            json_data = json.loads(request.raw_post_data)
            if json_data:
                manifest_detail = Manifest.read(manifest_name)
                for key in json_data.keys():
                    manifest_detail[key] = json_data[key]
                Manifest.write(manifest_name, manifest_detail,
                               request.user)
            return HttpResponse(json.dumps('success'))
    if request.method == 'GET':
        manifest = Manifest.read(manifest_name)
        valid_install_items = Manifest.getValidInstallItems(manifest_name)
        valid_catalogs = Catalog.list()
        valid_manifest_names = Manifest.list()
        manifest_user = manifest.get(MANIFEST_USERNAME_KEY, '')
        
        c = RequestContext(request, 
            {'manifest_name': manifest_name.replace(':', '/'),
            'manifest_user': manifest_user,
            'manifest_user_is_editable': MANIFEST_USERNAME_IS_EDITABLE,
            'manifest': manifest,
            'valid_install_items': valid_install_items,
            'valid_catalogs': valid_catalogs,
            'valid_manifest_names': valid_manifest_names,
            'user': request.user,
            'show_edit_controls':
                request.user.has_perm('reports.change_machine'),
            'user': request.user,
            'page': 'manifests'})
        c.update(csrf(request))
        return render_to_response('manifests/detail.html', c)
