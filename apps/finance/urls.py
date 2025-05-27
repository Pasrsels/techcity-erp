from django.urls import path, include
from . views import *
from rest_framework.routers import DefaultRouter
# from apps.finance.custom_views.cashbook_views import cashbook_data

app_name = 'finance'

router = DefaultRouter()
router.register(r'api/v1/customers_list', CustomersViewset, basename='customers_list')
router.register(r'api/v1/currency', CurrencyViewset, basename= 'api_currency_crud')
router.register(r'api/v1/Cashwithrawals', CashWithdrawalsViewset, basename= 'api_cash_withrawals')
router.register(r'api/v1/quotation', QuatationCrud, basename= 'api_quotation')

urlpatterns = [
    path('', Finance.as_view(), name='finance'),
    path('generate-report/', generate_financial_report, name='generate-report'),
    
    # expenses
    path('expenses/', expenses, name='expenses'),
    path('get_expense/<int:expense_id>/',get_expense, name='get_expense'),
    path('add/expense/', add_expense_category, name='add_expense_category'),
    path('edit/expense/', add_or_edit_expense, name='add_or_edit_expense'),
    path('delete_expense/<int:expense_id>/', delete_expense, name='delete_expense'),
    path('update_expense_status/', update_expense_status, name='update_expense_status'),
    path('get_expenses/', get_expenses, name='get_expenses'),
    path('save_expense_split/', save_expense_split, name="save_expense_split"),
    
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
    path('qoutation/preview/modal/<int:qoutation_id>/', qoute_preview_modal, name='quotation_preview_modal'),
    path('send_quote_email/<int:quote_id>/', send_quote_email, name='send_quote_email'),
    
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
    path('finance/cashbook/data/', cashbook_data, name='cashbook_data'),
    path('cashbook/note/<int:entry_id>/', cashbook_note_view, name='cashbook_note_view'),
    path('update_transaction_status/<int:pk>/', update_transaction_status, name='update_transaction_status'),

    # # New report endpoints
    # path('get-transactions-preview/', get_transactions_preview, name='get_transactions_preview'),
    # path('export-transactions/pdf/', export_transactions_pdf, name='export_transactions_pdf'),
    # path('export-transactions/excel/', export_transactions_excel, name='export_transactions_excel'),

    # days data
    path('days_data', days_data, name='days_data'),

    path('pl_overview/', pl_overview, name='pl_overview'),
    path('income_json/', income_json, name='income_json'),
    path('expense_json/', expense_json, name='expense_json'),

    # cash_flows
    path('cash_flow', cash_flow, name='cash_flow'),
    path('cash-flow/', cashflow_list, name='cashflow_list'),
    path('branch_cash_up/<int:branch_id>/', get_branch_data, name='branch_cash_up'),
    path('create_cash_flow/', cashflow_create, name='create_cash_flow'),
    path('cash_up_list/', cash_up_list, name='cash_up_list'),
    path('record_transaction/', record_cashflow_transaction, name='record_transaction'),
    path('cash-flow/categories/', get_cashflow_categories, name='cashflow_categories'),
    path('get_cash_up_details/', cash_up_list, name='get_cash_up_details'),
    path('check_cash_up_status/<int:cash_up_id>/', check_cashup_status, name='check_cashup_status'),
    path('add_income_category/', add_income_category, name='add_income_category'),
    path('confirm_cash_up/', confirm_cash_up, name='confirm_cash_up'),
    
    path('get_recorded_cash_ups/', get_recorded_cash_ups, name='get_recorded_cash_ups'),

    # user accounts
    path('user_accounts/', user_accounts, name='user_accounts'),

    # vat
    path('vat/', vat, name='vat'),

    # layby
    path('layby/', layby_data, name='layby'),
    path('layby/pay/<int:layby_date_id>/', layby_payment, name='layby_payment'),

    # tax
    path('tax', tax, name='tax'),
    path('get_status/', get_config, name='overview'),
    path('open_fiscal/', open_fiscal_day, name='get_status'),
    path('day_status/', check_fiscal_status, name='day_status'),
    path('close_fiscal/', close_fiscal_day, name='close_fiscal'),
    path('submit_z_report/', submit_z_report, name='get_status'),
    path('get_signature/', get_signature_data, name='get_signature'),
    path('submit_invoice_data/', submit_invoice_data_zimra, name='submit_invoice'),
    path('record_cashflow/', record_cashflow, name='record_cashflow'),
    path('record_income/', record_income, name='record_income'),
    path('get-incomes/', get_incomes, name='get_incomes'),
    path('banking/', banking, name='banking'),
    path('create_bank_account/', create_bank_account, name='create_bank_account'),
    path('banking_data/', banking_data, name='banking_data'),
    
    path('paylater/', paylater, name='paylater'),
    path('paylater/details/<int:paylater_id>/', paylater_details, name='paylater_details'),

    ########################################################################################################################
    # API end points
    path('', include(router.urls)),
    
    #Customers
    # path('api/v1/customers/', CustomersViewset.as_view(), name='api_customers'),
    path('api/v1/all-customer-account/', AllCustomerAccounts.as_view(), name='api_all_customer_account'),
    path('api/v1/customer-total-balances/', CustomerCurrenciesTotal.as_view(), name='api_currencies_total'),
    path('api/v1/customer-account/<int:customer_id>/', CustomerAccountView.as_view(), name='api_customer_account'),
    path('api/v1/customer-account-payments/<int:customer_id>/', CustomerPaymentsJsonView.as_view(), name='api_customer_account_payments'),
    path('api/v1/customer-deposit-edit/<int:deposit_id>/', EditCustomerDeposit.as_view(), name='api_customer_deposit_edit'),
    path('api/v1/customer-account-json/<int:customer_id>/', CustomerAccountJson.as_view(), name='api_customer_account_json'),
    path('api/v1/customer-account-transaction-json/<int:id>/', CustomerAccountTransactionsJson.as_view(), name='api_customer_account_transaction_json'),
    path('api/v1/customer-refund-deposit/<int:deposit_id>/', RefundCustomerDeposit.as_view(), name='api_customer_account_refund'),
    path('api/v1/print-account-statement/<int:customer_id>/', PrintAccountStatement.as_view(), name='api_print_account_statement'),
    path('api/v1/customer-deposits/<int:id>/', CustomerDepositsView.as_view(), name='api_customer_deposits'),

    #Deposits
    path('api/v1/deposits-list/', DepositList.as_view(), name='api_deposits_list'),

    #Transfers
    path('api/v1/cash-transfer/', CashTransfer.as_view(), name='api_cash_transfer'),
    path('api/v1/cash-transfer-list/', CashTransferList.as_view(), name='api_cash_transfer_list'),
    path('api/v1/recieve-money-transfer/<int:transfer_id>/', ReceiveMoneyTransfer.as_view(), name='api_recieve_money_transfer'),

    #Notifications
    path('api/v1/finance-notification/', FinanceNotification.as_view(), name='api_finance_notification'),

    #End of Day
    path('api/v1/end-of-day/', EndOfDay.as_view(), name='api_end_of_day'),

    #Quotation
    # path('api/v1/quotation-list/', QuotationList.as_view(), name='api_quotation_list'),

    #Expense
    path('api/v1/expense/', ExpenseView.as_view(), name='api_expense'),
    path('api/v1/expense/<int:expense_id>/', ExpenseDetail.as_view(), name='api_expense_detail'),
    path('api/v1/expense_category/', AddExpenseCategory.as_view(), name='api_expense_category'),
    path('api/v1/add-or-edit-expense/<int:id>/', EditExpense.as_view(), name='api_add_edit_expense'),
    path('api/v1/delete-expense/', DeleteExpense.as_view(), name='api_delete_expense'),
    path('api/v1/update-expense-status/<int:id>/', UpdateExpenseStatus.as_view(), name='api_update_expense_status'),

    #Invoice
    path('api/v1/invoice-pdf/', InvoicePDF.as_view(), name='api_invoice_pdf'),
    path('api/v1/invoice-list/', InvoiceList.as_view(), name='api_invoice_list'),
    path('api/v1/invoice-create/', CreateInvoice.as_view(), name='api_create_invoice'),
    path('api/v1/invoice-payment-track/<int:invoice_id>/', InvoicePaymentTrack.as_view(), name='api_invoice_payment_track'),
    path('api/v1/invoice-delete/<int:invoice_id>/', InvoiceDelete.as_view(), name='api_invoice_delete'),
    path('api/v1/invoice-update/<int:invoice_id>/', InvoiceUpdate.as_view(), name='api_invoice_update'),
    path('api/v1/invoice-details/<int:invoice_id>/', InvoiceDetails.as_view(), name='api_invoice_details'),
    path('api/v1/invoice-preview/<int:invoice_id>/', InvoicePreview.as_view(), name='api_invoice_preview'),
    path('api/v1/invoice-preview-json/<int:invoice_id>/', InvoicePreviewJson.as_view(), name='api_invoice_preview_json'),
    path('api/v1/invoice-held/', HeldInvoiceView.as_view(), name='api_invoice_held'),

    #Report
    path('api/v1/expense-report/', ExpenseReport.as_view(), name='api_expense_report'), 

    #Email
    path('api/v1/invoice/send/email/', SendEmails.as_view(), name='api_send_email'),
    path('api/v1/send_invoice_whatsapp/<int:invoice_id>/', SendWhatsapp.as_view(), name='api_send_whatsapp'),

    #Cashbook
    path('api/v1/cashbook/', CashbookView.as_view(), name='api_cashbook_view'),
    path('api/v1/cashbook/note/', CashbookNote.as_view(), name='api_cashbook_note'),
    path('api/v1/report/', CashbookReport.as_view(), name='api_cashbook_report'),
    path('api/v1/cancel-entry/', CancelTransaction.as_view(), name='api_cancel_entry'),
    path('api/v1/cashbook/note/<int:entry_id>/', CashbookNoteView.as_view(), name='api_cashbook_noteview'),
    path('api/v1/update_transaction_status/<int:pk>/', UpdateTransactionStatus.as_view(), name='api_update_transaction_status'),

    #Cash flow
    path("api/v1/cashflows", CashFlowView.as_view(), name="api_cash_flow"),
    path("api/v1/cash-up-list", CashUpList.as_view(), name="api_cash_up_list"),

    #Days data
    path('api/v1/days_data', DaysData.as_view(), name='api_days_data'),

    #Vat
    path('api/v1/vat/', VAT.as_view(), name='api_vat'),

    path('api/v1/pl_overview/', PLOverview.as_view(), name='api_pl_overview'),
    path('api/v1/income_json/', IncomeJson.as_view(), name='api_income_json'),
    path('api/v1/expense_json/', ExpenseJson.as_view(), name='api_expense_json'),

    #Account type
    path('api/v1/account-types/', AccountType.as_view(), name = 'api_account_types'),

    #Finance
    path('api/v1/finance', FinanceApi.as_view(), name ='finance_api'),

    #User accounts
    path('api/v1/user_accounts/', UserAccountsView.as_view(), name='api_user_accounts'),
]
