from apps.settings.models import OfflineReceipt, FiscalDay
from datetime import datetime
from loguru import logger
from utils.zimra import ZIMRA
import qrcode
from io import BytesIO
from apps.settings.models import FiscalCounter
from apps.finance.models import Invoice

def submit_receipt_data(request, receipt_data, hash, signature):
    try:

        receipt = OfflineReceipt(receipt_data=receipt_data)
        receipt.save()
        logger.info(f'Receipt saved offline: {receipt}')
    
        zimra_instance = ZIMRA()
        response = zimra_instance.submit_receipt({"receipt":receipt_data}, hash, signature)
        logger.info(f"Receipt submission response: {response}")

        if response:
            logger.info('here')

            invoice = Invoice.objects.filter(issue_date__date=datetime.today(), branch=request.user.branch).order_by('-id').first()

            invoice.receiptServerSignature = signature
            invoice.receipt_hash = hash

            qr = qrcode.make(hash)
            qr_io = BytesIO()
            qr.save(qr_io, format='PNG')
            qr_io.seek(0)

            from django.core.files.base import ContentFile
            invoice.qr_code.save(f"qr_{invoice.invoice_number}.png", ContentFile(qr_io.getvalue()), save=False)
            try:
                invoice.save()
            except Exception as e:
                print(e)

            fiscal_day = FiscalDay.objects.filter(created_at__date=datetime.today(), is_open=True).first()
            logger.info(f'fiscal_day: {fiscal_day}')

            if fiscal_day:

                fiscal_day.receipt_count += 1

                fiscal_day.total_sales += invoice.amount

                fiscal_day.save()

                logger.info('Fiscale day incremented.')

            # salesbytax
            fiscal_sale_counter_obj, _sbt = FiscalCounter.objects.get_or_create(
                fiscal_counter_type='SaleByTax',
                created_at__date=datetime.today(),
                fiscal_counter_currency=invoice.currency.name.lower(),

                defaults={
                    "fiscal_counter_tax_percent":15,
                    "fiscal_counter_tax_id":3,
                    "fiscal_counter_money_type":"Cash", #to be dynamic
                    "fiscal_counter_value":invoice.amount
                }
            )

            if not _sbt:
                fiscal_sale_counter_obj.fiscal_counter_value += invoice.amount
                fiscal_sale_counter_obj.save()

            # Sale Tax By Tax
            fiscal_counter_obj, _stbt = FiscalCounter.objects.get_or_create(
                fiscal_counter_type='SaleTaxByTax',
                created_at__date=datetime.today(),
                fiscal_counter_currency=invoice.currency.name.lower(),

                defaults={
                    "fiscal_counter_tax_percent":15,
                    "fiscal_counter_tax_id":3,
                    "fiscal_counter_money_type":None,
                    "fiscal_counter_value":invoice.vat
                }
            )
            
            if not _stbt:
                fiscal_counter_obj.fiscal_counter_value += invoice.vat
                fiscal_counter_obj.save()

            
            try:
                # Balance By Money Type
                fiscal_counter_bal_obj, _ = FiscalCounter.objects.get_or_create(
                    fiscal_counter_type="Balancebymoneytype",
                    created_at__date=datetime.today(),
                    fiscal_counter_currency=invoice.currency.name.lower(),

                    defaults={
                        "fiscal_counter_tax_percent": None,
                        "fiscal_counter_tax_id": 0,
                        "fiscal_counter_tax_percent": 0,
                        "fiscal_counter_money_type": "Cash", # payment type to be dynamic
                        "fiscal_counter_value": invoice.amount
                    }
                )

                if not _:
                    fiscal_counter_bal_obj.fiscal_counter_value += invoice.amount
                    fiscal_counter_bal_obj.save()

            except Exception as e:
                logger.error(f'{e}')

            logger.info("Receipt signature and QR code saved to invoice.")

    except KeyError as e:
        logger.error(f"KeyError: Missing key in invoice data: {e}")
        raise ValueError(f"Invalid invoice data: {e}")