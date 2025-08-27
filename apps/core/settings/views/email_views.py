import json
import environ
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

@csrf_exempt
@login_required
def save_email_config(request):
    if request.method == 'POST':
        env_file_path = Path(__file__).resolve().parent.parent / '.env'

        email_settings_mapping = {
            'EMAIL_HOST': 'EMAIL_HOST',
            'EMAIL_PORT': 'EMAIL_PORT',
            'EMAIL_USE_TLS': 'EMAIL_USE_TLS',
            'EMAIL_HOST_USER': 'EMAIL_HOST_USER',
            'EMAIL_HOST_PASSWORD': 'EMAIL_HOST_PASSWORD',
        }

        email_settings_updated = False
        new_lines = []
        keys_updated = set()

        if env_file_path.exists():
            with env_file_path.open('r') as f:
                lines = f.readlines()

            for line in lines:
                if '=' in line:
                    key, *value = line.strip().split('=', 1)
                    if key in email_settings_mapping:
                        new_value = request.POST.get(key)
                        if new_value is not None:
                            if key in ('EMAIL_USE_TLS', 'EMAIL_USE_SSL'):
                                new_value = str(new_value.lower() == 'true')
                            new_lines.append(f"{email_settings_mapping[key]}={new_value}\n")
                            email_settings_updated = True
                            keys_updated.add(key)
                        else:
                            new_lines.append(line)
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)

            for key in email_settings_mapping:
                if key not in keys_updated:
                    new_value = request.POST.get(key)
                    if new_value is not None:
                        if key in ('EMAIL_USE_TLS', 'EMAIL_USE_SSL'):
                            new_value = str(new_value.lower() == 'true')
                        new_lines.append(f"{email_settings_mapping[key]}={new_value}\n")
                        email_settings_updated = True
        else:
            for key in email_settings_mapping:
                new_value = request.POST.get(key)
                if new_value is not None:
                    if key in ('EMAIL_USE_TLS', 'EMAIL_USE_SSL'):
                        new_value = str(new_value.lower() == 'true')
                    new_lines.append(f"{email_settings_mapping[key]}={new_value}\n")
                    email_settings_updated = True

        with env_file_path.open('w') as f:
            f.writelines(new_lines)

        environ.Env.read_env()

        if email_settings_updated:
            return JsonResponse({'success': True, 'message': 'Email settings updated successfully!'})
        else:
            return JsonResponse({'success': False, 'message': 'No email settings found in the form.'})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)
