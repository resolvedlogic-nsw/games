from django.urls import path, include

urlpatterns = [
    path('', include('scattegories.players.urls')),
    path('game/', include('scattegories.game_core.urls')),
    path('answers/', include('scattegories.answers.urls')),
]