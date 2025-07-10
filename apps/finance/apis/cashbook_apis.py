from apps.finance.helpers.imports import *

class CashBook(APIView):
    def get(self, request, *args, **kwargs):
        Currency = Currency.objects.get(default=True)
        
        data = {"message": "GET method overridden successfully"}
        return Response(data)
 

class RecordIncomeAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = IncomeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:

            name = data['name']
            amount = data['amount']
            currency_id = data['currency']
            account_id = data['account_to']
            branch_id = data['branch']
            r_value = data.get('is_recurring', False)
            reminder = data.get('has_reminder', False)
            r_unit = data.get('r_unit')
            from_date = data.get('from_date')
            to_date = data.get('to_date')
            reminder_dated = data.get('reminder_dated')

            category_data = data.get('category', {})
            main_category_data = data.get('main_category', {})

            main_category, _ = IncomeCategory.objects.get_or_create(
                name=main_category_data.get('text'),
                defaults={'parent': None}
            )

            if category_data.get('isNew', False):
                category, _ = IncomeCategory.objects.get_or_create(
                    name=category_data.get('text'),
                    parent=main_category
                )
            else:
                try:
                    category = IncomeCategory.objects.get(id=category_data.get('value'))
                except IncomeCategory.DoesNotExist:
                    return Response({
                        "success": False,
                        "message": "Selected Category does not exist."
                    }, status=400)

            with transaction.atomic():
                income = Income.objects.create(
                    amount=amount,
                    account_id=account_id,
                    currency_id=currency_id,
                    category=category,
                    note=category.name,
                    user=request.user,
                    branch_id=branch_id,
                    is_recurring=r_value,
                    from_date=from_date,
                    to_date=to_date,
                    reminder=reminder,
                    remainder_date=reminder_dated,
                    recurrence_value=r_value if r_value else None,
                    recurrence_unit=r_unit
                )

                Cashbook.objects.create(
                    income=income,
                    amount=amount,
                    description=f"Income: {name} -> {category.name}",
                    debit=True,
                    credit=False,
                    branch_id=branch_id,
                    created_by=request.user,
                    updated_by=request.user,
                    issue_date=timezone.now(),
                    currency_id=currency_id
                )

            return Response({
                'success': True,
                'message': 'Income recorded successfully',
                'income_id': income.id
            }, status=200)

        except Exception as e:
            logger.exception("Error while recording income")
            return Response({'success': False, 'message': str(e)}, status=500)

class CreateExpenseAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ExpenseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        try:
            amount = data['amount']
            if amount < 0:
                return Response({"error": "Amount cannot be negative."}, status=400)

            main_category_data = data['main_category']
            main_category, _ = ExpenseCategory.objects.get_or_create(
                name=main_category_data.get('text'),
                defaults={'parent': None}
            )

            category_data = data['category']
            if category_data.get('isNew', False):
                category, _ = ExpenseCategory.objects.get_or_create(
                    name=category_data.get('text'),
                    parent=main_category
                )
            else:
                try:
                    category = ExpenseCategory.objects.get(id=category_data.get('value'))
                except ExpenseCategory.DoesNotExist:
                    return Response({"error": "Selected Category does not exist."}, status=400)

            currency = Currency.objects.get(id=data['currency'])
            branch = Branch.objects.get(id=data['branch'])

            account_to = None
            if data.get('account_to'):
                account_to = User.objects.get(id=data['account_to'])

            with transaction.atomic():
                expense = Expense.objects.create(
                    amount=amount,
                    currency=currency,
                    category=category,
                    branch=branch,
                    account_to=account_to,
                    user=request.user,
                    payment_method=data.get('payment_type', 'cash'),
                    is_recurring=data.get('is_recurring', False),
                    is_loan=data.get('is_loan', False)
                )

                if expense.is_recurring:
                    if not data.get('from_date') or not data.get('recurrence_value') or not data.get('recurrence_unit'):
                        return Response({"error": "Missing recurrence info"}, status=400)

                    Recurrence.objects.create(
                        expense=expense,
                        recurrence_value=data['recurrence_value'],
                        recurrence_unit=data['recurrence_unit'],
                        from_date=data['from_date'],
                        to_date=data.get('to_date'),
                        has_reminder=data.get('has_reminder', False),
                        reminder_dated=data.get('reminder_dated')
                    )

                if expense.is_loan:
                    Loan.objects.create(
                        expense=expense,
                        loan_repayment_amount=data.get('loan_repayment_amount', 0),
                        loan_interest_rate=data.get('loan_interest_rate', 0),
                        loan_period_value=data.get('loan_period_value', 0),
                        loan_period_unit=data.get('loan_period_unit')
                    )

                Cashbook.objects.create(
                    amount=amount,
                    expense=expense,
                    currency=currency,
                    credit=True,
                    description=f'Expense entry - {category.name}',
                    branch=branch,
                    created_by=request.user,
                    updated_by=request.user
                )

            return Response({
                "success": True,
                "message": "Expense recorded successfully",
                "expense_id": expense.id
            })

        except Currency.DoesNotExist:
            return Response({"error": "Invalid currency."}, status=400)
        except Branch.DoesNotExist:
            return Response({"error": "Invalid branch."}, status=400)
        except User.DoesNotExist:
            return Response({"error": "Invalid user/account_to."}, status=400)
        except Exception as e:
            logger.exception("Unexpected error during expense creation")
            return Response({"error": str(e)}, status=500)
    
