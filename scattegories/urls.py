from django.urls import path, include
from scattegories.game_core import views as core_views  # Import the core views

app_name = 'scattegories'

urlpatterns = [
    # The Front Door: Route the empty base URL to the landing page
    path('', core_views.landing_page, name='landing_page'),

    # Your existing sub-routes
    path('core/', include('scattegories.game_core.urls')),
    path('players/', include('scattegories.players.urls')),
    path('answers/', include('scattegories.answers.urls')),
]