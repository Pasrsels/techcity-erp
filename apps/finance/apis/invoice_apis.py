# from collections import defaultdict
# from datetime import timedelta
# from pytz import timezone as pytz_timezone
# from django.utils import timezone
# from django.db.models import Q, Sum
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.response import Response
# from apps.finance.models import Invoice, InvoiceItem
# from ..serializers import InvoiceSerializer, InvoiceItemsSerializer

# @api_view(['GET'])
# # @permission_classes([IsAuthenticated])
# def invoice_list(request):
#     invoices = Invoice.objects.filter(
#         branch=request.user.branch, 
#         status=True, 
#         cancelled=False
#     ).select_related('branch', 'currency', 'user').order_by('-invoice_number')

#     query_params = request.query_params
#     search_query = query_params.get('q')
#     if search_query:
#         invoices = invoices.filter(
#             Q(customer__name__icontains=search_query) |
#             Q(invoice_number__icontains=search_query) |
#             Q(issue_date__icontains=search_query)
#         )

#     # Handle timezone
#     user_timezone_str = getattr(request.user, 'timezone', 'UTC')
#     user_timezone = pytz_timezone(user_timezone_str)
#     now = timezone.now().astimezone(user_timezone)
#     today = now.date()

#     def filter_by_date_range(start_date, end_date):
#         start_datetime = user_timezone.localize(
#             timezone.datetime.combine(start_date, timezone.datetime.min.time())
#         )
#         end_datetime = user_timezone.localize(
#             timezone.datetime.combine(end_date, timezone.datetime.max.time())
#         )
#         return invoices.filter(issue_date__range=[start_datetime, end_datetime])

#     date_filters = {
#         'today': lambda: filter_by_date_range(today, today),
#         'yesterday': lambda: filter_by_date_range(today - timedelta(days=1), today - timedelta(days=1)),
#         't_week': lambda: filter_by_date_range(today - timedelta(days=today.weekday()), today),
#         'l_week': lambda: filter_by_date_range(today - timedelta(days=today.weekday() + 7), today - timedelta(days=today.weekday() + 1)),
#         't_month': lambda: invoices.filter(issue_date__month=today.month, issue_date__year=today.year),
#         'l_month': lambda: invoices.filter(
#             issue_date__month=today.month - 1 if today.month > 1 else 12,
#             issue_date__year=today.year if today.month > 1 else today.year - 1
#         ),
#         't_year': lambda: invoices.filter(issue_date__year=today.year),
#     }

#     if query_params.get('day') in date_filters:
#         invoices = date_filters[query_params['day']]()

#     # Totals
#     total_partial = invoices.filter(payment_status='Partial').aggregate(Sum('amount'))['amount__sum'] or 0
#     total_paid = invoices.filter(payment_status='Paid').aggregate(Sum('amount'))['amount__sum'] or 0
#     total_amount = invoices.aggregate(Sum('amount'))['amount__sum'] or 0

#     # Grouping invoices by date
#     grouped_invoices = defaultdict(lambda: {'invoices': [], 'total_amount': 0, 'amount_due': 0})
#     for invoice in invoices:
#         issue_date = invoice.issue_date.date()
#         if issue_date == today:
#             date_key = 'Today'
#         elif issue_date == today - timedelta(days=1):
#             date_key = 'Yesterday'
#         else:
#             date_key = issue_date.strftime('%A, %d %B %Y')

#         serialized_invoice = InvoiceSerializer(invoice).data
#         grouped_invoices[date_key]['invoices'].append(serialized_invoice)
#         grouped_invoices[date_key]['total_amount'] += invoice.amount_paid

#         if invoice.payment_status == 'Paid':
#             amount_due = 0
#         elif invoice.payment_status == 'Partial':
#             amount_due = invoice.amount - invoice.amount_paid
#         else:
#             amount_due = invoice.amount
#         grouped_invoices[date_key]['amount_due'] += amount_due

#     # Reorder
#     ordered_grouped_invoices = {}
#     for key in ['Today', 'Yesterday']:
#         if key in grouped_invoices:
#             ordered_grouped_invoices[key] = grouped_invoices[key]
#     for key, value in grouped_invoices.items():
#         if key not in ['Today', 'Yesterday']:
#             ordered_grouped_invoices[key] = value

#     return Response({
#         'grouped_invoices': ordered_grouped_invoices,
#         'total_paid': total_paid,
#         'total_due': total_partial,
#         'total_amount': total_amount
#     })
