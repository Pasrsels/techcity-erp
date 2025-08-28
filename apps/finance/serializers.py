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
