from django.shortcuts import render

def index(request):
    return render(request, 'flip7/index.html')