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

        previous_invoice = Invoice.objects.filter(
            branch=request.user.branch,
            issue_date__date=datetime.today()
        ).exclude(id=invoice.id).order_by('-id').first()

        for index, item in enumerate(invoice_items, start=1):
            line_total = float(item.unit_price) * item.quantity

            # Determine tax details
            tax_name = item.item.tax_type.name
            tax_id = item.item.tax_type.tax_id
            tax_percent = item.item.tax_type.tax_percent  # None for exempt
            tax_code = item.item.tax_type.tax_code        # e.g., "A", "B", "C"

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
                    "paymentAmount": float(invoice.amount_paid)
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

        return signature_data, receipt_data

    except Exception as e:
        logger.exception("Error generating receipt data")
        return None
    

