import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt

from .models import Game


def index(request):
    """Landing page – choose number of players."""
    return render(request, 'game/index.html')


def new_game(request):
    num_players = int(request.POST.get('num_players', 2))
    num_players = max(2, min(4, num_players))
    game = Game.new_game(num_players=num_players)
    # Store which player this browser "is"
    request.session['player_id'] = 0   # host is always player 0 for now
    return render(request, 'game/board.html', {
        'game': game,
        'player_id': 0,
        'state_json': json.dumps(game.get_state_dict(player_id=0)),
    })


def board(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    player_id = request.session.get('player_id', 0)
    return render(request, 'game/board.html', {
        'game': game,
        'player_id': player_id,
        'state_json': json.dumps(game.get_state_dict(player_id=player_id)),
    })


# ── API endpoints (called via fetch / HTMX) ───────────────────────────────────

@csrf_exempt
@require_POST
def api_rotate_spare(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    game.rotate_spare()
    player_id = request.session.get('player_id', 0)
    return JsonResponse(game.get_state_dict(player_id=player_id))


@csrf_exempt
@require_POST
def api_push(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    data = json.loads(request.body)
    direction = data.get('direction')
    index     = int(data.get('index', 0))

    if direction not in ('left', 'right', 'top', 'bottom'):
        return JsonResponse({'error': 'Invalid direction'}, status=400)

    ok = game.push_tile(direction, index)
    player_id = request.session.get('player_id', 0)
    state = game.get_state_dict(player_id=player_id)
    state['push_ok'] = ok
    if not ok:
        state['error'] = 'Cannot reverse the previous push'
    return JsonResponse(state)


@csrf_exempt
@require_POST
def api_move(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    data = json.loads(request.body)
    player_id  = int(data.get('player_id', 0))
    target_row = int(data.get('row', 0))
    target_col = int(data.get('col', 0))

    ok, msg = game.move_player(player_id, target_row, target_col)
    p_id = request.session.get('player_id', 0)
    state = game.get_state_dict(player_id=p_id)
    
    state['move_ok'] = ok
    state['message'] = msg  # <-- ADD THIS LINE to pass "TARGET_FOUND" to JS
    
    if not ok:
        state['error'] = msg
    return JsonResponse(state)


@require_GET
def api_state(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    player_id = request.session.get('player_id', 0)
    return JsonResponse(game.get_state_dict(player_id=player_id))
