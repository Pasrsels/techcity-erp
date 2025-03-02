import json
import environ
import asyncio
from pathlib import Path
from django.shortcuts import render, redirect
from django.http import JsonResponse
from utils.identify_pc import get_mac_address, get_system_uuid, get_hostname
from .forms import EmailSettingsForm
from techcity.settings.base import INVENTORY_EMAIL_NOTIFICATIONS_STATUS
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from loguru import logger
from .models import NotificationsSettings, Printer, TaxSettings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from . models import *
from . forms import *

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
        'tax_settings':tax_settings,
        'notifications': notifications_settings
    })

# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Notifications settings >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

def validate_payload(payload):
    # check payload for status and notification
    if 'notification' not in payload:
        return JsonResponse({'success': False, 'error': 'Notification not provided'}, status=400)
    notification = payload.get('notification')
    # check if notification is in database
    logger.info(f'Notifications in database: {NotificationsSettings._meta.get_fields()}')
    if notification not in NotificationsSettings._meta.get_fields():
        return JsonResponse({'success': False, 'error': 'Invalid notification'}, status=400)

    if 'status' not in payload:
        return JsonResponse({'success': False, 'error': 'Status not provided'}, status=400)
    # if payload is empty
    if not payload:
        return JsonResponse({'success': False, 'error': 'Empty payload'}, status=400)

    status = payload.get('status')
    # check if status is valid
    if status not in ['on', 'off']:
        return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)

    return [notification, status]


# products notifications settings views
@require_http_methods(["POST"])
@login_required
def email_notification_status(request):
    """
        payload: {"notification": "product_creation","status": "on"}
    """
    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
            logger.info(f'Payload: {payload}')
            # result = validate_payload(payload)  # validate payload
            # logger.info(f'Payload validated: {result}')
            notification = payload.get('notification')
            status = payload.get('status')
            logger.info(f'Payload validated: {notification}, {status}')
            # update status from NotificationsSettings model
            notification_instance = NotificationsSettings.objects.first()
            logger.info(f'Notification instance: {notification_instance}')
            if notification_instance:
                # update notification_instance
                if status:
                    setattr(notification_instance, notification, True)
                elif not status:
                    setattr(notification_instance, notification, False)
                notification_instance.save()
            logger.info(f'Notification: {notification} Status: {status}, updated successfully')
            return JsonResponse({'success': True}, status=200)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)


# @require_http_methods(["POST"])
# @login_required
# def email_notification_status(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             status = data.get('status')
#             if status is None:
#                 return JsonResponse({'success': False, 'error': 'Status not provided'}, status=400)
#             settings.INVENTORY_EMAIL_NOTIFICATIONS_STATUS = status
#             logger.info(f'{settings.INVENTORY_EMAIL_NOTIFICATIONS_STATUS}')
#             return JsonResponse({'success': True}, status=200)
#         except json.JSONDecodeError:
#             return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)


@csrf_exempt
@login_required
def save_email_config(request):
    if request.method == 'POST':
        env_file_path = Path(__file__).resolve().parent.parent / '.env'

        email_settings_mapping = {
            'EMAIL_HOST': 'EMAIL_HOST',
            'EMAIL_PORT': 'EMAIL_PORT',
            'EMAIL_USE_TLS': 'EMAIL_USE_TLS',
            'EMAIL_HOST_USER': 'EMAIL_HOST_USER',
            'EMAIL_HOST_PASSWORD': 'EMAIL_HOST_PASSWORD',
        }

        email_settings_updated = False
        new_lines = []
        keys_updated = set()

        if env_file_path.exists():
            with env_file_path.open('r') as f:
                lines = f.readlines()

            for line in lines:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    if key in email_settings_mapping:
                        new_value = request.POST.get(key)
                        if new_value is not None:
                            if key in ('EMAIL_USE_TLS', 'EMAIL_USE_SSL'):
                                new_value = str(new_value.lower() == 'true')
                            new_lines.append(f"{email_settings_mapping[key]}={new_value}\n")
                            email_settings_updated = True
                            keys_updated.add(key)
                        else:
                            new_lines.append(line)
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)

            for key in email_settings_mapping:
                if key not in keys_updated:
                    new_value = request.POST.get(key)
                    if new_value is not None:
                        if key in ('EMAIL_USE_TLS', 'EMAIL_USE_SSL'):
                            new_value = str(new_value.lower() == 'true')
                        new_lines.append(f"{email_settings_mapping[key]}={new_value}\n")
                        email_settings_updated = True
        else:
            for key in email_settings_mapping:
                new_value = request.POST.get(key)
                if new_value is not None:
                    if key in ('EMAIL_USE_TLS', 'EMAIL_USE_SSL'):
                        new_value = str(new_value.lower() == 'true')
                    new_lines.append(f"{email_settings_mapping[key]}={new_value}\n")
                    email_settings_updated = True

        with env_file_path.open('w') as f:
            f.writelines(new_lines)

        environ.Env.read_env()

        if email_settings_updated:
            return JsonResponse({'success': True, 'message': 'Email settings updated successfully!'})
        else:
            return JsonResponse({'success': False, 'message': 'No email settings found in the form.'})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)


@csrf_exempt
def scan_for_printers(request):
    if request.method == 'GET':
        try:
            devices = asyncio.run(BleakScanner.discover())
            printer_data = [
                {
                    'address': device.address,
                    'name': device.name or "Unknown Device",
                }
                for device in devices
            ]
            return JsonResponse({'printers': printer_data})
        except Exception as e:
            return JsonResponse({'error': f'Error scanning for printers: {str(e)}'}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=400)


