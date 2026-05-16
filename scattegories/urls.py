from django.urls import path
from . import views

app_name = "scattegories"

urlpatterns = [
    path('', views.landing, name='index'),
]