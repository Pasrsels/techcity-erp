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
import qrcode, os, binascii
from io import BytesIO
from decimal import Decimal
from apps.finance.models import Invoice, CreditNote
from django.core.files.base import ContentFile

load_dotenv()
#global variables 

tax_amount = 0
total_tax_amount = 0
total_line_amount = 0
receipt_lines = []


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

def generate_credit_note_data(invoice, invoice_items, request):
    """
        Transform invoice data to receipt format, save offline, and submit to FDMS.
    """
    try:
        logger.info(f"Processing Invoice: {invoice.invoice_number}")
        logger.info(f'Invoice items: {invoice_items}')

        fiscal_day = FiscalDay.objects.filter(is_open=True).first()
        # fiscal_day = FiscalDay.objects.filter(is_open=True, created_at__date=datetime.today()).first()
        logger.info(fiscal_day)

        last_global_no = get_last_receipt_numbers()

        new_receipt_global_no = last_global_no + 1

        logger.info(f'Global number: {new_receipt_global_no}, Receipt_counter:{fiscal_day.receipt_count}')

        previous_invoice = Invoice.objects.filter(branch=request.user.branch, issue_date__date=datetime.today()).last() 
        
        logger.info(f'Previous Invoice: {previous_invoice}, id: {previous_invoice.id}')

        logger.info(f'previous hash: {previous_invoice.receipt_hash}')


        for index, item in enumerate(invoice_items, start=1):         
            if item.credit_note_issued:
                logger.info(item.item.name)
                tax_amount = (item.credit_note_amount - round(item.credit_note_amount / Decimal(1.15), 2)) #tax to be dynamic
                total_line_amount += float(item.credit_note_amount)
                total_tax_amount += float(tax_amount)
                
                receipt_lines.append({
                    "receiptLineType": "Sale",
                    "receiptLineNo": index,
                    "receiptLineHSCode": "01010101",
                    "receiptLineName": item.item.name,
                    "receiptLinePrice": float(item.credit_note_amount),
                    "receiptLineQuantity":item.quantity,
                    "receiptLineTotal":float(item.credit_note_amount),
                    "taxCode": "C",
                    "taxPercent": 15.00,
                    "taxID": 3
                })

        logger.info(f'processing totals -> tax amount {tax_amount } total line amount: {total_line_amount} total_tax_amount: {total_tax_amount}')

        receipt_data = {
            "receiptType": "CreditNote",
            "receiptCurrency": invoice.currency.name.upper(),
            "receiptCounter":fiscal_day.receipt_count + 1,
            "receiptGlobalNo":new_receipt_global_no,
            "invoiceNo": f"a{new_receipt_global_no}",
            "receiptNotes": "Customer returned items",
            "receiptDate": datetime.now().replace(microsecond=0).isoformat(),
            "creditDebitNote": {
                "receiptID": invoice.zimra_inv_id,
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
                    "taxPercent": 15.00, # to be dynamic
                    "taxAmount": float(total_tax_amount),
                    "salesAmountWithTax": float(total_line_amount)
                }
            ],
            "receiptPayments": [
                {
                    "moneyTypeCode": invoice.payment_terms,
                    "paymentAmount": float(total_line_amount)
                }
            ],
            "receiptTotal": float(total_line_amount),
            "receiptPrintForm": "Receipt48",
            "previousReceiptHash": "" if fiscal_day.receipt_count == 0 else previous_invoice.receipt_hash,
        }

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

