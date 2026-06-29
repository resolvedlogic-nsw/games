from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='finances-home'),
    path('run/', views.run_report, name='finances-run'),
    path('download/', views.download_csv, name='finances-download'),
]