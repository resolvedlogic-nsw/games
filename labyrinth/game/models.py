import json
import random
import string
from collections import deque
from django.db import models


def make_room_code():
    while True:
        code = ''.join(random.choices(string.ascii_uppercase, k=4))
        if not Game.objects.filter(room_code=code).exists():
            return code


BASE_EXITS = {
    'i': {0, 2},
    'l': {0, 1},
    't': {0, 1, 2},
}

def rotate_exits(exits, rotation):
    return {(e + rotation) % 4 for e in exits}

def tile_exits(shape, rotation):
    return rotate_exits(BASE_EXITS[shape], rotation)

OPPOSITE  = {0: 2, 1: 3, 2: 0, 3: 1}
DIR_DELTA = {0: (-1, 0), 1: (0, 1), 2: (1, 0), 3: (0, -1)}
CORNERS   = [(0, 0), (0, 6), (6, 6), (6, 0)]


class Game(models.Model):
    # ── Multiplayer / lobby ───────────────────────────────────────────
    room_code    = models.CharField(max_length=8, unique=True, null=True, blank=True)
    mode         = models.CharField(max_length=20, default='pass_and_play')
    # 'lobby' → waiting for players | 'playing' → game active | 'over' → finished
    phase        = models.CharField(max_length=20, default='playing')
    # Incremented on every state change — clients poll against this
    seq          = models.IntegerField(default=0)

    # ── Theme ─────────────────────────────────────────────────────────
    theme        = models.CharField(max_length=20, default='classic')

    # ── Core game state ───────────────────────────────────────────────
    tiles_json     = models.TextField(default='[]')
    spare_json     = models.TextField(default='{}')
    players_json   = models.TextField(default='[]')
    current_turn   = models.IntegerField(default=0)
    num_players    = models.IntegerField(default=2)
    tokens_to_win  = models.IntegerField(default=12)
    last_push_json = models.TextField(default='null')
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    # ── JSON helpers ──────────────────────────────────────────────────

    @property
    def tiles(self):
        return json.loads(self.tiles_json)

    @tiles.setter
    def tiles(self, v):
        self.tiles_json = json.dumps(v)

    @property
    def spare(self):
        return json.loads(self.spare_json)

    @spare.setter
    def spare(self, v):
        self.spare_json = json.dumps(v)

    @property
    def players(self):
        return json.loads(self.players_json)

    @players.setter
    def players(self, v):
        self.players_json = json.dumps(v)

    @property
    def last_push(self):
        return json.loads(self.last_push_json)

    @last_push.setter
    def last_push(self, v):
        self.last_push_json = json.dumps(v)

    # ── Factory ───────────────────────────────────────────────────────

    @classmethod
    def new_game(cls, num_players=2, tokens_to_win=None, theme='classic', mode='pass_and_play'):
        game = cls(num_players=num_players, theme=theme, mode=mode, phase='playing')
        deck = game._initialise_board()
        game._initialise_players(num_players, deck, tokens_to_win)
        game.seq = 1
        game.save()
        return game

    @classmethod
    def new_lobby(cls, num_players=2, tokens_to_win=None, theme='classic'):
        """Create a game in lobby phase waiting for players to join."""
        game = cls(
            num_players=num_players,
            theme=theme,
            mode='online',
            phase='lobby',
            room_code=None,
        )
        # Generate unique room code
        while True:
            code = ''.join(random.choices(string.ascii_uppercase, k=4))
            if not cls.objects.filter(room_code=code).exists():
                game.room_code = code
                break

        # Store setup params — board is built when host starts the game
        ttw = tokens_to_win or (24 // num_players)
        game.tokens_to_win = ttw
        # Initialise empty players list — filled as players join
        game.players_json = '[]'
        game.tiles_json   = '[]'
        game.spare_json   = '{}'
        game.seq = 1
        game.save()
        return game

    # ── Board setup ───────────────────────────────────────────────────

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
        char_ids  = all_chars[:24]
        char_iter = iter(char_ids)

        movable_pool = []
        for _ in range(12): movable_pool.append(self._make_tile('i', 0))
        for _ in range(10): movable_pool.append(self._make_tile('l', 0))
        for _ in range(6):  movable_pool.append(self._make_tile('l', 0, character=next(char_iter)))
        for _ in range(6):  movable_pool.append(self._make_tile('t', 0, character=next(char_iter)))

        for t in movable_pool:
            t['rotation'] = random.randint(0, 3)
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

        self.tiles  = grid
        self.spare  = spare_tile
        return char_ids

    def _initialise_players(self, num_players, deck, tokens_to_win=None):
        """
        Accepts a pre-built players list (online mode, already has names/colours)
        or builds from scratch (pass-and-play / classic).
        """
        # Classic colours for pass-and-play
        classic_colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12']
        classic_names  = ['Red', 'Blue', 'Green', 'Yellow']

        random.shuffle(deck)
        max_possible   = len(deck) // num_players
        cards_per_player = min(tokens_to_win, max_possible) if tokens_to_win else max_possible
        self.tokens_to_win = cards_per_player

        existing = self.players  # may be pre-filled (online lobby joiners)

        players = []
        for i in range(min(num_players, 4)):
            player_deck  = deck[i * cards_per_player: (i + 1) * cards_per_player]
            first_target = player_deck.pop(0) if player_deck else None

            # Preserve name/colour from lobby join if available
            base = existing[i] if i < len(existing) else {}

            players.append({
                'id':           i,
                'name':         base.get('name', classic_names[i]),
                'color':        base.get('color', classic_colors[i]),
                'row':          CORNERS[i][0],
                'col':          CORNERS[i][1],
                'deck':         player_deck,
                'current_target': first_target,
                'score':        0,
                'total_tokens': cards_per_player,
                'winner':       False,
            })
        self.players = players

    # ── Lobby: player joins ───────────────────────────────────────────

    def lobby_join(self, name, color):
        """
        Add a player to the lobby. Returns their assigned player_id or None if full.
        """
        players = self.players
        if len(players) >= self.num_players:
            return None
        pid = len(players)
        players.append({'id': pid, 'name': name, 'color': color})
        self.players = players
        self.seq += 1
        self.save()
        return pid

    def lobby_start(self):
        """Host triggers game start. Board is built, phase set to playing."""
        deck = self._initialise_board()
        self._initialise_players(self.num_players, deck, self.tokens_to_win)
        self.phase = 'playing'
        self.seq  += 1
        self.save()

    # ── Push ─────────────────────────────────────────────────────────

    def push_tile(self, direction, index):
        lp = self.last_push
        if lp:
            rev = {'left': 'right', 'right': 'left', 'top': 'bottom', 'bottom': 'top'}
            if rev[direction] == lp['direction'] and index == lp['index']:
                return False

        grid    = self.tiles
        spare   = self.spare
        players = self.players

        if direction == 'left':
            row = index; ejected = grid[row][-1]
            grid[row] = [spare] + grid[row][:-1]
            new_spare = ejected
            for p in players:
                if p['row'] == row:
                    p['col'] = p['col'] + 1 if p['col'] + 1 < 7 else 0

        elif direction == 'right':
            row = index; ejected = grid[row][0]
            grid[row] = grid[row][1:] + [spare]
            new_spare = ejected
            for p in players:
                if p['row'] == row:
                    p['col'] = p['col'] - 1 if p['col'] - 1 >= 0 else 6

        elif direction == 'top':
            col = index; ejected = grid[6][col]
            for r in range(6, 0, -1): grid[r][col] = grid[r - 1][col]
            grid[0][col] = spare; new_spare = ejected
            for p in players:
                if p['col'] == col:
                    p['row'] = p['row'] + 1 if p['row'] + 1 < 7 else 0

        elif direction == 'bottom':
            col = index; ejected = grid[0][col]
            for r in range(0, 6): grid[r][col] = grid[r + 1][col]
            grid[6][col] = spare; new_spare = ejected
            for p in players:
                if p['col'] == col:
                    p['row'] = p['row'] - 1 if p['row'] - 1 >= 0 else 6

        self.tiles     = grid
        self.spare     = new_spare
        self.players   = players
        self.last_push = {'direction': direction, 'index': index}
        self.seq      += 1
        self.save()
        return True

    # ── BFS ──────────────────────────────────────────────────────────

    def reachable_cells(self, start_row, start_col):
        grid    = self.tiles
        visited = set()
        queue   = deque([(start_row, start_col)])
        visited.add((start_row, start_col))
        while queue:
            r, c = queue.popleft()
            exits = tile_exits(grid[r][c]['shape'], grid[r][c]['rotation'])
            for d in exits:
                dr, dc = DIR_DELTA[d]
                nr, nc = r + dr, c + dc
                if 0 <= nr < 7 and 0 <= nc < 7 and (nr, nc) not in visited:
                    if OPPOSITE[d] in tile_exits(grid[nr][nc]['shape'], grid[nr][nc]['rotation']):
                        visited.add((nr, nc))
                        queue.append((nr, nc))
        return visited

    # ── Move ─────────────────────────────────────────────────────────

    def move_player(self, player_id, target_row, target_col):
        player_id = self.current_turn  # always trust server turn

        players = self.players
        p = next((x for x in players if x['id'] == player_id), None)
        if p is None:
            return False, 'Player not found'

        reachable = self.reachable_cells(p['row'], p['col'])
        if (target_row, target_col) not in reachable:
            return False, 'Cell not reachable'

        p['row'] = target_row
        p['col'] = target_col

        # Token collection
        target_hit  = False
        landed_tile = self.tiles[target_row][target_col]
        if landed_tile.get('character') and landed_tile['character'] == p['current_target']:
            p['score']          += 1
            p['current_target']  = p['deck'].pop(0) if p['deck'] else None
            target_hit           = True

        # Win condition: all tokens collected AND standing on home corner
        player_won           = False
        home_row, home_col   = CORNERS[p['id']]
        if p['current_target'] is None and p['deck'] == [] and p['row'] == home_row and p['col'] == home_col:
            p['winner'] = True
            player_won  = True

        self.players = players
        if not player_won:
            self.current_turn = (self.current_turn + 1) % self.num_players
        else:
            self.phase = 'over'

        self.last_push = None
        self.seq      += 1
        self.save()

        if player_won:   return True, 'PLAYER_WON'
        if target_hit:   return True, 'TARGET_FOUND'
        return True, 'Moved'

    def rotate_spare(self):
        spare = self.spare
        spare['rotation'] = (spare['rotation'] + 1) % 4
        self.spare = spare
        self.seq  += 1
        self.save()

    # ── State dict ────────────────────────────────────────────────────

    def get_state_dict(self, requesting_player_id=None):
        players       = self.players
        if not players:
            return {'phase': self.phase, 'seq': self.seq}

        current_player = players[self.current_turn] if self.current_turn < len(players) else players[0]

        reachable = [list(x) for x in self.reachable_cells(
            current_player['row'], current_player['col']
        )] if self.phase == 'playing' else []

        # Build player list — hide other players' tokens in online mode
        players_out = []
        for p in players:
            p_out = dict(p)
            if self.mode == 'online' and requesting_player_id is not None and p['id'] != requesting_player_id:
                # Hide the actual token image — show count but not what it is
                p_out['current_target'] = None
                p_out['target_hidden']  = True
            players_out.append(p_out)

        return {
            'game_id':       self.pk,
            'room_code':     self.room_code,
            'mode':          self.mode,
            'phase':         self.phase,
            'theme':         self.theme,
            'seq':           self.seq,
            'tiles':         self.tiles,
            'spare':         self.spare,
            'players':       players_out,
            'current_turn':  self.current_turn,
            'current_player': current_player,
            'reachable':     reachable,
            'last_push':     self.last_push,
        }

    # ── Lobby state (minimal — for polling before game starts) ────────

    def get_lobby_dict(self):
        return {
            'phase':       self.phase,
            'room_code':   self.room_code,
            'seq':         self.seq,
            'num_players': self.num_players,
            'players':     self.players,
            'game_id':     self.pk,
        }
