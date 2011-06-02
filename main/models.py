from django.db import models
from django.contrib.auth.models import User
from django.utils import simplejson

class GameRoom(models.Model):
    players = models.ManyToManyField(User)
    board = models.TextField()
    ready = models.ManyToManyField(User, related_name='active_rooms')
    status = models.TextField()

    @models.permalink
    def get_absolute_url(self):
        return ('game-view', [str(self.pk)])

    @models.permalink
    def board_json_url(self):
        return ('game-json', [str(self.pk)])

    def num_players(self):
        return self.players.count()

    def load_board(self):
        return Board.load(self.board.encode("ascii"))

    def save_board(self, board):
        self.board = board.dump()

class Item(object):
    def __init__(self, **kw):
        self.data = kw

class Board(object):
    def __init__(self):
        self.grid = {}

    def size(self):
        return (10, 10)

    def in_range(self, x, y):
        return x > -1 and x < self.size()[0] \
            and y > -1 and y < self.size()[1]

    def adjacent_units(self, x, y, team):
        units = []
        for _x in (x-1, x, x+1):
            for _y in (y-1, y, y+1):
                if not self.has_item(_x, _y):
                    continue
                item = self.grid[(_x, _y)]
                if item.data.get("type") != "unit":
                    continue
                if item.data.get("team") != team:
                    continue
                units.append((_x, _y))
        return units

    def units(self, team):
        units = []
        for coords, item in self.grid.items():
            if item.data.get("type") != "unit":
                continue
            if item.data.get("team") != team:
                continue
            units.append(coords)
        return units

    def get_item(self, x, y):
        return self.grid[(x, y)]

    def has_item(self, x, y):
        return (x, y) in self.grid
        
    def add_item(self, x, y, item):
        self.grid[(x, y)] = item

    def pop_item(self, x, y):
        item = self.grid[(x, y)]
        del self.grid[(x, y)]
        return item

    @classmethod
    def load(cls, json):
        data = simplejson.loads(json)
        board = cls()
        for coord in data:
            x, y = eval(coord)
            item = Item(**data[coord])
            board.add_item(x, y, item)
        return board

    def dump(self):
        data = {}
        for (x, y) in self.grid:
            item = self.grid[(x, y)]
            data['(%s, %s)' % (x, y)] = item.data
        return simplejson.dumps(data)

if __name__ == '__main__':
    grid = {
        '(2, 5)': {'type': 'knight', 'color': 'red', 'health': 50},
        '(1, 7)': {'type': 'rock', 'height': 2},
        }
    
    data = simplejson.dumps(grid)
    board = Board.load(data)
    board.pop_item(1, 7)
    dump = board.dump()
    Board.load(dump)
