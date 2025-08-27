from django.test import TestCase
from .models import Company

class CompanyTestCase(TestCase):
    def test_company_creation(self):
        company = Company.objects.create(
            name='Test Company',
        )
        self.assertEqual(company.name, 'Test Company')
