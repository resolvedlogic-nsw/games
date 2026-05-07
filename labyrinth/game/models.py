import json
import random
from collections import deque
from django.db import models
import string

# ─── Tile connectivity ────────────────────────────────────────────────────────
BASE_EXITS = {
    'i': {0, 2},          # N, S
    'l': {0, 1},          # N, E
    't': {0, 1, 2},       # N, E, S (Top, Right, Bottom - matches your image perfectly)
}

def rotate_exits(exits, rotation):
    """Rotate a set of exits (0=N,1=E,2=S,3=W) clockwise by rotation*90 degrees."""
    return {(e + rotation) % 4 for e in exits}

def tile_exits(shape, rotation):
    return rotate_exits(BASE_EXITS[shape], rotation)

OPPOSITE = {0: 2, 1: 3, 2: 0, 3: 1}   # N<->S, E<->W
DIR_DELTA = {0: (-1, 0), 1: (0, 1), 2: (1, 0), 3: (0, -1)}  # row,col

class Game(models.Model):
    room_code = models.CharField(max_length=6, unique=True, null=True, blank=True)
    mode = models.CharField(max_length=20, default='pass_and_play') # 'pass_and_play' or 'online'
    phase = models.CharField(max_length=20, default='lobby') # 'lobby', 'playing', 'over'
    theme = models.CharField(max_length=20, default='classic') # 'classic' or 'pokemon'
    tokens_to_win = models.IntegerField(default=12)
    seq = models.IntegerField(default=0) # Increments on every move to trigger polls
    
    tiles_json     = models.TextField(default='[]')
    spare_json     = models.TextField(default='{}')
    players_json   = models.TextField(default='[]')
    current_turn   = models.IntegerField(default=0)
    num_players    = models.IntegerField(default=2)
    last_push_json = models.TextField(default='null')
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    @classmethod
    def generate_room_code(cls):
        """Generates a random 4-letter uppercase code"""
        while True:
            code = ''.join(random.choices(string.ascii_uppercase, k=4))
            if not cls.objects.filter(room_code=code).exists():
                return code

    # ── JSON helpers ──────────────────────────────────────────────────────────
    @property
    def tiles(self): return json.loads(self.tiles_json)
    @tiles.setter
    def tiles(self, value): self.tiles_json = json.dumps(value)

    @property
    def spare(self): return json.loads(self.spare_json)
    @spare.setter
    def spare(self, value): self.spare_json = json.dumps(value)

    @property
    def players(self): return json.loads(self.players_json)
    @players.setter
    def players(self, value): self.players_json = json.dumps(value)

    @property
    def last_push(self): return json.loads(self.last_push_json)
    @last_push.setter
    def last_push(self, value): self.last_push_json = json.dumps(value)

    # ── Board initialisation ──────────────────────────────────────────────────
    @classmethod
    def new_game(cls, num_players=2, tokens_to_win=None, theme='classic', mode='pass_and_play'):
        game = cls(num_players=num_players, theme=theme, mode=mode)
        if mode == 'online':
            game.room_code = cls.generate_room_code()
            
        if tokens_to_win is None:
            tokens_to_win = 24 // num_players
        game.tokens_to_win = tokens_to_win
        
        deck = game._initialise_board()
        if mode == 'pass_and_play':
            game._initialise_players(num_players, deck, tokens_to_win, theme)
            game.phase = 'playing'
        else:
            game.players = [{'deck': deck}] 
        
        game.save()
        return game

    def _make_tile(self, shape, rotation=0, character=None, fixed=False):
        return {'shape': shape, 'rotation': rotation, 'character': character, 'fixed': fixed}

    def _initialise_board(self):
        fixed_layout = {
            (0, 0): ('l', 1), (0, 2): ('t', 1), (0, 4): ('t', 1), (0, 6): ('l', 2),
            (2, 0): ('t', 0), (2, 2): ('t', 0), (2, 4): ('t', 1), (2, 6): ('t', 2),
            (4, 0): ('t', 0), (4, 2): ('t', 3), (4, 4): ('t', 2), (4, 6): ('t', 2),
            (6, 0): ('l', 0), (6, 2): ('t', 3), (6, 4): ('t', 3), (6, 6): ('l', 3),
        }
        all_chars = list(range(1, 38))
        random.shuffle(all_chars)
        char_ids = all_chars[:24]
        char_iter = iter(char_ids)

        movable_pool = []
        for _ in range(12): movable_pool.append(self._make_tile('i', 0))
        for _ in range(10): movable_pool.append(self._make_tile('l', 0))
        for _ in range(6):  movable_pool.append(self._make_tile('l', 0, character=next(char_iter)))
        for _ in range(6):  movable_pool.append(self._make_tile('t', 0, character=next(char_iter)))
        for t in movable_pool: t['rotation'] = random.randint(0, 3)
        random.shuffle(movable_pool)

        spare_tile = movable_pool.pop()
        spare_tile['rotation'] = random.randint(0, 3)
        movable_iter = iter(movable_pool)

        grid = []
        for row in range(7):
            grid_row = []
            for col in range(7):
                if row % 2 == 0 and col % 2 == 0:
                    shape, rot = fixed_layout[(row, col)]
                    char = next(char_iter) if shape == 't' else None
                    grid_row.append(self._make_tile(shape, rot, character=char, fixed=True))
                else:
                    grid_row.append(next(movable_iter))
            grid.append(grid_row)

        self.tiles = grid
        self.spare = spare_tile
        return char_ids   

    def _initialise_players(self, num_players, deck, tokens_to_win=None, theme='classic'):
        corners = [(0, 0), (0, 6), (6, 6), (6, 0)]
        if theme == 'pokemon':
            colors  = ['#e74c3c', '#3498db', '#f39c12', '#9b59b6']
        else:
            colors  = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12']
            
        names   = ['Red', 'Blue', 'Green' if theme != 'pokemon' else 'Purple', 'Yellow']
        random.shuffle(deck)
        
        max_possible = len(deck) // num_players
        cards_per_player = max_possible if (tokens_to_win is None or tokens_to_win > max_possible) else tokens_to_win

        players = []
        for i in range(min(num_players, 4)):
            player_deck = deck[i * cards_per_player : (i + 1) * cards_per_player]
            first_target = player_deck.pop(0) if player_deck else None
            
            players.append({
                'id': i,
                'name': names[i],
                'color': colors[i],
                'row': corners[i][0],
                'col': corners[i][1],
                'deck': player_deck,
                'current_target': first_target,
                'score': 0,
                'total_tokens': cards_per_player 
            })
        self.players = players

    # ── Push logic ────────────────────────────────────────────────────────────
    def push_tile(self, direction, index):
        if self.phase != 'playing': return False
        lp = self.last_push
        if lp:
            reverse = {'left': 'right', 'right': 'left', 'top': 'bottom', 'bottom': 'top'}
            if reverse[direction] == lp['direction'] and index == lp['index']:
                return False

        grid = self.tiles
        spare = self.spare
        players = self.players

        if direction == 'left':
            row = index
            ejected = grid[row][-1]
            grid[row] = [spare] + grid[row][:-1]
            new_spare = ejected
            for p in players:
                if p['row'] == row:
                    p['col'] = p['col'] + 1 if p['col'] < 6 else 0
        elif direction == 'right':
            row = index
            ejected = grid[row][0]
            grid[row] = grid[row][1:] + [spare]
            new_spare = ejected
            for p in players:
                if p['row'] == row:
                    p['col'] = p['col'] - 1 if p['col'] > 0 else 6
        elif direction == 'top':
            col = index
            ejected = grid[6][col]
            for r in range(6, 0, -1): grid[r][col] = grid[r - 1][col]
            grid[0][col] = spare
            new_spare = ejected
            for p in players:
                if p['col'] == col:
                    p['row'] = p['row'] + 1 if p['row'] < 6 else 0
        elif direction == 'bottom':
            col = index
            ejected = grid[0][col]
            for r in range(0, 6): grid[r][col] = grid[r + 1][col]
            grid[6][col] = spare
            new_spare = ejected
            for p in players:
                if p['col'] == col:
                    p['row'] = p['row'] - 1 if p['row'] > 0 else 6

        self.tiles = grid
        self.spare = new_spare
        self.players = players
        self.last_push = {'direction': direction, 'index': index}
        self.seq += 1
        self.save()
        return True

    # ── BFS reachability ──────────────────────────────────────────────────────
    def reachable_cells(self, start_row, start_col):
        grid = self.tiles
        visited = set()
        queue = deque([(start_row, start_col)])
        visited.add((start_row, start_col))

        while queue:
            r, c = queue.popleft()
            exits = tile_exits(grid[r][c]['shape'], grid[r][c]['rotation'])
            for d in exits:
                dr, dc = DIR_DELTA[d]
                nr, nc = r + dr, c + dc
                if 0 <= nr < 7 and 0 <= nc < 7 and (nr, nc) not in visited:
                    neighbour_exits = tile_exits(grid[nr][nc]['shape'], grid[nr][nc]['rotation'])
                    if OPPOSITE[d] in neighbour_exits:
                        visited.add((nr, nc))
                        queue.append((nr, nc))
        return visited

    # ── Move player ───────────────────────────────────────────────────────────
    def move_player(self, player_id, target_row, target_col):
        if self.phase != 'playing': return False, "Game over"
        player_id = self.current_turn 
        
        players = self.players
        p = next((x for x in players if x['id'] == player_id), None)
        if p is None: return False, "Player not found"

        reachable = self.reachable_cells(p['row'], p['col'])
        if (target_row, target_col) not in reachable:
            return False, "Cell not reachable"

        p['row'] = target_row
        p['col'] = target_col
        
        target_hit = False
        landed_tile = self.tiles[target_row][target_col]
        
        if landed_tile.get('character') and landed_tile['character'] == p['current_target']:
            p['score'] += 1
            p['current_target'] = p['deck'].pop(0) if p['deck'] else None
            target_hit = True

        player_won = False
        corners = [(0, 0), (0, 6), (6, 6), (6, 0)]
        home_row, home_col = corners[p['id']]
        
        if p['current_target'] is None and p['row'] == home_row and p['col'] == home_col:
            p['winner'] = True
            player_won = True

        self.players = players
        
        if not player_won:
            self.current_turn = (self.current_turn + 1) % self.num_players
        else:
            self.phase = 'over'
            
        self.last_push = None
        self.seq += 1
        self.save()
        
        if player_won: msg = "PLAYER_WON"
        elif target_hit: msg = "TARGET_FOUND"
        else: msg = "Moved"
            
        return True, msg

    def rotate_spare(self):
        if self.phase != 'playing': return
        spare = self.spare
        spare['rotation'] = (spare['rotation'] + 1) % 4
        self.spare = spare
        self.seq += 1
        self.save()

    def get_state_dict(self, player_perspective=None):
        players = self.players
        current_player = players[self.current_turn] if players and self.phase == 'playing' else None

        reachable = []
        if current_player:
            reachable = [list(x) for x in self.reachable_cells(current_player['row'], current_player['col'])]

        safe_players = []
        for p in players:
            if self.mode == 'online' and player_perspective is not None and p.get('id') != player_perspective:
                p_copy = p.copy()
                p_copy['current_target'] = '?' if p_copy.get('current_target') else None
                safe_players.append(p_copy)
            else:
                safe_players.append(p)

        return {
            'game_id': self.pk,
            'room_code': self.room_code,
            'mode': self.mode,
            'phase': self.phase,
            'theme': self.theme,
            'tiles': self.tiles,
            'spare': self.spare,
            'players': safe_players,
            'current_turn': self.current_turn,
            'current_player': current_player,
            'reachable': reachable,
            'last_push': self.last_push,
            'seq': self.seq,
        }