# from apps.finance.helpers.imports import *

# class CashBook(APIView):
#     def get(self, request, *args, **kwargs):
#         Currency = Currency.objects.get(default=True)
        
#         data = {"message": "GET method overridden successfully"}
#         return Response(data)


# class RecordIncomeAPI(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         serializer = IncomeSerializer(data=request.data)
#         if not serializer.is_valid():
#             return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

#         data = serializer.validated_data
#         try:

#             name = data['name']
#             amount = data['amount']
#             currency_id = data['currency']
#             account_id = data['account_to']
#             branch_id = data['branch']
#             r_value = data.get('is_recurring', False)
#             reminder = data.get('has_reminder', False)
#             r_unit = data.get('r_unit')
#             from_date = data.get('from_date')
#             to_date = data.get('to_date')
#             reminder_dated = data.get('reminder_dated')

#             category_data = data.get('category', {})
#             main_category_data = data.get('main_category', {})

#             main_category, _ = IncomeCategory.objects.get_or_create(
#                 name=main_category_data.get('text'),
#                 defaults={'parent': None}
#             )

#             if category_data.get('isNew', False):
#                 category, _ = IncomeCategory.objects.get_or_create(
#                     name=category_data.get('text'),
#                     parent=main_category
#                 )
#             else:
#                 try:
#                     category = IncomeCategory.objects.get(id=category_data.get('value'))
#                 except IncomeCategory.DoesNotExist:
#                     return Response({
#                         "success": False,
#                         "message": "Selected Category does not exist."
#                     }, status=400)

#             with transaction.atomic():
#                 income = Income.objects.create(
#                     amount=amount,
#                     account_id=account_id,
#                     currency_id=currency_id,
#                     category=category,
#                     note=category.name,
#                     user=request.user,
#                     branch_id=branch_id,
#                     is_recurring=r_value,
#                     from_date=from_date,
#                     to_date=to_date,
#                     reminder=reminder,
#                     remainder_date=reminder_dated,
#                     recurrence_value=r_value if r_value else None,
#                     recurrence_unit=r_unit
#                 )

#                 Cashbook.objects.create(
#                     income=income,
#                     amount=amount,
#                     description=f"Income: {name} -> {category.name}",
#                     debit=True,
#                     credit=False,
#                     branch_id=branch_id,
#                     created_by=request.user,
#                     updated_by=request.user,
#                     issue_date=timezone.now(),
#                     currency_id=currency_id
#                 )

#             return Response({
#                 'success': True,
#                 'message': 'Income recorded successfully',
#                 'income_id': income.id
#             }, status=200)

#         except Exception as e:
#             logger.exception("Error while recording income")
#             return Response({'success': False, 'message': str(e)}, status=500)

# class CreateExpenseAPI(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         serializer = ExpenseSerializer(data=request.data)
#         if not serializer.is_valid():
#             return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

#         data = serializer.validated_data

#         try:
#             amount = data['amount']
#             if amount < 0:
#                 return Response({"error": "Amount cannot be negative."}, status=400)

#             main_category_data = data['main_category']
#             main_category, _ = ExpenseCategory.objects.get_or_create(
#                 name=main_category_data.get('text'),
#                 defaults={'parent': None}
#             )

#             category_data = data['category']
#             if category_data.get('isNew', False):
#                 category, _ = ExpenseCategory.objects.get_or_create(
#                     name=category_data.get('text'),
#                     parent=main_category
#                 )
#             else:
#                 try:
#                     category = ExpenseCategory.objects.get(id=category_data.get('value'))
#                 except ExpenseCategory.DoesNotExist:
#                     return Response({"error": "Selected Category does not exist."}, status=400)

#             currency = Currency.objects.get(id=data['currency'])
#             branch = Branch.objects.get(id=data['branch'])

#             account_to = None
#             if data.get('account_to'):
#                 account_to = User.objects.get(id=data['account_to'])

#             with transaction.atomic():
#                 expense = Expense.objects.create(
#                     amount=amount,
#                     currency=currency,
#                     category=category,
#                     branch=branch,
#                     account_to=account_to,
#                     user=request.user,
#                     payment_method=data.get('payment_type', 'cash'),
#                     is_recurring=data.get('is_recurring', False),
#                     is_loan=data.get('is_loan', False)
#                 )

#                 if expense.is_recurring:
#                     if not data.get('from_date') or not data.get('recurrence_value') or not data.get('recurrence_unit'):
#                         return Response({"error": "Missing recurrence info"}, status=400)

#                     Recurrence.objects.create(
#                         expense=expense,
#                         recurrence_value=data['recurrence_value'],
#                         recurrence_unit=data['recurrence_unit'],
#                         from_date=data['from_date'],
#                         to_date=data.get('to_date'),
#                         has_reminder=data.get('has_reminder', False),
#                         reminder_dated=data.get('reminder_dated')
#                     )

#                 if expense.is_loan:
#                     Loan.objects.create(
#                         expense=expense,
#                         loan_repayment_amount=data.get('loan_repayment_amount', 0),
#                         loan_interest_rate=data.get('loan_interest_rate', 0),
#                         loan_period_value=data.get('loan_period_value', 0),
#                         loan_period_unit=data.get('loan_period_unit')
#                     )

#                 Cashbook.objects.create(
#                     amount=amount,
#                     expense=expense,
#                     currency=currency,
#                     credit=True,
#                     description=f'Expense entry - {category.name}',
#                     branch=branch,
#                     created_by=request.user,
#                     updated_by=request.user
#                 )

#             return Response({
#                 "success": True,
#                 "message": "Expense recorded successfully",
#                 "expense_id": expense.id
#             })

#         except Currency.DoesNotExist:
#             return Response({"error": "Invalid currency."}, status=400)
#         except Branch.DoesNotExist:
#             return Response({"error": "Invalid branch."}, status=400)
#         except User.DoesNotExist:
#             return Response({"error": "Invalid user/account_to."}, status=400)
#         except Exception as e:
#             logger.exception("Unexpected error during expense creation")
#             return Response({"error": str(e)}, status=500)
    
   