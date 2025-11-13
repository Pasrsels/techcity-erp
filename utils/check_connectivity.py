import requests
import socket
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from utils.zimra import ZIMRA
from loguru import logger

zimra = ZIMRA()

@login_required
def check_connectivity_for_invoice(request):
    """
        Check both internet and ZIMRA connectivity before invoice creation
    """
    
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        has_internet = True
        logger.info('Internet is reachable')
    except OSError:
        has_internet = False
        logger.info('Internet is not reachable')    
    if not has_internet:
        return JsonResponse({
            'success': False,
            'online': False,
            'can_create_invoice': False,
            'message': 'No internet connection. Cannot submit to ZIMRA.'
        })
    
    response = zimra.ping()
    if response.get('reportingFrequency'):
        zimra_reachable = True
        logger.info('ZIMRA is reachable')
    else:
        zimra_reachable = False
        logger.info('ZIMRA is not reachable')
    
    return JsonResponse({
        'success': True,
        'online': has_internet,
        'zimra_reachable': zimra_reachable,
        'can_create_invoice': has_internet and zimra_reachable,
        'message': 'Ready to create invoice' if (has_internet and zimra_reachable) else 'ZIMRA service unavailable'
    })