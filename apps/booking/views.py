from django.shortcuts import render
from .views import *
# Create your views here.


def services_view(request):
    return render(request, 'service.html')