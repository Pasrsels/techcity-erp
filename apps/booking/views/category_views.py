from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from ..models import Category
import json
from loguru import logger

@login_required
def category_crud(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name')
            name = name.lower()

            if Category.objects.filter(category_name=name).exists():
                return JsonResponse({'success': False, 'message':f'{name} category exists.' }, status = 400)

            logger.info('Creating category .....')

            cat = Category.objects.create(
                category_name = name
            )

            logger.info(f'Category created: {cat}')

            categories = Category.objects.all().values()

            logger.info(f'Categories: {categories}')
            return JsonResponse({'success': True, 'data':list(categories)}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'response': f'{e}'}, status = 400)
