import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404

from .models import Answer, AnswerReview
from players.models import Player
from game_core.models import Question, Round


def get_player(request):
    uuid = request.session.get('player_uuid')
    if not uuid:
        return None
    try:
        return Player.objects.get(uuid=uuid)
    except Player.DoesNotExist:
        return None


@require_POST
def submit_answer(request):
    """Incrementally save/update a single answer for one question."""
    player = get_player(request)
    if not player:
        return JsonResponse({'error': 'Not logged in'}, status=403)

    data = json.loads(request.body)
    question_id = data.get('question_id')
    raw_answer = data.get('answer', '').strip()

    question = get_object_or_404(Question, id=question_id)
    round_obj = question.round

    # Only accept answers while round is playing
    if round_obj.status not in ('playing',):
        return JsonResponse({'error': 'Round is not accepting answers'}, status=400)

    # Also reject if timer expired (server-authoritative check)
    if round_obj.is_time_expired():
        return JsonResponse({'error': 'Time has expired'}, status=400)

    answer, created = Answer.objects.update_or_create(
        player=player,
        question=question,
        defaults={'raw_answer': raw_answer},
    )

    return JsonResponse({
        'status': 'saved',
        'question_id': question_id,
        'answer': raw_answer,
        'created': created,
    })


def player_answers_for_round(request, round_id):
    """Get all of a player's current answers for a round (for pre-filling inputs)."""
    player = get_player(request)
    if not player:
        return JsonResponse({'error': 'Not logged in'}, status=403)

    round_obj = get_object_or_404(Round, id=round_id)
    answers = Answer.objects.filter(
        player=player,
        question__round=round_obj,
    ).select_related('question')

    data = {}
    for answer in answers:
        data[answer.question.id] = answer.raw_answer

    return JsonResponse({'answers': data})
