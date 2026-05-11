from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('players.urls')),
    path('game/', include('game_core.urls')),
    path('answers/', include('answers.urls')),
]
