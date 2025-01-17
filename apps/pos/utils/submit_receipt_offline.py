from apps.settings.models import OfflineReceipt
from datetime import datetime
from loguru import logger

def save_receipt_offline(invoice_data, cashier):
    """
    Transform invoice data to receipt format and save offline for later submission.
    """
    try:
        data = invoice_data['data'][0]
        items = invoice_data['items']

        receipt_data = {
            "receiptType": "FiscalInvoice",
            "receiptCurrency": "USD",  
            "receiptCounter": 123,  
            "receiptGlobalNo": "12345",
            "receiptDate": datetime.now().isoformat(),
            "receiptLinesTaxInclusive": True,
            "receiptLines": [
                {
                    "receiptLineName": item['product_name'],
                    "receiptLinePrice": float(item['price']),
                    "receiptLineQuantity": item['quantity'],
                    "receiptLineTotal": float(item['price']) * item['quantity'],
                    "taxID": 1  
                }
                for item in items
            ],
            "receiptTaxes": [
                {
                    "taxID": 1,
                    "taxPercent": round(data['vat_amount'] / (float(data['subtotal']) - data['vat_amount']) * 100, 2),
                    "taxAmount": data['vat_amount'],
                    "salesAmountWithTax": float(data['subtotal'])
                }
            ],
            "receiptTotal": data['payable'],
            "customerName": f"Client-{data['client_id']}",
            "cashierName": cashier,  
            "paymentDetails": {
                "paymentMethod": data['payment_method'],
                "amountPaid": data['amount_paid'],
                "recurring": data['recourring'],
                "paymentTerms": data['paymentTerms']
            },
            "additionalDetails": {
                "holdStatus": data['hold_status'],
                "payLaterDate": data['pay_later_date']
            },
            "savedAt": datetime.now().isoformat()
        }

        print(receipt_data)

        receipt = OfflineReceipt(receipt_data=receipt_data)
        receipt.save()

        logger.info(OfflineReceipt.objects.all())

        logger.info(f'Receipt data saved successfully: {receipt}')
        return receipt

    except KeyError as e:
        logger.error(f"KeyError: Missing key in invoice data: {e}")
        raise ValueError(f"Invalid invoice data: {e}")

    except Exception as e:
        logger.error(f"Error saving receipt offline: {e}")
        raise
