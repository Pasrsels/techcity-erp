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
from django.db import transaction
from collections import defaultdict
from django.apps import apps
import datetime


@shared_task
def process_transfer(data, user_id, user_branch_id):
    """
        Asynchronously process product transfer between branches
    """
    # Get models using apps.get_model to avoid circular imports
    Transfer = apps.get_model('inventory', 'Transfer')
    TransferItems = apps.get_model('inventory', 'TransferItems')
    Inventory = apps.get_model('inventory', 'Inventory')
    Branch = apps.get_model('company', 'Branch')
    ActivityLog = apps.get_model('inventory', 'ActivityLog')
    User = apps.get_model('users', 'User')

    try:
        with transaction.atomic():
            user = User.objects.get(id=user_id)
            user_branch = Branch.objects.get(id=user_branch_id)
            
            branches_data = data['branches_to']
            transfer_id = data.get('transfer_id', '')
            cart = data['cart']
        
            # Get branch objects
            branch_objects = []
            logger.info(branch_objects)
            for branch in branches_data:
                if branch.get('value'):
                    branch_obj = Branch.objects.get(id=branch['value'])
                else:
                    branch_obj = Branch.objects.get(name=branch['name'])
                branch_objects.append(branch_obj)

            # Get products
            products = Inventory.objects.filter(
                branch=user_branch
            ).select_related('branch')
            products_dict = {product.id: product for product in products}

            # Validate quantities
            product_quantities = defaultdict(int)
            for item in cart:
                product_quantities[item['product_id']] += item['quantity']

            for product_id, total_quantity in product_quantities.items():
                product = products_dict.get(int(product_id))
                if total_quantity > product.quantity:
                    raise ValueError(f'Insufficient stock for product: {product.name}')

            # Create or get transfer
            branch_names = [branch['name'] for branch in branches_data]
            if not transfer_id:
                transfer = Transfer.objects.create(
                    branch=user_branch,
                    user=user,
                    transfer_ref=Transfer.generate_transfer_ref(user_branch.name, branch_names),
                    description='transfer'
                )
            else:
                transfer = Transfer.objects.get(id=transfer_id)
            
            transfer.transfer_to.set(branch_objects)

            # Process transfer items
            track_quantity = 0
            transfer_items = []
            
            for branch_obj in branch_objects:
                logger.info(f'Branch object: {branch_obj}')
                for item in cart:
                    if item['branch_name'] == branch_obj.name:
                        product = products_dict.get(int(item['product_id']))
                        
                        transfer_item = TransferItems(
                            transfer=transfer,
                            product=product,
                            cost=item['cost'],
                            price=item['price'],
                            dealer_price=item['dealer_price'],
                            quantity=item['quantity'],
                            from_branch=user_branch,
                            to_branch=branch_obj,
                            description=f'from {user_branch} to {branch_obj}'
                        )
                        transfer_items.append(transfer_item)
                        track_quantity += item['quantity']

            # Bulk create transfer items
            created_items = TransferItems.objects.bulk_create(transfer_items)

            # Update inventory and create activity logs
            for transfer_item in created_items:
                inventory = Inventory.objects.select_for_update().get(
                    id=transfer_item.product.id,
                    branch__name=transfer_item.from_branch
                )
                inventory.quantity -= int(transfer_item.quantity)
                inventory.save()

                # Create activity log
                ActivityLog.objects.create(
                    invoice=None,
                    product_transfer=transfer_item,
                    branch=user_branch,
                    user=user,
                    action='transfer out',
                    dealer_price=transfer_item.dealer_price,
                    selling_price=transfer_item.price,
                    inventory=inventory,
                    system_quantity=inventory.quantity,
                    quantity=-transfer_item.quantity,
                    total_quantity=inventory.quantity,
                    description=f'to {transfer_item.to_branch}'
                )

                # Update transfer quantity
                transfer.quantity += transfer_item.quantity

            transfer.total_quantity_track = track_quantity
            transfer.hold = False
            transfer.date = datetime.datetime.now()
            transfer.save()

            return {'success': True}

    except Exception as e:
        logger.error(f"Error processing transfer: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}

@shared_task
def notify_branch_transfer(transfer_id):
    """
    Notify destination branch about incoming transfer
    """
    Transfer = apps.get_model('inventory', 'Transfer')
    
    try:
        transfer = Transfer.objects.get(id=transfer_id)
        # Add notification logic here
        # Could integrate with email, SMS, or internal notification system
        return {'success': True}
    except Exception as e:
        logger.error(f"Error notifying branch: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}

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




