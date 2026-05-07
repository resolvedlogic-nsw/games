import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.views.decorators.csrf import csrf_exempt

from .models import Game


# ── Helpers ──────────────────────────────────────────────────────────────────

def jbody(request):
    try:
        return json.loads(request.body)
    except Exception:
        return {}

def ok(data=None):
    return JsonResponse({'ok': True, **(data or {})})

def err(msg, status=400):
    return JsonResponse({'ok': False, 'error': msg}, status=status)


# ── Pass-and-play ─────────────────────────────────────────────────────────────

def index(request):
    return render(request, 'game/index.html')


def new_game(request):
    num_players   = max(2, min(4, int(request.POST.get('num_players', 2))))
    tokens_to_win = int(request.POST.get('tokens_to_win', 24 // num_players))
    theme         = request.POST.get('theme', 'classic')

    game = Game.new_game(
        num_players=num_players,
        tokens_to_win=tokens_to_win,
        theme=theme,
        mode='pass_and_play',
    )
    request.session['player_id'] = 0
    return render(request, 'game/board.html', {
        'game':        game,
        'player_id':   0,
        'state_json':  json.dumps(game.get_state_dict(requesting_player_id=0)),
        'mode':        'pass_and_play',
        'theme':       theme,
    })


def board(request, labyrinth_id):
    game      = get_object_or_404(Game, pk=labyrinth_id)
    player_id = request.session.get('player_id', 0)
    return render(request, 'game/board.html', {
        'game':       game,
        'player_id':  player_id,
        'state_json': json.dumps(game.get_state_dict(requesting_player_id=player_id)),
        'mode':       game.mode,
        'theme':      game.theme,
    })


# ── Online lobby ──────────────────────────────────────────────────────────────

def online_page(request):
    return render(request, 'game/online.html')


@csrf_exempt
@require_POST
def host_game(request):
    """
    Host creates a new online lobby.
    Body: { num_players, tokens_to_win, theme, name, color }
    """
    data          = jbody(request)
    num_players   = max(2, min(4, int(data.get('num_players', 2))))
    tokens_to_win = int(data.get('tokens_to_win', 24 // num_players))
    theme         = data.get('theme', 'classic')
    name          = data.get('name', 'Host')[:30]
    color         = data.get('color', '#e74c3c')

    game = Game.new_lobby(
        num_players=num_players,
        tokens_to_win=tokens_to_win,
        theme=theme,
    )
    # Host is always player 0
    pid = game.lobby_join(name, color)
    request.session['player_id'] = pid
    request.session['game_id']   = game.pk

    return ok({
        'game_id':   game.pk,
        'room_code': game.room_code,
        'player_id': pid,
    })


@csrf_exempt
@require_POST
def join_game(request, code):
    """
    Player joins an existing lobby.
    Body: { name, color }
    """
    data  = jbody(request)
    name  = data.get('name', 'Player')[:30]
    color = data.get('color', '#3498db')

    game = Game.objects.filter(room_code=code.upper(), phase='lobby').first()
    if not game:
        return err('Room not found or game already started.', 404)

    pid = game.lobby_join(name, color)
    if pid is None:
        return err('Room is full.')

    request.session['player_id'] = pid
    request.session['game_id']   = game.pk

    return ok({
        'game_id':   game.pk,
        'room_code': game.room_code,
        'player_id': pid,
        'theme':     game.theme,
    })


@csrf_exempt
@require_POST
def start_game(request, code):
    """Host starts the game — builds board and sets phase to playing."""
    game = Game.objects.filter(room_code=code.upper(), phase='lobby').first()
    if not game:
        return err('Room not found.', 404)
    if len(game.players) < 2:
        return err('Need at least 2 players to start.')
    game.lobby_start()
    return ok({'game_id': game.pk, 'seq': game.seq})


@require_GET
def lobby_status(request, code):
    """
    Polling endpoint for the lobby page.
    Returns player list and phase — lightweight, no board data.
    """
    game = Game.objects.filter(room_code=code.upper()).first()
    if not game:
        return err('Room not found.', 404)
    client_seq = int(request.GET.get('seq', 0))
    if game.seq <= client_seq:
        return JsonResponse({'ok': True, 'unchanged': True, 'seq': game.seq})
    return ok(game.get_lobby_dict())


# ── In-game API ───────────────────────────────────────────────────────────────

@require_GET
def api_state(request, labyrinth_id):
    game      = get_object_or_404(Game, pk=labyrinth_id)
    player_id = request.session.get('player_id', 0)
    client_seq = int(request.GET.get('seq', 0))
    if game.seq <= client_seq:
        return JsonResponse({'ok': True, 'unchanged': True, 'seq': game.seq})
    return JsonResponse(game.get_state_dict(requesting_player_id=player_id))


@csrf_exempt
@require_POST
def api_rotate_spare(request, labyrinth_id):
    game      = get_object_or_404(Game, pk=labyrinth_id)
    player_id = request.session.get('player_id', 0)
    game.rotate_spare()
    return JsonResponse(game.get_state_dict(requesting_player_id=player_id))


@csrf_exempt
@require_POST
def api_push(request, labyrinth_id):
    game      = get_object_or_404(Game, pk=labyrinth_id)
    data      = jbody(request)
    direction = data.get('direction')
    index     = int(data.get('index', 0))
    player_id = request.session.get('player_id', 0)

    if direction not in ('left', 'right', 'top', 'bottom'):
        return JsonResponse({'error': 'Invalid direction'}, status=400)

    ok_push = game.push_tile(direction, index)
    state   = game.get_state_dict(requesting_player_id=player_id)
    state['push_ok'] = ok_push
    if not ok_push:
        state['error'] = 'Cannot reverse the previous push'
    return JsonResponse(state)


@csrf_exempt
@require_POST
def api_move(request, labyrinth_id):
    game      = get_object_or_404(Game, pk=labyrinth_id)
    data      = jbody(request)
    player_id = int(data.get('player_id', 0))
    target_row = int(data.get('row', 0))
    target_col = int(data.get('col', 0))

    move_ok, msg = game.move_player(player_id, target_row, target_col)
    pid   = request.session.get('player_id', 0)
    state = game.get_state_dict(requesting_player_id=pid)
    state['move_ok'] = move_ok
    state['message'] = msg
    if not move_ok:
        state['error'] = msg
    return JsonResponse(state)
