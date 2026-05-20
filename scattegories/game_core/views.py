import json
import random
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum

from .models import Game, Round, Question, LETTERS, DEFAULT_QUESTIONS
from scattegories.players.models import Player
from scattegories.answers.models import Answer, AnswerReview, JuryVote


# ─── Host authentication helper ─────────────────────────────────────────────

def get_host_player(request):
    uuid = request.session.get('player_uuid')
    if not uuid:
        return None
    try:
        return Player.objects.get(uuid=uuid)
    except Player.DoesNotExist:
        return None


# ─── Host master view ────────────────────────────────────────────────────────

def host_dashboard(request):
    """Main host control panel."""
    player = get_host_player(request)
    if not player:
        return redirect('player_join')

    games = Game.objects.all().prefetch_related('rounds')
    return render(request, 'game_core/host_dashboard.html', {
        'player': player,
        'games': games,
    })


def host_game(request, game_id):
    """Host view for a specific game."""
    player = get_host_player(request)
    if not player:
        return redirect('player_join')

    game = get_object_or_404(Game, id=game_id)
    return render(request, 'game_core/host_game.html', {
        'player': player,
        'game': game,
    })


# ─── Game management API ─────────────────────────────────────────────────────

@require_POST
def create_game(request):
    player = get_host_player(request)
    if not player:
        return JsonResponse({'error': 'Not logged in'}, status=403)

    data = json.loads(request.body)
    game = Game.objects.create(
        title=data.get('title', 'Scattegories'),
        host=player,
        status='setup',
    )
    return JsonResponse({'game_id': game.id, 'title': game.title})


@require_POST
def start_round(request, game_id):
    """Create and start a new round for the game."""
    game = get_object_or_404(Game, id=game_id)
    player = get_host_player(request)
    if not player:
        return JsonResponse({'error': 'Not logged in'}, status=403)

    data = json.loads(request.body) if request.body else {}

    with transaction.atomic():
        # Determine round number
        next_number = game.rounds.count() + 1
        if next_number > 4:
            return JsonResponse({'error': 'Maximum 4 rounds per game'}, status=400)

        # Pick a random letter not used yet
        used_letters = list(game.rounds.values_list('letter', flat=True))
        available = [l for l in LETTERS if l not in used_letters]
        letter = random.choice(available) if available else random.choice(LETTERS)

        # Pick 10 questions (shuffle from pool, or use custom)
        custom_questions = data.get('questions', [])
        if not custom_questions:
            pool = list(DEFAULT_QUESTIONS)
            random.shuffle(pool)
            question_prompts = pool[:10]
        else:
            question_prompts = custom_questions[:10]

        timer = data.get('timer_seconds', 90)

        round_obj = Round.objects.create(
            game=game,
            number=next_number,
            letter=letter,
            status='waiting',
            timer_seconds=timer,
        )

        for i, prompt in enumerate(question_prompts):
            Question.objects.create(round=round_obj, index=i, prompt=prompt)

        game.current_round_number = next_number
        game.status = 'active'
        game.save()

    return JsonResponse({
        'round_id': round_obj.id,
        'round_number': next_number,
        'letter': letter,
        'questions': question_prompts,
        'timer_seconds': timer,
    })


@require_POST
def begin_round_timer(request, round_id):
    """Transition round from waiting → playing."""
    round_obj = get_object_or_404(Round, id=round_id)
    if round_obj.status != 'waiting':
        return JsonResponse({'error': f'Round is {round_obj.status}, not waiting'}, status=400)

    round_obj.status = 'playing'
    round_obj.started_at = timezone.now()
    round_obj.save()
    return JsonResponse({'status': 'playing', 'started_at': round_obj.started_at.isoformat()})


@require_POST
def lock_round(request, round_id):
    """Transition round playing → locked. Freeze answers, run duplicate detection."""
    round_obj = get_object_or_404(Round, id=round_id)
    if round_obj.status not in ('playing', 'waiting'):
        return JsonResponse({'error': f'Cannot lock from {round_obj.status}'}, status=400)

    with transaction.atomic():
        round_obj.status = 'locked'
        round_obj.locked_at = timezone.now()
        round_obj.save()

        # Run automated duplicate detection for all questions
        for question in round_obj.questions.all():
            answers = list(question.answers.all())
            # Group by normalised answer
            seen = {}
            for answer in answers:
                key = answer.normalised_answer
                if key not in seen:
                    seen[key] = []
                seen[key].append(answer)

            for key, group in seen.items():
                is_dup = len(group) > 1
                blank = not key.strip()
                for answer in group:
                    score = 0 if (is_dup or blank) else 1
                    AnswerReview.objects.update_or_create(
                        answer=answer,
                        defaults={
                            'is_duplicate': is_dup,
                            'final_score': score,
                            'decided_by_host': False,
                        }
                    )

        round_obj.status = 'reviewing'
        round_obj.current_review_question = 0
        round_obj.save()

    return JsonResponse({'status': 'reviewing'})


@require_POST
def host_score_answer(request, review_id):
    """Host overrides score for a specific answer review."""
    review = get_object_or_404(AnswerReview, id=review_id)
    data = json.loads(request.body)
    score = int(data.get('score', 0))
    if score not in (0, 1):
        return JsonResponse({'error': 'Score must be 0 or 1'}, status=400)

    review.final_score = score
    review.decided_by_host = True
    review.save()
    return JsonResponse({'review_id': review_id, 'final_score': score})


