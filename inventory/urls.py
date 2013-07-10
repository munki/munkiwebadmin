from django.conf.urls import patterns, include, url

urlpatterns = patterns('inventory.views',
    url(r'^index/*$', 'index'),
    url(r'^$', 'index'),
    url(r'^submit/*$', 'submit'),
    url(r'^hash/(?P<mac>[^/]+)$', 'inventory_hash'),
    url(r'^detail/(?P<mac>[^/]+)$', 'detail'),
    url(r'^items/*$', 'items'),
    url(r'^items.json/*$', 'items_json'),
    #url(r'^(?P<mac>[^/]+)$', 'detail'),
)