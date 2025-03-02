import threading
from datetime import datetime, timedelta
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from io import BytesIO
from xhtml2pdf import pisa 
from django.utils import timezone
from django.conf import settings 
from celery import shared_task
from apps.finance.models import *
from apps.users.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from utils.email import EmailThread
from django.core.mail import EmailMessage
from loguru import logger
from django.core.mail import send_mail
from django.db.models import Q
import calendar


def get_end_of_month(date):
    """Helper function to get the last day of the current month"""
    last_day = calendar.monthrange(date.year, date.month)[1]
    return date.replace(day=last_day)

@shared_task
def generate_recurring_invoices():
    recurring_invoices = []
    next_seven_days = datetime.now() + timedelta(days=7)
    invoices_due = Invoice.objects.filter(
        reocurring=True,  
        next_due_date__lte=next_seven_days
    )

    for invoice in invoices_due:
        new_invoice = Invoice(
            invoice_number=Invoice.generate_invoice_number(invoice.branch.name),
            amount=invoice.amount,
            amount_paid=0,
            amount_due=invoice.amount_due,
            customer=invoice.customer,
            branch=invoice.branch,
            vat=invoice.vat,
            payment_status='Partial',
            currency=invoice.currency,
            subtotal=invoice.subtotal,
            note=invoice.note,
            user=invoice.user,
            products_purchased=invoice.products_purchased,
            issue_date=datetime.now(),
            due_date=datetime.now() + timedelta(days=2),
            next_due_date=datetime.now() + timedelta(days=invoice.recurrence_period), 
        )
        new_invoice.save()
        
        recurring_invoices.append(new_invoice)
       

def send_account_statement_email(customer_id, branch_id, user_id):
    # Validate inputs
    if not customer_id or not branch_id or not user_id:
        logger.error("Invalid customer_id or branch_id provided.")
        return
    
    def send_email():
        try:
            invoice_payments = Payment.objects.filter(
                invoice__branch_id=branch_id, 
                invoice__customer_id=customer_id
            ).order_by('-payment_date')

            if not invoice_payments.exists():
                logger.warning(f"No invoice payments found for customer_id: {customer_id} and branch_id: {branch_id}")
                return
        
            try:
                customer = Customer.objects.get(id=customer_id)
                account = CustomerAccountBalances.objects.filter(account__customer=customer)
            except Customer.DoesNotExist:
                logger.error(f"Customer with id {customer_id} does not exist.")
                return
            
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                logger.error(f"Customer with id {user_id} does not exist.")
                return
            
            email_body = render_to_string('emails/email_template.html', {
                "customer": customer,
                'message': f'Hi, {customer.name}. Please find your attached account statement.',
                'sender_name':user.first_name
            })
            
            html_string = render_to_string('emails/account_statement.html', {
                "invoice_payments": invoice_payments,
                'customer':customer,
                'account':account,
                'date': datetime.now()
            })

            email = EmailMessage(
                subject='Your Account Statement',
                body=email_body,
                from_email='admin@techcity.co.zw', 
                to=['cassymyo@gmail.com'],
            )
            email.content_subtype = "html"

            with BytesIO() as buffer:
                pisa.CreatePDF(html_string, dest=buffer)
                buffer.seek(0)
                email.attach(f'account statement({customer.name}).pdf', buffer.getvalue(), 'application/pdf')
                email.send()
                logger.info(f"Account statement email sent to {customer.email}")

        except Exception as e:
            logger.error(f"Error sending account statement email: {e}", exc_info=True)

    # Start the email sending function in a new thread
    email_thread = threading.Thread(target=send_email)
    email_thread.start()



def send_invoice_email_task(invoice_id):
    invoice = Invoice.objects.get(id=invoice_id)
    invoice_items = InvoiceItem.objects.filter(invoice=invoice)
    account = CustomerAccount.objects.get(customer__id = invoice.customer.id)
    
    html_string = render_to_string('pos/receipt.html', {'invoice': invoice, 'invoice_items':invoice_items, 'account':account})
    buffer = BytesIO()

    pisa.CreatePDF(html_string, dest=buffer) 

    # email = EmailMessage(
    #     'Your Invoice',
    #     'Please find your invoice attached.',
    #     'cassymyo@gmail.com',
    #     ['cassymyo@gmail.com'],
    # )
    send_html(
        'Your Invoice',
        'Please find your invoice attached.',
        'cassymyo@gmail.com',
        ['cassymyo@gmail.com'],
    )
    
    # buffer.seek(0)
    # email.attach(f'invoice_{invoice.invoice_number}.pdf', buffer.getvalue(), 'application/pdf')

    # # Send the email
    # email.send()
    print('done')



def send_email_notification(notification_id):
    try:
        expense = Expense.objects.get(pk=notification_id)
        
        subject = 'Expense Confirmation Notification'
        message = f'Please log on to confirm the expense: {expense.description}'
        from_email = expense.user.email
        to_email = ['admin@techcity .co.zw'] 
        sender_name = expense.user.first_name

        # Render the email template with context
        html_content = render_to_string('emails/email_template.html', {
            'subject': subject,
            'message': message,
            'sender_name': sender_name,
        })

        send_mail_func(subject, message, html_content, from_email, to_email)
            
    except Expense.DoesNotExist:
        print(f"Expense with ID {notification_id} does not exist")

    except Exception as e:
        print(f"An error occurred while sending email: {e}")



