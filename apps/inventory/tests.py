# import pytest
# from django.urls import reverse
# from django.test import Client
# from apps.users.models import User
# from apps.inventory.models import *
# from apps.company.models import Branch, Company

# #global objects

# # create company and branch
# test_company = Company.objects.create(name='test company')
# test_branch = Company.objects.create(name='test_branch', company=test_company)

# # create and login test user
# test_user = User.objects.create_user(
#     username='test',
#     password='test_password',
#     branch=test_branch
# )

# @pytest.mark.django_db
# def inventory_transfer_tests(client):
#     """
#         Testing the GET request of the view and to match if the required data is been back
#     """

#     Client.login(test_user)

#     branch = test_user.branch 
#     transfer = Transfer.objects.create(branch=branch, transfer_to=branch, delete=False) 
#     TransferItems.objects.create(from_branch=branch, to_branch=branch, transfer=transfer, product__name='lenovo', quantity=10, product__cost=20)

#     #GET request to the inventory_transfers view 
#     response = client.get(reverse('inventory:inventory_transfers')) 
    
#     assert response.status_code == 200



