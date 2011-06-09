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
    vs_cpu = models.BooleanField(default=False)

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
        elif self.board_type == "tactics":
            return TacticsBoard
        return BaseBoard

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

class Item(object):
    def __init__(self, **kw):
        self.data = kw

class BaseBoard(object):
    """
    Provides common functionality used by all game types.
    Documents per-game custom functionality that must be implemented.
    Implements a trivial sample game if not subclassed.
    """

    def __init__(self):
        self.grid = {}

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
            copy = dict()
            for key, val in data[coord].items():
                copy[str(key)] = val
            item = Item(**copy)
            board.add_item(x, y, item)
        return board

    def dump(self):
        data = {}
        for (x, y) in self.grid:
            item = self.grid[(x, y)]
            data['(%s, %s)' % (x, y)] = item.data
        return simplejson.dumps(data)
    
    def game_specific_head(self):
        """
        Games can provide extra HTML to provide,
        e.g. custom CSS or Javascript to insert.
        """
        return """
<style type="text/css">
  div.sprite[data-team="red"][data-type="unit"] {
    background-image: url(/static/images/checkers/red.png);
  }
  div.sprite[data-team="blue"][data-type="unit"] {
    background-image: url(/static/images/checkers/black.png);
  }
</style>
"""
        
    def size(self):
        """
        Games should provide a (rows, cols) tuple.
        Theoretically this could be stored statefully
        in the board's JSON dump; at the moment it's 
        hardcoded for both game types that have been
        implemented.
        """
        return (10, 10)

    def start_board(self):
        """
        Games should perform any initial setup they need,
        like adding the team's units in the proper places.
        """
        self.add_item(0, 0, Item(team="red", type="unit"))
        self.add_item(9, 9, Item(team="blue", type="unit"))

    def next_status(self, status):
        """
        Calculate the next status (a string, persisted in
        the GameRoom instance) based on the current status.
        """
        return "no status"
        
    def describe_turn(self, status):
        """
        Describe the parameters and potentialities of the next
        turn that should occur, based on the current status.
        """
        import random
        next_team = random.choice(["blue", "red"])
        status = "no status"
        turn_type = "move"

        for coords in self.grid:
            if self.get_item(*coords).data.get("team") == next_team:
                break
        while True:
            row = random.choice(range(self.size()[0]))
            col = random.choice(range(self.size()[1]))
            if not self.has_item(row, col):
                break

        available_actions = {
            'move': {
                "[%d, %d]" % coords: [(row, col)],
                }
            }
        return (next_team, status, turn_type, available_actions)

    def act(self, room, 
            actor_row, actor_col, target_row, target_col,
            action_type):
        """
        Perform an action from one of the players.
        """
        self.add_item(target_row, target_col,
                      self.pop_item(actor_row, actor_col))

class CheckersBoard(BaseBoard):

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

    def next_status(self, status):
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
            for i in (-1, 1):
                possibility = (coords[0] + direction, coords[1] + i)
                if possibility in self.grid:
                    if self.grid[possibility].data.get("team") == team:
                        continue
                    beyond = (possibility[0] + direction, possibility[1] + i)
                    if beyond in self.grid:
                        continue
                    available_moves.setdefault("[%d, %d]" % coords, []).append(beyond)
                    continue
                available_moves.setdefault("[%d, %d]" % coords, []).append(possibility)
        if not sum(True for i in available_moves.values() if i):
            # if no available moves, switch to other team
            return self.next_status(status)
        return status

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
            for i in (-1, 1):
                possibility = (coords[0] + direction, coords[1] + i)
                if possibility in self.grid:
                    if self.grid[possibility].data.get("team") == team:
                        continue
                    beyond = (possibility[0] + direction, possibility[1] + i)
                    if beyond in self.grid:
                        continue
                    available_moves.setdefault("[%d, %d]" % coords, []).append(beyond)
                    continue
                available_moves.setdefault("[%d, %d]" % coords, []).append(possibility)
        if not sum(True for i in available_moves.values() if i):
            # if no available moves, switch to other team
            return self.describe_turn(status)

        return (team, status, "move", dict(move=available_moves))

    def act(self, room, row, col, row1, col1, action_type):
        if action_type == 'move':
            item = self.pop_item(row, col)
            self.add_item(row1, col1, item)
            
            # if it's a jump, change the status and eliminate the jumpee
            if abs(row1 - row) == 2 and abs(col1 - col) == 2:
                team, action = room.status.split(":")
                room.status = "%s: jump:(%s, %s)" % (team, row1, col1)
                rr = row - (row - row1) / 2
                cc = col - (col - col1) / 2
                board.pop_item(rr, cc)

