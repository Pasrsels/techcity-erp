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


def generate_credit_note_number(credit_note):
    last_credit_note = CreditNote.objects.filter(branch=credit_note.branch).order_by('-id').first()
    if last_credit_note:
        last_number = int(last_credit_note.credit_note_number.split('-')[2])
        new_number = last_number + 1
        return f"{credit_note.branch.name}-CN-{new_number:06d}"
    return f"{credit_note.branch.name}-CN-000001"
    
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

def get_receipt_global_no(invoice):
    receipt = OfflineReceipt.objects.filter(invoice=invoice).first()
    return receipt.receipt_data["receiptGlobalNo"] if receipt else 0

def generate_receipt_data(invoice, invoice_items, request):
    """
        Transform invoice data to receipt format, save offline, and submit to FDMS.
    """
    try:
        logger.info(f"Processing Invoice: {invoice.invoice_number}")

        fiscal_day = FiscalDay.objects.filter(is_open=True, created_at__date=datetime.today()).first()
        logger.info(fiscal_day)
        if not fiscal_day:
            zimra = ZIMRA()
            zimra.open_day()

        last_global_no = get_last_receipt_numbers()

        new_receipt_global_no = last_global_no + 1

        logger.info(f'Global number: {new_receipt_global_no}, Receipt_counter:{fiscal_day.receipt_count}')

        receipt_lines = []
        total_tax_amount = 0

        previous_invoice = Invoice.objects.filter(branch=request.user.branch, issue_date__date=datetime.today())\
            .exclude(id=invoice.id)\
            .order_by('-id')\
            .first()  
        

        logger.info(f'Previous Invoice: {previous_invoice}')

        total_tax_amount = 0
        total_line_amount = 0
        for index, item in enumerate(invoice_items, start=1):
            line_total = float(item.unit_price) * item.quantity
            tax_amount = round(line_total / 1.15, 2)
            total_tax_amount += tax_amount
            
            if item.credit_note_amount > 0:

                receipt_lines.append({
                    "receiptLineType": "Sale",
                    "receiptLineNo": index,
                    "receiptLineHSCode": "01010101",
                    "receiptLineName": item.item.name,
                    "receiptLinePrice": -float(item.credit_note_amount),
                    "taxCode": "C",
                    "taxPercent": 15.00,
                    "taxID": 3
                })

                tax_amount = round(item.credit_note_amount / 1.15, 2)
                total_line_amount += item.credit_note_amount
                total_tax_amount += tax_amount

        receipt_data = {
            "receiptType": "FiscalInvoice",
            "receiptCurrency": invoice.currency.name.upper(),
            "receiptCounter":fiscal_day.receipt_count + 1,
            "receiptGlobalNo":new_receipt_global_no,
            "invoiceNo": invoice.invoice_number,
            "receiptNotes": "Customer returned items",
            "receiptDate": datetime.now().replace(microsecond=0).isoformat(),
            "creditDebitNote": {
                "receiptID": invoice.id,
                "deviceID": os.getenv('DEVICE_ID'),
                "receiptGlobalNo": get_receipt_global_no(invoice),
                "fiscalDayNo": fiscal_day.id
            },
            "receiptLinesTaxInclusive": True,
            "receiptLines": receipt_lines,
            "receiptTaxes": [
                {
                    "taxCode": "C",
                    "taxID": 3,
                    "taxPercent": 15.00,
                    "taxAmount": -float(total_tax_amount),
                    "salesAmountWithTax": -(float(total_line_amount) - float(total_tax_amount))
                }
            ],
            "receiptPayments": [
                {
                    "moneyTypeCode": invoice.payment_terms,
                    "paymentAmount": -(float(total_line_amount) - float(total_tax_amount))
                }
            ],
            "receiptTotal": -(float(total_line_amount) - float(total_tax_amount)),
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

        return signature_data, receipt_data
    except Exception as e:
        return (f"Error saving receipt offline: {e}")

