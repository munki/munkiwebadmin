from django.conf.urls import patterns, include, url

urlpatterns = patterns('catalogs.views',
    #url(r'^$', 'index'),
    #url(r'^(?P<catalog_name>[^/]+)/$', 'detail'),
    #url(r'^(?P<catalog_name>[^/]+)/(?P<item_index>\d+)/$', 'item_detail'),
    #url(r'^(?P<catalog_name>[^/]+)/(?P<item_name>[^/]+)/$', 'detail'),
    url(r'^$', 'catalog_view'),
    url(r'^(?P<catalog_name>[^/]+)/$', 'catalog_view'),
    url(r'^(?P<catalog_name>[^/]+)/(?P<item_index>\d+)/$', 'item_detail'),
    #url(r'^(?P<catalog_name>[^/]+)/(?P<item_name>[^/]+)/$', 'test_index'),
    #url(r'^(?P<catalog_name>[^/]+)/edit/$', 'edit'),
)