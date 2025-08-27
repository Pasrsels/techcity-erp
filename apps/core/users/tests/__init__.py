from django.test import TestCase
from ..models import User

class UserTestCase(TestCase):
    def test_user_creation(self):
        user = User.objects.create_user(
            email='test@example.com',
            password='password',
            first_name='Test',
            last_name='User'
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('password'))
