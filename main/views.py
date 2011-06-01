from django.http import HttpResponseRedirect as redirect, HttpResponse
from django.shortcuts import get_object_or_404
from djangohelpers.lib import rendered_with, allow_http
from bagels.main.models import GameRoom, Board, Item
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from restclient import GET
import random
import urllib
from django.conf import settings
from django.utils import simplejson

def start_board():
    board = Board()
    board.add_item(1, 1, Item(type='rock', height=3))
    board.add_item(2, 2, Item(type='rock', height=3))
    board.add_item(4, 4, Item(type='rock', height=3))
    board.add_item(2, 5, Item(type='rock', height=3))
    board.add_item(5, 4, Item(type='rock', height=3))

    board.add_item(9, 9, Item(type='unit', job='knight', team='red', health=10))
    board.add_item(8, 9, Item(type='unit', job='winger', team='red', health=10))
    board.add_item(7, 9, Item(type='unit', job='healer', team='red', health=10))
    board.add_item(6, 9, Item(type='unit', job='wizard', team='red', health=10))

    board.add_item(0, 0, Item(type='unit', job='knight', team='blue', health=10))
    board.add_item(1, 0, Item(type='unit', job='winger', team='blue', health=10))
    board.add_item(2, 0, Item(type='unit', job='healer', team='blue', health=10))
    board.add_item(3, 0, Item(type='unit', job='smallrus', team='blue', health=10))
    return board

@rendered_with("main/game_board.html")
@allow_http("GET")
def room(request, room_id):
    room = get_object_or_404(GameRoom, pk=room_id)
    board = room.load_board()    
    rows = range(board.size()[0])
    cols = range(board.size()[1])
    return {
        'room': room, 'board': board,
        'rows': rows,
        'cols': cols,
        }

@allow_http("GET")
def room_json(request, room_id):
    room = get_object_or_404(GameRoom, pk=room_id)
    board = room.board.encode("ascii")
    return HttpResponse(board, mimetype="application/json")

@csrf_exempt
@allow_http("POST")
def room_ready(request, room_id):
    room = get_object_or_404(GameRoom, pk=room_id)

    name = request.COOKIES['user']
    user = User.objects.get(username=name)
    room.ready.add(user)

    if room.ready.count() == 2:
        type = "move"
        if not room.status:
            this_team = "blue"
        else:
            if "blue" in room.status:
                team = "blue"
                next_team = "red"
            else:
                team = "red"
                next_team = "blue"
            this_team = next_team
        
            if "act" not in room.status:
                board = room.load_board()
                for coords in board.units(team):
                    if board.adjacent_units(coords[0], coords[1], next_team):
                        type = "act"
                        this_team = team

        room.ready.clear()

        room.status = "%s: %s" % (type, this_team)
        room.save()

        announce_turn(room, this_team, type)
    return HttpResponse("ok")

@csrf_exempt
@allow_http("POST")
def room_move(request, room_id):
    room = get_object_or_404(GameRoom, pk=room_id)

    name = request.COOKIES['user']

    row = int(request.POST['r0'])
    col = int(request.POST['c0'])

    board = room.load_board()
    item = board.pop_item(row, col)

    row1 = int(request.POST['r1'])
    col1 = int(request.POST['c1'])

    board.add_item(row1, col1, item)
    room.save_board(board)
    room.save()

    announce_move(room, (row, col), (row1, col1))
    return HttpResponse("ok")

@csrf_exempt
@allow_http("POST")
def room_act(request, room_id):
    room = get_object_or_404(GameRoom, pk=room_id)

    name = request.COOKIES['user']

    row = int(request.POST['r1'])
    col = int(request.POST['c1'])
    action = request.POST['action']
    assert action == "attack"

    srcrow = int(request.POST['r0'])
    srccol = int(request.POST['c0'])

    board = room.load_board()
    assert board.has_item(srcrow, srccol)
    assert board.has_item(row, col)

    actor = board.get_item(srcrow, srccol)
    target = board.get_item(row, col)

    health = int(target.data['health']) - 4
    if health < 0:
        board.pop_item(row, col)
    target.data['health'] = health

    room.save_board(board)
    room.save()

    announce_action(room, action, (srcrow, srccol), (row, col))
    return HttpResponse("ok")

def announce_action(room, action, from_, to):
    payload = {'msgtype': 'act'}
    payload['from'] = {'row': from_[0], 'col': from_[1]}
    payload['to'] = {'row': to[0], 'col': to[1]}
    payload['action'] = action
    payload = simplejson.dumps(payload)

    payload = urllib.quote(payload)
    channel = str(room.pk)
    url = "%s/rest/publish?secret=%s&channel_name=%s&payload=%s" % (
        settings.HOOKBOX_URL,
        "altoids",
        channel,
        payload)
    GET(url, async=True)

def announce_move(room, from_, to):
    payload = {'msgtype': 'move'}
    payload['from'] = {'row': from_[0], 'col': from_[1]}
    payload['to'] = {'row': to[0], 'col': to[1]}

    payload = simplejson.dumps(payload)
    payload = urllib.quote(payload)
    channel = str(room.pk)
    url = "%s/rest/publish?secret=%s&channel_name=%s&payload=%s" % (
        settings.HOOKBOX_URL,
        "altoids",
        channel,
        payload)
    GET(url, async=True)

def announce_turn(room, team, type):
    payload = {'msgtype': "turnchange",
               'turntype': type,
               'team': team}

    payload['board'] = room.board.encode("ascii")
    payload = simplejson.dumps(payload)
    payload = urllib.quote(payload)

    channel = str(room.pk)
    url = "%s/rest/publish?secret=%s&channel_name=%s&payload=%s" % (
        settings.HOOKBOX_URL,
        "altoids",
        channel,
        payload)
    GET(url, async=True)

@allow_http("POST")
def create_room(request):
    room = GameRoom()
    board = start_board()
    room.save_board(board)
    room.save()
    return redirect(room.get_absolute_url())

@rendered_with("main/room_index.html")
@allow_http("GET", "POST")
def room_index(request):
    if request.method == "POST":
        return create_room(request)
    rooms = GameRoom.objects.all()
    return {'rooms': rooms}

