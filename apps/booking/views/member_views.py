from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from ..models import Members, Services, MemberAccounts, Payments, Logs
import json
from django.db import transaction

@login_required
def members_view(request):
    member = Services.objects.filter(delete=False)
    return render(request, 'members.html',{'formMemberData': member})

@login_required
def member_crud(request):
    if request.method == "GET":
        member = Members.objects.all()
        return JsonResponse({'success': True, 'data': list(member)}, status = 200)
    elif request.method == "POST":
        data = json(request.body)

        member_data = data.get('member_data', {})
        service_data = data.get('service_data', {})
        member_acc_data = data.get('member_acc_data',{})
        office_data = data.get('office_data',{})
        payments_data = data.get('payments_data',{})
        type_data = data.get('types_data',{})

        office_name = office_data.get('Name')

        s_name = service_data.get('Name')
        s_del = service_data.get('delete')
        s_type_name = type_data.get('Name')
        service_amount = type_data.get('Price')
        service_duration = type_data.get('Duration')
        promotion = type_data.get('Promotion')

        member_balance = member_acc_data.get('Balance')
        payments_date = payments_data.get('Date')
        payments_amount = payments_data.get('Amount')
        payments_admin = payments_data.get('Admin_fee')

        n_ID = member_data.get('National_ID')
        m_name = member_data.get('Name')
        m_email = member_data.get('Email')
        m_phone = member_data.get('Phone')
        m_adress = member_data.get('Address')
        m_enrollment = member_data.get('Enrollment')
        m_company = member_data.get('Company')
        m_age = member_data.get('Age')
        m_gender = member_data.get('Gender')

        if Members.objects.filter(Email = m_email).exists():
            return JsonResponse({'success': True, 'response': 'field already exists'}, status = 400)
        elif not n_ID or not m_name or not m_email or not m_phone or not m_adress or not m_enrollment \
        or not m_company or not m_age or not m_gender:
            return JsonResponse({'success': False, 'response': 'empty fields'}, status = 400)

        with transaction.atomic():
            try:
                if not Members.objects.filter(Phone=m_phone).exists():
                    admin_amount = 0
                    bal = 0
                    if payments_amount > service_amount:
                        bal = (payments_amount - service_amount) - payments_admin
                        if bal < 0:
                            admin_amount = bal
                    elif payments_amount == service_amount:
                        admin_amount = -20
                        bal = admin_amount
                    else:
                        admin_amount = 20
                        bal = (service_amount - payments_amount) + admin_amount

                payment_add = Payments.objects.create(
                    Amount = payments_amount,
                    Admin_fee = admin_amount,
                    Description = f'payment for {m_name}'
                )
                service_add = Services.objects.create(
                    Name = s_name,
                    delete = s_del
                )

                member_acc_add = MemberAccounts.objects.create(
                    Balance  = bal,
                    Payments = payment_add,
                    delete = False
                )


                member_add = Members.objects.create(
                    National_ID = n_ID,
                    Name = m_name,
                    Email = m_email,
                    Phone = m_phone,
                    Address = m_adress,
                    Enrollment = m_enrollment,
                    Company = m_company,
                    Age = m_age,
                    Gender = m_gender,
                    delete = False,
                    Services=service_add,
                    Member_accounts = member_acc_add,
                    Payments = payment_add
                )
                Logs.objects.create(
                    action = 'create'
                )
                return JsonResponse({'success': True, 'response': 'Data saved'}, status = 200)
            except Exception as e:
                pass
    elif request.method == "PUT":
        data = json(request.body)

        member_data = data.get('member_data', {})
        service_data = data.get('service_data', {})
        member_acc_data = data.get('member_acc_data',{})
        office_data = data.get('office_data',{})
        payments_data = data.get('payments_data',{})
        type_data = data.get('types_data',{})

        office_id = office_data.get('id')
        office_name = office_data.get('Name')

        s_id = service_data.get('id')
        s_name = service_data.get('Name')
        s_del = service_data.get('delete')
        s_type_id = type_data.get('id')
        s_type_name = type_data.get('Name')
        service_amount = type_data.get('Price')
        service_duration = type_data.get('Duration')
        promotion = type_data.get('Promotion')

        member_balance = member_acc_data.get('Balance')
        payments_date = payments_data.get('Date')
        payments_amount = payments_data.get('Amount')
        payments_admin = payments_data.get('Admin_fee')

        n_ID = member_data.get('National_ID')
        m_name = member_data.get('Name')
        m_email = member_data.get('Email')
        m_phone = member_data.get('Phone')
        m_adress = member_data.get('Address')
        m_enrollment = member_data.get('Enrollment')
        m_company = member_data.get('Company')
        m_age = member_data.get('Age')
        m_gender = member_data.get('Gender')

        try:
            Members.objects.get(Phone = m_phone)

            with transaction.Atomic():

                payment_add = Payments.objects.update(
                    Amount = payments_amount,
                    Admin_fee = admin_amount,
                    Description = f'payment for {m_name}'
                )
                service_add = Services.objects.update(
                    Name = s_name,
                    delete = s_del
                )

                member_acc_add = MemberAccounts.objects.update(
                    Balance  = bal,
                    Payments = payment_add,
                    delete = False
                )

                member_add = Members.objects.update(
                    National_ID = n_ID,
                    Name = m_name,
                    Email = m_email,
                    Phone = m_phone,
                    Address = m_adress,
                    Enrollment = m_enrollment,
                    Company = m_company,
                    Age = m_age,
                    Gender = m_gender,
                    delete = False,
                    Services=service_add,
                    Member_accounts = member_acc_add,
                    Payments = payment_add
                )
                Logs.objects.update(
                    action = 'update'
                )
        except Exception as e:
            return JsonResponse({'success': False, 'response': f'{e}'}, status = 400)
    elif request.method == "DELETE":
        data = json(request.body)

        id = member_data.get('id')

        try:
            Members.objects.get(id = id)
            member = Members.objects.get(id = id)
            member.delete = True
            member.save()
            Logs.objects.delete(
                action = 'delete'
            )
        except Exception as e:
            return JsonResponse({'success': False, 'response': f'{e}'}, status = 400)
