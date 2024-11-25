from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
import json
from .models import Members, Office_spaces, Services, Types, Payments, Member_accounts

# Members CRUD View
@csrf_exempt
def members_view(request):
    if request.method == "GET":
        members = Members.objects.all()
        data = [
            {
                'id': member.id,
                'Name': member.Name,
                'Email': member.Email,
                'Phone': member.Phone,
                'Address': member.Address,
                'Enrollment': member.Enrollmnet,
                'Company': member.Company,
                'Age': member.Age,
                'Gender': member.Gender,
            }
            for member in members
        ]
        return JsonResponse({'success': True, 'data': data}, status=200)
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

# Office CRUD View
@csrf_exempt
def offices_view(request):
    if request.method == "GET":
        offices = Office_spaces.objects.all()
        data = [
            {
                'id': office.id,
                'Name': office.Name,
            }
            for office in offices
        ]
        return JsonResponse({'success': True, 'data': data}, status=200)
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

# Service CRUD View
@csrf_exempt
def service_crud(request):
    if request.method == "GET":
        # Search functionality
        search_query = request.GET.get('search', '')
        if search_query:
            services = Services.objects.filter(
                Q(Name__icontains=search_query) |
                Q(Types__Name__icontains=search_query)
            ).select_related('Types')
        else:
            services = Services.objects.all().select_related('Types')

        # Serialize data for the response
        data = [
            {
                'id': service.id,
                'Name': service.Name,
                'Types__Name': service.Types.Name,
                'Types__Price': service.Types.Price,
                'Types__Duration': service.Types.Duration,
                'Types__Promotion': service.Types.Promotion
            }
            for service in services
        ]
        return JsonResponse({'success': True, 'data': data}, status=200)

    elif request.method == "POST":
        try:
            # Parse JSON data
            data = json.loads(request.body)

            # Create Type object
            type_data = data.get('type_data', {})
            type_obj = Types.objects.create(
                Name=type_data['Name'],
                Price=type_data['Price'],
                Duration=type_data['Duration'],
                Promotion=type_data.get('Promotion', '')
            )

            # Create Service object
            Services.objects.create(
                Name=data['service_name'],
                Types=type_obj
            )
            return JsonResponse({'success': True, 'message': 'Service added successfully!'}, status=201)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

    elif request.method == "PUT":
        try:
            # Parse JSON data
            data = json.loads(request.body)
            service_id = data.get('id')

            # Fetch service and type objects
            service = Services.objects.get(id=service_id)
            type_data = data.get('type_data', {})
            type_obj = service.Types

            # Update Type object
            type_obj.Name = type_data['Name']
            type_obj.Price = type_data['Price']
            type_obj.Duration = type_data['Duration']
            type_obj.Promotion = type_data.get('Promotion', '')
            type_obj.save()

            # Update Service object
            service.Name = data['service_name']
            service.save()

            return JsonResponse({'success': True, 'message': 'Service updated successfully!'}, status=200)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

    elif request.method == "DELETE":
        try:
            # Parse JSON data
            data = json.loads(request.body)
            service_id = data.get('id')

            # Delete service
            service = Services.objects.get(id=service_id)
            service.delete()

            return JsonResponse({'success': True, 'message': 'Service deleted successfully!'}, status=200)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

# Types CRUD View
@csrf_exempt
def type_crud(request):
    if request.method == "GET":
        types = Types.objects.all()
        data = [
            {
                'id': type.id,
                'Name': type.Name,
                'Price': type.Price,
                'Duration': type.Duration,
                'Promotion': type.Promotion,
            }
            for type in types
        ]
        return JsonResponse({'success': True, 'data': data}, status=200)
    
    elif request.method == "POST":
        try:
            # Parse JSON data
            data = json.loads(request.body)
            type_data = data.get('type_data', {})
            Types.objects.create(
                Name=type_data['Name'],
                Price=type_data['Price'],
                Duration=type_data['Duration'],
                Promotion=type_data.get('Promotion', '')
            )
            return JsonResponse({'success': True, 'message': 'Type added successfully!'}, status=201)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

# Member CRUD View
@csrf_exempt
def member_crud(request):
    if request.method == "GET":
        members = Members.objects.all()
        data = [
            {
                'id': member.id,
                'Name': member.Name,
                'Email': member.Email,
                'Phone': member.Phone,
                'Address': member.Address,
                'Enrollment': member.Enrollmnet,
                'Company': member.Company,
                'Age': member.Age,
                'Gender': member.Gender,
            }
            for member in members
        ]
        return JsonResponse({'success': True, 'data': data}, status=200)

    # You can add POST, PUT, DELETE functionality here similarly to the service_crud view

    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

# Payments CRUD View
@csrf_exempt
def payments_crud(request):
    if request.method == "GET":
        payments = Payments.objects.all()
        data = [
            {
                'id': payment.id,
                'Date': payment.Date,
                'Amount': payment.Amount,
                'Admin_fee': payment.Admin_fee,
                'Description': payment.Description,
            }
            for payment in payments
        ]
        return JsonResponse({'success': True, 'data': data}, status=200)
    
    # You can add POST, PUT, DELETE functionality here similarly to the service_crud view

    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

# Office CRUD View
@csrf_exempt
def office_crud(request):
    if request.method == "GET":
        offices = Office_spaces.objects.all()
        data = [
            {
                'id': office.id,
                'Name': office.Name,
            }
            for office in offices
        ]
        return JsonResponse({'success': True, 'data': data}, status=200)

    # You can add POST, PUT, DELETE functionality here similarly to the service_crud view

    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)