@require_POST
def confirm_question(request, round_id, question_index):
    """Host confirms a question is done — advance review to next question."""
    round_obj = get_object_or_404(Round, id=round_id)
    if round_obj.status != 'reviewing':
        return JsonResponse({'error': 'Not in review mode'}, status=400)

    next_index = question_index + 1
    if next_index >= 10:
        # All questions reviewed — complete the round
        round_obj.status = 'complete'
        round_obj.save()
        game = round_obj.game
        if game.rounds.filter(status='complete').count() == game.rounds.count():
            game.status = 'complete'
            game.save()
        return JsonResponse({'status': 'complete', 'round_complete': True})
    else:
        round_obj.current_review_question = next_index
        round_obj.save()
        return JsonResponse({'status': 'reviewing', 'current_question': next_index})


# ─── State polling API ───────────────────────────────────────────────────────

def game_state(request, game_id):
    """Full game state for polling. Used by both host and player views."""
    game = get_object_or_404(Game, id=game_id)
    player_uuid = request.session.get('player_uuid')

    current_round = game.get_current_round()
    round_data = None

    if current_round:
        questions = []
        for q in current_round.questions.all():
            questions.append({
                'id': q.id,
                'index': q.index,
                'prompt': q.prompt,
            })

        round_data = {
            'id': current_round.id,
            'number': current_round.number,
            'letter': current_round.letter,
            'status': current_round.status,
            'timer_seconds': current_round.timer_seconds,
            'remaining_seconds': current_round.get_remaining_seconds(),
            'current_review_question': current_round.current_review_question,
            'questions': questions,
        }

    return JsonResponse({
        'game_id': game.id,
        'title': game.title,
        'status': game.status,
        'current_round_number': game.current_round_number,
        'round': round_data,
        'player_uuid': str(player_uuid) if player_uuid else None,
    })


def review_state(request, round_id):
    """Detailed review state for host — all answers with review decisions."""
    round_obj = get_object_or_404(Round, id=round_id)
    question_index = round_obj.current_review_question

    # Get all players who have any answer for this round
    all_players = Player.objects.filter(
        answers__question__round=round_obj
    ).distinct().order_by('display_name')

    questions_data = []
    for question in round_obj.questions.all():
        answers_data = []
        for player in all_players:
            try:
                answer = Answer.objects.get(player=player, question=question)
                try:
                    review = answer.review
                    review_data = {
                        'review_id': review.id,
                        'is_duplicate': review.is_duplicate,
                        'final_score': review.final_score,
                        'decided_by_host': review.decided_by_host,
                    }
                except AnswerReview.DoesNotExist:
                    review_data = None
            except Answer.DoesNotExist:
                answer = None
                review_data = None

            answers_data.append({
                'player_name': player.display_name,
                'player_uuid': str(player.uuid),
                'answer_id': answer.id if answer else None,
                'raw_answer': answer.raw_answer if answer else '',
                'review': review_data,
            })

        questions_data.append({
            'id': question.id,
            'index': question.index,
            'prompt': question.prompt,
            'answers': answers_data,
        })

    return JsonResponse({
        'round_id': round_obj.id,
        'round_number': round_obj.number,
        'letter': round_obj.letter,
        'status': round_obj.status,
        'current_review_question': question_index,
        'questions': questions_data,
    })


def leaderboard(request, game_id):
    """Cumulative leaderboard across all complete rounds."""
    game = get_object_or_404(Game, id=game_id)

    players = Player.objects.filter(
        answers__question__round__game=game
    ).distinct()

    scores = []
    for player in players:
        total = AnswerReview.objects.filter(
            answer__player=player,
            answer__question__round__game=game,
        ).aggregate(total=Sum('final_score'))['total'] or 0

        # Per-round breakdown
        rounds = []
        for round_obj in game.rounds.filter(status='complete').order_by('number'):
            round_score = AnswerReview.objects.filter(
                answer__player=player,
                answer__question__round=round_obj,
            ).aggregate(total=Sum('final_score'))['total'] or 0
            rounds.append({'round': round_obj.number, 'score': round_score})

        scores.append({
            'player_name': player.display_name,
            'player_uuid': str(player.uuid),
            'total': total,
            'rounds': rounds,
        })

    scores.sort(key=lambda x: x['total'], reverse=True)

    return JsonResponse({'game_id': game_id, 'leaderboard': scores})


# ─── Jury voting ─────────────────────────────────────────────────────────────

@require_POST
def trigger_jury_vote(request, round_id):
    """Host triggers a jury vote session."""
    round_obj = get_object_or_404(Round, id=round_id)
    data = json.loads(request.body)
    context_label = data.get('context_label', 'Jury Vote')

    # Clear previous votes for this context (clean slate)
    JuryVote.objects.filter(round=round_obj, context_label=context_label).delete()

    # Store active jury session in game (use a simple marker)
    round_obj.game.title  # just to verify game exists
    # We use the context_label to identify the session — ephemeral

    return JsonResponse({
        'status': 'active',
        'context_label': context_label,
        'round_id': round_id,
    })


def jury_results(request, round_id):
    """Get current jury vote results."""
    round_obj = get_object_or_404(Round, id=round_id)
    context_label = request.GET.get('context', '')

    votes = JuryVote.objects.filter(round=round_obj, context_label=context_label)
    yes = votes.filter(vote=True).count()
    no = votes.filter(vote=False).count()
    total = votes.count()

    return JsonResponse({
        'yes': yes,
        'no': no,
        'total': total,
        'context_label': context_label,
    })
