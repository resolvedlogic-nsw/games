from django.urls import path
from . import views

app_name = 'knightstrap'

urlpatterns = [
    path('', views.game_page, name='index'),
    path('api/new/',      views.new_room,   name='new_room'),
    path('api/join/<str:code>/', views.join_room, name='join_room'),
    path('api/poll/<str:code>/', views.poll,      name='poll'),
    path('api/move/<str:code>/', views.make_move, name='make_move'),
    
]