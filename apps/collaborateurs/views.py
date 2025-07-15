from django.shortcuts import render

def index(request):
    return render(request, 'collaborateurs/index.html')