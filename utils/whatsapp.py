from apps.settings.models import WhatsAppConfig
from loguru import logger

def send_whatsapp_message(user, message):
    try:
        whatsapp_configs = WhatsAppConfig.objects.all()
        logger.info(f"Found {whatsapp_configs.count()} WhatsApp configurations")
        
        if not whatsapp_configs.exists():
            return {
                'success': False,
                'message': 'No active WhatsApp configurations found'
            }
        
        import requests
        results = []
        
        for config in whatsapp_configs:
            if not config.api_key or not config.phone_number:
                logger.warning(f"Skipping incomplete config: {config}")
                results.append({
                    'success': False,
                    'phone': getattr(config, 'phone_number', 'N/A'),
                    'message': 'Incomplete configuration (missing api_key or phone_number)'
                })
                continue
                
            try:
                url = f"https://api.callmebot.com/whatsapp.php"
                params = {
                    'phone': config.phone_number,
                    'text': message,
                    'apikey': config.api_key
                }
                
                logger.info(f"Sending WhatsApp to {config.phone_number}")
                response = requests.get(url, params=params)
                
                result = {
                    'success': response.status_code == 200,
                    'phone': config.phone_number,
                    'status_code': response.status_code,
                    'response': response.text
                }
                
                if not result['success']:
                    logger.error(f"Failed to send to {config.phone_number}: {response.status_code} - {response.text}")
                
                results.append(result)
                
            except Exception as e:
                error_msg = f"Error sending to {getattr(config, 'phone_number', 'N/A')}: {str(e)}"
                logger.error(error_msg)
                results.append({
                    'success': False,
                    'phone': getattr(config, 'phone_number', 'N/A'),
                    'message': error_msg
                })
        
        any_success = any(r.get('success') for r in results)
        return {
            'success': any_success,
            'results': results,
            'message': 'Completed sending messages',
            'sent_count': sum(1 for r in results if r.get('success')),
            'failed_count': sum(1 for r in results if not r.get('success'))
        }

    except Exception as e:
        error_msg = f'Unexpected error in send_whatsapp_message: {str(e)}'
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'message': error_msg
        }