from django.urls import path
from . import views

app_name = 'gamehub'

urlpatterns = [
    path('', views.hub_home, name='home'),
]