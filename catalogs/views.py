from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from models import Catalog

import json

def nameAndVersion(aString):
    ### from munkilib.updatecheck
    """Splits a string into the name and version number.

    Name and version must be seperated with a hyphen ('-')
    or double hyphen ('--').
    'TextWrangler-2.3b1' becomes ('TextWrangler', '2.3b1')
    'AdobePhotoshopCS3--11.2.1' becomes ('AdobePhotoshopCS3', '11.2.1')
    'MicrosoftOffice2008-12.2.1' becomes ('MicrosoftOffice2008', '12.2.1')
    """
    for delim in ('--', '-'):
        if aString.count(delim) > 0:
            chunks = aString.split(delim)
            vers = chunks.pop()
            name = delim.join(chunks)
            if vers[0] in '0123456789':
                return (name, vers)

    return (aString, '')
    
    
def trimVersionString(version_string):
    ### from munkilib.updatecheck
    """Trims all lone trailing zeros in the version string after major/minor.

    Examples:
      10.0.0.0 -> 10.0
      10.0.0.1 -> 10.0.0.1
      10.0.0-abc1 -> 10.0.0-abc1
      10.0.0-abc1.0 -> 10.0.0-abc1
    """
    if version_string == None or version_string == '':
        return ''
    version_parts = version_string.split('.')
    # strip off all trailing 0's in the version, while over 2 parts.
    while len(version_parts) > 2 and version_parts[-1] == '0':
        del(version_parts[-1])
    return '.'.join(version_parts)


@login_required                              
def item_detail(request, catalog_name, item_index):
    catalog_item = Catalog.item_detail(catalog_name, item_index)
    return render_to_response('catalogs/item_detail.html', 
                              {'catalog_item': catalog_item})
                              

@login_required
def catalog_view(request, catalog_name=None, item_index=None):
    catalog_list = Catalog.list()
    if request.is_ajax():
        return HttpResponse(json.dumps(catalog_list),
                            mimetype='application/json')
    catalog = None
    catalog_item = None
    if not catalog_name:
        if 'production' in catalog_list:
            catalog_name = 'production'
        else:
            catalog_name = catalog_list[0]
    catalog = Catalog.detail(catalog_name)
    if item_index:
        catalog_item = Catalog.item_detail(catalog_name, item_index)
    return render_to_response('catalogs/catalog.html',
                          {'catalog_list': catalog_list,
                           'catalog_name': catalog_name,
                           'catalog': catalog,
                           'item_index': item_index,
                           'catalog_item': catalog_item,
                           'user': request.user,
                           'page': 'catalogs'})
    #else:
    #    return render_to_response('catalogs/index.html',
    #                              {'catalog_list': catalog_list,
    #                               'user': request.user,
    #                               'page': 'catalogs'})
        
    
                              