@csrf_exempt
@login_required
def update_or_create_printer(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        printer_address = data.get('printer_address')

        if not printer_address:
            return JsonResponse({'success': False, 'error': 'Invalid printer address'})

        device = asyncio.run(get_bluetooth_device(printer_address))

        if device:
            env_file_path = Path(__file__).resolve().parent.parent / '.env'

            try:
                with env_file_path.open('r') as f:
                    lines = f.readlines()
            except FileNotFoundError:
                lines = []

            printer_found = False
            with env_file_path.open('w') as f:
                for line in lines:
                    key, *value = line.strip().split('=')
                    if key == 'PRINTER_ADDRESS':
                        printer_found = True
                        f.write(f"{key}={printer_address}\n")
                    else:
                        f.write(line)

                if not printer_found:
                    f.write(f"PRINTER_ADDRESS={printer_address}\n")

            environ.Env.read_env()

            return JsonResponse({'success': True, 'message': 'Printer settings updated/created successfully!'})
        else:
            return JsonResponse({'success': False, 'error': 'Selected printer not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


# >>>>>>>>>>>>>>>>>>>>>>>>>>> PRINTER SETTINGS >>>>>>>>>>>>>>>>>>>>>>>>>>

@require_http_methods(["POST"])
def add_printer(request):
    """
    Add printer details to DB:

    payload = {
        printer_name: printerName,
        printer_address: printerAddress,
        pc_identifier: pcIdentifier,
        hostname: hostname
    }

    """
    if request.method == 'POST':
        payload = json.loads(request.body)
        logger.info(f"payload: {payload}")

        name = payload.get('printer_name')
        address = payload.get('printer_address')
        hostname = payload.get('hostname')
        pc_identifier = payload.get('pc_identifier')

        if name and address and hostname and pc_identifier:
            logger.info(f"saving printer details")
            printer = Printer.objects.create(
                name=name,
                address=address,
                hostname=hostname,
                pc_identifier=pc_identifier,
                printer_type='system',

            )
            logger.info(f"printer {printer.name} added successfully: {printer}")
            return JsonResponse({"success": True, "message": "Printer added successfully"}, status=200)


def scan_printers(request):
    """
    Scan locally configured Printer settings in this OS, filter out printers already in the system
    """
    logger.info(f"scanning printers")
    # Get all printers in the system
    printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
    logger.info(f"printers: {printers}")
    # Extract printer names and addresses
    local_printers = [
        {'name': printer[2], 'address': printer[1]}
        for printer in printers
    ]
    logger.info(f"local printers: {local_printers}")
    stored_printers = Printer.objects.values_list('name', flat=True)
    # Filter out the printers that are already stored in the system
    new_printers = [printer for printer in local_printers if printer['name'] not in stored_printers]

    logger.info(f"new printers add")
    logger.info(f"scanning successful")
    return JsonResponse({"success": True, "printers": new_printers}, safe=False, status=200)


def identify_pc(request):
    """
    Identify the PC using MAC address AND system uuid
    """
    mac_address = get_mac_address()
    system_uuid = get_system_uuid()
    hostname = get_hostname()
    return JsonResponse({"status": True, "mac_address": mac_address, "system_uuid": system_uuid, "hostname": hostname}, status=200)


def get_printers(request):
    """
    Fetch printers from the database based on PC information.
    """
    pc_identifier = request.COOKIES.get('pc_identifier')
    logger.info(f"PC identifier: {pc_identifier}")
    if not pc_identifier:
        return JsonResponse({"success": False, "error": "PC identifier not found."}, status=400)

    printers = Printer.objects.filter(pc_identifier=pc_identifier)
    printer_list = list(printers.values('name', 'address', 'hostname', 'mac_address', 'system_uuid'))

    return JsonResponse({"success": True, "printers": printer_list}, status=200)

# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>> DONE >>>>>>>>>>>>>>>>>>>>>>>>...

async def get_bluetooth_device(address):
    devices = await BleakScanner.discover()
    device = next((d.address for d in devices), None)
    return device

@login_required
def update_tax_method(request):
    selected_method_id = request.GET.get('method', None)
    try:
        if selected_method_id:
            logger.info(f'selected method: {selected_method_id}')

            tax_setting = TaxSettings.objects.get(id=selected_method_id)

            logger.info(f'tax object: {tax_setting}')

            logger.info(TaxSettings.objects.all().values())
            
            # remove the selected on any tax_setting method
            selected_settings = TaxSettings.objects.filter(selected=True)

            for setting in selected_settings:
                setting.selected = False
                setting.save()

            # assign the selected tax_method to be default
            tax_setting.selected = True 
            tax_setting.save()
          
            response_data = {
                'name': tax_setting.name,
                'selected': tax_setting.selected
            }
            return JsonResponse(response_data, safe=False)
        else:
            return JsonResponse({'error': 'Invalid method'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, }, status=400)
    

# @login_required
# def update_api_settings(request):
#     setting = APISettings.objects.get(name="FDMS")
#     if request.method == "POST":
#         form = APISettingsForm(request.POST, instance=setting)
#         if form.is_valid():
#             form.save()
#             return JsonResponse({'success':True}) 
#     else:
#         form = APISettingsForm(instance=setting)
#     return render(request, "update_api_settings.html", {"form": form})