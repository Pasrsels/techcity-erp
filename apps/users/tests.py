import pytest
from django.urls import reverse
from .models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

@pytest.fixture
def create_user():
    def make_user():
        User.objects.create_user(**kwargs)
    return make_user

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
class test_login(api_client, create_user):

    user = create_user(username='casy', password='neverfail')

    response = api_client.post(reverse('api_login'), {
        'username': 'casy',
        'password': 'neverfail'
    }, format='json')

    assert response.status_code == 200
    assert 'access' in response.data
    assert 'refresh' in response.data

    access_token = response.data['access']
    refresh_token = response.data['refresh']

    print('Access token', access_token)
    print('Refresh token', refresh_token)
