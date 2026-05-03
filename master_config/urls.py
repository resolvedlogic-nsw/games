from django.urls import path, include
from gamehub import views as hub_views
from django.contrib import admin

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('gamehub.urls')),
    path('cinqo/', include('cinqo.urls')),
    path('fivecrowns/', include('fivecrowns.urls')),
    path('knightstrap/', include('knightstrap.urls')),
    path('labyrinth/', include('labyrinth.urls')),
]