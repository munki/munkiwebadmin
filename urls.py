from django.conf.urls import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    
    url(r'^login/$', 'django.contrib.auth.views.login', name='login'),
    url(r'^logout/$', 'django.contrib.auth.views.logout_then_login', name='logout'),
    url(r'^manifest/', include('manifests.urls')),
    url(r'^catalog/', include('catalogs.urls')),
    url(r'^report/', include('reports.urls')),
    url(r'^inventory/', include('inventory.urls')),
    url(r'^licenses/', include('licenses.urls')),
    # for compatibility with MunkiReport scripts
    url(r'^update/', include('reports.urls')),
    url(r'^lookup/', include('reports.urls')),
    url(r'^$', include('reports.urls')),
)
# comment out the following if you are serving
# static files a different way
urlpatterns += staticfiles_urlpatterns()
