import json
import os
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from .models import GameRoom


# ── Helpers ──────────────────────────────────────────────────────────────────

def json_body(request):
    """Parse JSON from request body, return dict or {}."""
    try:
        return json.loads(request.body)
    except Exception:
        return {}

def err(msg, status=400):
    return JsonResponse({'ok': False, 'error': msg}, status=status)

def ok(data=None):
    return JsonResponse({'ok': True, **(data or {})})


# ── Views ─────────────────────────────────────────────────────────────────────

def game_page(request):
    """Serve the game HTML page."""
    import os
    from django.http import HttpResponse
    html_path = os.path.join(os.path.dirname(__file__), 'game.html')
    with open(html_path, 'r') as f:
        return HttpResponse(f.read())


@csrf_exempt
@require_http_methods(['POST'])
def new_room(request):
    """
    Player 1 creates a room.
    Body: { board_size: 8|10, p1_color: '0x1a55ff' }
    Returns: { code: 'ABCD', player: 'blue' }
    """
    data = json_body(request)
    board_size = int(data.get('board_size', 8))
    # Store colour as plain int — works whether client sends 0x1a55ff or 1791231
    p1_color = int(str(data.get('p1_color', '1791231')), 0)

    # Clean up stale rooms (keep db tidy)
    for room in GameRoom.objects.all():
        if room.is_stale():
            room.delete()

    room = GameRoom.objects.create(
        board_size=board_size,
        p1_color=str(p1_color),
    )

    initial_state = {
        'phase':      'lobby',
        'turn':       'blue',
        'blue':       {'x': 0, 'z': 0},
        'red':        {'x': board_size - 1, 'z': board_size - 1},
        'burned':     [],
        'board_size': board_size,
        'p1_color':   p1_color,   # int, so JS parseInt works directly
    }
    room.set_state(initial_state)
    room.save()

    return ok({'code': room.code, 'player': 'blue', 'seq': room.seq})


@csrf_exempt
@require_http_methods(['POST'])
def join_room(request, code):
    """
    Player 2 joins an existing room.
    Body: { p2_color: '0xdd1111' }
    Returns: { board_size, p1_color, p2_color, seq }
    """
    data = json_body(request)
    p2_color = int(str(data.get('p2_color', '14487057')), 0)

    try:
        room = GameRoom.objects.get(code=code.upper())
    except GameRoom.DoesNotExist:
        return err('Room not found. Check the code and try again.', 404)

    if room.get_state().get('phase') not in ('lobby',):
        return err('This game has already started.')

    room.p2_color = str(p2_color)
    state = room.get_state()
    state['phase']    = 'playing'
    state['p1_color'] = room.p1_color   # already stored as int string
    state['p2_color'] = str(p2_color)
    room.set_state(state)
    room.save()

    return ok({
        'board_size': room.board_size,
        'p1_color':   int(room.p1_color),
        'p2_color':   p2_color,
        'seq':        room.seq,
    })


@require_http_methods(['GET'])
def poll(request, code):
    """
    Short-poll endpoint. Client calls this every second.
    Returns immediately — either with new state or unchanged:true.
    Query param: ?seq=N
    """
    try:
        room = GameRoom.objects.get(code=code.upper())
    except GameRoom.DoesNotExist:
        return err('Room not found.', 404)

    client_seq = int(request.GET.get('seq', 0))

    if room.seq > client_seq:
        state = room.get_state()
        return ok({
            'seq':        room.seq,
            'state':      state,
            'winner':     room.winner,
            'win_reason': room.win_reason,
        })

    # Nothing new yet
    return JsonResponse({'ok': True, 'unchanged': True, 'seq': room.seq})


@csrf_exempt
@require_http_methods(['POST'])
def make_move(request, code):
    """
    A player submits their move.
    Body: { player: 'blue'|'red', tx: int, tz: int }
    Returns updated state.
    """
    data   = json_body(request)
    player = data.get('player')
    tx     = int(data.get('tx', 0))
    tz     = int(data.get('tz', 0))

    try:
        room = GameRoom.objects.get(code=code.upper())
    except GameRoom.DoesNotExist:
        return err('Room not found.', 404)

    state = room.get_state()

    if state.get('phase') != 'playing':
        return err('Game is not in progress.')

    if state.get('turn') != player:
        return err('Not your turn.')

    board_size = state.get('board_size', 8)
    enemy      = 'red' if player == 'blue' else 'blue'
    cur        = state[player]
    sx, sz     = cur['x'], cur['z']
    burned     = [tuple(b) for b in state.get('burned', [])]

    # Validate move (knight L-shape, not burned)
    dx, dz = abs(tx - sx), abs(tz - sz)
    valid_shape = (dx == 2 and dz == 1) or (dx == 1 and dz == 2)
    in_bounds   = 0 <= tx < board_size and 0 <= tz < board_size
    not_burned  = [tx, tz] not in state.get('burned', [])

    if not (valid_shape and in_bounds and not_burned):
        return err('Illegal move.')

    # Burn the tile just left
    state['burned'].append([sx, sz])

    # Move the piece
    state[player] = {'x': tx, 'z': tz}

    # Check capture
    ep = state[enemy]
    if tx == ep['x'] and tz == ep['z']:
        state['phase'] = 'over'
        room.winner    = player
        room.win_reason = f'{player.capitalize()} captured the enemy knight!'
        room.set_state(state)
        room.save()
        return ok({'seq': room.seq, 'state': state, 'winner': room.winner, 'win_reason': room.win_reason})

    # Check if current player trapped themselves (no moves from new position)
    if not has_moves(state, player, board_size):
        state['phase'] = 'over'
        room.winner     = enemy
        room.win_reason = f'{player.capitalize()} has no moves left!'
        room.set_state(state)
        room.save()
        return ok({'seq': room.seq, 'state': state, 'winner': room.winner, 'win_reason': room.win_reason})

    # Switch turn
    state['turn'] = enemy

    # Check if the new current player has any moves
    if not has_moves(state, enemy, board_size):
        state['phase']  = 'over'
        room.winner     = player
        room.win_reason = f'{enemy.capitalize()} is trapped!'
        room.set_state(state)
        room.save()
        return ok({'seq': room.seq, 'state': state, 'winner': room.winner, 'win_reason': room.win_reason})

    room.set_state(state)
    room.save()
    return ok({'seq': room.seq, 'state': state})


def has_moves(state, player, board_size):
    """Check if a player has at least one legal move."""
    pos    = state[player]
    sx, sz = pos['x'], pos['z']
    burned = state.get('burned', [])
    deltas = [(1,2),(1,-2),(-1,2),(-1,-2),(2,1),(2,-1),(-2,1),(-2,-1)]
    for dx, dz in deltas:
        tx, tz = sx + dx, sz + dz
        if 0 <= tx < board_size and 0 <= tz < board_size:
            if [tx, tz] not in burned:
                return True
    return False