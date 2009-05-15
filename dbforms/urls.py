from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^([0-9]+)/$', 'dbforms.views.handle_contactform')
)
