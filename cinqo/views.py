from django.shortcuts import render

def index(request):
    return render(request, 'cinqo/templates/cinqo/index.html')