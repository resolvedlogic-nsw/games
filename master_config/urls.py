from django.urls import path, include
from gamehub import views as hub_views

urlpatterns = [
    # 1. The Hub owns the homepage
    path('', hub_views.hub_home, name='home'),

    # 2. Add your games here as separate 'rooms'
    path('knightstrap/', include('knightstrap.urls')),
    path('cinqo/', include('cinqo.urls')),
    path('fivecrowns/', include('fivecrowns.urls')),
    path('labyrinth/', include('labyrinth.urls')),
     

    path('admin/', admin.site.urls),
    path('', include('gamehub.urls')), # Main landing page
    

]