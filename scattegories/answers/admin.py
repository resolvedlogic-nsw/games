from django.contrib import admin
from .models import Answer, AnswerReview, JuryVote

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['player', 'question', 'raw_answer', 'updated_at']

@admin.register(AnswerReview)
class AnswerReviewAdmin(admin.ModelAdmin):
    list_display = ['answer', 'is_duplicate', 'final_score', 'decided_by_host']

@admin.register(JuryVote)
class JuryVoteAdmin(admin.ModelAdmin):
    list_display = ['player', 'round', 'vote', 'context_label']
