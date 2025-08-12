import unittest
from unittest.mock import patch, MagicMock
from utils.new_zimra import Device
import datetime

class TestZimraDevice(unittest.TestCase):

    def setUp(self):
        self.device = Device(test_mode=True)

    def test_tax_calculator(self):
        self.assertAlmostEqual(self.device.tax_calculator(115, 15), 15.00)
        self.assertAlmostEqual(self.device.tax_calculator(100, 0), 0.00)

    def test_concatenate_receipt_taxes(self):
        receipt_taxes = [
            {'taxID': 1, 'taxPercent': 15.0, 'taxAmount': 15.00, 'salesAmountWithTax': 115.00},
            {'taxID': 2, 'taxPercent': 0.0, 'taxAmount': 0.00, 'salesAmountWithTax': 50.00}
        ]
        concatenated_string = self.device.concatenate_receipt_taxes(receipt_taxes)
        self.assertEqual(concatenated_string, '15.001500115000.0005000')

    @patch('utils.new_zimra.RSA.import_key')
    @patch('utils.new_zimra.pkcs1_15.new')
    def test_sign_data(self, mock_pkcs1_15, mock_import_key):
        # Mock the private key and signature
        mock_key = MagicMock()
        mock_import_key.return_value = mock_key
        mock_signer = MagicMock()
        mock_pkcs1_15.return_value = mock_signer
        mock_signer.sign.return_value = b'signed_data'

        # Call the method
        signature = self.device.sign_data('test_data')

        # Assert the signature is correct
        self.assertEqual(signature, 'c2lnbmVkX2RhdGE=')

    def test_prepare_receipt(self):
        receipt_data = {
            "receiptType": "FISCALINVOICE",
            "receiptCurrency": "USD",
            "receiptCounter": 1,
            "receiptGlobalNo": 1,
            "invoiceNo": "INV-001",
            "receiptDate": datetime.datetime.now(),
            "receiptLines": [
                {
                    "item_name": "Test Item",
                    "unit_price": 100,
                    "quantity": 1,
                    "tax_percent": 15.0
                }
            ],
            "receiptPayments": [
                {
                    "paymentType": "CASH",
                    "paymentAmount": 115.00
                }
            ]
        }
        prepared_receipt = self.device.prepareReceipt(receiptData=receipt_data)
        self.assertIn('receiptDeviceSignature', prepared_receipt)
        self.assertIn('hash', prepared_receipt['receiptDeviceSignature'])
        self.assertIn('signature', prepared_receipt['receiptDeviceSignature'])

    def test_close_day(self):
        fiscal_day_counters = [
            {
                'fiscalCounterType': 'SaleByTax',
                'fiscalCounterCurrency': 'USD',
                'fiscalCounterTaxPercent': 15.0,
                'fiscalCounterTaxID': 3,
                'fiscalCounterValue': 115.00
            }
        ]

        with patch('utils.new_zimra.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success"}
            mock_post.return_value = mock_response

            response = self.device.closeDay(
                fiscalDayNo=1,
                fiscalDayDate=datetime.date.today(),
                lastReceiptCounterValue=1,
                fiscalDayCounters=fiscal_day_counters
            )
            self.assertEqual(response, {"status": "success"})

if __name__ == '__main__':
    unittest.main()
