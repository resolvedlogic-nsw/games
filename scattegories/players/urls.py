from django.urls import path
from . import views

urlpatterns = [
    path('', views.player_join, name='player_join'),
    path('lobby/', views.player_lobby, name='player_lobby'),
    path('play/<int:game_id>/', views.player_game, name='player_game'),
    path('api/register/', views.player_register, name='player_register'),
    path('api/jury-vote/', views.player_jury_vote, name='player_jury_vote'),
    path('change-name/', views.player_change_name, name='player_change_name'),
]
