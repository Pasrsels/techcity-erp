import json
from django.urls import reverse
from django.test import TestCase
from apps.users.models import User
from apps.company.models import Branch
from ..models import Cashflow


class CashflowTests(TestCase):

    def setUp(self):
        self.branch = Branch.objects.create(name="Test Branch")
        
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            branch=self.branch
        )

        self.client = self.client() 
        self.client.login(username='testuser', password='testpass123')

    def test_create_income_transaction_success(self):
        data = {
            "IncomeAmount": 1000.00,
            "transaction_type": "income",
            "categories": {
                "category": {"value": "Salary"},
                "subcategory": {"value": "Monthly"},
                "name": {"value": "Regular Income"}
            }
        }

        response = self.client.post(
            reverse('finance:record_cashflow_transaction'),
            data=json.dumps(data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['success'])

        self.assertTrue(Cashflow.objects.filter(amount=1000.00).exists())

    def test_create_expense_transaction_success(self):
        expense_data = {
            "ExpenseAmount": 500.00,
            "transaction_type": "expense",
            "categories": {
                "category": {"value": "Utilities"},
                "subcategory": {"value": "Electricity"},
                "name": {"value": "Monthly Bill"}
            }
        }

        response = self.client.post(
            reverse('finance:record_cashflow_transaction'),
            data=json.dumps(expense_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['success'])

        self.assertTrue(Cashflow.objects.filter(amount=500.00).exists())