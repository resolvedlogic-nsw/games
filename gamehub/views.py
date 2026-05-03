from django.shortcuts import render

def hub_home(request):
    return render(request, 'gamehub/index.html')