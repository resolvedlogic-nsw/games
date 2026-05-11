from django.urls import path
from . import views

urlpatterns = [
    path('submit/', views.submit_answer, name='submit_answer'),
    path('round/<int:round_id>/mine/', views.player_answers_for_round, name='player_answers_for_round'),
]
