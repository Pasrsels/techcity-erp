import json
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from apps.finance.models import (
    Currency, 
    Account, 
    AccountBalance, 
    ChartOfAccounts,
    VATRate, 
    Customer, 
    CustomerAccount, 
    CustomerAccountBalances,
    COGS, 
    Invoice, 
    InvoiceItem, 
    Transaction, 
    VATTransaction, 
    Sale, 
    Payment,
    layby, 
    laybyDates, 
    recurringInvoices, 
    Branch
)
from apps.inventory.models import (
    Inventory,
    ActivityLog,
    Accessory
)
from apps.finance.utils import update_latest_due


class CreateInvoiceViewTest(TestCase):
    def setUp(self):
        # Create test user with branch
        self.branch = Branch.objects.create(name="Test Branch")
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword',
            email='test@example.com'
        )
        self.user.branch = self.branch
        self.user.save()
        
        # Create test currency
        self.currency = Currency.objects.create(name="USD", symbol="$")
        
        # Create test VAT rate
        self.vat_rate = VATRate.objects.create(rate=15, status=True)
        
        # Create test customer
        self.customer = Customer.objects.create(
            name="Test Customer",
            email="customer@example.com",
            phone="1234567890",
        )
        
        # Create customer account
        self.customer_account = CustomerAccount.objects.create(customer=self.customer)
        
        # Create customer account balance
        self.customer_balance = CustomerAccountBalances.objects.create(
            account=self.customer_account,
            currency=self.currency,
            balance=Decimal('0.00')
        )
        
        # Create test inventory items
        self.inventory_item1 = Inventory.objects.create(
            name="Test Product 1",
            description="Test Description",
            quantity=100,
            cost=Decimal('50.00'),
            price=Decimal('100.00'),
            branch=self.branch
        )
        
        self.inventory_item2 = Inventory.objects.create(
            name="Test Product 2",
            description="Test Description",
            quantity=50,
            cost=Decimal('75.00'),
            price=Decimal('150.00'),
            branch=self.branch
        )
        
        # Create accounts receivable
        self.accounts_receivable = ChartOfAccounts.objects.create(name="Accounts Receivable")
        
        # Factory for creating requests
        self.factory = RequestFactory()
        
        # Patch generate_invoice_number function
        patcher = patch('apps.finance.models.Invoice.generate_invoice_number', return_value='INV-2025-0001')
        self.addCleanup(patcher.stop)
        self.mock_gen_invoice = patcher.start()

    @patch('apps.finance.utils.update_latest_due')
    def test_successful_invoice_creation(self, mock_update_latest_due):
        """Test successful invoice creation with full payment"""
        mock_update_latest_due.return_value = Decimal('250.00')
        
        # Login
        self.client.login(username='testuser', password='testpassword')
        
        # Prepare invoice data
        invoice_data = {
            'data': [{
                'client_id': self.customer.id,
                'currency': self.currency.id,
                'payment_method': 'cash',
                'amount_paid': '250.00',
                'payable': '250.00',
                'vat_amount': '32.61',
                'subtotal': '217.39',
                'recourring': False,
                'paymentTerms': 'normal',
                'hold_status': False
            }],
            'items': [
                {
                    'inventory_id': self.inventory_item1.id,
                    'product_name': 'Test Product 1',
                    'quantity': 2,
                    'price': '100.00'
                },
                {
                    'inventory_id': self.inventory_item2.id,
                    'product_name': 'Test Product 2',
                    'quantity': 1,
                    'price': '50.00'
                }
            ]
        }
        
        # Create the request
        url = reverse('finance:create_invoice')
        response = self.client.post(
            url, 
            data=json.dumps(invoice_data),
            content_type='application/json'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('invoice_id', response_data)
        
        # Verify invoice was created
        invoice = Invoice.objects.get(id=response_data['invoice_id'])
        self.assertEqual(invoice.customer, self.customer)
        self.assertEqual(invoice.amount, Decimal('250.00'))
        self.assertEqual(invoice.amount_paid, Decimal('250.00'))
        self.assertEqual(invoice.amount_due, Decimal('0.00'))
        self.assertEqual(invoice.payment_status, Invoice.PaymentStatus.PAID)
        
        # Verify inventory was updated
        self.inventory_item1.refresh_from_db()
        self.inventory_item2.refresh_from_db()
        self.assertEqual(self.inventory_item1.quantity, 98)
        self.assertEqual(self.inventory_item2.quantity, 49)
        
        # Verify invoice items were created
        self.assertEqual(InvoiceItem.objects.filter(invoice=invoice).count(), 2)
        
        # Verify transaction was created
        self.assertEqual(Transaction.objects.filter(customer=self.customer).count(), 1)
        
        # Verify activity logs were created
        self.assertEqual(ActivityLog.objects.filter(invoice=invoice).count(), 2)

    @patch('apps.finance.utils.views.update_latest_due')
    def test_partial_payment_invoice(self, mock_update_latest_due):
        """Test invoice creation with partial payment"""
        mock_update_latest_due.return_value = Decimal('100.00')
        
        self.client.login(username='testuser', password='testpassword')
        
        invoice_data = {
            'data': [{
                'client_id': self.customer.id,
                'currency': self.currency.id,
                'payment_method': 'bank',
                'amount_paid': '100.00',
                'payable': '250.00',
                'vat_amount': '32.61',
                'subtotal': '217.39',
                'recourring': False,
                'paymentTerms': 'normal',
                'hold_status': False
            }],
            'items': [
                {
                    'inventory_id': self.inventory_item1.id,
                    'product_name': 'Test Product 1',
                    'quantity': 1,
                    'price': '100.00'
                },
                {
                    'inventory_id': self.inventory_item2.id,
                    'product_name': 'Test Product 2',
                    'quantity': 1,
                    'price': '150.00'
                }
            ]
        }
        
        url = reverse('create_invoice')
        response = self.client.post(
            url, 
            data=json.dumps(invoice_data),
            content_type='application/json'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Verify invoice
        invoice = Invoice.objects.get(id=response_data['invoice_id'])
        self.assertEqual(invoice.amount_paid, Decimal('100.00'))
        self.assertEqual(invoice.amount_due, Decimal('150.00'))
        self.assertEqual(invoice.payment_status, Invoice.PaymentStatus.PARTIAL)
        
        # Verify customer account balance was updated
        self.customer_balance.refresh_from_db()
        self.assertEqual(self.customer_balance.balance, Decimal('-150.00'))

    @patch('apps.pos.utils.views.save_receipt_offline')
    def test_layby_invoice_creation(self, mock_save_receipt):
        """Test creating a layby invoice with scheduled payments"""
        self.client.login(username='testuser', password='testpassword')
        
        # Prepare layby dates
        layby_dates = [
            str(timezone.now().date() + timezone.timedelta(days=30)),
            str(timezone.now().date() + timezone.timedelta(days=60))
        ]
        
        invoice_data = {
            'data': [{
                'client_id': self.customer.id,
                'currency': self.currency.id,
                'payment_method': 'cash',
                'amount_paid': '50.00',
                'payable': '200.00',
                'vat_amount': '26.09',
                'subtotal': '173.91',
                'recourring': False,
                'paymentTerms': 'layby',
                'hold_status': False
            }],
            'items': [
                {
                    'inventory_id': self.inventory_item1.id,
                    'product_name': 'Test Product 1',
                    'quantity': 2,
                    'price': '100.00'
                }
            ],
            'layby_dates': layby_dates
        }
        
        with patch('apps.finance.utils.views.update_latest_due', return_value=Decimal('50.00')):
            url = reverse('create_invoice')
            response = self.client.post(
                url, 
                data=json.dumps(invoice_data),
                content_type='application/json'
        )

        # Check response
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Verify layby was created
        invoice = Invoice.objects.get(id=response_data['invoice_id'])
        self.assertEqual(invoice.payment_terms, 'layby')
        self.assertTrue(layby.objects.filter(invoice=invoice).exists())
        
        # Verify layby dates were created
        layby_obj = layby.objects.get(invoice=invoice)
        self.assertEqual(laybyDates.objects.filter(layby=layby_obj).count(), 2)

    def test_hold_status_invoice(self):
        """Test creating an invoice with hold status"""
        self.client.login(username='testuser', password='testpassword')
        
        invoice_data = {
            'data': [{
                'client_id': self.customer.id,
                'currency': self.currency.id,
                'payment_method': 'cash',
                'amount_paid': '0.00',
                'payable': '100.00',
                'vat_amount': '13.04',
                'subtotal': '86.96',
                'recourring': False,
                'paymentTerms': 'normal',
                'hold_status': True
            }],
            'items': [
                {
                    'inventory_id': self.inventory_item1.id,
                    'product_name': 'Test Product 1',
                    'quantity': 1,
                    'price': '100.00'
                }
            ]
        }
        
        with patch('apps.finance.utils.views.update_latest_due', return_value=Decimal('0.00')):
            with patch('apps.finance.utils.views.held_invoice') as mock_held_invoice:
                url = reverse('create_invoice')
                response = self.client.post(
                    url, 
                    data=json.dumps(invoice_data),
                    content_type='application/json'
                )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['hold'])
        
        # Verify held_invoice function was called
        mock_held_invoice.assert_called_once()

    def test_installment_invoice_creation(self):
        """Test creating an invoice with installment payment terms"""
        self.client.login(username='testuser', password='testpassword')
        
        invoice_data = {
            'data': [{
                'client_id': self.customer.id,
                'currency': self.currency.id,
                'payment_method': 'ecocash',
                'amount_paid': '50.00',
                'payable': '150.00',
                'vat_amount': '19.57',
                'subtotal': '130.43',
                'recourring': True,
                'paymentTerms': 'installment',
                'hold_status': False
            }],
            'items': [
                {
                    'inventory_id': self.inventory_item1.id,
                    'product_name': 'Test Product 1',
                    'quantity': 1,
                    'price': '100.00'
                },
                {
                    'inventory_id': self.inventory_item2.id,
                    'product_name': 'Test Product 2',
                    'quantity': 1,
                    'price': '50.00'
                }
            ]
        }
        
        with patch('apps.finance.utils.views.update_latest_due', return_value=Decimal('50.00')):
            url = reverse('create_invoice')
            response = self.client.post(
                url, 
                data=json.dumps(invoice_data),
                content_type='application/json'
            )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Verify recurring invoice was created
        invoice = Invoice.objects.get(id=response_data['invoice_id'])
        self.assertEqual(invoice.payment_terms, 'installment')
        self.assertTrue(recurringInvoices.objects.filter(invoice=invoice).exists())
        
        # Verify recurring invoice status
        recurring_invoice = recurringInvoices.objects.get(invoice=invoice)
        self.assertFalse(recurring_invoice.status)

    def test_invoice_with_accessories(self):
        """Test creating an invoice for products with accessories"""
        # Create an accessory relationship
        accessory_product = Inventory.objects.create(
            name="Accessory Product",
            description="An accessory",
            quantity=20,
            cost=Decimal('10.00'),
            price=Decimal('20.00'),
            branch=self.branch
        )
        
        Accessory.objects.create(
            main_product=self.inventory_item1,
            accessory_product=accessory_product,
            quantity=1
        )
        
        self.client.login(username='testuser', password='testpassword')
        
        invoice_data = {
            'data': [{
                'client_id': self.customer.id,
                'currency': self.currency.id,
                'payment_method': 'cash',
                'amount_paid': '100.00',
                'payable': '100.00',
                'vat_amount': '13.04',
                'subtotal': '86.96',
                'recourring': False,
                'paymentTerms': 'normal',
                'hold_status': False
            }],
            'items': [
                {
                    'inventory_id': self.inventory_item1.id,
                    'product_name': 'Test Product 1',
                    'quantity': 1,
                    'price': '100.00'
                }
            ]
        }
        
        with patch('apps.finance.utils.views.update_latest_due', return_value=Decimal('100.00')):
            url = reverse('create_invoice')
            response = self.client.post(
                url, 
                data=json.dumps(invoice_data),
                content_type='application/json'
            )
        
        # Check response and verify accessory was processed
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        # Verify accessory inventory was updated
        accessory_product.refresh_from_db()
        self.assertEqual(accessory_product.quantity, 19)  # One accessory should be deducted
        
        # Verify COGS items include the accessory
        invoice = Invoice.objects.get(id=response_data['invoice_id'])
        cogs_items = COGS.objects.filter(cogsitems__invoice=invoice)
        self.assertEqual(cogs_items.count(), 1)

    def test_error_handling(self):
        """Test error handling for invalid data"""
        self.client.login(username='testuser', password='testpassword')
        
        # Test with invalid customer ID
        invoice_data = {
            'data': [{
                'client_id': 999999,  # Non-existent customer
                'currency': self.currency.id,
                'payment_method': 'cash',
                'amount_paid': '100.00',
                'payable': '100.00',
                'vat_amount': '13.04',
                'subtotal': '86.96',
                'recourring': False,
                'paymentTerms': 'normal',
                'hold_status': False
            }],
            'items': [
                {
                    'inventory_id': self.inventory_item1.id,
                    'product_name': 'Test Product 1',
                    'quantity': 1,
                    'price': '100.00'
                }
            ]
        }
        
        url = reverse('create_invoice')
        response = self.client.post(
            url, 
            data=json.dumps(invoice_data),
            content_type='application/json'
        )
        
        # Check error response
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn('error', response_data)
        
        # Test with invalid JSON
        response = self.client.post(
            url, 
            data="invalid json data",
            content_type='application/json'
        )
        
        # Check error response
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn('error', response_data)