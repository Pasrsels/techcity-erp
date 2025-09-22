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
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import DatabaseBackupSchedule
from django.http import JsonResponse


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

def validate_payload(payload):
    if 'notification' not in payload:
        logger.warning("Notification not provided in payload")
        return JsonResponse({'success': False, 'error': 'Notification not provided'}, status=400)
    notification = payload.get('notification')
    if notification not in NotificationsSettings._meta.get_fields():
        logger.warning(f"Invalid notification: {notification}")
        return JsonResponse({'success': False, 'error': 'Invalid notification'}, status=400)
    if 'status' not in payload:
        logger.warning("Status not provided in payload")
        return JsonResponse({'success': False, 'error': 'Status not provided'}, status=400)
    if not payload:
        logger.warning("Empty payload received")
        return JsonResponse({'success': False, 'error': 'Empty payload'}, status=400)
    status = payload.get('status')
    if status not in ['on', 'off']:
        logger.warning(f"Invalid status: {status}")
        return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
    return [notification, status]

@require_http_methods(["POST"])
@login_required
def email_notification_status(request):
    try:
        payload = json.loads(request.body)
        logger.info(f'Payload: {payload}')
        notification = payload.get('notification')
        status = payload.get('status')
        logger.info(f'Updating notification: {notification} to status: {status}')
        notification_instance = NotificationsSettings.objects.first()
        if notification_instance:
            setattr(notification_instance, notification, status == 'on')
            notification_instance.save()
            logger.info(f'Notification {notification} updated to {status}')
        return JsonResponse({'success': True}, status=200)
    except json.JSONDecodeError:
        logger.error("Invalid JSON received")
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error updating notification status: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

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
            logger.info("Email settings updated successfully")
            return JsonResponse({'success': True, 'message': 'Email settings updated successfully!'})
        else:
            logger.warning("No email settings found in the form.")
            return JsonResponse({'success': False, 'message': 'No email settings found in the form.'})
    logger.warning("Invalid request method for saving email config")
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
            logger.info(f"Found printers: {printer_data}")
            return JsonResponse({'printers': printer_data})
        except Exception as e:
            logger.error(f'Error scanning for printers: {str(e)}')
            return JsonResponse({'error': f'Error scanning for printers: {str(e)}'}, status=500)
    logger.warning("Invalid request method for scanning printers")
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@csrf_exempt
@login_required
def update_or_create_printer(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        printer_address = data.get('printer_address')
        if not printer_address:
            logger.warning("Invalid printer address received")
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
            logger.info("Printer settings updated/created successfully")
            return JsonResponse({'success': True, 'message': 'Printer settings updated/created successfully!'})
        else:
            logger.warning("Selected printer not found")
            return JsonResponse({'success': False, 'error': 'Selected printer not found'})
    logger.warning("Invalid request method for updating/creating printer")
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)

@require_http_methods(["POST"])
def add_printer(request):
    payload = json.loads(request.body)
    logger.info(f"Adding printer with payload: {payload}")
    name = payload.get('printer_name')
    address = payload.get('printer_address')
    hostname = payload.get('hostname')
    pc_identifier = payload.get('pc_identifier')
    if name and address and hostname and pc_identifier:
        printer = Printer.objects.create(
            name=name,
            address=address,
            hostname=hostname,
            pc_identifier=pc_identifier,
            printer_type='system',
        )
        logger.info(f"Printer {printer.name} added successfully: {printer}")
        return JsonResponse({"success": True, "message": "Printer added successfully"}, status=200)
    logger.warning("Missing printer details in payload")
    return JsonResponse({"success": False, "message": "Missing printer details"}, status=400)

def scan_printers(request):
    logger.info("Scanning local printers")
    printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
    local_printers = [
        {'name': printer[2], 'address': printer[1]}
        for printer in printers
    ]
    stored_printers = Printer.objects.values_list('name', flat=True)
    new_printers = [printer for printer in local_printers if printer['name'] not in stored_printers]
    logger.info(f"New printers found: {new_printers}")
    return JsonResponse({"success": True, "printers": new_printers}, safe=False, status=200)

def identify_pc(request):
    mac_address = get_mac_address()
    system_uuid = get_system_uuid()
    hostname = get_hostname()
    logger.info(f"Identified PC - MAC: {mac_address}, UUID: {system_uuid}, Hostname: {hostname}")
    return JsonResponse({"status": True, "mac_address": mac_address, "system_uuid": system_uuid, "hostname": hostname}, status=200)

def get_printers(request):
    pc_identifier = request.COOKIES.get('pc_identifier')
    logger.info(f"Fetching printers for PC identifier: {pc_identifier}")
    if not pc_identifier:
        logger.warning("PC identifier not found in cookies")
        return JsonResponse({"success": False, "error": "PC identifier not found."}, status=400)
    printers = Printer.objects.filter(pc_identifier=pc_identifier)
    printer_list = list(printers.values('name', 'address', 'hostname', 'mac_address', 'system_uuid'))
    logger.info(f"Printers found: {printer_list}")
    return JsonResponse({"success": True, "printers": printer_list}, status=200)

async def get_bluetooth_device(address):
    devices = await BleakScanner.discover()
    device = next((d.address for d in devices), None)
    logger.info(f"Bluetooth device found: {device}")
    return device

@login_required
def update_tax_method(request):
    selected_method_id = request.GET.get('method', None)
    try:
        if selected_method_id:
            logger.info(f'Selected tax method: {selected_method_id}')
            tax_setting = TaxSettings.objects.get(id=selected_method_id)
            logger.info(f'Tax object: {tax_setting}')
            selected_settings = TaxSettings.objects.filter(selected=True)
            for setting in selected_settings:
                setting.selected = False
                setting.save()
            tax_setting.selected = True 
            tax_setting.save()
            response_data = {
                'name': tax_setting.name,
                'selected': tax_setting.selected
            }
            logger.info(f"Tax method updated: {response_data}")
            return JsonResponse(response_data, safe=False)
        else:
            logger.warning("Invalid method parameter for tax update")
            return JsonResponse({'error': 'Invalid method'}, status=400)
    except Exception as e:
        logger.error(f"Error updating tax method: {e}")
        return JsonResponse({'success': False}, status=400)


@login_required
def save_backup_schedule(request):
    try:
        data = json.loads(request.body)
        schedule_time = data.get('schedule_time')
        enabled = data.get('enabled', False)
        if not schedule_time:
            return JsonResponse({'success': False, 'error': 'No schedule time provided'}, status=400)
        obj, created = DatabaseBackupSchedule.objects.update_or_create(
            created_by=request.user,
            defaults={'time': schedule_time, 'enabled': enabled}
        )
        logger.info(f"Backup schedule updated: {obj}")
        return JsonResponse({'success': True, 'message': 'Backup schedule updated'})
    except Exception as e:
        logger.error(f"Error saving backup schedule: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)    