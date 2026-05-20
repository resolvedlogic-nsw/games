from django.contrib import admin
from .models import Game, Round, Question

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['title', 'host', 'status', 'current_round_number', 'created_at']

@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = ['game', 'number', 'letter', 'status', 'timer_seconds']

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['round', 'index', 'prompt']
