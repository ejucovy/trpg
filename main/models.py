from django.db import models
from django.contrib.auth.models import User
from django.utils import simplejson
from django.contrib.admin import site

class GameRoom(models.Model):
    players = models.ManyToManyField(User)
    board = models.TextField()
    ready = models.ManyToManyField(User, related_name='ready_rooms')
    status = models.TextField()
    board_type = models.TextField()
    present = models.ManyToManyField(User, related_name='present_rooms')

    @models.permalink
    def get_absolute_url(self):
        return ('game-view', [str(self.pk)])

    @models.permalink
    def board_json_url(self):
        return ('game-json', [str(self.pk)])

    def num_players(self):
        return self.players.count()

    @property
    def BoardClass(self):
        if self.board_type == "checkers":
            return CheckersBoard
        return Board

    def start_board(self):
        board = self.BoardClass()
        board.start_board()
        return board

    def load_board(self):
        return self.BoardClass.load(self.board.encode("ascii"))

    def save_board(self, board):
        self.board = board.dump()

class UserTeam(models.Model):
    user = models.ForeignKey(User)
    game = models.ForeignKey(GameRoom)
    team = models.TextField()

site.register(GameRoom)

class Item(object):
    def __init__(self, **kw):
        self.data = kw

class CheckersBoard(object):
    def __init__(self):
        self.grid = {}

    def game_specific_head(self):
        return """
<script type="text/javascript">
    $(window).load(function() {
      $("tr:even td:even, tr:odd td:odd").css("background-color", "pink");
      $("tr:even td:odd, tr:odd td:even").css("background-color", "lightblue");
    });
</script>
"""

    def size(self):
        return (8, 8)

    def start_board(self):
        for j in range(0, 3):
            for i in range(j % 2, 8, 2):
                self.add_item(j, i, Item(type="pawn", team="red"))
        for j in range(5, 8):
            for i in range(j % 2, 8, 2):
                self.add_item(j, i, Item(type="pawn", team="blue"))

    def describe_turn(self, status):
        if "red" in status:
            if "jump" in status:
                team = "red"
                direction = 1
                jumper = eval(status.split(":")[-1])
                movable_coords = [jumper]
            else:
                team = "blue"
                direction = -1
                movable_coords = self.grid.keys()
        else:
            if "jump" in status:
                team = "blue"
                direction = -1
                jumper = eval(status.split(":")[-1])
                movable_coords = [jumper]
            else:
                team = "red"
                direction = 1
                movable_coords = self.grid.keys()
        
        status = "%s: move" % team
        available_moves = {}
        for coords in movable_coords:
            item = self.grid[coords]
            if item.data.get("team") != team:
                continue
            available_moves.setdefault("[%d, %d]" % coords, [])
            for i in (-1, 1):
                possibility = (coords[0] + direction, coords[1] + i)
                if possibility in self.grid:
                    if self.grid[possibility].data.get("team") == team:
                        continue
                    beyond = (possibility[0] + direction, possibility[1] + i)
                    if beyond in self.grid:
                        continue
                    available_moves["[%d, %d]" % coords].append(beyond)
                    continue
                available_moves["[%d, %d]" % coords].append(possibility)
        if not sum(True for i in available_moves.values() if i):
            # if no available moves, switch to other team
            return self.describe_turn(status)

        return (team, status, "move", available_moves)

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

class Board(object):
    def __init__(self):
        self.grid = {}

    def game_specific_head(self):
        return """
<script type="text/javascript">
    $(window).load(function() {
      $("td").css("background-image", "url(/static/images/grass.jpg)");
    });
</script>
"""

    def size(self):
        return (10, 10)

    def in_range(self, x, y):
        return x > -1 and x < self.size()[0] \
            and y > -1 and y < self.size()[1]

    def describe_turn(self, status):
        """
        Return (team, status, available_moves)
        """
        type = "move"
        if not status:
            this_team = "blue"
        else:
            if "blue" in status:
                team = "blue"
                next_team = "red"
            else:
                team = "red"
                next_team = "blue"
            this_team = next_team
        
            if "act" not in status:
                for coords in self.units(team):
                    if self.adjacent_units(coords[0], coords[1], next_team):
                        type = "act"
                        this_team = team

        available_moves = {}
        if type == "move":
            for coords in self.units(this_team):
                unit = self.get_item(*coords)
                mp = int(unit.data["move"])
                for x in range(coords[0]-mp, coords[0]+mp+1):
                    for y in range(coords[1]-mp, coords[1]+mp+1):
                        if self.in_range(x, y) and not self.has_item(x, y):
                            available_moves.setdefault("[%d, %d]" % coords, []).append((x, y))

        status = "%s: %s" % (type, this_team)
        return (this_team, status, type, available_moves)
        

    def start_board(self):
        board = self
        board.add_item(1, 1, Item(type='rock', height=3))
        board.add_item(2, 2, Item(type='rock', height=3))
        board.add_item(4, 4, Item(type='rock', height=3))
        board.add_item(2, 5, Item(type='rock', height=3))
        board.add_item(5, 4, Item(type='rock', height=3))
        
        board.add_item(9, 9, Item(type='unit', job='knight', team='red', health=10, move=2))
        board.add_item(8, 9, Item(type='unit', job='winger', team='red', health=10, move=4))
        board.add_item(7, 9, Item(type='unit', job='healer', team='red', health=10, move=3))
        board.add_item(6, 9, Item(type='unit', job='wizard', team='red', health=10, move=2))
        
        board.add_item(0, 0, Item(type='unit', job='knight', team='blue', health=10, move=2))
        board.add_item(1, 0, Item(type='unit', job='winger', team='blue', health=10, move=4))
        board.add_item(2, 0, Item(type='unit', job='healer', team='blue', health=10, move=3))
        board.add_item(3, 0, Item(type='unit', job='smallrus', team='blue', health=10, move=3))
        
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
