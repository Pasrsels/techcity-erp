import pytest
from django.urls import reverse
from django.test import Client
from apps.users.models import User
from apps.inventory.models import *
from apps.company.models import Branch, Company

@pytest.fixture
def create_user():
    def make_user():
        User.objects.create_user(**kwargs)
    return make_user

@pytest.mark.django_db
class TestTransferBack():
    user = create_user(
        username='casy',
        password='neverfail'
    )


