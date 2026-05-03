from django.urls import path, include

urlpatterns = [
    # 1. The Hub owns the homepage
    path('', hub_views.hub_home, name='home'),

    # 2. Add your games here as separate 'rooms'
    path('knightstrap/', include('knightstrap.urls')),
    path('cinqo/', include('cinqo.urls')),
    path('fivecrowns/', include('fivecrowns.urls')),
    path('labyrinth/', include('labyrinth_game.urls')),
     
]