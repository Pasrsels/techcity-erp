from django.contrib import admin
from . models import *

admin.site.register(Transaction)
admin.site.register(StockTransaction)
admin.site.register(VATTransaction)
admin.site.register(VATRate)
admin.site.register(Customer)
admin.site.register(Expense)
admin.site.register(ExpenseCategory)
admin.site.register(Invoice)
admin.site.register(InvoiceItem)
admin.site.register(Sale)
admin.site.register(CustomerAccount)
admin.site.register(Currency)
admin.site.register(Payment)
admin.site.register(AccountBalance)
admin.site.register(Account)
admin.site.register(CustomerAccountBalances)
admin.site.register(FinanceNotifications)
admin.site.register(CashTransfers)
admin.site.register(Qoutation)
admin.site.register(Cashbook)
admin.site.register(PurchaseOrderAccount)
admin.site.register(COGSItems)
admin.site.register(CashWithdraw)
admin.site.register(PaymentMethod)
admin.site.register(CashUp)
admin.site.register(Cashflow)
admin.site.register(MainExpenseCategory)
admin.site.register(ExpenseSubCategory)
admin.site.register(Income)
admin.site.register(IncomeCategory)
admin.site.register(Paylater)
admin.site.register(paylaterDates)

