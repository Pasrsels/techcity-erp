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
    member_bal = member.get['Member_accounts__Balance']

    if member_bal > 0:
        return JsonResponse({'response': f'{member_name} owes ${member_bal}'})
    return JsonResponse({'response': f'{member} is owed ${member_bal}'})


def add_admin_fee(id):
    member = Members.objects.filter(id= id).values('name','Payments__Admin_fee')
    member_name = member.get['Name']
    member_admin_fee = member.get['Payments__Admin_fee']

    if member_admin_fee > 0:
        return JsonResponse({'response':f'{member_name} admin fee is {member_admin_fee}'})
    return JsonResponse({'response':f'{member_name} admin fee cleared'})

def past_bal_payment(id):
    member = Members.objects.filter(id= id).values('name','Payments__Admin_fee','Payments__Amount','Member_accounts__Balance')
    cost = Members.objects.filter(id = id).values('Services__Types__Price')
    member_name = member.get['Name']
    member_admin_fee = member.get['Payments__Admin_fee']
    member_payments = member.get['Payments__Amount']
    member_bal = member.get['Member_accounts__Balance']
    total_cost = cost.get['Services__Types__Price']

    if member_admin_fee > 0:
        remainder = member_payments - member_admin_fee
        if remainder > 0:
            cost = Member_accounts.Balance() 
            cost = total_cost - remainder
        return JsonResponse({'response': f'{cost}'})
    