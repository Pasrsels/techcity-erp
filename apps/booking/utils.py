from .models import *
from django.http import JsonResponse
import json


def check_admin_fee(id):
    member = Members.objects.filter(id= id).values('name','Payments__Admin_fee')
    member_name = member.get['Name']
    member_admin_fee = member.get['Payments__Admin_fee']

    if member_admin_fee > 0:
        return JsonResponse({'response':f'{member_name} is owing admin fee of {member_admin_fee}'})
    return JsonResponse({'response':f'{member_name} has cleared admin fee'})


def check_bal(id):
    member = Members.objects.filter(id= id).values('name','Member_accounts__Balance')
    member_name = member.get['Name']
    member_bal = member.get('Member_accounts__Balance')

    if member_bal > 0:
        return JsonResponse({'response': f'{member_name} owes ${member_bal}'})
    return JsonResponse({'response': f'{member} is owed ${member_bal}'})


def add_admin_fee(id):
    member = Members.objects.filter(id= id).values('name','Payments__Admin_fee')
    member_name = member.get['Name']
    member_admin_fee = member.get['Payments__Admin_fee']

    if member_admin_fee > 0:
        return print(f'{member_name} admin fee is {member_admin_fee}')
    return print(f'{member_name} admin fee cleared')
