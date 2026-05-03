from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from gamehub import views as hub_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('game.urls')),
    path('', hub_views.index, name='index'), # This makes the Hub the home page
    path('labyrinth/', include('labyrinth_app.urls')), # Moves the game to a sub-folder
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
