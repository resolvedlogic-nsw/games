from django.db import models
from scattegories.players.models import Player
from scattegories.game_core.models import Question, Round


class Answer(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    raw_answer = models.CharField(max_length=200, blank=True)
    normalised_answer = models.CharField(max_length=200, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['player', 'question']
        ordering = ['player__display_name']

    def __str__(self):
        return f"{self.player.display_name}: {self.raw_answer}"

    def save(self, *args, **kwargs):
        # Auto-normalise: strip, lowercase, remove articles for comparison
        self.normalised_answer = self.raw_answer.strip().lower()
        super().save(*args, **kwargs)


class AnswerReview(models.Model):
    answer = models.OneToOneField(Answer, on_delete=models.CASCADE, related_name='review')
    is_duplicate = models.BooleanField(default=False)   # advisory: automated detection
    final_score = models.IntegerField(default=0)         # authoritative: host decision (0 or 1)
    decided_by_host = models.BooleanField(default=False)
    reviewed_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.answer} → {self.final_score}pt"


class JuryVote(models.Model):
    """Ephemeral jury votes — advisory only, never affects scoring."""
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name='jury_votes')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='jury_votes')
    vote = models.BooleanField()  # True = accept, False = reject
    context_label = models.CharField(max_length=200, blank=True)  # what was being voted on
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # One vote per player per jury session (identified by context_label)
        unique_together = ['round', 'player', 'context_label']
