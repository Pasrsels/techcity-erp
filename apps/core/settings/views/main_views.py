from pathlib import Path
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from ..models import NotificationsSettings, TaxSettings
from ..forms import EmailSettingsForm


@login_required
def settings(request):
    email_form = EmailSettingsForm()
    env_file_path = Path(__file__).resolve().parent.parent / '.env'
    try:
        with env_file_path.open('r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []

    printer_data = None

    for line in lines:
        key, *value = line.strip().split('=')
        if key == 'PRINTER_ADDRESS':
            printer_data = value[0]

    notifications_settings = NotificationsSettings.objects.filter(user=request.user).first()
    tax_settings = TaxSettings.objects.all()

    return render(request, 'settings/settings.html', {
        'printer': printer_data,
        'email_form': email_form,
        'tax_settings': tax_settings,
        'notifications': notifications_settings
    })
