from django.urls import path
from . import views

app_name = 'gamehub'

urlpatterns = [
    path('', views.index, name='index'),
]