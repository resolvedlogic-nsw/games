from django.urls import path
from . import views

app_name = 'cinqo'
urlpatterns = [
    path('', views.index, name='index'),
]