from django.urls import path, include
from .views import (
    expense_views,
    customer_views,
    currency_views,
    report_views,
    invoice_views,
    cashbook_views,
    financial_statement_views,
    layby_views,
    tax_views,
    quotation_views,
    cash_transfer_views,
)

app_name = 'finance'

urlpatterns = [
    # Financial Statement
    path('', financial_statement_views.Finance.as_view(), name='finance'),
    path('generate-report/', report_views.generate_financial_report, name='generate-report'),
    path('pl_overview/', report_views.pl_overview, name='pl_overview'),
    path('income_json/', report_views.income_json, name='income_json'),
    path('expense_json/', report_views.expense_json, name='expense_json'),
    path('daily_summary/', report_views.daily_summary, name='daily_summary'),
    path('branch_summary/<int:branch_id>/', report_views.branch_summary, name='branch_summary'),

    # Expenses
    path('expenses/', expense_views.expenses, name='expenses'),
    path('expenses/create/', expense_views.expenses, name='create_expense'),
    path('expenses/get/<int:expense_id>/', expense_views.get_expense, name='get_expense'),
    path('expenses/add/', expense_views.add_expense_category, name='add_expense_category'),
    path('expenses/edit/', expense_views.add_or_edit_expense, name='add_or_edit_expense'),
    path('expenses/delete/<int:expense_id>/', expense_views.delete_expense, name='delete_expense'),
    path('expenses/update-status/', expense_views.update_expense_status, name='update_expense_status'),
    path('expenses/get/', expense_views.get_expenses, name='get_expenses'),
    path('expenses/save-split/', expense_views.save_expense_split, name="save_expense_split"),
    path('expenses/categories/create/', expense_views.add_expense_category, name='create_expense_category'),
    path('expenses/categories/list/', expense_views.list_expense_categories, name='list_expense_categories'),
    path('expenses/reports/', report_views.expenses_report, name='expenses_report'),
    path('expenses/add-to-expense/', expense_views.cash_withdrawal_to_expense, name='add_to_expense'),

    # Customers
    path('customers/api/', customer_views.customer, name='customer_api'),
    path('customers/list/', customer_views.customer_list, name='customer_list'),
    path('customers/update/<int:customer_id>/', customer_views.update_customer, name='update_customer'),
    path('customers/delete/<int:customer_id>/', customer_views.delete_customer, name='delete_customer'),
    path('customers/account/<int:customer_id>/', customer_views.customer_account, name='customer_account'),
    path('customers/deposit/add/<int:customer_id>/', customer_views.add_customer_deposit, name='add_customer_deposit'),
    path('customers/deposits/', customer_views.deposits_list, name='deposits_list'),
    path('customers/deposit/refund/<int:deposit_id>/', customer_views.refund_customer_deposit, name='refund_customer_deposit'),
    path('customers/deposit/edit/<int:deposit_id>/', customer_views.edit_customer_deposit, name='edit_customer_deposit'),
    path('customers/api/deposits/', customer_views.customer_deposits, name='customer_deposits_api'),
    path('customers/api/account/transactions/', customer_views.customer_account_transactions_json, name='customer_account_transactions_json'),
    path('customers/api/account/payments/', customer_views.customer_account_payments_json, name='customer_account_payments_json'),
    path('customers/api/account/<int:customer_id>/', customer_views.customer_account_json, name='customer_account_json'),
    path('customers/print/statement/<int:customer_id>/', customer_views.print_account_statement, name='print_account_statement'),

    # Currency
    path('currency/', currency_views.currency, name='currency'),
    path('currency/json/', currency_views.currency_json, name='currency_json'),
    path('currency/add/', currency_views.add_currency, name='add_currency'),
    path('currency/update/<int:currency_id>/', currency_views.update_currency, name='update_currency'),
    path('currency/delete/<int:currency_id>/', currency_views.delete_currency, name='delete_currency'),

    # Invoice
    path('invoice/', invoice_views.invoice, name='invoice'),
    path('invoice/pdf/', invoice_views.invoice_pdf, name='invoice_pdf'),
    path('invoice/create/', invoice_views.invoice, name='create_invoice'),
    path('invoice/payments/', invoice_views.invoice_payment_track, name='payments'),
    path('invoice/delete/<int:invoice_id>/', invoice_views.delete_invoice, name='delete_invoice'),
    path('invoice/update/<str:invoice_id>/', invoice_views.update_invoice, name='update_invoice'),
    path('invoice/details/<int:invoice_id>/', invoice_views.invoice_details, name='invoice_details'),
    path('invoice/preview/<int:invoice_id>/', invoice_views.invoice_preview, name='invoice_preview'),
    path('invoice/preview/json/<int:invoice_id>/', invoice_views.invoice_preview_json, name='invoice_preview_json'),
    path('invoice/preview/data/<int:invoice_id>/', invoice_views.invoice_preview_data, name='invoice_preview_data'),
    path('held/invoices/', invoice_views.held_invoice_view, name='held_invoice'),
    path('invoice/send/email/', invoice_views.send_invoice_email, name='invoice_email'),
    path('send_invoice_whatsapp/<int:invoice_id>/', invoice_views.send_invoice_whatsapp, name='send_invoice_whatsapp'),

    # Cashbook
    path('cashbook/', cashbook_views.cashbook_view, name='cashbook'),
    path('cashbook/note/', cashbook_views.cashbook_note, name='cashbook_note'),
    path('cashbook/report/', cashbook_views.download_cashbook_report, name='download_cashbook_report'),
    path('cashbook/data/', cashbook_views.cashbook_data, name='cashbook_data'),
    path('cashbook/note/<int:entry_id>/', cashbook_views.cashbook_note_view, name='cashbook_note_view'),
    path('cashbook/update_transaction_status/<int:pk>/', cashbook_views.update_transaction_status, name='update_transaction_status'),
    path('cashbook/cancel_transaction/', cashbook_views.cancel_transaction, name='cancel_transaction'),
    path('banking/', cashbook_views.banking, name='banking'),
    path('create_bank_account/', cashbook_views.create_bank_account, name='create_bank_account'),
    path('banking_data/', cashbook_views.banking_data, name='banking_data'),

    # Cash Transfers
    path('transfer/cash/', cash_transfer_views.cash_transfer, name='cash_transfer'),
    path('transfer/cash/list/', cash_transfer_views.cash_transfer_list, name='cash_transfer_list'),
    path('transfer/cash/receive/<int:transfer_id>/', cash_transfer_views.receive_money_transfer, name='receive_money_transfer'),
    path('create_transfer/', cash_transfer_views.create_transfer, name='create_transfer'),

    # Quotations
    path('qoutation/list/', quotation_views.qoutation_list, name='qoutation_list'),
    path('qoutation/add/', quotation_views.create_quotation, name='add_qoutation'),
    path('qoutation/delete/<int:qoutation_id>/', quotation_views.delete_qoute, name='delete_qoutation'),
    path('qoutation/preview/<int:qoutation_id>/', quotation_views.qoute_preview, name='quotation_preview'),
    path('qoutation/preview/modal/<int:qoutation_id>/', quotation_views.qoute_preview_modal, name='quotation_preview_modal'),
    path('send_quote_email/<int:quote_id>/', quotation_views.send_quote_email, name='send_quote_email'),
    
    # Tax and VAT
    path('vat/', tax_views.vat, name='vat'),
    path('tax/', tax_views.tax, name='tax'),
    path('get_config/', tax_views.get_config, name='get_config'),
    path('open_fiscal/', tax_views.open_fiscal_day, name='open_fiscal'),
    path('check_fiscal_status/', tax_views.check_fiscal_status, name='check_fiscal_status'),
    path('close_fiscal/', tax_views.close_fiscal_day, name='close_fiscal'),
    path('submit_z_report/', tax_views.submit_z_report, name='submit_z_report'),

    # Layby
    path('layby/', layby_views.laybys, name='layby'),
    path('layby/data/', layby_views.layby_data, name='layby_data'),
    path('layby/pay/<int:layby_date_id>/', layby_views.layby_payment, name='layby_payment'),
    
    path('api/', include('apps.finance.api_urls')),
]