def send_expense_email_notification(expense_id):
    expense = Expense.objects.get(pk=expense_id)
    subject = 'Expense to be approved',
    message = expense.notification
    from_email = 'test@email.com'
    to_email = 'test@email.com'
    email = EmailMessage(subject, message, from_email, [to_email])
    email.send()

def check_and_send_invoice_reminders():
    timezone.activate(settings.TIME_ZONE) 
    now = timezone.now()
    
    due_invoices = Invoice.objects.filter(due_date__lte=now.date(), payment_status=Invoice.PaymentStatus.PARTIAL)  

    for invoice in due_invoices:
        days_overdue = (now.date() - invoice.due_date).days

        # Internal Notification
        internal_subject = f"Invoice #{invoice.id} Overdue by {days_overdue} Days"
        internal_message = (
            f"Invoice #{invoice.id} for {invoice.customer.name} is {days_overdue} days overdue. Payment status: Partial"
        )
        internal_recipients = ["your-team@example.com"]  
        
        email = EmailMessage(
            internal_subject, internal_message, "from@example.com", internal_recipients
        )
        email.send()
        
        FinanceNotifications.objects.create(
            invoice=Invoice,
            notificatioin=f"Invoice #{invoice.id} for {invoice.customer.name} is {days_overdue} days overdue. Payment status: Partial",
            status=False,
            notification_type='Invoice'
        )

        # Customer Notification
        customer_subject = f"Overdue Invoice Reminder (Invoice #{invoice.id})"
        customer_message = f"Dear {invoice.customer.name},\n\nThis is a reminder that your invoice #{invoice.id} was due on {invoice.due_date} and is currently {days_overdue} days overdue. Please settle the remaining balance as soon as possible.\n\nThank you,\nYour Company"
        email = EmailMessage(
            customer_subject, customer_message, "from@example.com", [invoice.customer.email]
        )
        email.send()


def send_expense_creation_notification(expense_id):
    expense = Expense.objects.get(id=expense_id)
    
    email = EmailMessage(
        subject=f"Expense Notification:",
        body=f"""
        The email is to notify you on the creation of an expense for {expense.description}.
        For an amount of ${expense.amount}.
        """,
        from_email='admin@techcity.co.zw',
        to=['cassymyo@gmail.com'],
    )
    
    EmailThread(email).start()
    
    logger.info('send')


@shared_task
def check_upcoming_layby_payments():
    """
    task that runs daily and checks for layby payments due in 3 days.
    Sends notifications to customers and staff about these upcoming payments.
    """
   
    today = timezone.now().date()
    three_days_from_now = today + timedelta(days=3)
    
    upcoming_payments = laybyDates.objects.filter(
        Q(due_date=three_days_from_now) &  
        Q(paid=False) 
    ).select_related('layby', 'layby__invoice', 'layby__branch')
    
    
    logger.info(f"Checking for layby payments due on {three_days_from_now}")
    
    # Send notifications for each upcoming payment
    notification_count = 0
    for payment in upcoming_payments:
        customer_notified = notify_customer_about_payment(payment)
        staff_notified = notify_staff_about_payment(payment)
        
        if customer_notified or staff_notified:
            notification_count += 1
    
    return f"Sent {notification_count} notifications for layby payments due on {three_days_from_now}"


def notify_customer_about_payment(payment):
    """Send email notification to the customer"""
    invoice = payment.layby.invoice
    customer_email = invoice.customer.email
    
    if not customer_email:
        return False
    
    end_of_month = get_end_of_month(timezone.now().date())
    
    subject = f"Payment Reminder: Your layby payment is due at the end of the month"
    message = f"""
    Dear {invoice.customer.name},
    
    This is a friendly reminder that your layby payment of {payment.amount_to_be_paid} {invoice.currency.code} 
    for invoice #{invoice.invoice_number} is due on {end_of_month.strftime('%d %B, %Y')}.
    
    Payment Details:
    - Amount Due: {payment.amount_due} {invoice.currency.code}
    - Due Date: {payment.due_date}
    - Invoice #: {invoice.invoice_number}
    - Branch: {payment.layby.branch.name}
    
    Please ensure your payment is made on time to maintain your layby agreement.
    
    Thank you for your business.
    
    Regards,
    {payment.layby.branch.name} Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [customer_email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        # Log the error
        logger.info(f"Failed to send customer notification: {str(e)}")
        return False

def notify_staff_about_payment(payment):
    """Send email notification to branch staff"""
    invoice = payment.layby.invoice
    branch = payment.layby.branch
    end_of_month = get_end_of_month(timezone.now().date())
    
    # Get staff emails (adjust this based on your user model structure)
    staff_emails = list(branch.users.filter(is_active=True).values_list('email', flat=True))
    
    if not staff_emails:
        return False
    
    subject = f"End-of-Month Layby Payment Reminder: Customer {invoice.customer.name}"
    message = f"""
    End-of-Month Layby Payment Notification
    
    Customer: {invoice.customer.name}
    Invoice #: {invoice.invoice_number}
    Amount Due: {payment.amount_due} {invoice.currency.code}
    Due Date: {end_of_month.strftime('%d %B, %Y')}
    
    This payment is due at the end of the month. Please follow up with the customer if necessary.
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            staff_emails,
            fail_silently=False,
        )
        return True
    except Exception as e:
        # Log the error
        logger.info(f"Failed to send staff notification: {str(e)}")
        return False
