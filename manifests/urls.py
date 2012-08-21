from django.conf.urls.defaults import *

urlpatterns = patterns('manifests.views',
    url(r'^$', 'index'),
    url(r'^new$', 'new'),
    url(r'^delete/(?P<manifest_name>[^/]+)/$', 'delete'),
    #url(r'^#(?P<manifest_name>.+)/$', 'index'),
    url(r'^view/(?P<manifest_name>[^/]+)/$', 'view'),
    url(r'^detail/(?P<manifest_name>[^/]+)$', 'detail'),
    url(r'^json/suggested_items/(?P<manifest_name>[^/]+)$', 'json_suggested_items'),
    url(r'^json/catalog_names/$', 'json_catalog_names'),
    url(r'^json/manifest_names/$', 'json_manifest_names'),
)