from django.http import HttpResponseRedirect as redirect, HttpResponse, HttpRequest
from django.shortcuts import get_object_or_404
from djangohelpers.lib import rendered_with, allow_http
from bagels.main.models import GameRoom, Item, UserTeam
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

    if user in room.ready.all():
        return HttpResponse("ok")

    room.ready.add(user)
    if room.ready.count() == 2 or (room.ready.count() == 1 and room.vs_cpu):
        board = room.load_board()
        team, status, type, available_actions = board.describe_turn(room.status)

        if room.vs_cpu:
            if UserTeam.objects.get(user=room.ready.all()[0],
                                    game=room).team == team:
                # the human player's turn
                extra_data = dict(available_actions=available_actions)
                announce_turn(room, team, type, extra_data)
                return HttpResponse("ok")
            else:
                # the robot's turn
                action = random.choice(available_actions.keys())
                choices = available_actions[action]
                choice = random.choice(choices.keys())
                to_ = random.choice(choices[choice])
                from_ = eval(choice)
                fake_request = HttpRequest()
                fake_request.method = "POST"
                fake_request.POST['r0'] = from_[0]
                fake_request.POST['c0'] = from_[1]
                fake_request.POST['r1'] = to_[0]
                fake_request.POST['c1'] = to_[1]
                if action == "attack":
                    fake_request.POST['actionType'] = 'attack'
                    room_act(fake_request, room.id)
                elif action == "move":
                    fake_request.POST['actionType'] = 'move'
                    room_move(fake_request, room.id)

                return HttpResponse("ok")

        extra_data = dict(available_actions=available_actions)
        announce_turn(room, team, type, extra_data)

    return HttpResponse("ok")

@csrf_exempt
@allow_http("POST")
def room_move(request, room_id):
    room = get_object_or_404(GameRoom, pk=room_id)

    row = int(request.POST['r0'])
    col = int(request.POST['c0'])

    board = room.load_board()

    team = board.get_item(row, col).data.get("team")

    row1 = int(request.POST['r1'])
    col1 = int(request.POST['c1'])

    action_type = request.POST['actionType']

    board.act(room, row, col, row1, col1, action_type)

    room.save_board(board)

    room.status = board.next_status(room.status)

    room.ready.clear()
    room.save()

    announce_move(room, (row, col), (row1, col1), team)
    return HttpResponse("ok")

@csrf_exempt
@allow_http("POST")
def room_act(request, room_id):
    room = get_object_or_404(GameRoom, pk=room_id)

    row = int(request.POST['r1'])
    col = int(request.POST['c1'])
    action_type = request.POST['actionType']
    assert action_type == "attack"

    srcrow = int(request.POST['r0'])
    srccol = int(request.POST['c0'])

    board = room.load_board()
    assert board.has_item(srcrow, srccol)
    assert board.has_item(row, col)

    actor = board.get_item(srcrow, srccol)
    target = board.get_item(row, col)

    team = actor.data.get("team")

    actor_before = dict(actor.data)
    target_before = dict(target.data)
    
    health = int(target.data['health']) - 4
    if health < 1:
        board.pop_item(row, col)
    target.data['health'] = health

    msgs = i18n.attack(actor, target, 
                       actor_before, target_before)
    room.save_board(board)
    room.status = board.next_status(room.status)
    room.ready.clear()
    room.save()

    announce_action(room, action_type, 
                    (srcrow, srccol), (row, col), 
                    team, msgs)
    return HttpResponse("ok")

def announce_action(room, action, from_, to, 
                    team, msgs=[[],[]]):
    payload = {'msgtype': 'act'}
    payload['from'] = {'row': from_[0], 'col': from_[1]}
    payload['to'] = {'row': to[0], 'col': to[1]}
    payload['action'] = action
    payload['acting_team'] = team

    if msgs[0]:
        payload['chatBefore'] = msgs[0]
    if msgs[1]:
        payload['chatAfter'] = msgs[1]

    payload = simplejson.dumps(payload)

    payload = urllib.quote(payload)
    channel = str(room.pk)
    url = "%s/rest/publish?secret=%s&channel_name=%s&payload=%s" % (
        settings.HOOKBOX_URL,
        "altoids",
        channel,
        payload)
    GET(url, async=True)

def announce_move(room, from_, to, team):
    payload = {'msgtype': 'move'}
    payload['from'] = {'row': from_[0], 'col': from_[1]}
    payload['to'] = {'row': to[0], 'col': to[1]}
    payload['acting_team'] = team

    payload = simplejson.dumps(payload)
    payload = urllib.quote(payload)
    channel = str(room.pk)
    url = "%s/rest/publish?secret=%s&channel_name=%s&payload=%s" % (
        settings.HOOKBOX_URL,
        "altoids",
        channel,
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
    vs_cpu = request.POST.get("players") == "cpu"
    room = GameRoom(board_type=request.POST['gametype'], status="starting", vs_cpu=vs_cpu)
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

