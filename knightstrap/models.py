import json
import random
import string
from django.db import models
from django.utils import timezone


def make_room_code():
    """Generate a random 4-character uppercase room code."""
    return ''.join(random.choices(string.ascii_uppercase, k=4))


class GameRoom(models.Model):
    code        = models.CharField(max_length=8, unique=True, default=make_room_code)
    created_at  = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)

    # Which colours each player chose (stored as hex strings e.g. '0x1a55ff')
    p1_color    = models.CharField(max_length=20, blank=True, default='')
    p2_color    = models.CharField(max_length=20, blank=True, default='')

    # Board size chosen by host
    board_size  = models.IntegerField(default=8)

    # Full game state as JSON — updated on every move
    # Stores: { blue: {x, z}, red: {x, z}, burned: [[x,z],...], turn: 'blue'|'red', phase: 'lobby'|'playing'|'over' }
    state_json  = models.TextField(default='{}')

    # Sequence number — incremented on every state change so clients know when to update
    seq         = models.IntegerField(default=0)

    # Winner if game is over
    winner      = models.CharField(max_length=10, blank=True, default='')
    win_reason  = models.CharField(max_length=200, blank=True, default='')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Room {self.code} (seq {self.seq})"

    def get_state(self):
        try:
            return json.loads(self.state_json)
        except Exception:
            return {}

    def set_state(self, state_dict):
        self.state_json = json.dumps(state_dict)
        self.seq += 1

    def is_stale(self):
        """Rooms inactive for more than 2 hours are considered stale."""
        return (timezone.now() - self.last_active).total_seconds() > 7200