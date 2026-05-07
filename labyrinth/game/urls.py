from django.urls import path
from . import views

app_name = 'labyrinth'

urlpatterns = [
    # Pass-and-play
    path('',                                   views.index,          name='index'),
    path('new/',                               views.new_game,       name='new_game'),
    path('<int:labyrinth_id>/',                views.board,          name='board'),

    # Online lobby
    path('online/',                            views.online_page,    name='online'),
    path('host/',                              views.host_game,      name='host_game'),
    path('join/<str:code>/',                   views.join_game,      name='join_game'),
    path('lobby/<str:code>/',                  views.lobby_status,   name='lobby_status'),
    path('start/<str:code>/',                  views.start_game,     name='start_game'),

    # In-game API
    path('<int:labyrinth_id>/state/',          views.api_state,          name='api_state'),
    path('<int:labyrinth_id>/rotate-spare/',   views.api_rotate_spare,   name='api_rotate_spare'),
    path('<int:labyrinth_id>/push/',           views.api_push,           name='api_push'),
    path('<int:labyrinth_id>/move/',           views.api_move,           name='api_move'),
]
