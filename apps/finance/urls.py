from django.urls import path, include
from . views import *
from rest_framework.routers import DefaultRouter

app_name = 'finance'

router = DefaultRouter()
<<<<<<< HEAD
router.register(r'api/v1/customers', CustomerViewset,  basename='customers')
=======
router.register(r'api-customers', CustomerCrud,  basename='customers')
router.register(r'api-currency', CurrencyViewset, basename= 'currency_crud')
router.register(r'api-Cashwithrawals', CashWithdrawalsViewset, basename= 'cash_withrawals')
router.register(r'api-quotation', QuatationCrud, basename= 'quotation')
>>>>>>> 4e458560178051856fe1d1650fc899090671a1ab

urlpatterns = [
    path('', Finance.as_view(), name='finance'),
    
    # expenses
    path('expenses', expenses, name='expenses'),
    path('get_expense/<int:expense_id>/',get_expense, name='get_expense'),
    path('add/expense/', add_expense_category, name='add_expense_category'),
    path('edit/expense/', add_or_edit_expense, name='add_or_edit_expense'),
    path('delete_expense/<int:expense_id>/', delete_expense, name='delete_expense'),
    path('update_expense_status/', update_expense_status, name='update_expense_status'),
    
    
    #invoice
    path('invoice/', invoice, name='invoice'),
    path('invoice/pdf/', invoice_pdf, name='invoice_pdf'),
    path('invoice/create/', create_invoice, name='create_invoice'),
    path('invoice/payments/', invoice_payment_track, name='payments'),
    path('invoice/delete/<int:invoice_id>/', delete_invoice, name='delete_invoice'),
    path('invoice/update/<str:invoice_id>/', update_invoice, name='update_invoice'),
    path('invoice/details/<int:invoice_id>/', invoice_details, name='invoice_details'),
    path('invoice/preview/<int:invoice_id>/', invoice_preview, name='invoice_preview'),
    path('invoice/preview/json/<int:invoice_id>/', invoice_preview_json, name='invoice_preview_json'),
    path('held/invoices', held_invoice_view, name='held_invoice'),
    
    #customer
    path('customers/', customer, name='customers'),
    path('customer/add/', customer, name='add_customer'),
    path('customers/list/', customer_list, name='customer_list'),
    path('customer/account/<int:customer_id>/', customer_account, name='customer'),
    path('customers/update/<int:customer_id>/', update_customer, name='update_customer'),
    path('customer/delete/<int:customer_id>/delete/', delete_customer, name='customer_delete'),
    #path('customer/payments/json/', customer_account_payments_json, name='customer_payments_json'),
    path('customer/edit/deposit/<int:deposit_id>/', edit_customer_deposit, name='edit_customer_deposit'),
    path('customer/account/json/<int:customer_id>/', customer_account_json, name='customer_account_json'),
    path('customer/transactions/json/', customer_account_transactions_json, name='customer_transactions_json'),
    path('customer/refund/deposit/<int:deposit_id>/', refund_customer_deposit, name='refund_customer_deposit'),
    path('print/customer/account/statement/<int:customer_id>/', print_account_statement, name='print_account_statement'),
    
    #deposits
    path('deposits/', deposits_list, name='deposits_list'),
    
    # qoutation
    path('qoutation/list/', qoutation_list, name='qoutation_list'),
    path('qoutation/add/', create_quotation, name='add_qoutation'),
    path('qoutation/delete/<int:qoutation_id>/', delete_qoute, name='delete_qoutation'),
    path('qoutation/preview/<int:qoutation_id>/', qoute_preview, name='quotation_preview'),
    
    # transfers
    path('transfer/cash/', cash_transfer, name='cash_transfer'),
    path('transfer/cash/list/', cash_transfer_list, name='cash_transfer_list'),
    path('transfer/cash/receive/<int:transfer_id>/', receive_money_transfer, name='receive_money_transfer'),
    
    # notifications
    path('finance/notifications/', finance_notifications_json, name='finance_notifications_json'),

    #currency
    path('currency/', currency, name='currency'),
    path('currency/json', currency_json, name='currency_json'),
    path('currency/add/', add_currency, name='add_currency'),
    path('currency/update/<int:currency_id>/', update_currency, name='update_currency'),
    path('currency/delete/<int:currency_id>/', delete_currency, name='delete_currency'),

    # withdrawals
    path('withdrawals/', cashWithdrawals, name='withdrawals'),
    path('delete/withdrawal/<int:withdrawal_id>/', delete_withdrawal, name='delete_withdrawal'),
    path('add/to/expense/', cash_withdrawal_to_expense, name='add_to_expense'),
    path('withdrawals/json/', cash_withdrawal_to_expense, name='withdraws_json'),
    
    # customer deposits
    path('deposits/ ', customer_deposits, name="deposits"),
    path('deposits/create-deposit/<int:customer_id>/', add_customer_deposit, name="create_customer_deposit"),
    
    # end of day
    path('end_of_day/', end_of_day, name='end_of_day'),
    
    #settings
    path('settings/', finance_settings, name='finance_setings'),
    
    #reports
    path('expenses-report/', expenses_report, name='expenses_report'),  
    
    #email
    path('invoice/send/email/', send_invoice_email, name='invoice_email'),
    path('send_invoice_whatsapp/<int:invoice_id>/', send_invoice_whatsapp, name='send_invoice_whatsapp'),
    # path('invoice/email/status/<str:task_id>/', check_email_task_status, name='email_status')
    
    # cashbook
    path('cashbook/', cashbook_view, name='cashbook'),
    path('cashbook/note/', cashbook_note, name='cashbook_note'),
    path('report/', download_cashbook_report, name='download_cashbook_report'),
    path('cancel-entry/', cancel_transaction, name='cancel-entry'),
    path('cashbook/note/<int:entry_id>/', cashbook_note_view, name='cashbook_note_view'),
    path('update_transaction_status/<int:pk>/', update_transaction_status, name='update_transaction_status'),

    # days data
    path('days_data', days_data, name='days_data'),

    path('pl_overview/', pl_overview, name='pl_overview'),
    path('income_json/', income_json, name='income_json'),
    path('expense_json/', expense_json, name='expense_json'),

    # vat
    path('vat/', vat, name='vat'),

    ########################################################################################################################
    # API end points
<<<<<<< HEAD
    path('', include(router.urls))
=======

    path('api/', include(router.urls)),

    #Customers
    path('api/customer-account/<int:customer_id>/', CustomerAccount.as_view(), name='customer_account'),
    path('api/customer-account-payments/<int:customer_id>/', customer_account_payments_json.as_view(), name='customer_account_payments'),
    path('api/customer-deposit-edit/<int:deposit_id>/', EditCustomerDeposit.as_view(), name='customer_deposit_edit'),
    path('api/customer-account-json/<int:customer_id>/', CustomerAccountJson.as_view(), name='customer_account_json'),
    path('api/customer-account-transaction-json/<int:id>/', CustomerAccountTransactionsJson.as_view(), name='customer_account_transaction_json'),
    path('api/customer-refund-deposit/<int:deposit_id>/', RefundCustomerDeposit.as_view(), name='customer_account_refund'),
    path('api/print-account-statement/<int:customer_id>/', PrintAccountStatement.as_view(), name='print_account_statement'),
    path('api/customer-deposits/<int:id>/', CustomerDeposits.as_view(), name='customer-deposits'),

    #Deposits
    path('api/deposits-list/', DepositList.as_view(), name='deposits_list'),

    #Transfers
    path('api/cash-transfer/', CashTransfer.as_view(), name='cash_transfer'),
    path('api/cash-transfer-list/', CashTransferList.as_view(), name='cash_transfer_list'),
    path('api/recieve-money-transfer/<int:transfer_id>/', ReceiveMoneyTransfer.as_view(), name='recieve_money_transfer'),

    #Nitifications
    path('api/finance-notification/', FinanceNotification.as_view(), name='finance_notification'),

    #End of Day
    path('api/end-of-day/', EndOfDay.as_view(), name='end_of_day'),

    #Quotation
    path('api/quotation-list/', QuotationList.as_view(), name='quotation_list'),

    #Expense
    path('api/expense/<int:expense_id>/', Expense.as_view(), name='expense'),
    path('api/expense_category/', ExpenseCategory.as_view(), name='expense_category'),
    path('api/add-or-edit-expense/<int:id>/', AddOrEditExpense.as_view(), name='add_edit_expense'),
    path('api/delete-expense/', DeleteExpense.as_view(), name='delete_expense'),
    path('api/update-expense-status/<int:id>/', UpdateExpenseStatus.as_view(), name='update_expense_status'),

    #Invoice
    path('api/invoice-pdf/', InvoicePDF.as_view(), name='invoice_pdf'),
    path('api/invoice-list/', InvoiceList.as_view(), name='invoice_list'),
    path('api/invoice-create/', CreateInvoice.as_view(), name='create_invoice'),
    path('api/invoice-payment-track/<int:invoice_id>/', InvoicePaymentTrack.as_view(), name='invoice_payment_track'),
    path('api/invoice-delete/<int:invoice_id>/', InvoiceDelete.as_view(), name='invoice_delete'),
    path('api/invoice-update/<int:invoice_id>/', InvoiceUpdate.as_view(), name='invoice_update'),
    path('api/invoice-details/<int:invoice_id>/', InvoiceDetails.as_view(), name='invoice_details'),
    path('api/invoice-preview/<int:invoice_id>/', InvoicePreview.as_view(), name='invoice_preview'),
    path('api/invoice-preview-json/<int:invoice_id>/', InvoicePreviewJson.as_view(), name='invoice_preview_json'),
    path('api/invoice-held/', HeldInvoiceView.as_view(), name='invoice_held'),

    #Report
    path('api/expense-report/', ExpenseReport.as_view(), name='expense_report'), 

    #Email
    path('api/invoice/send/email/', SendEmails.as_view(), name='api_send_email'),
    path('api/send_invoice_whatsapp/<int:invoice_id>/', SendWhatsapp.as_view(), name='api_send_whatsapp'),

    #Casbook
    path('api/cashbook/', CashbookView.as_view(), name='cashbook-view'),
    path('api/cashbook/note/', CashbookNote.as_view(), name='cashbook_note_'),
    path('api/report/', CashbookReport.as_view(), name='cashbook_report'),
    path('api/cancel-entry/', CancelTransaction.as_view(), name='cancel-entry_'),
    path('api/cashbook/note/<int:entry_id>/', CashbookNoteView.as_view(), name='cashbook_noteview'),
    path('api/update_transaction_status/<int:pk>/', UpdateTransactionStatus.as_view(), name='update_transaction_status'),

    #Days data
    path('api/days_data', DaysData.as_view(), name='daysdata'),

    #Vat
    path('api/vat/', VAT.as_view(), name='api_vat'),

    path('aoi/pl_overview/', PLOverview.as_view(), name='api_pl_overview'),
    path('api/income_json/', IncomeJson.as_view(), name='api_income_json'),
    path('api/expense_json/', ExpenseJson.as_view(), name='api_expense_json'),

>>>>>>> 4e458560178051856fe1d1650fc899090671a1ab
]   