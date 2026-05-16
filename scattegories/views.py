from django.urls import path
from . import views   # ← correct import

app_name = "scattegories"

urlpatterns = [
    path('', views.landing, name='index'),
]