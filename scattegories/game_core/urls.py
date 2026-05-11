from django.urls import path
from . import views

urlpatterns = [
    # Host views
    path('host/', views.host_dashboard, name='host_dashboard'),
    path('host/<int:game_id>/', views.host_game, name='host_game'),

    # Game management API
    path('api/create/', views.create_game, name='create_game'),
    path('api/<int:game_id>/start-round/', views.start_round, name='start_round'),
    path('api/round/<int:round_id>/begin/', views.begin_round_timer, name='begin_round_timer'),
    path('api/round/<int:round_id>/lock/', views.lock_round, name='lock_round'),
    path('api/round/<int:round_id>/confirm/<int:question_index>/', views.confirm_question, name='confirm_question'),
    path('api/review/<int:review_id>/score/', views.host_score_answer, name='host_score_answer'),

    # State polling
    path('api/<int:game_id>/state/', views.game_state, name='game_state'),
    path('api/round/<int:round_id>/review/', views.review_state, name='review_state'),
    path('api/<int:game_id>/leaderboard/', views.leaderboard, name='leaderboard'),

    # Jury voting
    path('api/round/<int:round_id>/jury/trigger/', views.trigger_jury_vote, name='trigger_jury_vote'),
    path('api/round/<int:round_id>/jury/results/', views.jury_results, name='jury_results'),
]
