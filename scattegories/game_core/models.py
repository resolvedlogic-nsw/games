from django.db import models
from scattegories.players.models import Player


GAME_STATUS = [
    ('setup', 'Setup'),
    ('active', 'Active'),
    ('complete', 'Complete'),
]

ROUND_STATUS = [
    ('waiting', 'Waiting'),
    ('playing', 'Playing'),
    ('locked', 'Locked'),
    ('reviewing', 'Reviewing'),
    ('complete', 'Complete'),
]

# Default questions pool — host can customise via admin
DEFAULT_QUESTIONS = [
    "Something you find in a kitchen",
    "A type of vehicle",
    "Something at a party",
    "An animal",
    "A job or profession",
    "Something romantic",
    "A sport or physical activity",
    "Something you'd find at the beach",
    "A type of food",
    "Something that makes noise",
]


class Game(models.Model):
    title = models.CharField(max_length=100, default='Scattegories')
    host = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name='hosted_games')
    status = models.CharField(max_length=20, choices=GAME_STATUS, default='setup')
    current_round_number = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.status})"

    def get_current_round(self):
        if self.current_round_number == 0:
            return None
        return self.rounds.filter(number=self.current_round_number).first()


LETTERS = 'ABCDEFGHIJKLMNOPRSTW'  # Excludes tricky letters


class Round(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='rounds')
    number = models.IntegerField()  # 1–4
    letter = models.CharField(max_length=1)
    status = models.CharField(max_length=20, choices=ROUND_STATUS, default='waiting')
    started_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    timer_seconds = models.IntegerField(default=90)
    current_review_question = models.IntegerField(default=0)  # 0-9, which question is being reviewed

    class Meta:
        ordering = ['number']
        unique_together = ['game', 'number']

    def __str__(self):
        return f"Round {self.number} (Letter: {self.letter}) - {self.status}"

    def get_elapsed_seconds(self):
        if self.started_at is None:
            return 0
        from django.utils import timezone
        elapsed = (timezone.now() - self.started_at).total_seconds()
        return min(int(elapsed), self.timer_seconds)

    def get_remaining_seconds(self):
        return max(0, self.timer_seconds - self.get_elapsed_seconds())

    def is_time_expired(self):
        return self.get_remaining_seconds() == 0


class Question(models.Model):
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name='questions')
    index = models.IntegerField()  # 0–9
    prompt = models.CharField(max_length=200)

    class Meta:
        ordering = ['index']
        unique_together = ['round', 'index']

    def __str__(self):
        return f"Q{self.index}: {self.prompt}"
