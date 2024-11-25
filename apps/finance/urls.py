from django.urls import path
from . views import *

app_name = 'finance'

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
    path('customer/payments/json/', customer_account_payments_json, name='customer_payments_json'),
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
    path('vat/', vat, name='vat')
]   