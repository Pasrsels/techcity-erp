from apps.finance.models import *
from rest_framework import serializers

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        exclude = ['branch', 'id_number']

class CustomerAccountBalancesSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAccountBalances
        fields = '__all__'

class CustomerDepositSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerDeposits
        fields = '__all__'

class CashTransferSerializer(serializers.Serializer):
    model = CashTransfers
    fields = '__all__'


class FinanceNotificationSerializer(serializers.Serializer):
    model = FinanceNotifications
    fields = '__all__'

class CurrencySerializer(serializers.Serializer):
    model = Currency
    fields = ['code', 'name', 'symbol', 'exchange_rate']

class CashWithdrawalSerializer(serializers.Serializer):
    model = CashWithdrawals
    fields = '__all__'

class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = '__all__'

class InvoiceItemsSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = '__all__'

class PaymentSerializer(serializers.Serializer):
    class Meta:
        model = Payment
        fields = '__all__'

class QuotationSerializer(serializers.Serializer):
    class Meta:
        model = Qoutation
        fields = '__all__'

class QuotationItemSerializer(serializers.Serializer):
    class Meta:
        model = QoutationItems
        fields = '__all__'

class ExpenseSerializer(serializers.Serializer):
    class Meta:
        model = Expense
        fields = '__all__'

class ExpenseCategorySerializer(serializers.Serializer):
    class Meta:
        model = ExpenseCategory
        fields = '__all__'

class LayByDatesSerializer(serializers.Serializer):
    class Meta:
        model = laybyDates
        fields = '__all__'

class TransferSerializer(serializers.Serializer):
    class Meta:
        model = CashTransfers
        exclude = ['user', 'from_branch', 'branch', 'received_status']
        

class IncomeSerializer(serializers.Serializer):
    name = serializers.CharField()
    amount = serializers.FloatField()
    currency = serializers.IntegerField()
    account_to = serializers.IntegerField()
    branch = serializers.IntegerField()
    is_recurring = serializers.BooleanField(required=False, default=False)
    has_reminder = serializers.BooleanField(required=False, default=False)
    r_unit = serializers.CharField(required=False, allow_null=True)
    from_date = serializers.DateField(required=False, allow_null=True)
    to_date = serializers.DateField(required=False, allow_null=True)
    reminder_dated = serializers.DateField(required=False, allow_null=True)
    category = serializers.JSONField()
    main_category = serializers.JSONField()
    
    
class CashUpSerializer(serializers.ModelSerializer):
    sales = InvoiceSerializer(many=True, read_only=True)
    expenses = ExpenseSerializer(many=True, read_only=True)

    class Meta:
        model = CashUp
        fields = [
            'id', 'date', 'branch', 'expected_cash', 'received_amount',
            'balance', 'sales', 'expenses', 'status', 'sales_status',
            'expenses_status', 'cashed_amount', 'short_fall', 'created_by',
            'created_at', 'updated_at'
        ]

class PaylaterSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    customer_name = serializers.CharField(source='invoice.customer.name', read_only=True)

    class Meta:
        model = Paylater
        fields = [
            'id',
            'invoice_number',
            'customer_name',
            'due_date',
            'amount_due',
            'amount_paid',
            'paid'
        ]


class PaylaterDatesSerializer(serializers.ModelSerializer):
    class Meta:
        model = paylaterDates
        fields = ['id', 'due_date', 'amount_due', 'amount_paid', 'paid']


class PaylaterDetailSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    customer_name = serializers.CharField(source='invoice.customer.name', read_only=True)
    invoice_amount = serializers.DecimalField(source='invoice.amount', max_digits=10, decimal_places=2, read_only=True)
    invoice_amount_paid = serializers.DecimalField(source='invoice.amount_paid', max_digits=10, decimal_places=2, read_only=True)
    currency_symbol = serializers.CharField(source='invoice.currency.symbol', read_only=True)
    payment_schedule = PaylaterDatesSerializer(source='paylaterdates_set', many=True, read_only=True)

    class Meta:
        model = Paylater
        fields = [
            'id',
            'invoice_number',
            'customer_name',
            'invoice_amount',
            'due_date',
            'amount_due',
            'invoice_amount_paid',
            'currency_symbol',
            'paid',
            'payment_schedule'
        ]


class ProcessPaylaterPaymentSerializer(serializers.Serializer):
    paylater_id = serializers.IntegerField(required=True)
    amount_paid = serializers.DecimalField(max_digits=12, decimal_places=2, required=True)
    payment_method = serializers.CharField(required=True)
    payment_date = serializers.DateField(required=True)
