from django.urls import path
from . import views

app_name = 'fivecrowns'
urlpatterns = [
    path('', views.index, name='index'),
]