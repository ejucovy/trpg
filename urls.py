from django.conf.urls.defaults import *

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns(
    '',
    # (r'^bagels/', include('bagels.foo.urls')),
    (r'^$', 'bagels.main.views.room_index'),

    (r'^static/(?P<path>.+)/$', 'bagels.main.static_view.static_view'),
    (r'^connect$', 'bagels.main.hookbox.connect'),
    (r'^create_channel$', 'bagels.main.hookbox.create_channel'),
    (r'^publish$', 'bagels.main.hookbox.publish'),
    (r'^subscribe$', 'bagels.main.hookbox.subscribe'),
    (r'^unsubscribe$', 'bagels.main.hookbox.unsubscribe'),

    url(r'^(?P<room_id>\d+)/$', 'bagels.main.views.room', name='game-view'),
    url(r'^(?P<room_id>\d+)/json/$', 'bagels.main.views.room_json', name='game-json'),
    url(r'^(?P<room_id>\d+)/move/$', 'bagels.main.views.room_move', name='game-move'),
    url(r'^(?P<room_id>\d+)/act/$', 'bagels.main.views.room_act', name='game-act'),
    url(r'^(?P<room_id>\d+)/ready/$', 'bagels.main.views.room_ready', name='game-ready'),

    (r'^admin/', include(admin.site.urls)),
)