def submit_credit_note(request, receipt_data, credit_note_data, hash, signature, invoice__id, credit_note_id):
    receipt = OfflineReceipt(
        invoice_id=invoice__id,
        receipt_data=credit_note_data
    )
    receipt.save()
    logger.info(f'Receipt saved offline: {receipt}')
    if credit_note_data:
        zimra_instance = ZIMRA()
        invoice = Invoice.objects.get(id=invoice__id)

        response = zimra_instance.submit_receipt({"receipt":receipt_data}, {"receipt":credit_note_data}, hash, signature)
        logger.info(f'response: {response}')
        
        if response:
            invoiceId = response.get('receiptID')
            base_url = "https://fdmstest.zimra.co.zw"
            
            try:
                credit_note = CreditNote.objects.get(id=credit_note_id)
                device_id = f'00000{os.getenv('DEVICE_ID')}'
                receipt_date = datetime.strptime(credit_note_data['receiptDate'], "%Y-%m-%dT%H:%M:%S").strftime('%d%m%Y')
                receipt_global_no = str(credit_note_data['receiptGlobalNo']).zfill(10) #to fix
                receipt_qr_data = generate_verification_code(signature).replace('-', '')
                
                full_url = f"{base_url}/{device_id}{receipt_date}{receipt_global_no}{receipt_qr_data}"

                # Generate QR code
                qr = qrcode.make(full_url)

                qr = qrcode.make(full_url)
                qr_io = BytesIO()
                qr.save(qr_io, format='PNG')
                qr_io.seek(0)
                
                fiscal_day = FiscalDay.objects.filter(created_at__date=datetime.today(), is_open=True).first()
                logger.info(f'fiscal_day: {fiscal_day}')

                credit_note.qr_code.save(f"qr_{credit_note.id}.png", ContentFile(qr_io.getvalue()), save=False)
                code = generate_verification_code(signature)
                
                credit_note.code=code
                credit_note.fiscal_day=fiscal_day.day_no
                credit_note.zimra_inv_id=invoiceId
                
                credit_note.save()
                
                if fiscal_day:

                    fiscal_day.receipt_count += 1

                    fiscal_day.total_sales += credit_note.amount

                    fiscal_day.save()

                    logger.info('Fiscale day incremented.')
                    
<<<<<<< HEAD
                    # salesbytax
=======
                
                # salesbytax -receip data
>>>>>>> refs/remotes/origin/fiscalisation
                fiscal_sale_counter_obj, _sbt = FiscalCounter.objects.get_or_create(
                    fiscal_counter_type='SaleByTax',
                    created_at__date=datetime.today(),
                    fiscal_counter_currency=invoice.currency.name.lower(),

                    defaults={
                        "fiscal_counter_tax_percent":15,
                        "fiscal_counter_tax_id":3,
                        "fiscal_counter_money_type":invoice.payment_terms,
                        "fiscal_counter_value":credit_note_data['receiptTotal']
                    }
                )
                
                logger.info(f'sbt: {_sbt}, {fiscal_sale_counter_obj}')

                if not _sbt:
                    fiscal_sale_counter_obj.fiscal_counter_value += Decimal(credit_note_data['receiptTotal'])
                    fiscal_sale_counter_obj.save()
                    
                logger.info(f'taxes: {credit_note_data['receiptTaxes'][0]['taxAmount']}')

                # Sale Tax By Tax
                fiscal_counter_obj, _stbt = FiscalCounter.objects.get_or_create(
                    fiscal_counter_type='SaleTaxByTax',
                    created_at__date=datetime.today(),
                    fiscal_counter_currency=invoice.currency.name.lower(),
            
                    defaults={
                        "fiscal_counter_tax_percent":15,
                        "fiscal_counter_tax_id":3,
                        "fiscal_counter_money_type":None,
<<<<<<< HEAD
                        "fiscal_counter_value":credit_note_data['receiptTaxes'][0]['taxAmount']
=======
                        "fiscal_counter_value":total_tax_amount
>>>>>>> refs/remotes/origin/fiscalisation
                    }
                )
                
                if not _stbt:
                    fiscal_counter_obj.fiscal_counter_value += Decimal(credit_note_data['receiptTaxes'][0]['taxAmount'])
                    fiscal_counter_obj.save()
<<<<<<< HEAD
                
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
                        "fiscal_counter_value": credit_note_data['receiptTotal']
                    }
                )

                if not _:
                    fiscal_counter_bal_obj.fiscal_counter_value += Decimal(credit_note_data['receiptTotal'])
                    fiscal_counter_bal_obj.save()

=======
          
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
                            "fiscal_counter_value": credit_note.amount
                        }
                    )

                    if not _:
                        fiscal_counter_bal_obj.fiscal_count
                        er_value += total_tax_amount
                        fiscal_counter_bal_obj.save()
                        
                return True
>>>>>>> refs/remotes/origin/fiscalisation
            except Exception as e:
                logger.info(e)
                    
def generate_verification_code(base64_signature):
    decoded_bytes = base64.b64decode(base64_signature)
    hex_string = decoded_bytes.hex()
    
    md5 = hashlib.md5()
    md5.update(binascii.unhexlify(hex_string))
    md5_hash = md5.hexdigest()
    
    verification_code = md5_hash[:16]

    return verification_code.upper()
    
    
    
