import json
import asyncio
from pathlib import Path
import environ
# import win32print # This module is only available on Windows
from bleak import BleakScanner
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from loguru import logger

from utils.identify_pc import get_mac_address, get_system_uuid, get_hostname
from ..models import Printer


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


async def get_bluetooth_device(address):
    devices = await BleakScanner.discover()
    device = next((d for d in devices if d.address == address), None)
    return device
