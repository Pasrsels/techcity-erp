from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from ..models import UnitMeasurement
import json
from loguru import logger

@login_required
def unit_measurement_crud(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            measure = data.get('measurement')

            measure = measure

            if UnitMeasurement.objects.filter(measurement=measure).exists():
                return JsonResponse({'success': False, 'message':f'{measure} measurement exists.' }, status = 400)

            logger.info('Creating measurement .....')

            unit = UnitMeasurement.objects.create(
                measurement = measure,
            )

            logger.info(f'Measurement created: {unit}')

            measurements = UnitMeasurement.objects.all().values()

            logger.info(f'Measurements: {measurements}')

            return JsonResponse({'success': True, 'data':list(measurements)}, status = 200)
        except Exception as e:
           return JsonResponse({'success': False, 'message':f'{e}' }, status = 400)

    elif request.method == 'GET':
        unit_measure = UnitMeasurement.objects.all()
        return JsonResponse({'success': True, 'unit_measure': unit_measure})

    elif request.method == 'UPDATE':
        data = json.load(request.body)
        measure = data.get('unit_measure')
        promotion = data.get('promotion')
        id = data.get('id')

        if not UnitMeasurement.objects.filter(id = id).exists():
            return JsonResponse({'success': False, 'message': f'id :{id} doesnot exist'})
        try:
            unit_measure = UnitMeasurement.objects.get(id = id)
            unit_measure.measurement = measure
            unit_measure.save()
            return JsonResponse({'success': True}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'reason :{e}'}, status = 400)

    elif request.method == 'DELETE':
        data = json.load(request.body)
        id = data.get('id')
        try:
            unit_measure_delete = UnitMeasurement.objects.get(id = id)
            unit_measure_delete.delete()
            return JsonResponse({'success': True}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'message':f'reason : {e}'}, status = 400)
    return JsonResponse({'success': False, 'message': 'invalid request'}, status = 500)
