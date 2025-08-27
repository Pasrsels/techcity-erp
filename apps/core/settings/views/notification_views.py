import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from loguru import logger
from ..models import NotificationsSettings


def validate_payload(payload):
    # check payload for status and notification
    if 'notification' not in payload:
        return JsonResponse({'success': False, 'error': 'Notification not provided'}, status=400)
    notification = payload.get('notification')
    # check if notification is in database
    logger.info(f'Notifications in database: {NotificationsSettings._meta.get_fields()}')
    if notification not in NotificationsSettings._meta.get_fields():
        return JsonResponse({'success': False, 'error': 'Invalid notification'}, status=400)

    if 'status' not in payload:
        return JsonResponse({'success': False, 'error': 'Status not provided'}, status=400)
    # if payload is empty
    if not payload:
        return JsonResponse({'success': False, 'error': 'Empty payload'}, status=400)

    status = payload.get('status')
    # check if status is valid
    if status not in ['on', 'off']:
        return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)

    return [notification, status]


# products notifications settings views
@require_http_methods(["POST"])
@login_required
def email_notification_status(request):
    """
        payload: {"notification": "product_creation","status": "on"}
    """
    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
            logger.info(f'Payload: {payload}')
            # result = validate_payload(payload)  # validate payload
            # logger.info(f'Payload validated: {result}')
            notification = payload.get('notification')
            status = payload.get('status')
            logger.info(f'Payload validated: {notification}, {status}')
            # update status from NotificationsSettings model
            notification_instance = NotificationsSettings.objects.first()
            logger.info(f'Notification instance: {notification_instance}')
            if notification_instance:
                # update notification_instance
                if status:
                    setattr(notification_instance, notification, True)
                elif not status:
                    setattr(notification_instance, notification, False)
                notification_instance.save()
            logger.info(f'Notification: {notification} Status: {status}, updated successfully')
            return JsonResponse({'success': True}, status=200)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
