from django.shortcuts import render

def landing(request):
    return render(request, "scattegories_landing.html")