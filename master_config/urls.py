from django.urls import path, include

urlpatterns = [
    path('', include('gamehub.urls')),             # The Hub owns the front door
    path('knightstrap/', include('knightstrap.urls')), # Game 1
    path('cinqo/', include('cinqo.urls')),             # Game 2
]