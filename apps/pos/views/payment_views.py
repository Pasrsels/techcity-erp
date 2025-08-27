from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.template.loader import render_to_string
from apps.finance.models import Paylater, layby, laybyDates, paylaterDates

@login_required
def paylaters(request):
    paylaters = Paylater.objects.all()
    paylaters_dates = paylaterDates.objects.all()

    html = render_to_string('partials/paylaters.html')

    return JsonResponse({'success':True, 'html':html})

@login_required
def laybyes(request):
    laybys= layby.objects.all()
    layby_dates = laybyDates.objects.all()

    html = render_to_string('partials/paylaters.html')

    return JsonResponse({'success':True, 'html':html})
