from apps.settings.models import OfflineReceipt, FiscalDay
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv
from cryptography.hazmat.backends import default_backend
import hashlib
import base64
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import hashes, serialization
from apps.settings.models import OfflineReceipt, FiscalDay, FiscalCounter
from datetime import datetime
from loguru import logger
from utils.zimra import ZIMRA
import qrcode, os
from io import BytesIO
from apps.finance.models import Invoice
from collections import defaultdict

load_dotenv()


def load_private_key(file_path, password=None):
    with open(file_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=password.encode() if password else None
        )
    return private_key

def receipt_signature(
    device_id, 
    receipt_type, 
    receipt_currency, 
    receipt_global_no, 
    receipt_date, 
    receipt_total, 
    receipt_taxes, 
    previous_receipt_hash=None
):
    
    receipt_total_cents = int(receipt_total * 100)

    def format_tax_line(tax):

        if tax.get('taxPercent') is not None:
            if isinstance(tax['taxPercent'], int):
                tax_percent = f"{tax['taxPercent']}.00"
            else:
                tax_percent = f"{tax['taxPercent']:.2f}"
        else:
            tax_percent = ""
        
        tax_amount_cents = int(tax['taxAmount'] * 100)
        sales_amount_cents = int(tax['salesAmountWithTax'] * 100)
        
        return f"{tax.get('taxCode')}{tax_percent}{tax_amount_cents}{sales_amount_cents}"
    
    sorted_taxes = sorted(
        receipt_taxes, 
        key=lambda x: (x['taxID'], x.get('taxCode', ''))
    )
    
    tax_string = ''.join(format_tax_line(tax) for tax in sorted_taxes)
    
    signature_components = [
        str(device_id),
        receipt_type.upper(),
        receipt_currency.upper(),
        str(receipt_global_no),
        receipt_date,
        str(receipt_total_cents),
        tax_string
    ]

    if previous_receipt_hash:
        signature_components.append(previous_receipt_hash)
    return ''.join(signature_components)

def generate_receipt_signature(signature_string, private_key):
    
    logger.info(signature_string)
    
    receipt_hash = hashlib.sha256(signature_string.encode('utf-8')).digest()

    signature = private_key.sign(
        receipt_hash,
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    signature_base64 = base64.b64encode(signature).decode()
    decoded_receipt_hash = base64.b64encode(receipt_hash).decode()

    return signature_base64, decoded_receipt_hash

def get_last_receipt_numbers():
    """Fetch the last receiptGlobalNo and receiptCounter"""
    last_receipt = OfflineReceipt.objects.order_by("-id").first()

    last_global_no = last_receipt.receipt_data["receiptGlobalNo"] if last_receipt else 0

    return last_global_no

def generate_receipt_data(invoice, invoice_items, request):
    """
        Transform invoice data to receipt format, save offline, and submit to FDMS.
    """
    logger.info('here')
    try:
        fiscal_day = FiscalDay.objects.filter(is_open=True).first()
        logger.info(fiscal_day)
        logger.info(f"Processing Invoice: {invoice.invoice_number} {invoice}")

        last_global_no = get_last_receipt_numbers()
        logger.info(last_global_no)
        new_receipt_global_no = last_global_no + 1
        logger.info(f'Global number: {new_receipt_global_no}')

        receipt_lines = []
        total_tax_amount = 0
        tax_group_totals = defaultdict(lambda: {"taxAmount": 0.00, "salesAmountWithTax": 0.00})
        logger.info('here jjj')
        
        previous_invoice = Invoice.objects.filter(
            issue_date__date=datetime.today()
        ).exclude(id=invoice.id).order_by('-id').first()
        
        logger.info('invoice items')

        for index, item in enumerate(invoice_items, start=1):
            print(item)
            line_total = float(item.unit_price) * item.quantity
            
            logger.info(f'Line total: {line_total}')

            # Determine tax details
            tax_name = item.item.tax_type.name
            tax_id = item.item.tax_type.tax_id
            tax_percent = item.item.tax_type.tax_percent  # None for exempt
            tax_code = item.item.tax_type.tax_code        # e.g., "A", "B", "C"

            print('here')
            # Calculate tax amount
            if tax_percent is not None:
                tax_amount = round(line_total * (tax_percent / (100 + tax_percent)), 2)
            else:
                tax_amount = 0.00

            # Accumulate tax group totals
            key = (tax_id, tax_percent, tax_code)
            tax_group_totals[key]["taxAmount"] += tax_amount
            tax_group_totals[key]["salesAmountWithTax"] += line_total

            # Add line
            line_data = {
                "receiptLineType": "Sale",
                "receiptLineNo": index,
                "receiptLineHSCode": "01010101",
                "receiptLineName": item.item.name,
                "receiptLinePrice": float(item.unit_price),
                "receiptLineQuantity": item.quantity,
                "receiptLineTotal": line_total,
                "taxID": tax_id,
                "taxCode": tax_code
            }
            if tax_percent is not None:
                line_data["taxPercent"] = float(tax_percent)

            receipt_lines.append(line_data)
            total_tax_amount += tax_amount
            
        print('done')

        # Construct receiptTaxes from actual usage
        receipt_taxes = []
        for (tax_id, tax_percent, tax_code), totals in tax_group_totals.items():
            tax_obj = {
                "taxID": tax_id,
                "taxCode": tax_code,
                "taxAmount": round(totals["taxAmount"], 2),
                "salesAmountWithTax": round(totals["salesAmountWithTax"], 2)
            }
            if tax_percent is not None:
                tax_obj["taxPercent"] = float(tax_percent)
            receipt_taxes.append(tax_obj)

        receipt_data = {
            "receiptType": "FiscalInvoice",
            "receiptCurrency": invoice.currency.name.upper(),
            "receiptCounter": fiscal_day.receipt_count + 1,
            "receiptGlobalNo": new_receipt_global_no,
            "invoiceNo": f"a{new_receipt_global_no}",
            "receiptNotes": "Thank you for shopping with us!",
            "receiptDate": datetime.now().replace(microsecond=0).isoformat(),
            "receiptLinesTaxInclusive": True,
            "receiptLines": receipt_lines,
            "receiptTaxes": receipt_taxes,
            "receiptPayments": [
                {
                    "moneyTypeCode": invoice.payment_terms,
                    "paymentAmount": float(invoice.amount)
                }
            ],
            "receiptTotal": float(invoice.amount),
            "receiptPrintForm": "Receipt48",
            "previousReceiptHash": "" if fiscal_day.receipt_count == 0 else previous_invoice.receipt_hash,
        }

        print(receipt_data)
        signature_data = receipt_signature(
            os.getenv('DEVICE_ID'), 
            receipt_data['receiptType'],
            receipt_data['receiptCurrency'],
            receipt_data['receiptGlobalNo'],
            receipt_data['receiptDate'],
            receipt_data['receiptTotal'],
            receipt_data['receiptTaxes'],
            receipt_data['previousReceiptHash'],
        )
        
        logger.info(f'Signature data: {signature_data}')
        logger.info(f'Receipt_data: {receipt_data}')
    except Exception as e:
        logger.error(f"Error generating receipt data: {e}")
        return (f"Error saving receipt offline: {e}")

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

            # Updated to remove branch filtering like in the second code
            invoice = Invoice.objects.filter(issue_date__date=datetime.today()).order_by('-id').first()

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

            # Updated fiscal counter logic using the improved approach from the second code
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