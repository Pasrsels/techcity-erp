from apps.settings.models import OfflineReceipt, FiscalDay
from datetime import datetime
from loguru import logger
from utils.zimra import ZIMRA
import qrcode
from io import BytesIO
from apps.settings.models import FiscalCounter
from apps.finance.models import Invoice
import hashlib
import os
import base64
import binascii
from collections import defaultdict
from decimal import Decimal
from django.utils.timezone import now

def submit_receipt_data(request, receipt_data, credit_note, hash, signature, invoice__id):
    logger.info(invoice__id)
    try:

        receipt = OfflineReceipt(
            invoice_id=invoice__id,
            receipt_data=receipt_data
        )
        receipt.save()
        logger.info(f'Receipt saved offline: {receipt}')
    
        zimra_instance = ZIMRA()
        response = zimra_instance.submit_receipt({"receipt":receipt_data}, {"receipt":credit_note}, hash, signature)
        logger.info(f"Receipt submission response: {response}")

        invoiceId = response.get('receiptID')
        logger.info(f'Zimra invoice id: {invoiceId}')

        if response:
            logger.info('here')

            invoice = Invoice.objects.filter(issue_date__date=datetime.today(), branch=request.user.branch).order_by('-id').first()

            invoice.receiptServerSignature = signature
            invoice.receipt_hash = hash

            base_url = "https://fdmstest.zimra.co.zw"
            
            device_id = f'00000{os.getenv('DEVICE_ID')}'
            receipt_date = datetime.strptime(receipt_data['receiptDate'], "%Y-%m-%dT%H:%M:%S").strftime('%d%m%Y')
            receipt_global_no = str(receipt_data['receiptGlobalNo']).zfill(10) #to fix
            receipt_qr_data = generate_verification_code(signature).replace('-', '')
            
            logger.info(f'{device_id}, {receipt_date}, {receipt_global_no} {receipt_qr_data}')

            # qr_url = "https://invoice.zimra.co.zw"  
            full_url = f"{base_url}/{device_id}{receipt_date}{receipt_global_no}{receipt_qr_data}"

            # Generate QR code
            qr = qrcode.make(full_url)

            qr = qrcode.make(full_url)
            qr_io = BytesIO()
            qr.save(qr_io, format='PNG')
            qr_io.seek(0)
                        
            from django.core.files.base import ContentFile
            
            fiscal_day = FiscalDay.objects.filter(created_at__date=datetime.today(), is_open=True).first()
            logger.info(f'fiscal_day: {fiscal_day}')

            invoice.qr_code.save(f"qr_{invoice.invoice_number}.png", ContentFile(qr_io.getvalue()), save=False)
            code = generate_verification_code(signature)
            logger.info(code)
            
            try:
                invoice.code=code
                invoice.fiscal_day=fiscal_day.day_no
                invoice.invoice_number = f"{receipt_data['receiptGlobalNo']}"

                if invoiceId:
                    invoice.zimra_inv_id = invoiceId
                
                invoice.save()
                logger.info(f'invoice saved: {invoice}')
            except Exception as e:
                logger.info(e)

            if fiscal_day:

                fiscal_day.receipt_count += 1

                fiscal_day.total_sales += invoice.amount

                fiscal_day.save()

                logger.info('Fiscale day incremented.')

            invoice_items = invoice.invoice_items.all()
            grouped = defaultdict(lambda: {
                "amount": Decimal("0.00"),
                "vat": Decimal("0.00")
            })

            for item in invoice_items:
                
                rate = item.vat_rate.rate  
                tax_id = item.item.tax_type.tax_id
                key = (invoice.currency.name.lower(), rate, tax_id)
                grouped[key]["amount"] += item.total_amount
                grouped[key]["vat"] += item.vat_amount

            today = now().date()

            for (currency, rate, tax_id), values in grouped.items():
                if values["amount"] == 0:
                    continue 

                # --- SALEBYTAX ---
                sale_counter = FiscalCounter.objects.filter(
                    fiscal_counter_type='SaleByTax',
                    fiscal_counter_currency=currency,
                    fiscal_counter_tax_percent=rate,
                    fiscal_counter_tax_id=tax_id,
                    created_at__date=today
                ).first()

                if sale_counter:
                    sale_counter.fiscal_counter_value += values["amount"]
                    sale_counter.save()
                else:
                    FiscalCounter.objects.create(
                        fiscal_counter_type='SaleByTax',
                        fiscal_counter_currency=currency,
                        fiscal_counter_tax_percent=rate,
                        fiscal_counter_tax_id=tax_id,
                        fiscal_counter_money_type=None,
                        fiscal_counter_value=values["amount"]
                    )

                # --- SALETAXBYTAX ---
                if rate is not None and rate > 0:
                    tax_counter = FiscalCounter.objects.filter(
                        fiscal_counter_type='SaleTaxByTax',
                        fiscal_counter_currency=currency,
                        fiscal_counter_tax_percent=rate,
                        fiscal_counter_tax_id=tax_id,
                        created_at__date=today
                    ).first()

                    if tax_counter:
                        tax_counter.fiscal_counter_value += values["vat"]
                        tax_counter.save()
                    else:
                        FiscalCounter.objects.create(
                            fiscal_counter_type='SaleTaxByTax',
                            fiscal_counter_currency=currency,
                            fiscal_counter_tax_percent=rate,
                            fiscal_counter_tax_id=tax_id,
                            fiscal_counter_money_type=None,
                            fiscal_counter_value=values["vat"]
                        )
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
                        "fiscal_counter_money_type": invoice.payment_terms,
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
    
def generate_verification_code(base64_signature):
    decoded_bytes = base64.b64decode(base64_signature)
    hex_string = decoded_bytes.hex()
    
    md5 = hashlib.md5()
    md5.update(binascii.unhexlify(hex_string))
    md5_hash = md5.hexdigest()
    
    verification_code = md5_hash[:16]

    return verification_code.upper()
