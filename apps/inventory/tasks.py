from . models import *
from utils.utils import send_mail_func
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from techcity.settings.development import SYSTEM_EMAIL
from xhtml2pdf import pisa
from io import BytesIO
from django.http import HttpResponse
from django.template.loader import render_to_string
from loguru import logger
from celery import shared_task


@shared_task
def add(x, y):
    return x + y

@shared_task
def name():
    return 'Cassim'

def send_stock_transfer_email(notification_id):
    notification = StockNotifications.objects.get(pk=notification_id)
    subject = 'Stock Transfer Notification'
    message = notification.notification
    from_email = 'admin@techcity.co.zw'
    to_email = 'cassymyo@gmail.com'
    email = EmailMessage(subject, message, from_email, [to_email])
    email.send()

def send_low_stock_email(notification_id):
    # Validate inputs
    if not notification_id:
        logger.error("Invalid notification_id provided.")
        return
    
    try:
        notification = StockNotifications.objects.get(inventory__id=notification_id)
        
        branch = notification.inventory.branch.name
        product = notification.inventory.name
        threshold = notification.inventory.stock_level_threshold
        quantity = notification.inventory.quantity
        
        subject = 'Low stock notification'
        message = f'''Hi, please take note {product} have reached low stock threshold level of {threshold} and the currenct product quantity is {quantity}. {branch} branch'''
        from_email = SYSTEM_EMAIL
        to_email = ['admin@techcity.co.zw', 'cassymyo@gmail.com'] #'pcpasels@gmail.com'
        sender_name = 'Admin'
        
        html_content = render_to_string('emails/email_template.html', {
            'subject': subject,
            'message': message,
            'sender_name': sender_name,
        })
        
        send_mail_func(subject, message, html_content, from_email, to_email)
        
        logger.info(f'{product} low stock email to {to_email} succefully sent')

    except Exception as e:
        logger.error(f"Error sending account statement email: {e}", exc_info=True)
    
def send_transfer_email(user_email, transfer_id, branch_id):
    # Validate inputs
    if not transfer_id or not branch_id or not user_email:
        logger.error("Invalid transfer_id or branch_id or user_email provided.")
        return
    
    try:
        transfer = Transfer.objects.get(id=transfer_id)
        
        try:
            branch = Branch.objects.get(id=branch_id)
        except Branch.DoesNotExist:
            logger.error(f"Branch with id {branch_id} does not exist.")
            return
        
        subject = 'Inventory transfer notification'
        message = f'''Hi, please take note Inventory with reference {transfer.transfer_ref} was transfered to your branch. 
                    Please also verify is the reference number on the IBT note is the same as on this email
                '''
        from_email = user_email
        to_email = [branch.email] 
        sender_name = transfer.user.first_name
        
        html_content = render_to_string('emails/email_template.html', {
            'subject': subject,
            'message': message,
            'sender_name': sender_name,
        })
        
        send_mail_func(subject, message, html_content, from_email, to_email)
        
        logger.info(f'Product transfer email to {branch.name} succefully sent')

    except Exception as e:
        logger.error(f"Error sending account statement email: {e}", exc_info=True)


def download_stock_logs_account(type, logs, inventory):
    """
        Generate a PDF for either stock logs or stock accounts based on the 'type'.
    """

    context = {
        'inventory':inventory,
        'logs': logs, 
    }
    
    if type == 'logs':
        html_content = render_to_string('pdf_templates/stock_logs.html', context)
    elif type == 'account':
        html_content = render_to_string('pdf_templates/stock_account.html', context)
    else:
        return HttpResponse('Invalid type', status=400)

    buffer = BytesIO()
    
    pdf_status = pisa.pisaDocument(BytesIO(html_content.encode('utf-8')), buffer)
    
    if pdf_status.err:
        return HttpResponse('Error generating PDF', status=500)
    
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename={type}_report.pdf'
    return response




