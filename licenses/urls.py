from django.conf.urls import patterns, include, url

urlpatterns = patterns('licenses.views',
    url(r'^$', 'index'),
    url(r'^available/$', 'available'),
    url(r'^available/(?P<item_name>[^/]+)$', 'available'),
    url(r'^usage/$', 'usage'),
    url(r'^usage/(?P<item_name>[^/]+)$', 'usage'),
)