class TacticsBoard(BaseBoard):

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

    def act(self, room, row, col, row1, col1, action_type):
        if action_type == 'move':
            item = self.pop_item(row, col)
            self.add_item(row1, col1, item)

    def start_board(self):
        board = self
        board.add_item(1, 1, Item(type='rock', height=3))
        board.add_item(2, 2, Item(type='rock', height=3))
        board.add_item(4, 4, Item(type='rock', height=3))
        board.add_item(2, 5, Item(type='rock', height=3))
        board.add_item(5, 4, Item(type='rock', height=3))
        
        board.add_item(9, 9, Item(type='unit', job='knight', team='red', health=14, move=2, range=1))
        board.add_item(8, 9, Item(type='unit', job='winger', team='red', health=10, move=4, range=1))
        board.add_item(7, 9, Item(type='unit', job='healer', team='red', health=6, move=3, range=1))
        board.add_item(6, 9, Item(type='unit', job='wizard', team='red', health=10, move=2, range=3))
        
        board.add_item(0, 0, Item(type='unit', job='knight', team='blue', health=14, move=2, range=1))
        board.add_item(1, 0, Item(type='unit', job='winger', team='blue', health=10, move=4, range=1))
        board.add_item(2, 0, Item(type='unit', job='healer', team='blue', health=6, move=3, range=1))
        board.add_item(3, 0, Item(type='unit', job='smallrus', team='blue', health=7, move=3, range=1))

    def next_status(self, status):
        if not status:
            return "move: blue"

        if "blue" in status:
            team = "blue"
            next_team = "red"
        else:
            team = "red"
            next_team = "blue"
        this_team = next_team
        
        type = "move"
        if "act" not in status:
            for coords in self.units(team):
                radius = int(self.get_item(*coords).data.get("range", 1))
                enemies = self.adjacent_units(coords[0], coords[1], next_team, radius)
                if enemies:
                    type = "act"
                    this_team = team
                    break

        status = "%s: %s" % (type, this_team)
        return status

    def describe_turn(self, status):
        if "act" in status:
            type = "act"
        else:
            type = "move"
        if not status:
            this_team = "blue"
        else:
            if "blue" in status:
                this_team = "blue"
                next_team = "red"
            else:
                this_team = "red"
                next_team = "blue"
        
        available_actions = {}
        if type == "move":
            available_moves = {}
            for coords in self.units(this_team):
                unit = self.get_item(*coords)
                mp = int(unit.data["move"])
                for x in range(coords[0]-mp, coords[0]+mp+1):
                    for y in range(coords[1]-mp, coords[1]+mp+1):
                        if self.in_range(x, y) and not self.has_item(x, y):
                            available_moves.setdefault("[%d, %d]" % coords, []).append((x, y))
            available_actions['move'] = available_moves
        elif type == "act":
            available_attack = {}
            for coords in self.units(this_team):
                radius = int(self.get_item(*coords).data.get("range", 1))
                enemies = self.adjacent_units(coords[0], coords[1], next_team, radius)
                for enemy in enemies:
                    available_attack.setdefault(
                        "[%s, %s]" % coords, []).append(enemy)
            available_actions['attack'] = available_attack

        status = "%s: %s" % (type, this_team)
        return (this_team, status, type, available_actions)
        
        
    def in_range(self, x, y):
        return x > -1 and x < self.size()[0] \
            and y > -1 and y < self.size()[1]

    def adjacent_units(self, x, y, team, radius=1):
        units = []
        for _x in range(x - radius, x + radius + 1):
            for _y in range(y - radius, y + radius + 1):
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

if __name__ == '__main__':
    grid = {
        '(2, 5)': {'type': 'knight', 'color': 'red', 'health': 50},
        '(1, 7)': {'type': 'rock', 'height': 2},
        }
    
    data = simplejson.dumps(grid)
    board = BaseBoard.load(data)
    board.pop_item(1, 7)
    dump = board.dump()
    BaseBoard.load(dump)
