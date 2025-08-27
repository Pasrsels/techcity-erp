from rest_framework import views, status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from decimal import Decimal
import json
from ..views.invoice_views import invoice_preview_json
from ..models import (
    Invoice,
    Customer,
    CustomerAccount,
    CustomerAccountBalances,
    Transaction,
    Currency,
    CashTransfers,
    FinanceNotifications,
    CashUp,
    Qoutation,
    Expense,
    Cashbook,
    Account,
    AccountBalance,
    Payment,
    Sale,
    VATRate,
    VATTransaction,
    StockTransaction,
    InvoiceItem,
    CustomerDeposits,
    COGS,
    COGSItems,
    MainIncomeCategory,
    MainExpenseCategory,
    IncomeSubCategory,
    ExpenseSubCategory,
    CashFlowName,
    Cashflow,
    Income,
    UserAccount,
    UserTransaction,
    LossAccount,
)
from ..serializers import (
    CustomerSerializer,
    QuotationSerializer,
    CashWithdrawalSerializer,
    InvoiceSerializer,
    TransferSerializer,
)
from loguru import logger
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum
from ..utils import generate_pdf, calculate_expenses_totals
import datetime
from django.http import JsonResponse, HttpResponse
from ..consumers import CashTransferConsumer
from django.template.loader import render_to_string
from ..tasks import send_invoice_email_task, send_quotation_email
from xhtml2pdf import pisa
from io import BytesIO
from django.core.mail import EmailMessage
import boto3
from django.conf import settings
from twilio.rest import Client

class FinanceDataAPI(views.APIView):
    """API endpoint for fetching finance data dynamically"""

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)

        period = request.GET.get('period', 'this_month')
        finance_view = Finance()

        start_date, end_date = finance_view.get_date_range(period)
        graph_data = finance_view.get_graph_data(request.user.branch, period, start_date, end_date)
        metrics = finance_view.calculate_metrics(request.user.branch, start_date, end_date)

        # Convert Decimal to float for JSON serialization
        for key, value in metrics.items():
            if isinstance(value, Decimal):
                metrics[key] = float(value)

        return JsonResponse({
            'graph_data': graph_data,
            'metrics': metrics,
            'period': period
        })

