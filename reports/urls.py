from django.conf.urls.defaults import *

urlpatterns = patterns('reports.views',
    url(r'^index/*$', 'index'),
    url(r'^$', 'overview'),
    url(r'^overview/*$', 'overview'),
    url(r'^detail/(?P<mac>[^/]+)$', 'detail'),
    url(r'^raw/(?P<mac>[^/]+)$', 'raw'),
    url(r'^submit/(?P<submission_type>[^/]+)$', 'submit'),
    # for compatibilty with MunkiReport scripts
    url(r'^ip$', 'lookup_ip'),
    url(r'^(?P<submission_type>[^/]+)$', 'submit'),
)