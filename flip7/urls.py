from django.urls import path
from . import views

app_name = 'flip7'
urlpatterns = [
    path('', views.index, name='index'),
]