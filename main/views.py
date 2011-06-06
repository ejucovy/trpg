from django.http import HttpResponseRedirect as redirect, HttpResponse
from django.shortcuts import get_object_or_404
from djangohelpers.lib import rendered_with, allow_http
from bagels.main.models import GameRoom, Board, Item, UserTeam
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from restclient import GET
import random
import urllib
from django.conf import settings
from django.utils import simplejson
from bagels.main import i18n

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
        'game_specific_head': board.game_specific_head(),
        }

@allow_http("GET")
def game_user_team(request, room_id, username):
    team = get_object_or_404(UserTeam, game__id=room_id, user__username=username)
    return HttpResponse(team.team, mimetype="text/plain")
    
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
        board = room.load_board()
        team, status, type, available_moves = board.next_turn(room.status)

        room.ready.clear()

        room.status = status
        room.save()

        extra_data = dict(available_moves=available_moves)
        announce_turn(room, team, type, extra_data)

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

    # @@todo checkers logic
    if abs(row1-row) == 2 and abs(col1-col) == 2:
        team, action = room.status.split(":")
        room.status = "%s: jump:(%s, %s)" % (team, row1, col1)
        rr = row - (row-row1) / 2
        cc = col - (col-col1) / 2
        board.pop_item(rr, cc)

    room.save_board(board)
    room.save()

    announce_move(room, (row, col), (row1, col1), name)
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

    actor_before = dict(actor.data)
    target_before = dict(target.data)
    
    health = int(target.data['health']) - 4
    if health < 1:
        board.pop_item(row, col)
    target.data['health'] = health

    msgs = i18n.attack(actor, target, 
                       actor_before, target_before)
    room.save_board(board)
    room.save()

    announce_action(room, action, 
                    (srcrow, srccol), (row, col), 
                    name, msgs)
    return HttpResponse("ok")

def announce_action(room, action, from_, to, 
                    username, msgs=[[],[]]):
    payload = {'msgtype': 'act'}
    payload['from'] = {'row': from_[0], 'col': from_[1]}
    payload['to'] = {'row': to[0], 'col': to[1]}
    payload['action'] = action
    payload['acting_user'] = username

    if msgs[0]:
        payload['chatBefore'] = msgs[0]
    if msgs[1]:
        payload['chatAfter'] = msgs[1]

    payload = simplejson.dumps(payload)

    payload = urllib.quote(payload)
    channel = str(room.pk)
    url = "%s/rest/publish?secret=%s&channel_name=%s&user=%s&payload=%s" % (
        settings.HOOKBOX_URL,
        "altoids",
        channel,
        username,
        payload)
    GET(url, async=True)

def announce_move(room, from_, to, username):
    payload = {'msgtype': 'move'}
    payload['from'] = {'row': from_[0], 'col': from_[1]}
    payload['to'] = {'row': to[0], 'col': to[1]}
    payload['acting_user'] = username

    payload = simplejson.dumps(payload)
    payload = urllib.quote(payload)
    channel = str(room.pk)
    url = "%s/rest/publish?secret=%s&channel_name=%s&user=%s&payload=%s" % (
        settings.HOOKBOX_URL,
        "altoids",
        channel,
        username,
        payload)
    GET(url, async=True)

def announce_turn(room, team, type, extra_data={}):
    payload = {'msgtype': "turnchange",
               'turntype': type,
               'team': team}

    payload['board'] = room.board.encode("ascii")
    for item in extra_data:
        payload[item] = extra_data[item]

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
    room = GameRoom(board_type=request.POST['gametype'])
    board = room.start_board()
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

