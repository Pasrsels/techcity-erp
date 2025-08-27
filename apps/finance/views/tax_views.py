from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from ..models import VATTransaction
from apps.core.settings.models import OfflineReceipt, FiscalDay, FiscalCounter
from utils.zimra import ZIMRA
import datetime
from datetime import timedelta
import json
from loguru import logger

zimra = ZIMRA()

@login_required
def vat(request):
    if request.method == 'GET':

        filter_option = request.GET.get('filter', 'today')
        download = request.GET.get('download')

        now = datetime.datetime.now()
        end_date = now

        if filter_option == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif filter_option == 'this_week':
            start_date = now - timedelta(days=now.weekday())
        elif filter_option == 'yesterday':
            start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif filter_option == 'this_month':
            start_date = now.replace(day=1)
        elif filter_option == 'last_month':
            start_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
        elif filter_option == 'this_year':
            start_date = now.replace(month=1, day=1)
        elif filter_option == 'custom':
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        else:
            start_date = now - timedelta(days=now.weekday())
            end_date = now

        vat_transactions = VATTransaction.objects.filter(date__gte=start_date, date__lte=end_date).order_by('-date')

        if download:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="vat_report_{filter_option}.csv"'

            writer = csv.writer(response)
            writer.writerow(['Date', 'Description', 'Status', 'Input', 'Output'])

            balance = 0
            for transaction in vat_transactions:

                if transaction.vat_type == 'Input':
                    balance += transaction.tax_amount
                else:
                    balance -= transaction.tax_amount

                writer.writerow([
                    transaction.date,
                    transaction.invoice.invoice_number if transaction.invoice else transaction.purchase_order.order_number,
                    transaction.tax_amount if transaction.vat_type == 'Input' else  '',
                    transaction.tax_amount if transaction.vat_type == 'Output' else  ''
                ])

            writer.writerow(['Total', '', '', balance])

            return response
        return render(request, 'vat.html',
            {
                'filter_option':filter_option,
                'vat_transactions':vat_transactions
            }
        )

    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            date_to = data.get('date_to')
            date_from = data.get('date_from')

            vat_transactions = VATTransaction.objects.filter(
                date__gte=date_from,
                date__lte=date_to
            )

            vat_transactions.update(paid=True)
        except Exception as e:
            return JsonResponse({'success':False, 'message':f'{e}'}, status = 400)
        return JsonResponse({'success':False, 'message':'VAT successfully paid'}, status = 200)

@login_required
def tax(request):
    tax_receipts = OfflineReceipt.objects.all()
    return render(request, 'tax/tax.html', {
        'tax_receipts':tax_receipts,
        'receipts_count':tax_receipts.count(),
    })

@login_required
def get_config(request):
    try:
        get_config_response = zimra.get_config()
        logger.info(get_config_response)
        return JsonResponse({'success':True, 'data':get_config_response})
    except Exception as e:
        return JsonResponse({'success':False, 'message':f'{e}'})

@login_required
def open_fiscal_day(request):
    try:
        open_day_response = zimra.open_day()
        return JsonResponse({'success': True, 'data': open_day_response})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'{e}'})

@login_required
def check_fiscal_status(request):

    fiscal_day = FiscalDay.objects.filter(created_at__date=datetime.datetime.today(), is_open=True).first()

    if fiscal_day:
        return  JsonResponse({'success':True, 'message':False}, status=200)

    return JsonResponse({'success':False, 'message':True}, status=400)

@login_required
def close_fiscal_day(request):
    if request.method == 'GET':
        try:
            fiscal_day = FiscalDay.objects.filter(created_at__date=datetime.datetime.today(), is_open=True).first()
            if not fiscal_day:
                return JsonResponse({'success': False, 'message': 'No open fiscal day found for today'}, status=404)

            fiscal_day_counters = FiscalCounter.objects.filter(created_at__date=datetime.datetime.today())

            sale_by_tax_string = ""
            sale_tax_by_tax_string = ""
            balance_money_string = ""

            sale_by_tax_dict = {}
            sale_tax_by_tax_dict = {}
            balance_by_currency_and_type = {}

            for counter in fiscal_day_counters:
                counter_type = counter.fiscal_counter_type.upper()
                counter_currency = counter.fiscal_counter_currency.upper().replace("ZWL", "ZIG")
                counter_value = int(counter.fiscal_counter_value * 100)

                if counter_type == "BALANCEBYMONEYTYPE":
                    money_type = counter.fiscal_counter_money_type.upper()
                    key = f"{counter_currency}_{money_type}"
                    if key not in balance_by_currency_and_type:
                        balance_by_currency_and_type[key] = {"type": counter_type, "currency": counter_currency, "money_type": money_type, "value": 0}
                    balance_by_currency_and_type[key]["value"] += counter_value

                elif counter_type == "SALEBYTAX":
                    tax_percent = float(counter.fiscal_counter_tax_percent)
                    key = f"{counter_currency}_{tax_percent}"
                    if key not in sale_by_tax_dict:
                        sale_by_tax_dict[key] = {"type": counter_type, "currency": counter_currency, "tax_percent": tax_percent, "value": 0}
                    sale_by_tax_dict[key]["value"] += counter_value

                elif counter_type == "SALETAXBYTAX":
                    tax_percent = float(counter.fiscal_counter_tax_percent)
                    key = f"{counter_currency}_{tax_percent}"
                    if key not in sale_tax_by_tax_dict:
                        sale_tax_by_tax_dict[key] = {"type": counter_type, "currency": counter_currency, "tax_percent": tax_percent, "value": 0}
                    sale_tax_by_tax_dict[key]["value"] += counter_value

            for key, data in sale_by_tax_dict.items():
                tax_percent = format_tax_percent(data["tax_percent"])
                sale_by_tax_string += f"{data['type']}{data['currency']}{tax_percent}{data['value']}"

            for key, data in sale_tax_by_tax_dict.items():
                tax_percent = format_tax_percent(data["tax_percent"])
                sale_tax_by_tax_string += f"{data['type']}{data['currency']}{tax_percent}{data['value']}"

            for key, data in balance_by_currency_and_type.items():
                balance_money_string += f"{data['type']}{data['currency']}{data['money_type']}{data['value']}"

            fiscal_day_counters_string = sale_by_tax_string + sale_tax_by_tax_string + balance_money_string

            hash_input = f"{ZIMRA.device_identification}{fiscal_day.day_no}{datetime.datetime.today().date()}{fiscal_day_counters_string}"

            return JsonResponse({'success': True, 'data': hash_input}, status=200)

        except Exception as e:
            return JsonResponse({'success': False, 'message': f'{str(e)}'}, status=400)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            signature_string = data.get('sig_string')

            if not signature_string:
                return JsonResponse({'message':'Hash data missing.', 'success':False})

            fiscal_day_counters = FiscalCounter.objects.filter(created_at__date=datetime.datetime.today())
            from utils.zimra_sig_hash import run
            day_signature = run(signature_string)

            close_day_response = zimra.close_day(day_signature['hash'], day_signature['signature'], fiscal_day_counters)

            return JsonResponse({'message':close_day_response, 'success':True})

        except Exception as e:
            return JsonResponse({'success':False, 'message':f'{e}'}, status=400)

def format_tax_percent(tax_percent):
    if tax_percent == int(tax_percent):
        return f"{int(tax_percent)}.00"
    else:
        return f"{tax_percent:.2f}"

@login_required
def submit_z_report(request):
    try:
        z_report_response = zimra.z_report()
        return JsonResponse({'success': True, 'data': z_report_response})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'{e}'})
