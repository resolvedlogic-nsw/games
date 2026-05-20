import json
import uuid as uuid_lib
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from scattegories.game_core.models import Game
from scattegories.answers.models import JuryVote
from scattegories.players.models import Player


def player_join(request):
    """Player join/name entry screen."""
    # If already have a session, redirect to game lobby
    existing_uuid = request.session.get('player_uuid')
    if existing_uuid:
        try:
            Player.objects.get(uuid=existing_uuid)
            return redirect('player_lobby')
        except Player.DoesNotExist:
            pass

    return render(request, 'players/join.html')


@require_POST
def player_register(request):
    """Register a player name, create/retrieve player, set session."""
    data = json.loads(request.body)
    display_name = data.get('display_name', '').strip()[:50]

    if not display_name:
        return JsonResponse({'error': 'Name required'}, status=400)

    # Check for existing UUID in request (returning player)
    existing_uuid = data.get('uuid')
    if existing_uuid:
        try:
            player = Player.objects.get(uuid=existing_uuid)
            player.display_name = display_name
            player.save()
            request.session['player_uuid'] = str(player.uuid)
            return JsonResponse({'uuid': str(player.uuid), 'display_name': player.display_name})
        except Player.DoesNotExist:
            pass

    # New player
    player = Player.objects.create(display_name=display_name)
    request.session['player_uuid'] = str(player.uuid)
    return JsonResponse({'uuid': str(player.uuid), 'display_name': player.display_name})


def player_lobby(request):
    """Player game lobby — shows current game state, waiting for host."""
    player_uuid = request.session.get('player_uuid')
    if not player_uuid:
        return redirect('player_join')

    try:
        player = Player.objects.get(uuid=player_uuid)
    except Player.DoesNotExist:
        return redirect('player_join')

    # Find the most recent active game
    game = Game.objects.filter(status__in=['setup', 'active']).order_by('-created_at').first()

    return render(request, 'players/lobby.html', {
        'player': player,
        'game': game,
    })


def player_game(request, game_id):
    """Player game screen — answer submission."""
    player_uuid = request.session.get('player_uuid')
    if not player_uuid:
        return redirect('player_join')

    try:
        player = Player.objects.get(uuid=player_uuid)
    except Player.DoesNotExist:
        return redirect('player_join')

    game = get_object_or_404(Game, id=game_id)
    return render(request, 'players/game.html', {
        'player': player,
        'game': game,
    })


@require_POST
def player_jury_vote(request):
    """Player submits a jury vote."""
    player_uuid = request.session.get('player_uuid')
    if not player_uuid:
        return JsonResponse({'error': 'Not logged in'}, status=403)

    try:
        player = Player.objects.get(uuid=player_uuid)
    except Player.DoesNotExist:
        return JsonResponse({'error': 'Player not found'}, status=404)

    data = json.loads(request.body)
    round_id = data.get('round_id')
    vote = data.get('vote')  # True or False
    context_label = data.get('context_label', 'Jury Vote')

    from scattegories.game_core.models import Round
    round_obj = get_object_or_404(Round, id=round_id)

    JuryVote.objects.update_or_create(
        round=round_obj,
        player=player,
        context_label=context_label,
        defaults={'vote': bool(vote)},
    )

    return JsonResponse({'status': 'voted', 'vote': vote})


def player_change_name(request):
    """Allow player to change name."""
    request.session.flush()
    return redirect('player_join')
