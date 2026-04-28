from django.urls import path
from . import views

app_name = 'game'

urlpatterns = [
    path('',                              views.index,           name='index'),
    path('new/',                          views.new_game,        name='new_game'),
    path('<int:game_id>/',                views.board,           name='board'),
    path('<int:game_id>/state/',          views.api_state,       name='api_state'),
    path('<int:game_id>/rotate-spare/',   views.api_rotate_spare, name='api_rotate_spare'),
    path('<int:game_id>/push/',           views.api_push,        name='api_push'),
    path('<int:game_id>/move/',           views.api_move,        name='api_move'),
]
