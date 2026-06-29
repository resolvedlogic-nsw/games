from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='finances-home'),
    path('download/', views.download_csv, name='finances-download'),
]