class CashBookData(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            page = int(request.query_params.get('page', 1))
            per_page = int(request.query_params.get('per_page', 20))
            filter_option = request.query_params.get('filter', 'this_week')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            search_query = request.query_params.get('search', '')
            currency = request.query_params.get('currency', '')
        except Exception as e:
            return Response({'error': e}, status.HTTP_404_NOT_FOUND)
        logger.info(f'filter Option: {filter_option}, currency: {currency}')

        now = timezone.now()
        end_date = now

        if filter_option == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif filter_option == 'this_week':
            start_date = now - timedelta(days=now.weekday())
        elif filter_option == 'yesterday':
            start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif filter_option == 'this_month':
            start_date = now.replace(day=1)
        elif filter_option == 'last_month':
            start_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
        elif filter_option == 'this_year':
            start_date = now.replace(month=1, day=1)
        elif filter_option == 'custom':
            if start_date and end_date:
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
            else:
                start_date = now - timedelta(days=now.weekday())
                end_date = now
        
        if currency in [str(i) for i in range(11)] or currency in [int(i) for i in range(11)]:  
            logger.info(f'currency: {currency}')
            entries = Cashbook.objects.filter(
                issue_date__range=[start_date, end_date],
                currency__id=currency,
                branch=request.user.branch
            ).select_related(
                'created_by', 'branch', 'updated_by', 'currency', 'invoice', 'expense'
            ).order_by('-issue_date')
            logger.info(f'entries: {entries}')
        else:
            if currency == 'bank' or currency == 'ecocash':
                entries = Cashbook.objects.filter(
                    issue_date__range=[start_date, end_date],
                    branch=request.user.branch
                ).filter(
                    Q(expense__payment_type=currency) |
                    Q(invoice__payment_type=currency)
                ).select_related(
                    'created_by', 'branch', 'updated_by', 'currency', 'invoice', 'expense'
                ).order_by('-issue_date')

            elif currency == 'transfer':
                entries = Cashbook.objects.filter(
                    issue_date__range=[start_date, end_date],
                    transfer__payment_method=currency,
                    branch=request.user.branch
                ).select_related(
                    'created_by', 'branch', 'updated_by', 'currency', 'transfer'
                ).order_by('-issue_date')

            elif currency == 'loan':
                entries = Cashbook.objects.filter(
                    issue_date__range=[start_date, end_date],
                    expense__is_loan=True,
                    branch=request.user.branch
                ).select_related(
                    'created_by', 'branch', 'updated_by', 'currency', 'expense'
                ).order_by('-issue_date')

            else:
                entries = Cashbook.objects.none()
        
        logger.info(f'Found {entries.count()} entries')

        if search_query:
            entries = entries.filter(
                Q(description__icontains=search_query) |
                Q(accountant__icontains=search_query) |
                Q(manager__icontains=search_query) |
                Q(director__icontains=search_query)
            )

        entries = entries.order_by('-issue_date')
        
        # Calculate totals
        total_cash_in = entries.filter(debit=True, cancelled=False).aggregate(total=Sum('amount'))['total'] or 0
        total_cash_out = entries.filter(credit=True, cancelled=False).aggregate(total=Sum('amount'))['total'] or 0
        total_balance = total_cash_in - total_cash_out

        total_entries = entries.count()
        total_pages = (total_entries + per_page - 1) // per_page
        start_index = (page - 1) * per_page
        end_index = start_index + per_page

        paginated_entries = entries[start_index:end_index]
        
        
        # usd and other currencies balances
        currency_cash_in_balances = []
        currency_cash_out_balances = []
        currency_net_balances = []
        
        for currency in Currency.objects.all():
            cash_in = entries.filter(currency=currency, debit=True, cancelled=False).aggregate(total=Sum('amount'))['total'] or 0
            cash_out = entries.filter(currency=currency, credit=True, cancelled=False).aggregate(total=Sum('amount'))['total'] or 0
            
            currency_cash_in_balances.append({'name': currency.name, 'amount':cash_in})
            currency_cash_out_balances.append({'name': currency.name, 'amount':cash_out})
            currency_net_balances.append({'name': currency.name, 'amount':cash_in - cash_out})
        
        logger.info(f'balances: {currency_net_balances} /n')
        logger.info(f'cash in{currency_cash_in_balances}')
        logger.info(f'cash out {currency_cash_out_balances}')
        
        balance = 0
        entries_data = []
        for entry in paginated_entries:
            if entry.debit:
                balance += entry.amount
            elif entry.credit:
                balance -= entry.amount
            
            entries_data.append({
                'id': entry.id,
                'date': entry.issue_date.strftime('%Y-%m-%d %H:%M'),
                'description': entry.description,
                'debit': float(entry.amount) if entry.debit else None,
                'credit': float(entry.amount) if entry.credit else None,
                'balance': float(balance),
                'accountant': entry.accountant,
                'manager': entry.manager,
                'director': entry.director,
                'status': entry.status,
                'created_by': entry.created_by.first_name
            })

        return Response({
            'entries': entries_data,
            'totals': {
                'cash_in': currency_cash_in_balances,
                'cash_out': currency_cash_out_balances,
                'balance': currency_net_balances
            },
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'total_entries': total_entries,
                'has_next': page < total_pages,
                'has_previous': page > 1
            }
        }, status.HTTP_200_OK)
    def post(self, request):
        """ cashbook data with filters and pagination"""
    
        logger.info('Processing cashbook data request')
        
        try:
            data = request.data
            page = int(data.get('page', 1))
            per_page = int(data.get('per_page', 20))
            filter_option = data.get('filter', 'this_week')
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            search_query = data.get('search', '')
            currency = data.get('currency')
        except Exception as e:
            return Response({'error': e}, status.HTTP_404_NOT_FOUND)
        
        logger.info(f'filter Option: {filter_option}, currency: {currency}')

        now = timezone.now()
        end_date = now

        if filter_option == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif filter_option == 'this_week':
            start_date = now - timedelta(days=now.weekday())
        elif filter_option == 'yesterday':
            start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif filter_option == 'this_month':
            start_date = now.replace(day=1)
        elif filter_option == 'last_month':
            start_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
        elif filter_option == 'this_year':
            start_date = now.replace(month=1, day=1)
        elif filter_option == 'custom':
            if start_date and end_date:
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
            else:
                start_date = now - timedelta(days=now.weekday())
                end_date = now
        
        if currency in [str(i) for i in range(11)] or currency in [int(i) for i in range(11)]:  
            logger.info(f'currency: {currency}')
            entries = Cashbook.objects.filter(
                issue_date__range=[start_date, end_date],
                currency__id=currency,
                branch=request.user.branch
            ).select_related(
                'created_by', 'branch', 'updated_by', 'currency', 'invoice', 'expense'
            ).order_by('-issue_date')
            logger.info(f'entries: {entries}')
        else:
            if currency == 'bank' or currency == 'ecocash':
                entries = Cashbook.objects.filter(
                    issue_date__range=[start_date, end_date],
                    branch=request.user.branch
                ).filter(
                    Q(expense__payment_type=currency) |
                    Q(invoice__payment_type=currency)
                ).select_related(
                    'created_by', 'branch', 'updated_by', 'currency', 'invoice', 'expense'
                ).order_by('-issue_date')

            elif currency == 'transfer':
                entries = Cashbook.objects.filter(
                    issue_date__range=[start_date, end_date],
                    transfer__payment_method=currency,
                    branch=request.user.branch
                ).select_related(
                    'created_by', 'branch', 'updated_by', 'currency', 'transfer'
                ).order_by('-issue_date')

            elif currency == 'loan':
                entries = Cashbook.objects.filter(
                    issue_date__range=[start_date, end_date],
                    expense__is_loan=True,
                    branch=request.user.branch
                ).select_related(
                    'created_by', 'branch', 'updated_by', 'currency', 'expense'
                ).order_by('-issue_date')

            else:
                entries = Cashbook.objects.none()
        
        logger.info(f'Found {entries.count()} entries')

        if search_query:
            entries = entries.filter(
                Q(description__icontains=search_query) |
                Q(accountant__icontains=search_query) |
                Q(manager__icontains=search_query) |
                Q(director__icontains=search_query)
            )

        entries = entries.order_by('-issue_date')
        
        # Calculate totals
        total_cash_in = entries.filter(debit=True, cancelled=False).aggregate(total=Sum('amount'))['total'] or 0
        total_cash_out = entries.filter(credit=True, cancelled=False).aggregate(total=Sum('amount'))['total'] or 0
        total_balance = total_cash_in - total_cash_out

        total_entries = entries.count()
        total_pages = (total_entries + per_page - 1) // per_page
        start_index = (page - 1) * per_page
        end_index = start_index + per_page

        paginated_entries = entries[start_index:end_index]
        
        
        # usd and other currencies balances
        currency_cash_in_balances = []
        currency_cash_out_balances = []
        currency_net_balances = []
        
        for currency in Currency.objects.all():
            cash_in = entries.filter(currency=currency, debit=True, cancelled=False).aggregate(total=Sum('amount'))['total'] or 0
            cash_out = entries.filter(currency=currency, credit=True, cancelled=False).aggregate(total=Sum('amount'))['total'] or 0
            
            currency_cash_in_balances.append({'name': currency.name, 'amount':cash_in})
            currency_cash_out_balances.append({'name': currency.name, 'amount':cash_out})
            currency_net_balances.append({'name': currency.name, 'amount':cash_in - cash_out})
        
        logger.info(f'balances: {currency_net_balances} /n')
        logger.info(f'cash in{currency_cash_in_balances}')
        logger.info(f'cash out {currency_cash_out_balances}')
        
        balance = 0
        entries_data = []
        for entry in paginated_entries:
            if entry.debit:
                balance += entry.amount
            elif entry.credit:
                balance -= entry.amount
            
            entries_data.append({
                'id': entry.id,
                'date': entry.issue_date.strftime('%Y-%m-%d %H:%M'),
                'description': entry.description,
                'debit': float(entry.amount) if entry.debit else None,
                'credit': float(entry.amount) if entry.credit else None,
                'balance': float(balance),
                'accountant': entry.accountant,
                'manager': entry.manager,
                'director': entry.director,
                'status': entry.status,
                'created_by': entry.created_by.first_name
            })

        return Response({
            'entries': entries_data,
            'totals': {
                'cash_in': currency_cash_in_balances,
                'cash_out': currency_cash_out_balances,
                'balance': currency_net_balances
            },
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'total_entries': total_entries,
                'has_next': page < total_pages,
                'has_previous': page > 1
            }
        }, status.HTTP_200_OK) 