class CustomersViewset(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request):
        data = request.data
        branch = request.user.branch

        if Customer.objects.filter(Q(phone_number=data.get('phonenumber')) | Q(email=data.get('email'))).exists():
            return Response({'error': 'Customer with this phone number or email already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        customer = Customer.objects.create(
            name=data.get('name'),
            email=data.get('email'),
            address=data.get('address'),
            phone_number=data.get('phonenumber'),
            branch=branch
        )
        account = CustomerAccount.objects.create(customer=customer)

        balances_to_create = [
            CustomerAccountBalances(account=account, currency=currency, balance=0)
            for currency in Currency.objects.all()
        ]
        CustomerAccountBalances.objects.bulk_create(balances_to_create)

        customer_serializer = self.get_serializer(customer)
        return Response(customer_serializer.data, status=status.HTTP_201_CREATED)

class AllCustomerAccounts(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        customer_infomation = Customer.objects.all()
        customer_balances = CustomerAccountBalances.objects.all()
        customer_transactions = Transaction.objects.all()

        customer_infomation_list = {}

        for items in customer_balances:
            total_transactions = sum(1 for item in customer_transactions if item.customer.id == items.account.customer.id)
            balance = []
            customer_infomation_list[items.account.customer.id] = {
                'name':items.account.customer.name,
                'phone_number': items.account.customer.phone_number,
                'email': items.account.customer.email,
                'transactions': total_transactions,
                'accounts':
                {

                }
            }
            id = items.account.customer.id
            for item in customer_balances:
                if id == item.account.customer.id:
                    balance.append(
                        {
                            'customer_id': item.account.customer.id,
                            'currency': item.currency.name,
                            'balance': item.balance

                        }
                    )
            customer_infomation_list[items.account.customer.id]['accounts'] = balance

        logger.info(customer_infomation_list)
        return Response(customer_infomation_list, status.HTTP_200_OK)

class CustomerCurrenciesTotal(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        currencies = Currency.objects.all()
        balances  = CustomerAccountBalances.objects.all()

        currencies_information = {}

        for item in currencies:
            total_balance = 0
            currencies_information[item.name] = {
                'balance': 0
            }
            currency_name = item.name
            for items in balances:
                if items.currency.name == currency_name:
                    total_balance += items.balance
            currencies_information[item.name]['balance'] = total_balance

        return Response(currencies_information, status.HTTP_200_OK)

class CustomerAccountView(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, customer_id):
        customer = get_object_or_404(Customer, id=customer_id)
        customer_serializer = CustomerSerializer(customer)

        account = CustomerAccountBalances.objects.filter(account__customer=customer).values()

        invoices = Invoice.objects.filter(
            customer=customer,
            branch=request.user.branch,
            status=True
        ).values()

        invoice_payments = Payment.objects.filter(
            invoice__branch=request.user.branch,
            invoice__customer=customer
        ).order_by('-payment_date').values()

        filters = Q()
        if request.GET.get('q'):
            filters &= Q(payment_status=request.GET['q'])
        if request.GET.get('search_query'):
            search_query = request.GET['search_query']
            filters &= (Q(invoice_number__icontains=search_query) | Q(issue_date__icontains=search_query))

        invoices = invoices.filter(filters)

        if request.GET.get('email_bool'):
            send_account_statement_email(customer.id, request.user.branch.id, request.user.id)
            return Response({'message': 'Email sent'},status.HTTP_200_OK)

        paid_invoice = invoices.filter(payment_status='Paid').count()
        due_invoice = invoices.filter(payment_status='Partial').count()
        return Response({
            'account': account,
            'invoices': invoices,
            'customer': customer_serializer.data,
            'invoice_count': invoices.count(),
            'invoice_payments': invoice_payments,
            'paid': paid_invoice,
            'due': due_invoice,
        },status.HTTP_200_OK)

class CustomerPaymentsJsonView(views.APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, customer_id):
        customer_id = customer_id
        transaction_type = request.data.get('type')

        customer = get_object_or_404(Customer, id=customer_id)

        if transaction_type == 'invoice_payments':
            invoice_payments = Payment.objects.select_related('invoice', 'invoice__currency', 'user').filter(
                invoice__branch=request.user.branch,
                invoice__customer=customer
            ).order_by('-payment_date').values(
                'invoice__products_purchased',
                'payment_date',
                'invoice__invoice_number',
                'invoice__currency__symbol',
                'invoice__payment_status',
                'invoice__amount_due',
                'invoice__amount',
                'user__username',
                'amount_paid',
                'amount_due'
            )
            return Response(invoice_payments,status.HTTP_200_OK)
        else:
            return Response(status.HTTP_400_BAD_REQUEST)

class EditCustomerDeposit(views.APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request, deposit_id):
        try:
            deposit = CustomerDeposits.objects.get(id=deposit_id)
        except CustomerDeposits.DoesNotExist:
            return Response(status.HTTP_404_NOT_FOUND)

        form = CustomerDepositSerializer(data = request.data)
        if not form.is_valid():
            return Response({'message':'Invalid form submission, redirect to finance:edit_customer_deposit' , 'Deposti Id':f'{deposit_id}'}, status.HTTP_400_BAD_REQUEST)

        amount = Decimal(request.data.get('amount'))
        if amount <= 0:
            return Response({'message':'Amount cannot be zero or negative, redirect to finance:edit_customer_deposit' , 'Deposti Id':f'{deposit_id}'}, status.HTTP_400_BAD_REQUEST)

        account_types = {
            'cash': Account.AccountType.CASH,
            'bank': Account.AccountType.BANK,
            'ecocash': Account.AccountType.ECOCASH,
        }

        account_name = f"{request.user.branch} {deposit.currency.name} {deposit.payment_method.capitalize()} Account"

        try:
            account = Account.objects.get(name=account_name, type=account_types[deposit.payment_method])
            account_balance = AccountBalance.objects.get(
                account=account,
                currency=deposit.currency,
                branch=request.user.branch,
            )
        except (Account.DoesNotExist, AccountBalance.DoesNotExist) as e:
            return Response({'message':f'{e}' , 'Deposti Id':f'{deposit_id}'}, status.HTTP_400_BAD_REQUEST)

        adj_amount = amount - deposit.amount

        if adj_amount != 0:
            if adj_amount > 0:
                account_balance.balance += adj_amount
                debit, credit = True, False
            else:
                account_balance.balance += adj_amount
                debit, credit = False, True

        Cashbook.objects.create(
            issue_date=datetime.date.today(),
            description=f'{deposit.payment_method.upper()} deposit adjustment ({deposit.customer_account.account.customer.name})',
            debit=debit,
            credit=credit,
            amount=abs(adj_amount),
            currency=deposit.currency,
            branch=deposit.branch
        )

        account_balance.save()
        deposit.amount = amount
        deposit.save()
        return Response({deposit.customer_account.account.customer.id}, status.HTTP_200_OK)

class CustomerAccountJson(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, customer_id):
        account = CustomerAccountBalances.objects.filter(account__customer__id=customer_id).values(
            'currency__symbol', 'balance'
        )
        return Response(account, status.HTTP_200_OK)

class CustomerAccountTransactionsJson(views.APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, id):
        customer_id = id
        transaction_type = request.data.get('type')

        customer = get_object_or_404(Customer, id=customer_id)

        if transaction_type == 'invoices':
            invoices = Invoice.objects.filter(
                customer=customer,
                branch=request.user.branch,
                status=True
            ).order_by('-issue_date').values(
                'issue_date',
                'invoice_number',
                'products_purchased',
                'amount_paid',
                'amount_due',
                'amount',
                'user__username',
                'payment_status'
            )
            return Response(invoices, status.HTTP_200_OK)
        else:
            return Response({'message': 'Invalid transaction type.'}, status.HTTP_400_BAD_REQUEST)

class RefundCustomerDeposit(views.APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request, deposit_id):
        try:
            deposit = CustomerDeposits.objects.get(id=deposit_id)
        except CustomerDeposits.DoesNotExist:
            return Response({'message': 'Deposit not found'}, status.HTTP_404_NOT_FOUND)

        try:
            data = request.data
            amount = Decimal(data.get('amount', 0))
            if amount <= 0:
                return Response({'message': 'Invalid amount'}, status.HTTP_400_BAD_REQUEST)
        except (json.JSONDecodeError, TypeError, ValueError):
            return Response({'message': 'Invalid input data'}, status.HTTP_400_BAD_REQUEST)

        account_types = {
            'cash': Account.AccountType.CASH,
            'bank': Account.AccountType.BANK,
            'ecocash': Account.AccountType.ECOCASH,
        }

        account_name = f"{request.user.branch} {deposit.currency.name} {deposit.payment_method.capitalize()} Account"

        try:
            account = Account.objects.get(name=account_name, type=account_types[deposit.payment_method])
            account_balance = AccountBalance.objects.get(
                account=account,
                currency=deposit.currency,
                branch=request.user.branch,
            )
        except (Account.DoesNotExist, AccountBalance.DoesNotExist) as e:
            return Response({'message': str(e)}, status.HTTP_400_BAD_REQUEST)

        if amount > deposit.amount:
            return Response({'message': 'Refund amount exceeds deposit amount'}, status.HTTP_400_BAD_REQUEST)

        account_balance.balance -= amount
        diff_amount = deposit.amount - amount

        if diff_amount == 0:
            deposit.delete()
        else:
            deposit.amount = diff_amount
            deposit.save()

        Cashbook.objects.create(
            issue_date=datetime.date.today(),
            description=f'{deposit.payment_method.upper()} deposit refund ({deposit.customer_account.account.customer.name})',
            debit=False,
            credit=True,
            amount=amount,
            currency=deposit.currency,
            branch=deposit.branch
        )

        account_balance.save()
        return Response(status.HTTP_200_OK)

class PrintAccountStatement(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, customer_id):
        try:
            customer = get_object_or_404(Customer, id=customer_id)

            account = CustomerAccountBalances.objects.filter(account__customer=customer).values()

            invoices = Invoice.objects.filter(
                customer=customer,
                branch=request.user.branch,
                status=True
            ).values()
        except:
            return Response({'message':'Error in processing the request'}, status.HTTP_400_BAD_REQUEST)

        invoice_payments = Payment.objects.select_related('invoice', 'invoice__currency', 'user').filter(
            invoice__branch=request.user.branch,
            invoice__customer=customer
        ).order_by('-payment_date').values()

        customer_serializer = CustomerSerializer(customer)

        return Response({
            'customer':customer_serializer.data,
            'account':account,
            'invoices':invoices,
            'invoice_payments':invoice_payments
        }, status.HTTP_200_OK)

class CustomerDepositsView(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, id):
        customer_id = id

        if customer_id:
            deposits = CustomerDeposits.objects.filter(branch=request.user.branch).values(
                'customer_account__account__customer_id',
                'date_created',
                'amount',
                'reason',
                'currency__name',
                'currency__symbol',
                'payment_method',
                'payment_reference',
                'cashier__username',
                'id'
            ).order_by('-date_created')

            return Response(deposits, status.HTTP_200_OK)
        else:
            return Response({
                'message':f'{customer_id} was not provided'
            }, status.HTTP_400_BAD_REQUEST)

class DepositList(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        deposits = CustomerDeposits.objects.filter(branch=request.user.branch).order_by('-date_created').values()
        return Response({
            'deposits':deposits,
            'total_deposits': deposits.aggregate(Sum('amount'))['amount__sum'] or 0,
        }, status.HTTP_200_OK)

class CashTransfer(views.APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        transfers = CashTransfers.objects.filter(branch=request.user.branch)

        account_types = {
            'cash': Account.AccountType.CASH,
            'bank': Account.AccountType.BANK,
            'ecocash': Account.AccountType.ECOCASH,
        }
        form = TransferSerializer(data = request.data)
        if form.is_valid():
            transfer = form.save(commit=False)
            transfer.user = request.user
            transfer.notification_type = 'Expense'
            transfer.from_branch = request.user.branch
            transfer.branch = request.user.branch
            transfer.received_status = False

            account_name = f"{request.user.branch} {transfer.currency.name} {transfer.transfer_method.capitalize()} Account"

            try:
                account = Account.objects.get(name=account_name, type=account_types[transfer.transfer_method.lower()])
            except Account.DoesNotExist:
                return Response({'message': f'Account {account_name} not found.'}, status.HTTP_400_BAD_REQUEST)

            try:
                account_balance = AccountBalance.objects.select_for_update().get(
                    account=account,
                    currency=transfer.currency,
                    branch=request.user.branch
                )
            except AccountBalance.DoesNotExist:
                return Response({'message':'Account balance record not found.'}, status.HTTP_400_BAD_REQUEST)

            if account_balance.balance < transfer.amount:
                return Response({'message':'Insufficient funds in the account.'}, status.HTTP_400_BAD_REQUEST)

            account_balance.balance -= transfer.amount
            account_balance.save()
            transfer.save()

            return Response({'message':'Money successfully transferred.'}, status.HTTP_200_OK)
        else:
            return Response({'message':'Invalid form data. Please correct the errors.'}, status.HTTP_400_BAD_REQUEST)

class CashTransferList(views.APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        search_query = request.data.get('q', '')
        transfers = CashTransfers.objects.filter(to=request.user.branch.id).values()

        if search_query:
            transfers = transfers.filter(Q(date__icontains=search_query))
        return Response({'transfers':transfers, 'search_query':search_query}, status.HTTP_200_OK)

class ReceiveMoneyTransfer(views.APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, transfer_id):
        if transfer_id:
            transfer = get_object_or_404(CashTransfers, id=transfer_id)
            account_types = {
                'cash': Account.AccountType.CASH,
                'bank': Account.AccountType.BANK,
                'ecocash': Account.AccountType.ECOCASH,
            }

            account_name = f"{request.user.branch} {transfer.currency.name} {transfer.transfer_method.capitalize()} Account"

            try:
                account, _ = Account.objects.get_or_create(name=account_name, type=account_types[transfer.transfer_method.lower()])
            except Account.DoesNotExist:
                return Response({'message':f"Account '{account_name}' not found."}, status.HTTP_400_BAD_REQUEST)

            try:
                account_balance, _ = AccountBalance.objects.get_or_create(
                    account=account,
                    currency=transfer.currency,
                    branch=request.user.branch
                )
            except AccountBalance.DoesNotExist:
                return Response({'message':"Account balance record not found."}, status.HTTP_400_BAD_REQUEST)

            account_balance.balance += transfer.amount
            account_balance.save()

            transfer.received_status = True
            transfer.save()
            return Response(status.HTTP_200_OK)
        return Response({'message':"Transfer ID is needed"}, status.HTTP_400_BAD_REQUEST)

class FinanceNotification(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        notifications = FinanceNotifications.objects.filter(status=True).values(
            'transfer__id',
            'transfer__to',
            'expense__id',
            'expense__branch',
            'invoice__id',
            'invoice__branch',
            'notification',
            'notification_type',
            'id'
        )
        return Response(notifications, status.HTTP_200_OK)

class CurrencyViewset(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    def retrieve(self, request, pk):
        logger.info(pk)
        data = Currency.objects.get(id = pk)
        info = {
            'code': data.code,
            'name': data.name,
            'symbol': data.symbol,
            'exchange rate': data.exchange_rate
        }
        return Response(info, status.HTTP_200_OK)
    def list(self, request):
        data = self.queryset.values()
        logger.info(data)
        return Response(data, status.HTTP_200_OK)
    def create(self, request):
        con_data = request.data
        data = {
            'code': con_data.get('code'),
            'name': con_data.get('name'),
            'symbol': con_data.get('symbol'),
            'exchange_rate': con_data.get('exchange_rate')
        }
        if not Currency.objects.filter(name = con_data.get('name')):
            Currency.objects.create(
                code = data.get('code'),
                name = data.get('name'),
                symbol = data.get('symbol'),
                exchange_rate = data.get('exchange_rate')
            )
            data_saved = Currency.objects.get(name = data.get('name'))
            logger.info(data_saved)
            data_returned = {
                'code': data_saved.code,
                'name': data_saved.name,
                'symbol': data_saved.symbol,
                'exchange_rate': data_saved.exchange_rate
            }
            return Response(data_returned,status.HTTP_201_CREATED)
        return Response(status.HTTP_400_BAD_REQUEST)
    def update(self, request, pk):
        logger.info(pk)
        data = request.data
        change_data = Currency.objects.get(id = pk)
        change_data.code = data.get('code')
        change_data.name = data.get('name')
        change_data.symbol = data.get('symbol')
        change_data.exchange_rate = data.get('exchange rate')

        change_data.save()
        updated_data = Currency.objects.get(id = pk)

        data_returned = {
                'code': updated_data.code,
                'name': updated_data.name,
                'symbol': updated_data.symbol,
                'exchange_rate': updated_data.exchange_rate
        }
        return Response(data_returned, status.HTTP_200_OK)

class CashWithdrawalsViewset(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = CashWithdrawals.objects.all()
    serializer_class = CashWithdrawalSerializer

class EndOfDay(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        today = timezone.now().date()

        user_timezone_str = request.user.timezone if hasattr(request.user, 'timezone') else 'UTC'
        user_timezone = pytz_timezone(user_timezone_str)

        def filter_by_date_range(start_date, end_date):
            start_datetime = user_timezone.localize(
                timezone.datetime.combine(start_date, timezone.datetime.min.time())
            )
            end_datetime = user_timezone.localize(
                timezone.datetime.combine(end_date, timezone.datetime.max.time())
            )
            return Invoice.objects.filter(branch=request.user.branch, issue_date__range=[start_datetime, end_datetime])

        now = timezone.now().astimezone(user_timezone)
        today = now.date()

        invoices = filter_by_date_range(today, today)
        withdrawals = CashWithdraw.objects.filter(user__branch=request.user.branch, date=today, status=False)

        total_cash_amounts = [
            {
                'total_invoices_amount': invoices.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0,
                'total_withdrawals_amount': withdrawals.aggregate(Sum('amount'))['amount__sum'] or 0
            }
        ]

        sold_inventory = (
            ActivityLog.objects
            .filter(invoice__branch=request.user.branch, timestamp__date=today, action='Sale')
            .values('inventory__id', 'inventory__name')
            .annotate(quantity_sold=Sum('quantity'))
        )

        all_inventory = Inventory.objects.filter(branch=request.user.branch, status=True).values(
            'id', 'name', 'quantity'
        )

        inventory_data = []
        for item in sold_inventory:
            sold_info = next((inv for inv in all_inventory if item['inventory__id'] == inv['id']), None)

            if sold_info:
                inventory_data.append({
                    'id': item['inventory__id'],
                    'name': item['inventory__name'],
                    'initial_quantity': item['quantity_sold'] + sold_info['quantity'] if sold_info else 0,
                    'quantity_sold': abs(item['quantity_sold']),
                    'remaining_quantity': sold_info['quantity'] if sold_info else 0,
                    'physical_count': None
                })

        return Response({'inventory': inventory_data, 'total_cash_amounts': total_cash_amounts}, status.HTTP_200_OK)
    def post(self, request):

        today = timezone.now().date()

        user_timezone_str = request.user.timezone if hasattr(request.user, 'timezone') else 'UTC'
        user_timezone = pytz_timezone(user_timezone_str)

        def filter_by_date_range(start_date, end_date):
            start_datetime = user_timezone.localize(
                timezone.datetime.combine(start_date, timezone.datetime.min.time())
            )
            end_datetime = user_timezone.localize(
                timezone.datetime.combine(end_date, timezone.datetime.max.time())
            )
            return Invoice.objects.filter(branch=request.user.branch, issue_date__range=[start_datetime, end_datetime])

        now = timezone.now().astimezone(user_timezone)
        today = now.date()

        invoices = filter_by_date_range(today, today)
        withdrawals = CashWithdraw.objects.filter(user__branch=request.user.branch, date=today, status=False)

        total_cash_amounts = [
            {
                'total_invoices_amount': invoices.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0,
                'total_withdrawals_amount': withdrawals.aggregate(Sum('amount'))['amount__sum'] or 0
            }
        ]

        sold_inventory = (
            ActivityLog.objects
            .filter(invoice__branch=request.user.branch, timestamp__date=today, action='Sale')
            .values('inventory__id', 'inventory__name')
            .annotate(quantity_sold=Sum('quantity'))
        )
        try:
            data = request.data
            logger.info(data)

            inventory_data = []
            cashed_amount = data['cash_input']
            physical_counts = data['physical_counts']

            if not cashed_amount:
                return Response({'success': False, 'error': 'Cash input is required.'}, status.HTTP_406_NOT_ACCEPTABLE)

            if not physical_counts:
                return Response({'success': False, 'error': 'Physical counts are required.'}, status.HTTP_406_NOT_ACCEPTABLE)

            with transaction.atomic():
                for item in physical_counts:
                    try:
                        inventory = Inventory.objects.get(id=int(item['item_id']), branch=request.user.branch, status=True)
                        inventory.physical_count = item['physical_count']
                        inventory.save()

                        sold_info = next((i for i in sold_inventory if i['inventory__id'] == inventory.id), None)
                        inventory_data.append({
                            'id': inventory.id,
                            'name': inventory.name,
                            'initial_quantity': inventory.quantity,
                            'quantity_sold': abs(sold_info['quantity_sold']) if sold_info else 0,
                            'remaining_quantity': inventory.quantity - (sold_info['quantity_sold'] if sold_info else 0),
                            'physical_count': inventory.physical_count,
                            'difference': inventory.physical_count - (inventory.quantity - (sold_info['quantity_sold'] if sold_info else 0))
                        })
                    except Inventory.DoesNotExist:
                        return Response({'success': False, 'error': f'Inventory item with id {item["inventory_id"]} does not exist.'}, status.HTTP_406_NOT_ACCEPTABLE)

                today_min = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
                today_max = timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)

                invoices = Invoice.objects.filter(branch=request.user.branch, issue_date__range=(today_min, today_max))
                partial_invoices = invoices.filter(payment_status=Invoice.PaymentStatus.PARTIAL)
                paid_invoices = invoices.filter(payment_status=Invoice.PaymentStatus.PAID)

                expenses = Expense.objects.filter(branch=request.user.branch, issue_date__range=(today_min, today_max))

                confirmed_expenses = expenses.filter(status=True)
                unconfirmed_expenses = expenses.filter(status=False)

                total_sales = paid_invoices.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
                total_partial = partial_invoices.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
                total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
                expected_cash = total_sales - total_expenses

                short_fall = expected_cash - Decimal(cashed_amount)

                cashup = CashUp.objects.create(
                    date=today,
                    branch=request.user.branch,
                    expected_cash=expected_cash,
                    cashed_amount=cashed_amount,
                    received_amount=0,
                    short_fall=short_fall,
                    balance=0,
                    created_by=request.user,
                    status=False
                )

                logger.info(cashup.expected_cash)

                items = Invoice.objects.filter(
                    payment_status=Invoice.PaymentStatus.PAID,
                    issue_date__range=(today_min, today_max),
                    branch=request.user.branch
                )

                cashup.sales.set(items)

                cashup.expenses.set(expenses)

                user_account, _ = UserAccount.objects.get_or_create(
                    user=request.user,
                    defaults={
                        'balance': Decimal('0.00'),
                        'total_credits': Decimal('0.00'),
                        'total_debits': Decimal('0.00'),
                        'last_transaction_date': timezone.now()
                    }
                )

                user_transaction = UserTransaction.objects.create(
                    account=user_account,
                    transaction_type='Cash',
                    amount=total_cash_amounts[0]['total_invoices_amount'] - total_cash_amounts[0]['total_withdrawals_amount'],
                    description='End of day transaction',
                    debit = expected_cash,
                    credit = 0,
                )

                user_account.balance += user_transaction.amount
                user_account.total_debits += user_transaction.amount
                user_account.last_transaction_date = timezone.now()
                user_account.save()

                return Response({
                        "success": True,
                        "cashup_id": cashup.id,
                }, status.HTTP_200_OK)
        except json.JSONDecodeError:
            return Response({'success': False, 'error': 'Invalid JSON data.'})
        except Exception as e:
            logger.exception(f"Error processing request: {e}")
            return Response({'success': False, 'error': str(e)})

class QuatationCrud(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Qoutation.objects.all()
    serializer_class = QuotationSerializer
    def create(self, request):
        data = request.data
        qoute_id = int(data.get('id'))
        qoute_subtotal = data.get('subtotal')
        qoute_currency_id = data.get('currency_id')
        items_data = data.get('items')

        customer = Customer.objects.get(id=qoute_id)
        currency = Currency.objects.get(id=qoute_currency_id)

        qoute = Qoutation.objects.create(
            customer = customer,
            amount =  Decimal(qoute_subtotal),
            branch = request.user.branch,
            currency = currency,
            qoute_reference = Qoutation.generate_qoute_number(request.user.branch.name),
            products = ', '.join([f'{item['product_name']} x {item['quantity']}' for item in items_data])
        )
        logger.info(data)
        logger.info(items_data)
        for item_data in items_data:
            pk_id = item_data['inventory_id']
            logger.info(pk_id)
            item = Inventory.objects.get(pk=pk_id)

            QoutationItems.objects.create(
                qoute=qoute,
                product=item,
                unit_price=item.price,
                quantity=item_data['quantity'],
                total_amount= item.price * item_data['quantity'],
            )
        return Response({'qoute_id': qoute.id}, status.HTTP_201_CREATED)
    def list(self, request, *args, **kwargs):
        search_query = request.GET.get('q', '')
        qoutations = Qoutation.objects.filter(branch=request.user.branch).order_by('-date').values()

        if search_query:
            qoutations = qoutations.filter(
                Q(customer__name__icontains=search_query)|
                Q(products__icontains=search_query)|
                Q(date__icontains=search_query)|
                Q(qoute_reference__icontains=search_query)
            )
        return Response(qoutations, status.HTTP_200_OK)
    def retrieve(self, request, pk):
        search_query = request.GET.get('q', '')
        qoutations = Qoutation.objects.filter(id = pk, branch=request.user.branch).order_by('-date').values()

        if search_query:
            qoutations = qoutations.filter(
                Q(customer__name__icontains=search_query)|
                Q(products__icontains=search_query)|
                Q(date__icontains=search_query)|
                Q(qoute_reference__icontains=search_query)
            )
        return Response(qoutations, status.HTTP_200_OK)

class QuotationDelete(views.APIView):
    permission_classes = [IsAuthenticated]
    def delete(request, qoutation_id):
        qoute = get_object_or_404(Qoutation, id=qoutation_id)
        qoute.delete()
        return Response(status.HTTP_202_ACCEPTED)

class QuotationView(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(request, qoutation_id):
        qoute = Qoutation.objects.get(id=qoutation_id)
        quote_serializer = QuotationSerializer(qoute)
        qoute_items = QoutationItems.objects.filter(qoute=qoute).values()
        return Response({quote_serializer.data, qoute_items}, status.HTTP_200_OK)

class InvoiceList(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        invoices = Invoice.objects.filter(branch=request.user.branch, status=True).order_by('-invoice_number').values()

        query_params = request.GET
        if query_params.get('q'):
            search_query = query_params['q']
            invoices = invoices.filter(
                Q(customer__name__icontains=search_query) |
                Q(invoice_number__icontains=search_query) |
                Q(issue_date__icontains=search_query)
            )

        user_timezone_str = request.user.timezone if hasattr(request.user, 'timezone') else 'UTC'
        user_timezone = pytz_timezone(user_timezone_str)

        def filter_by_date_range(start_date, end_date):
            start_datetime = user_timezone.localize(
                timezone.datetime.combine(start_date, timezone.datetime.min.time())
            )
            end_datetime = user_timezone.localize(
                timezone.datetime.combine(end_date, timezone.datetime.max.time())
            )
            return invoices.filter(issue_date__range=[start_datetime, end_datetime])

        now = timezone.now().astimezone(user_timezone)
        today = now.date()

        now = timezone.now()
        today = now.date()

        date_filters = {
            'today': lambda: filter_by_date_range(today, today),
            'yesterday': lambda: filter_by_date_range(today - timedelta(days=1), today - timedelta(days=1)),
            't_week': lambda: filter_by_date_range(today - timedelta(days=today.weekday()), today),
            'l_week': lambda: filter_by_date_range(today - timedelta(days=today.weekday() + 7), today - timedelta(days=today.weekday() + 1)),
            't_month': lambda: invoices.filter(issue_date__month=today.month, issue_date__year=today.year),
            'l_month': lambda: invoices.filter(issue_date__month=today.month - 1 if today.month > 1 else 12, issue_date__year=today.year if today.month > 1 else today.year - 1),
            't_year': lambda: invoices.filter(issue_date__year=today.year),
        }

        if query_params.get('day') in date_filters:
            invoices = date_filters[query_params['day']]()

        total_partial = invoices.filter(payment_status='Partial').aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid = invoices.filter(payment_status='Paid').aggregate(Sum('amount'))['amount__sum'] or 0
        total_amount = invoices.aggregate(Sum('amount'))['amount__sum'] or 0

        logger.info(f'Invoices: {invoices.values}')

        return Response({
            'invoices': invoices,
            'total_paid': total_paid,
            'total_due': total_partial,
            'total_amount': total_amount,
        },status.HTTP_200_OK)

class ExpenseView(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        filter_option = request.GET.get('filter', 'today')
        download = request.GET.get('download')

        now = datetime.datetime.now()
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
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        else:
            start_date = now - timedelta(days=now.weekday())
            end_date = now

        expenses = Expense.objects.filter(issue_date__gte=start_date, issue_date__lte=end_date, branch=request.user.branch).order_by('issue_date').values()

        if request.user.role == 'sale':
            expenses = expenses.filter(user=request.user)

        if download:
            return Response({'https://web-production-86a7.up.railway.app/finance/vat/'}, status.HTTP_200_OK)

        return Response(
            {
                'expenses':expenses,
                'filter_option': filter_option,
            }
        )

class ExpenseDetail(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, expense_id):
        expense = get_object_or_404(Expense, id=expense_id)
        return Response(
        {
            'id': expense.id,
            'amount': expense.amount,
            'description': expense.description,
            'category': expense.category.id
        }, status.HTTP_200_OK)

class AddExpenseCategory(views.APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        categories = ExpenseCategory.objects.all().values()
        data = request.data
        category = data.get('name')
        logger.info(data)

        if ExpenseCategory.objects.filter(name=category).exists():
            return Response({'message':f'Category with ID {category} Exists.'}, status.HTTP_400_BAD_REQUEST)

        ExpenseCategory.objects.create(
            name=category
        )
        return Response(categories, status.HTTP_201_CREATED)

class EditExpense(views.APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, id):
        try:
            data = request.data
            amount = data.get('amount')
            description = data.get('description')
            category_id = data.get('category')
            expense_id = id

            if not amount or not description or not category_id:
                return Response({'message': 'Missing fields: amount, description, category.'}, status.HTTP_400_BAD_REQUEST)

            category = get_object_or_404(ExpenseCategory, id=category_id)

            if expense_id:
                expense = get_object_or_404(Expense, id=expense_id)
                before_amount = expense.amount

                expense.amount = amount
                expense.description = description
                expense.category = category
                expense.save()
                message = 'Expense successfully updated'

                try:
                    cashbook_expense = Cashbook.objects.get(expense=expense)
                    expense_amount = Decimal(expense.amount)
                    if cashbook_expense.amount < expense_amount:
                        cashbook_expense.amount = expense_amount
                        cashbook_expense.description = cashbook_expense.description + f'Expense (update from {before_amount} to {cashbook_expense.amount})'
                    else:
                        cashbook_expense.amount -= cashbook_expense.amount - expense_amount
                        cashbook_expense.description = cashbook_expense.description + f'(update from {before_amount} to {cashbook_expense.amount})'
                    cashbook_expense.save()
                except Exception as e:
                    return Response({str(e)}, status.HTTP_400_BAD_REQUEST)
            return Response({'message': message}, status.HTTP_201_CREATED)
        except Exception as e:
            return Response({str(e)}, status.HTTP_400_BAD_REQUEST)

class DeleteExpense(views.APIView):
    permission_classes = [IsAuthenticated]
    def delete(self, request, expense_id):
        try:
            expense = get_object_or_404(Expense, id=expense_id)
            expense.cancel = True
            expense.save()

            Cashbook.objects.create(
                amount=expense.amount,
            debit=True,
            credit=False,
                description=f'Expense ({expense.description}): cancelled'
            )
            return Response({'message': 'Expense successfully deleted'}, status.HTTP_200_OK)
        except Exception as e:
            return Response({'message': str(e)}, status.HTTP_400_BAD_REQUEST)

class UpdateExpenseStatus(views.APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request, id):
        try:
            data = request.data
            expense_id = id
            expense_status = data.get('status')

            expense = Expense.objects.get(id=expense_id)
            expense.status = expense_status
            expense.save()

            return Response(status.HTTP_202_ACCEPTED)
        except Exception as e:
                return Response({'message': str(e)}, status.HTTP_400_BAD_REQUEST)

class InvoicePDF(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(request, id):
        invoice_id = id
        return Response({'https://web-production-86a7.up.railway.app/finance/invoice/pdf/'}, status.HTTP_200_OK)

class CreateInvoice(views.APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            data = request.data
            invoice_data = data['data'][0]
            items_data = data.get('items')
            layby_dates = data.get('layby_dates')

            logger.info(f'Invoice data: {data}')

            currency = Currency.objects.get(id=invoice_data['currency'])

            account_types = {
                'cash': Account.AccountType.CASH,
                'bank': Account.AccountType.BANK,
                'ecocash': Account.AccountType.ECOCASH,
            }

            account_name = f"{request.user.branch} {currency.name} {invoice_data['payment_method'].capitalize()} Account"

            account, _ = Account.objects.get_or_create(name=account_name, type=account_types[invoice_data['payment_method']])

            account_balance, _ = AccountBalance.objects.get_or_create(
                account=account,
                currency=currency,
                branch=request.user.branch,
                defaults={'balance': 0}
            )
            logger.info(f"[Create Invoice]: {account_balance}")


            accounts_receivable, _ = ChartOfAccounts.objects.get_or_create(name="Accounts Receivable")

            vat_rate = VATRate.objects.get(status=True)

            customer = Customer.objects.get(id=int(invoice_data['client_id']))
            logger.info(customer)

            customer_account = CustomerAccount.objects.get(customer=customer)

            customer_account_balance, _ = CustomerAccountBalances.objects.get_or_create(
                account=customer_account,
                currency=currency,
                defaults={'balance': 0}
            )

            amount_paid = invoice_data['amount_paid']

            logger.info(f'Amount paid: {amount_paid}')

            invoice_total_amount = Decimal(invoice_data['payable'])

            if amount_paid > invoice_total_amount:
                amount_paid = invoice_total_amount
            else:
                amount_paid = amount_paid

            amount_due = invoice_total_amount - Decimal(invoice_data['amount_paid'])

            logger.info(f'amount_due: {amount_due}, amount_paid: {amount_paid}, invoice_total_amount: {invoice_total_amount}')

            cogs = COGS.objects.create(amount=Decimal(0))

            products_purchased = f"""{', '.join([f'{item['product_name']} x {item['quantity']} ' for item in items_data])}"""
            logger.info(products_purchased)

            with transaction.atomic():
                invoice = Invoice.objects.create(
                    invoice_number=Invoice.generate_invoice_number(request.user.branch.name),
                    customer=customer,
                    issue_date=timezone.now(),
                    amount=invoice_total_amount,
                    amount_paid=amount_paid,
                    amount_due=amount_due,
                    vat=Decimal(invoice_data['vat_amount']),
                    payment_status = Invoice.PaymentStatus.PARTIAL if amount_due > 0 else Invoice.PaymentStatus.PAID,
                    branch = request.user.branch,
                    user=request.user,
                    currency=currency,
                    subtotal=invoice_data['subtotal'],
                    reocurring = invoice_data['recourring'],
                    products_purchased = products_purchased,
                    payment_terms = invoice_data['paymentTerms'],
                    hold_status = invoice_data['hold_status'],
                    amount_received = amount_paid
                )

                logger.info(f'Invoice created for customer: {invoice}')

                if invoice.hold_status == True:

                    logger.info(f'Processing held invoice: {invoice}')

                    held_invoice(items_data, invoice, request, vat_rate)

                    return JsonResponse({'hold':True, 'message':'Invoice succesfully on hold'})

                if invoice.payment_terms == 'layby':

                    if amount_due > 0:

                        logger.info(f'Creating layby object for invoice: {invoice}')

                        layby_obj = layby.objects.create(
                            invoice=invoice,
                            branch=request.user.branch
                        )

                        layby_dates_list = []
                        number_of_dates = len(layby_dates)

                        amount_per_due_date = (amount_due / number_of_dates) if number_of_dates > 0 else 0

                        logger.info(f'Amount per due date: {amount_per_due_date} : {number_of_dates} : {layby_dates}')

                        for date in layby_dates:

                            obj = laybyDates(
                                layby=layby_obj,
                                due_date=date,
                                amount_due=round(amount_per_due_date, 2),
                            )

                            layby_dates_list.append(obj)

                        laybyDates.objects.bulk_create(layby_dates_list)

                        logger.info(f'Layby object created for invoice: {invoice}')

                if invoice.payment_terms == 'installment':

                    if invoice.reocurring:
                        MonthlyInstallment.objects.create(
                            invoice = invoice,
                        )

                if invoice.payment_terms == 'pay later':
                    if amount_due > 0:
                        paylater_obj = Paylater.objects.create(
                            invoice=invoice,
                            amount_due=amount_due,
                            due_date=invoice_data['pay_later_dates'][0] if invoice_data['pay_later_dates'] else timezone.now().date(),
                            payment_method=invoice_data['payment_method']
                        )

                        if invoice_data['pay_later_dates']:
                            amount_per_interval = amount_due / len(invoice_data['pay_later_dates'])
                            for date in invoice_data['pay_later_dates']:
                                logger.info(date)
                                paylaterDates.objects.create(
                                    paylater=paylater_obj,
                                    due_date=date,
                                    amount_due=amount_per_interval,
                                    payment_method=invoice_data['payment_method']
                                )

                Transaction.objects.create(
                    date=timezone.now(),
                    description=invoice.products_purchased,
                    account=accounts_receivable,
                    debit=Decimal(invoice_data['payable']),
                    credit=Decimal('0.00'),
                    customer=customer
                )

                logger.info(f'Creating transaction obj for invoice: {invoice}')

                invoice_items = []
                for item_data in items_data:
                    logger.info(f'Invoice Items data: {item_data}')
                    item = Inventory.objects.get(pk=item_data['inventory_id'])

                    item.quantity -= item_data['quantity']
                    item.save()

                    invoice_items.append(
                        InvoiceItem.objects.create(
                            invoice=invoice,
                            item=item,
                            quantity=item_data['quantity'],
                            unit_price=Decimal(item_data['price']),
                            vat_rate = vat_rate,
                            total_amount = Decimal(int(item_data['quantity']) * float(item_data['price'])),
                            cash_up_status = False
                        )
                    )
                    logger.info(f'Invoice Items data: {item_data}')
                    COGSItems.objects.get_or_create(
                        invoice=invoice,
                        defaults={'cogs': cogs, 'product': Inventory.objects.get(id=item.id, branch=request.user.branch)}
                    )

                    ActivityLog.objects.create(
                        branch=request.user.branch,
                        inventory=item,
                        user=request.user,
                        quantity = -item_data['quantity'],
                        total_quantity = item.quantity,
                        action='Sale',
                        invoice=invoice
                    )

                logger.info(f'Vat data: {invoice_data['vat_amount']}')
                VATTransaction.objects.create(
                    invoice=invoice,
                    vat_type=VATTransaction.VATType.OUTPUT,
                    vat_rate=VATRate.objects.get(status=True).rate,
                    tax_amount=Decimal(invoice_data['vat_amount'])
                )
                logger.info(f'Invoice Total amount data: {invoice_total_amount}')
                sale = Sale.objects.create(
                    date=timezone.now(),
                    transaction=invoice,
                    total_amount=invoice_total_amount
                )
                sale.save()
                logger.info(f'Invoice Total amount data: {type(amount_paid)}')
                Payment.objects.create(
                    invoice=invoice,
                    amount_paid=amount_paid,
                    payment_method=invoice_data['payment_method'],
                    amount_due=invoice_total_amount - Decimal(amount_paid),
                    user=request.user
                )

                cogs.amount = COGSItems.objects.filter(cogs=cogs, cogs__date=datetime.datetime.today())\
                                               .aggregate(total=Sum('product__cost'))['total'] or 0
                cogs.save()

                if invoice.payment_status == 'Partial':
                    customer_account_balance.balance += -amount_due
                    customer_account_balance.save()

                account_balance.balance = Decimal(invoice_data['payable']) + Decimal(account_balance.balance)
                account_balance.save()

                logger.info(invoice_items)

                try:
                    invoice_data = invoice_preview_json(request, invoice.id)
                    logger.info(invoice_data)

                except Exception as e:
                    logger.info(e)
                    return JsonResponse({'success': False, 'error': str(e)})

                logger.info(f'inventory creation successfully done: {invoice}')

                return Response({'success':True, 'invoice_id': invoice.id, 'invoice_data':invoice_data}, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.info(e)
            return Response({'error': e}, status.HTTP_500_INTERNAL_SERVER_ERROR)

class InvoicePaymentTrack(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, invoice_id):
        invoice_id = invoice_id

        if invoice_id:
            payments = Payment.objects.filter(invoice__id=invoice_id).order_by('-payment_date').values(
                'payment_date', 'amount_paid', 'payment_method', 'user__username'
            )
        return Response(payments, status.HTTP_200_OK)

class InvoiceDelete(views.APIView):
    permission_classes = [IsAuthenticated]
    def delete(self, request, invoice_id):
        try:
            invoice = get_object_or_404(Invoice, id=invoice_id)
            account = get_object_or_404(CustomerAccount, customer=invoice.customer)
            customer_account_balance = get_object_or_404(CustomerAccountBalances, account=account, currency=invoice.currency)

            sale = get_object_or_404(Sale, transaction=invoice)
            invoice_payment = get_object_or_404(Payment, invoice=invoice)
            stock_transactions = invoice.stocktransaction_set.all()
            vat_transaction = get_object_or_404(VATTransaction, invoice=invoice)

            with transaction.atomic():
                if invoice.payment_status == Invoice.PaymentStatus.PARTIAL:
                    customer_account_balance.balance -= invoice.amount_due

                account_types = {
                    'cash': Account.AccountType.CASH,
                    'bank': Account.AccountType.BANK,
                    'ecocash': Account.AccountType.ECOCASH,
                }

                account = get_object_or_404(
                    Account,
                    name=f"{request.user.branch} {invoice.currency.name} {invoice_payment.payment_method.capitalize()} Account",
                    type=account_types.get(invoice_payment.payment_method, None)
                )
                account_balance = get_object_or_404(AccountBalance, account=account, currency=invoice.currency, branch=request.user.branch)
                account_balance.balance -= invoice.amount_paid

                for stock_transaction in stock_transactions:
                    product = Inventory.objects.get(product=stock_transaction.item, branch=request.user.branch)
                    product.quantity += stock_transaction.quantity
                    product.save()

                    ActivityLog.objects.create(
                        invoice=invoice,
                        product_transfer=None,
                        branch=request.user.branch,
                        user=request.user,
                        action='sale return',
                        inventory=product,
                        quantity=stock_transaction.quantity,
                        total_quantity=product.quantity
                    )

                InvoiceItem.objects.filter(invoice=invoice).delete()
                StockTransaction.objects.filter(invoice=invoice).delete()
                Payment.objects.filter(invoice=invoice).delete()

                account_balance.save()
                customer_account_balance.save()
                sale.delete()
                vat_transaction.delete()
                invoice.cancelled=True
                invoice.save()

            return Response({'message': f'Invoice {invoice.invoice_number} successfully deleted'}, status.HTTP_200_OK)
        except Exception as e:
            return Response({'message': f"{e}"}, status.HTTP_400_BAD_REQUEST)

class InvoiceUpdate(views.APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request, invoice_id):
        invoice = get_object_or_404(Invoice, id=invoice_id)
        customer_account = get_object_or_404(CustomerAccount, customer=invoice.customer)
        customer_account_balance = get_object_or_404(
            CustomerAccountBalances, account=customer_account, currency=invoice.currency
        )

        data = request.data
        amount_paid = Decimal(data.get('amount_paid'))

        invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
        customer_account_balance = CustomerAccountBalances.objects.select_for_update().get(pk=customer_account_balance.pk)

        if amount_paid <= 0:
            return Response({'message': 'Invalid amount paid.'}, status.HTTP_400_BAD_REQUEST)

        if amount_paid >= invoice.amount_due:
            invoice.payment_status = Invoice.PaymentStatus.PAID
            invoice.amount_due = 0
        else:
            invoice.amount_due -= amount_paid

        invoice.amount_paid += amount_paid

        latest_payment = Payment.objects.filter(invoice=invoice).order_by('-payment_date').first()
        if latest_payment:
            amount_due = latest_payment.amount_due - amount_paid
        else:
            amount_due = invoice.amount - invoice.amount_paid

        payment = Payment.objects.create(
            invoice=invoice,
            amount_paid=amount_paid,
            amount_due=amount_due,
            payment_method=data['payment_method'],
            user=request.user
        )

        account, _ = Account.objects.get_or_create(
            name=f"{request.user.branch} {invoice.currency.name} {payment.payment_method.capitalize()} Account",
            type=Account.AccountType[payment.payment_method.upper()]
        )
        account_balance, _ = AccountBalance.objects.get_or_create(
            account=account,
            currency=invoice.currency,
            branch=request.user.branch,
            defaults={'balance': 0}
        )

        account_balance.balance += amount_paid
        if customer_account_balance.balance < 0:
            customer_account_balance.balance += amount_paid
        else:
            customer_account_balance.balance -= amount_paid

        description = ''
        if invoice.hold_status:
            description = 'Held invoice payment'
            sale = Sale.objects.create(
                date=timezone.now(),
                transaction=invoice,
                total_amount=invoice.amount
            )

            VATTransaction.objects.create(
                invoice=invoice,
                vat_type=VATTransaction.VATType.OUTPUT,
                vat_rate=VATRate.objects.get(status=True).rate,
                tax_amount=invoice.vat
            )

        else:
            description = 'Invoice payment update'

        Cashbook.objects.create(
            issue_date=invoice.issue_date,
            description=f'({description} {invoice.invoice_number})',
            debit=True,
            credit=False,
            amount=invoice.amount_paid,
            currency=invoice.currency,
            branch=invoice.branch
        )

        invoice.hold_status = False
        account_balance.save()
        customer_account_balance.save()
        invoice.save()
        payment.save()

        return Response(status.HTTP_202_ACCEPTED)

class InvoiceDetails(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, invoice_id):
        invoice = Invoice.objects.filter(id=invoice_id, branch=request.user.branch).values(
            'invoice_number',
            'customer__id',
            'customer__name',
            'products_purchased',
            'payment_status',
            'amount'
        )
        return Response(invoice, status.HTTP_200_OK)

class InvoicePreview(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, invoice_id):
        invoice = Invoice.objects.get(id=invoice_id)
        invoice_serializer = InvoiceSerializer(invoice)
        invoice_items = InvoiceItem.objects.filter(invoice=invoice).values()
        return Response({'invoice_id':invoice_id, 'invoice':invoice_serializer.data, 'invoice_items':invoice_items}, status.HTTP_200_OK)

class InvoicePreviewJson(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, invoice_id):
        try:
            invoice = Invoice.objects.get(id=invoice_id)

        except Invoice.DoesNotExist:
            return Response({"error": "Invoice not found"}, status.HTTP_400_BAD_REQUEST)

        dates = {}
        if invoice.payment_terms == 'layby':
            dates = laybyDates.objects.filter(layby__invoice=invoice).values('due_date')

        invoice_items = InvoiceItem.objects.filter(invoice=invoice).values(
            'item__name',
            'quantity',
            'item__description',
            'total_amount',
            'unit_price'
        )

        invoice_dict = {
            field.name: getattr(invoice, field.name)
            for field in invoice._meta.fields
            if field.name not in ['customer', 'currency', 'branch', 'user']
        }

        invoice_dict['customer_name'] = invoice.customer.name
        invoice_dict['customer_email'] = invoice.customer.email
        invoice_dict['customer_cell'] = invoice.customer.phone_number
        invoice_dict['customer_address'] = invoice.customer.address
        invoice_dict['currency_symbol'] = invoice.currency.symbol
        invoice_dict['amount_paid'] = invoice.amount_paid
        invoice_dict['payment_terms'] = invoice.payment_terms

        if invoice.branch:
            invoice_dict['branch_name'] = invoice.branch.name
            invoice_dict['branch_phone'] = invoice.branch.phonenumber
            invoice_dict['branch_email'] = invoice.branch.email

        invoice_dict['user_username'] = invoice.user.username

        invoice_data = {
            'invoice': invoice_dict,
            'invoice_items': invoice_items,
            'dates':dates
        }
        return Response(invoice_data, status.HTTP_200_OK)

class HeldInvoiceView(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        invoices = Invoice.objects.filter(branch=request.user.branch, status=True, hold_status =True).order_by('-invoice_number').values()
        logger.info(f'Held invoices: {invoices}')
        return Response(invoices, status.HTTP_200_OK)

class ExpenseReport(views.APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        search = request.data.get('search', '')
        start_date_str = request.data.get('startDate', '')
        end_date_str = request.data.get('endDate', '')
        category_id = request.data.get('category', '')

        if start_date_str and end_date_str:
            try:
                end_date = datetime.date.fromisoformat(end_date_str)
                start_date = datetime.date.fromisoformat(start_date_str)
            except ValueError:
                return Response({'messgae':'Invalid date format. Please use YYYY-MM-DD.'}, status.HTTP_400_BAD_REQUEST)
        else:
            start_date = ''
            end_date= ''

        try:
            category_id = int(category_id) if category_id else None
        except ValueError:
            return Response({'messgae':'Invalid category or search ID.'}, status.HTTP_400_BAD_REQUEST)

        expenses = Expense.objects.all()

        if search:
            expenses = expenses.filter(Q('amount=search'))
        if start_date:
            start_date = parse_date(start_date_str)
            expenses = expenses.filter(date__gte=start_date)
        if end_date:
            end_date = parse_date(end_date_str)
            expenses = expenses.filter(date__lte=end_date)
        if category_id:
            expenses = expenses.filter(category__id=category_id)

        return Response(
            {
                'title': 'Expenses',
                'date_range': f"{start_date} to {end_date}",
                'report_date': datetime.date.today(),
                'total_expenses':calculate_expenses_totals(expenses),
                'expenses':expenses
            },status.HTTP_200_OK
        )

class SendEmails(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response({'https://web-production-86a7.up.railway.app/finance/invoice/send/email/'}, status.HTTP_200_OK)

class SendWhatsapp(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, invoice_id):
        try:
            return Response({f'https://web-production-86a7.up.railway.app/finance/send_invoice_whatsapp/{invoice_id}/'}, status.HTTP_200_OK)
        except Exception as e:
            logger.exception(f"Error sending invoice via WhatsApp: {e}")
            return Response({"error": "Error sending invoice via WhatsApp"}, status.HTTP_400_BAD_REQUEST)

class CashbookView(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        filter_option = request.GET.get('filter', 'today')
        now = datetime.datetime.now()
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
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        else:
            start_date = now - timedelta(days=now.weekday())
            end_date = now

        entries = Cashbook.objects.filter(issue_date__gte=start_date, issue_date__lte=end_date, branch=request.user.branch).order_by('issue_date').values()

        total_debit = entries.filter(debit=True, cancelled=False).aggregate(Sum('amount'))['amount__sum'] or 0
        total_credit = entries.filter(credit=True, cancelled=False).aggregate(Sum('amount'))['amount__sum'] or 0

        balance_bf = 0

        previous_entries = Cashbook.objects.filter(issue_date__lt=start_date, branch=request.user.branch)

        previous_debit = previous_entries.filter(debit=True).aggregate(Sum('amount'))['amount__sum'] or 0
        previous_credit = previous_entries.filter(credit=True).aggregate(Sum('amount'))['amount__sum'] or 0
        balance_bf = previous_debit - previous_credit

        total_balance = total_debit - total_credit
        logger.info(total_balance)
        invoice_items = InvoiceItem.objects.all().values()

        return Response({
            'filter_option': filter_option,
            'entries': entries,
            'balance_bf': balance_bf,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'total_balance': total_balance,
            'end_date': end_date,
            'start_date': start_date,
            'invoice_items': invoice_items
        })
    def post(self, request):
        filter_option = request.data.get('filter', 'today')
        now = datetime.datetime.now()
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
            start_date = request.data.get('start_date')
            end_date = request.data.get('end_date')
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        else:
            start_date = now - timedelta(days=now.weekday())
            end_date = now

        entries = Cashbook.objects.filter(issue_date__gte=start_date, issue_date__lte=end_date, branch=request.user.branch).order_by('issue_date').values()

        total_debit = entries.filter(debit=True, cancelled=False).aggregate(Sum('amount'))['amount__sum'] or 0
        total_credit = entries.filter(credit=True, cancelled=False).aggregate(Sum('amount'))['amount__sum'] or 0

        balance_bf = 0

        previous_entries = Cashbook.objects.filter(issue_date__lt=start_date, branch=request.user.branch)

        previous_debit = previous_entries.filter(debit=True).aggregate(Sum('amount'))['amount__sum'] or 0
        previous_credit = previous_entries.filter(credit=True).aggregate(Sum('amount'))['amount__sum'] or 0
        balance_bf = previous_debit - previous_credit

        total_balance = total_debit - total_credit
        logger.info(total_balance)
        invoice_items = InvoiceItem.objects.all().values()

        return Response({
            'filter_option': filter_option,
            'entries': entries,
            'balance_bf': balance_bf,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'total_balance': total_balance,
            'end_date': end_date,
            'start_date': start_date,
            'invoice_items': invoice_items
        }, status.HTTP_200_OK)

class CashbookNote(views.APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            data = request.data
            entry_id = data.get('entry_id')
            note = data.get('note')

            entry = Cashbook.objects.get(id=entry_id)
            entry.note = note

            entry.save()
        except Exception as e:
            return Response({'message':f'{e}.'}, status.HTTP_400_BAD_REQUEST)
        return Response({'message':'Note successfully saved.'}, status.HTTP_201_CREATED)

class CashbookReport(views.APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        return Response({'https://web-production-86a7.up.railway.app/finance/report/'}, status.HTTP_200_OK)

class CancelTransaction(views.APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            data = request.data
            entry_id = int(data.get('entry_id'))

            logger.info(entry_id)

            entry = Cashbook.objects.get(id=entry_id)

            entry.cancelled = True

            if entry.director:
                entry.director = False
            elif entry.manager:
                entry.manager = False
            elif entry.accountant:
                entry.accountant = False

            entry.save()
            logger.info(entry)
            return Response(status.HTTP_201_CREATED)
        except Exception as e:
            logger.info(e)
            return Response({'message': str(e)}, status.HTTP_400_BAD_REQUEST)

class CashbookNoteView(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, entry_id):
        entry = get_object_or_404(Cashbook, id=entry_id)

        notes = entry.notes.all().order_by('timestamp')
        notes_data = [
            {'user': note.user.username, 'note': note.note, 'timestamp': note.timestamp.strftime("%Y-%m-%d %H:%M:%S")}
            for note in notes
        ]
        return Response({'notes': notes_data}, status.HTTP_200_OK)

    def post(self, request, entry_id):
        entry = get_object_or_404(Cashbook, id=entry_id)
        try:
            data = json.loads(request.body)
            note_text = data.get('note')
            CashBookNote.objects.create(entry=entry, user=request.user, note=note_text)
            return Response({'message': 'Note successfully added.'}, status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'message': str(e)}, status.HTTP_400_BAD_REQUEST)

class UpdateTransactionStatus(views.APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request, pk):
        entry = get_object_or_404(Cashbook, pk=pk)
        data = request.data

        status_t = data.get('status')
        field = data.get('field')

        if field in ['manager', 'accountant', 'director']:
            setattr(entry, field, status_t)

            if entry.cancelled:
                entry.cancelled = False
            entry.save()
            return Response({'status': getattr(entry, field)}, status.HTTP_200_OK)

        return Response(status.HTTP_400_BAD_REQUEST)

class CashFlowView(views.APIView):
    def get(self, request):
        cashflows = Cashflow.objects.all().order_by('-date').values()
        cashups = CashUp.objects.select_related('branch').filter(status=False).values()

        cashFlows_total = cashflows.aggregate(total=Sum('total'))['total'] or 0
        cash_flow_items = CashUp.objects.filter(status=False).aggregate(total=Sum('expected_cash'))['total'] or 0

        main_income_category = MainIncomeCategory.objects.all().select_related('sub_income_category').values()
        main_expense_category = MainExpenseCategory.objects.all().select_related('sub_expense').values()
        cash_flow_names = CashFlowName.objects.all().values()

        return Response(
        {
            'cashflows': cashflows,
            'cashups': cashups,
            'cashFlows_total': cashFlows_total,
            'cash_flow_items': cash_flow_items,
            'cash_flow_names': cash_flow_names,
            'income_categories': main_income_category,
            'expense_categories': main_expense_category,
        }, status.HTTP_200_OK)
    def post(self, request):
        try:
            data = request.data
            income = float(data.get('IncomeAmount', 0))
            expense_amount = float(data.get('ExpenseAmount', 0))
            transaction_type = data.get('type', '')
            income_category = data.get('incomeCategory', '')
            expense_category = data.get('expenseCategory', '')
            name = data.get('name')
            income_sub_category = data.get('incomeSubCategory', '')
            expense_sub_category = data.get('expenseSubCategory', '')
            income_branch = data.get('incomeBranch', '')
            expense_branch = data.get('expenseBranch', '')

            logger.info(expense_category)

            if not transaction_type or transaction_type not in ['income', 'expense']:
                return JsonResponse({'success': False, 'message': 'Invalid transaction type.'}, status=400)

            with transaction.atomic():
                if transaction_type == 'income':

                    if not income or income <= 0:
                        return JsonResponse({'success': False, 'message': 'Invalid amount.'}, status=400)

                    if transaction_type == 'income' and not income_category:
                        return Response({'message': 'Income category is required.'}, status.HTTP_400_BAD_REQUEST)

                    logger.info(f'Creating Income amount: {income}')
                    cash_flow_name, _ = CashFlowName.objects.get_or_create(name=name)
                    income_category, _ = MainIncomeCategory.objects.get_or_create(id=income_category, defaults={'name': 'Income'})

                    object = Cashflow.objects.create(
                        name=cash_flow_name,
                        branch=request.user.branch,
                        total=income,
                        date=datetime.datetime.now(),
                        status=False,
                        income=income,
                        income_category=income_category,
                        created_by=request.user
                    )

                    logger.info(f'Income created: {object}.')

                    return Response({'message': 'Income cashflow successfully created'}, status.HTTP_201_CREATED)

                else:

                    if not expense_amount or expense_amount <= 0:
                        return JsonResponse({'success': False, 'message': 'Invalid amount.'}, status=400)

                    if transaction_type == 'expense' and not expense_category:
                        return JsonResponse({'success': False, 'message': 'Expense category is required.'}, status=400)

                    logger.info(f'Creating Expense amount: {expense_amount}')
                    cash_flow_name, _ = CashFlowName.objects.get_or_create(name=name)
                    expense_category, _ = MainExpenseCategory.objects.get_or_create(id=expense_category, defaults={'name': 'Expense'})

                    object = Cashflow.objects.create(
                        name=cash_flow_name,
                        branch=request.user.branch,
                        total=expense_amount,
                        date=datetime.datetime.now(),
                        status=False,
                        expense=expense_amount,
                        income=0,
                        expense_category=expense_category,
                        created_by=request.user
                    )

                    logger.info(f'Expense created: {object}.')

                    return JsonResponse({'success': True, 'message': 'Expense cashflow successfully created'}, status=201)

        except Exception as e:
            logger.error(f"Error recording transaction {e}.")
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

class CashUpList(views.APIView):
    def get(self, request):
        cashups = (
            CashUp.objects
            .select_related('branch', 'created_by')
            .filter(status=False)
            .values(
                'id',
                'branch__name',
                'expected_cash',
                'created_by__username',
                'created_at',
                'received_amount'
            )
            .order_by('-created_at')
        )

        data = []
        for cashup in cashups:
            cashup_dict = dict(cashup)
            cashup_dict['created_at'] = cashup['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            data.append(cashup_dict)

        return Response({
            'success': True,
            'data': data
        }, status.HTTP_200_OK)

    def post(self, request):
        try:
            data = request.data
            cash_up_type = data.get('type', '')
            branch_id = data.get('branch_id', '')

            cash_up=None

            if not branch_id:
                logger.info('here')
                cash_up = CashUp.objects.filter(
                    status=False,
                )
                logger.info(f'cash up: {cash_up}')

            else:
                cash_up = CashUp.objects.filter(
                    branch__id=branch_id,
                    status=False
                )

            cash_up = cash_up.annotate(
                total_sales_amount=Coalesce(
                    Sum('sales__amount_paid', output_field=models.DecimalField(max_digits=10, decimal_places=2)),
                    Value(0, output_field=models.DecimalField(max_digits=10, decimal_places=2))
                ),
                total_expenses_amount=Coalesce(
                    Sum('expenses__amount', output_field=models.DecimalField(max_digits=10, decimal_places=2)),
                    Value(0, output_field=models.DecimalField(max_digits=10, decimal_places=2))
                )
                ).prefetch_related(
                    'sales',
                    'expenses'
                ).select_related(
                    'branch',
                    'created_by'
                ).order_by('-created_at__time')

            if not cash_up:
                return Response({'message': 'Cash up not found', 'success': False}, status=404)

            sales = []
            expenses = []

            logger.info(f'cash up: {cash_up}')
            for cash in cash_up:
                sales.append(
                    {
                        'cash_id': cash.id,
                        'sales': list(cash.sales.values(
                            'id',
                            'invoice_number',
                            'products_purchased',
                            'amount_paid',
                            'branch',
                            'branch__name',
                            'cash_up_status'
                        )),
                        'expenses': list(cash.expenses.values(
                            'id',
                            'amount',
                            'category__name',
                            'category__parent__name',
                            'issue_date'
                        ))
                    }
                )
            logger.info(f'cash up: {cash_up}')
            return Response({
                'success': True,
                'cash_up': list(cash_up.values(
                    'id',
                    'branch__name',
                    'expected_cash',
                    'created_by__username',
                    'created_at',
                    'received_amount',
                    'total_sales_amount',
                    'total_expenses_amount',
                    'cashed_amount',
                    'short_fall'
                )),
                'data': {
                    'sales': sales if sales else [],
                    'expenses': expenses if expenses else []
                },
            }, status=200)

        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=500)

class DaysData(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        current_month = get_current_month()

        sales = Sale.objects.filter(date__month=current_month).values()
        cogs = COGSItems.objects.filter(date__month=current_month).values()
        if sales or cogs:
            first_day = min(sales.first().date, cogs.first().date)
        else:
            return Response({'Empty':{ 'sales':sales, 'COGS':cogs}}, status.HTTP_200_OK)
        logger.info(first_day)
        def get_week_data(queryset, start_date, end_date, amount_field):
            week_data = queryset.filter(date__gte=start_date, date__lt=end_date).values(amount_field, 'date')
            logger.info(week_data)
            total = week_data.aggregate(total=Sum(amount_field))['total'] or 0
            return week_data, total

        data = {}
        for week in range(1, 5):
            week_start = first_day + timedelta(days=(week-1)*7)
            week_end = week_start + timedelta(days=7)

            logger.info(week_start)
            logger.info(week_end)

            sales_data, sales_total = get_week_data(sales, week_start, week_end, 'total_amount')
            cogs_data, cogs_total = get_week_data(cogs, week_start, week_end, 'product__cost')

            data[f'week {week}'] = {
                'sales': list(sales_data),
                'cogs': list(cogs_data),
                'total_sales': sales_total,
                'total_cogs': cogs_total
            }

        return Response(data, status.HTTP_200_OK)

class VAT(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        filter_option = request.GET.get('filter', 'this_week')
        download = request.GET.get('download')

        now = datetime.datetime.now()
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
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        else:
            start_date = now - timedelta(days=now.weekday())
            end_date = now

        vat_transactions = VATTransaction.objects.filter(date__gte=start_date, date__lte=end_date).values().order_by('-date')

        if download:
            return Response({'https://web-production-86a7.up.railway.app/finance/vat/'}, status.HTTP_200_OK)
        return Response(
            {
                'filter_option':filter_option,
                'vat_transactions':vat_transactions
            },
            status.HTTP_200_OK
        )

    def post(self, request):
        try:
            data = request.data

            date_to = data.get('date_to')
            date_from = data.get('date_from')

            vat_transactions = VATTransaction.objects.filter(
                date__gte=date_from,
                date__lte=date_to
            )

            vat_transactions.update(paid=True)
        except Exception as e:
            return Response({'message':f'{e}'}, status.HTTP_400_BAD_REQUEST)
        return Response({'message':'VAT successfully paid'}, status.HTTP_200_OK)

class PLOverview(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        filter_option = request.data.get('filter', 'today')
        today = datetime.date.today()
        previous_month = get_previous_month()
        current_year = today.year
        current_month = today.month

        sales = Sale.objects.filter(transaction__branch=request.user.branch)
        expenses = Expense.objects.filter(branch=request.user.branch)
        cogs = COGSItems.objects.filter(invoice__branch=request.user.branch)

        if filter_option == 'today':
            date_filter = today
        elif filter_option == 'last_week':
            last_week_start = today - datetime.timedelta(days=today.weekday() + 7)
            last_week_end = last_week_start + datetime.timedelta(days=6)
            date_filter = (last_week_start, last_week_end)
        elif filter_option == 'this_month':
            date_filter = (datetime.date(current_year, current_month, 1), today)
        elif filter_option == 'year':
            year = int(request.GET.get('year', current_year))
            date_filter = (datetime.date(year, 1, 1), datetime.date(year, 12, 31))
        else:
            date_filter = (datetime.date(current_year, current_month, 1), today)

        if filter_option == 'today':
            current_month_sales = sales.filter(date=date_filter).aggregate(total_sales=Sum('total_amount'))['total_sales'] or 0
            current_month_expenses = expenses.filter(issue_date=date_filter).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0
            cogs_total = cogs.filter(date=date_filter).aggregate(total_cogs=Sum('product__cost'))['total_cogs'] or 0
        elif filter_option == 'last_week':
            current_month_sales = sales.filter(date__range=date_filter).aggregate(total_sales=Sum('total_amount'))['total_sales'] or 0
            current_month_expenses = expenses.filter(issue_date__range=date_filter).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0
            cogs_total = cogs.filter(date__range=date_filter).aggregate(total_cogs=Sum('product__cost'))['total_cogs'] or 0
        else:
            current_month_sales = sales.filter(date__range=date_filter).aggregate(total_sales=Sum('total_amount'))['total_sales'] or 0
            current_month_expenses = expenses.filter(dissue_date__range=date_filter).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0
            cogs_total = cogs.filter(date__range=date_filter).aggregate(total_cogs=Sum('product__cost'))['total_cogs'] or 0

        previous_month_sales = sales.filter(date__year=current_year, date__month=previous_month).aggregate(total_sales=Sum('total_amount'))['total_sales'] or 0
        previous_month_expenses = expenses.filter(issue_date__year=current_year, issue_date__month=previous_month).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0
        previous_cogs =  cogs.filter(date__year=current_year, date__month=previous_month).aggregate(total_cogs=Sum('product__cost'))['total_cogs'] or 0

        current_net_income = current_month_sales
        previous_net_income = previous_month_sales
        current_expenses = current_month_expenses

        current_gross_profit = current_month_sales - cogs_total
        previous_gross_profit = previous_month_sales - previous_cogs

        current_net_profit = current_gross_profit - current_month_expenses
        previous_net_profit = previous_gross_profit - previous_month_expenses

        current_gross_profit_margin = (current_gross_profit / current_month_sales * 100) if current_month_sales != 0 else 0
        previous_gross_profit_margin = (previous_gross_profit / previous_month_sales * 100) if previous_month_sales != 0 else 0

        data = {
            'net_profit':current_net_profit,
            'cogs_total':cogs_total,
            'current_expenses':current_expenses,
            'current_net_profit': current_net_profit,
            'previous_net_profit':previous_net_profit,
            'current_net_income': current_net_income,
            'previous_net_income': previous_net_income,
            'current_gross_profit': current_gross_profit,
            'previous_gross_profit': previous_gross_profit,
            'current_gross_profit_margin': f'{current_gross_profit_margin:.2f}',
            'previous_gross_profit_margin': previous_gross_profit_margin,
        }

        return Response(data, status.HTTP_200_OK)

class IncomeJson(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        current_month = get_current_month()
        today = datetime.date.today()

        month = request.data.get('month', current_month)
        day = request.data.get('day', today.day)

        sales = Sale.objects.filter(transaction__branch=request.user.branch).values()

        if request.data.get('filter') == 'today':
            sales_total = sales.filter(date=today).aggregate(Sum('total_amount'))
        else:
            sales_total = sales.filter(date__month=month).aggregate(Sum('total_amount'))

        return Response({'sales_total': sales_total['total_amount__sum'] or 0}, status.HTTP_200_OK)

class ExpenseJson(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        current_month = get_current_month()
        today = datetime.date.today()

        month = request.data.get('month', current_month)
        day = request.data.get('day', today.day)

        expenses = Expense.objects.filter(branch=request.user.branch).values()

        if request.data.get('filter') == 'today':
            expense_total = expenses.filter(issue_date=today, status=False).aggregate(Sum('amount'))
        else:
            expense_total = expenses.filter(issue_date__month=month, status=False).aggregate(Sum('amount'))

        return Response({'expense_total': expense_total['amount__sum'] or 0}, status.HTTP_200_OK)

class AccountType(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        payment_options = Account.objects.all().values('name', 'type')
        return Response({'payment options': payment_options}, status.HTTP_200_OK)

class FinanceApi(views.APIView):
    def get(self, request, *args, **kwargs):

        balances = AccountBalance.objects.filter(branch=request.user.branch).values()

        recent_sales = Sale.objects.filter(transaction__branch=request.user.branch).order_by('-date')[:5].values()

        expenses_by_category = Expense.objects.values('category__name').annotate(
            total_amount=Sum('amount', output_field=DecimalField())
        ).values()

        return Response({
            'balances': balances,
            'recent_transactions': recent_sales,
            'expenses_by_category': expenses_by_category,
        })

class UserAccountsView(views.APIView):
    def get(self, request):
        users = User.objects.filter(is_active=True).prefetch_related('accounts')

        users_with_accounts = []
        for user in users:
            accounts = user.accounts.all()

            total_balance = accounts.aggregate(
                total=Coalesce(Sum('balance', output_field=DecimalField()), Decimal('0.00'))
            )['total']

            total_credits = accounts.aggregate(
                total=Coalesce(Sum('total_credits', output_field=DecimalField()), Decimal('0.00'))
            )['total']

            total_debits = accounts.aggregate(
                total=Coalesce(Sum('total_debits', output_field=DecimalField()), Decimal('0.00'))
            )['total']

            last_activity = accounts.aggregate(
                last_date=Max('last_transaction_date')
            )['last_date']

            last_activity = accounts.aggregate(
                last_date=Max('last_transaction_date')
            )['last_date']

            users_with_accounts.append({
                'user': user.get_full_name(),
                'total_balance': total_balance,
                'total_credits': total_credits,
                'total_debits': total_debits,
                'last_activity': last_activity
            })

        return Response({'Account Data':users_with_accounts}, status.HTTP_200_OK)
