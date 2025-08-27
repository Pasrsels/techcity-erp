from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from loguru import logger
from ..models import TaxSettings


@login_required
def update_tax_method(request):
    selected_method_id = request.GET.get('method', None)
    try:
        if selected_method_id:
            logger.info(f'selected method: {selected_method_id}')

            tax_setting = TaxSettings.objects.get(id=selected_method_id)

            logger.info(f'tax object: {tax_setting}')

            logger.info(TaxSettings.objects.all().values())

            # remove the selected on any tax_setting method
            selected_settings = TaxSettings.objects.filter(selected=True)

            for setting in selected_settings:
                setting.selected = False
                setting.save()

            # assign the selected tax_method to be default
            tax_setting.selected = True
            tax_setting.save()

            response_data = {
                'name': tax_setting.name,
                'selected': tax_setting.selected
            }
            return JsonResponse(response_data, safe=False)
        else:
            return JsonResponse({'error': 'Invalid method'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, }, status=400)
