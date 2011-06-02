from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseRedirect as redirect, HttpResponse
from django.shortcuts import get_object_or_404
from djangohelpers.lib import rendered_with, allow_http
from bagels.main.models import GameRoom, Board, Item
from django.utils import simplejson
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

def json(func):
    def inner(*args, **kw):
        val = func(*args, **kw)
        val = simplejson.dumps(val)
        return HttpResponse(val, mimetype="application/json")
    return inner

@csrf_exempt
@json
def connect(request):
    name = request.COOKIES['user']
    game = request.COOKIES['game']
    return [True, {"name": name}]

@csrf_exempt
@json
def create_channel(request):
    return [True, {'history_size': 0, "reflective": True, "presenceful": True}]

@csrf_exempt
@json
def unsubscribe(request):
    name = request.COOKIES['user']
    game = request.COOKIES['game']

    room = GameRoom.objects.get(pk=game)
    user = User.objects.get(username=name)

    room.players.remove(user)
    return [True, {}]

@csrf_exempt
@json
def subscribe(request):
    name = request.COOKIES['user']
    game = request.COOKIES['game']

    room = GameRoom.objects.get(pk=game)
    if room.num_players() > 1:
        return [False, {}]

    try:
        user = User.objects.get(username=name)
    except User.DoesNotExist:
        data = dict(username=name,
                    password1='testing',
                    password2='testing',
                    )
        form = UserCreationForm(data)
        user = form.save()
    
    room.players.add(user)
    return [True, {}]
