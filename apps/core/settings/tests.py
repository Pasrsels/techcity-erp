from django.test import TestCase
from .models import TaxSettings

class TaxSettingsTestCase(TestCase):
    def test_tax_settings_creation(self):
        tax_settings = TaxSettings.objects.create(
            name='Test Tax Settings',
            selected=True
        )
        self.assertEqual(tax_settings.name, 'Test Tax Settings')
