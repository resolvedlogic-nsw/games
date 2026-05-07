import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from .models import Game

def index(request):
    return render(request, 'game/index.html')

def online_page(request):
    theme = request.GET.get('theme', 'classic')
    return render(request, 'game/online.html', {'theme': theme})

def new_game(request):
    num_players = int(request.POST.get('num_players', 2))
    num_players = max(2, min(4, num_players))
    theme = request.POST.get('theme', 'classic')
    
    default_tokens = 24 // num_players
    tokens_to_win = int(request.POST.get('tokens_to_win', default_tokens))
    
    game = Game.new_game(num_players=num_players, tokens_to_win=tokens_to_win, theme=theme, mode='pass_and_play')
    request.session['player_id'] = 0   
    
    return redirect('labyrinth:board', labyrinth_id=game.id)

@require_POST
def host_game(request):
    name = request.POST.get('player_name', 'Host')
    color_id = int(request.POST.get('color_id', 0))
    num_players = int(request.POST.get('num_players', 2))
    theme = request.POST.get('theme', 'classic')
    tokens_to_win = int(request.POST.get('tokens_to_win', 12))

    game = Game.new_game(num_players=num_players, tokens_to_win=tokens_to_win, theme=theme, mode='online')
    deck = game.players[0]['deck']
    
    game.players = []
    game.spare_json = json.dumps({'deck': deck}) 
    game.save()

    _join_player_to_game(game, name, color_id)
    request.session[f'player_id_{game.id}'] = color_id
    request.session['is_host'] = True

    # FIX: Return JSON so the front-end can smoothly transition to the lobby!
    return JsonResponse({'success': True, 'room_code': game.room_code, 'game_id': game.id})

@require_POST
def join_game(request, code):
    code = code.upper()
    game = get_object_or_404(Game, room_code=code, mode='online', phase='lobby')
    
    data = json.loads(request.body)
    name = data.get('player_name', 'Player')
    color_id = int(data.get('color_id', -1))

    if any(p['id'] == color_id for p in game.players):
        return JsonResponse({'error': 'Color taken'}, status=400)

    _join_player_to_game(game, name, color_id)
    request.session[f'player_id_{game.id}'] = color_id
    request.session['is_host'] = False

    return JsonResponse({'success': True, 'game_id': game.id})

def _join_player_to_game(game, name, color_id):
    corners = [(0, 0), (0, 6), (6, 6), (6, 0)]
    colors = ['#e74c3c', '#3498db', '#f39c12', '#9b59b6'] if game.theme == 'pokemon' else ['#e74c3c', '#3498db', '#2ecc71', '#f39c12']
    
    players = game.players
    players.append({
        'id': color_id,
        'name': name,
        'color': colors[color_id],
        'row': corners[color_id][0],
        'col': corners[color_id][1],
        'deck': [], 
        'current_target': None,
        'score': 0,
        'total_tokens': game.tokens_to_win 
    })
    
    game.players = sorted(players, key=lambda x: x['id'])
    game.seq += 1
    game.save()

@require_GET
def lobby_status(request, code):
    code = code.upper()
    game = get_object_or_404(Game, room_code=code)
    return JsonResponse({
        'phase': game.phase,
        'players': game.players,
        'num_players': game.num_players,
        'game_id': game.id
    })

@require_POST
def start_game(request, code):
    game = get_object_or_404(Game, room_code=code, phase='lobby')
    if len(game.players) < 2:
        return JsonResponse({'error': 'Need more players'}, status=400)
    
    temp_state = json.loads(game.spare_json)
    deck = temp_state['deck']
    
    cards_per_player = game.tokens_to_win
    players = game.players
    for i, p in enumerate(players):
        p_deck = deck[i * cards_per_player : (i + 1) * cards_per_player]
        p['current_target'] = p_deck.pop(0) if p_deck else None
        p['deck'] = p_deck
        
    game.players = players
    game.spare_json = game.tiles_json 
    game._initialise_board() 
    
    game.phase = 'playing'
    game.seq += 1
    game.save()
    return JsonResponse({'success': True})

def board(request, labyrinth_id):
    game = get_object_or_404(Game, pk=labyrinth_id)
    player_id = request.session.get(f'player_id_{game.id}', 0) if game.mode == 'online' else 0
    is_host = request.session.get('is_host', False)
    
    return render(request, 'game/board.html', {
        'game': game,
        'player_id': player_id,
        'is_host': is_host,
        'theme': game.theme,
        'state_json': json.dumps(game.get_state_dict(player_perspective=player_id)),
    })

@require_GET
def poll_state(request, labyrinth_id):
    game = get_object_or_404(Game, pk=labyrinth_id)
    player_id = request.session.get(f'player_id_{game.id}', 0) if game.mode == 'online' else 0
    return JsonResponse(game.get_state_dict(player_perspective=player_id))

@csrf_exempt
@require_POST
def api_rotate_spare(request, labyrinth_id):
    game = get_object_or_404(Game, pk=labyrinth_id)
    game.rotate_spare()
    pid = request.session.get(f'player_id_{game.id}', 0) if game.mode == 'online' else 0
    return JsonResponse(game.get_state_dict(player_perspective=pid))

@csrf_exempt
@require_POST
def api_push(request, labyrinth_id):
    game = get_object_or_404(Game, pk=labyrinth_id)
    data = json.loads(request.body)
    direction = data.get('direction')
    index = int(data.get('index', 0))

    if direction not in ('left', 'right', 'top', 'bottom'):
        return JsonResponse({'error': 'Invalid direction'}, status=400)

    ok = game.push_tile(direction, index)
    pid = request.session.get(f'player_id_{game.id}', 0) if game.mode == 'online' else 0
    state = game.get_state_dict(player_perspective=pid)
    state['push_ok'] = ok
    if not ok: state['error'] = 'Cannot reverse the previous push'
    return JsonResponse(state)

@csrf_exempt
@require_POST
def api_move(request, labyrinth_id):
    game = get_object_or_404(Game, pk=labyrinth_id)
    data = json.loads(request.body)
    player_id = int(data.get('player_id', 0))
    target_row = int(data.get('row', 0))
    target_col = int(data.get('col', 0))

    ok, msg = game.move_player(player_id, target_row, target_col)
    pid = request.session.get(f'player_id_{game.id}', 0) if game.mode == 'online' else 0
    state = game.get_state_dict(player_perspective=pid)
    
    state['move_ok'] = ok
    state['message'] = msg  
    if not ok: state['error'] = msg
    return JsonResponse(state)

@require_GET
def api_state(request, labyrinth_id):
    game = get_object_or_404(Game, pk=labyrinth_id)
    pid = request.session.get(f'player_id_{game.id}', 0) if game.mode == 'online' else 0
    return JsonResponse(game.get_state_dict(player_perspective=pid))