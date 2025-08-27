from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from apps.finance.models import Invoice
from apps.finance.forms import CashWithdrawForm
from apps.inventory.models import ProductCategory, Inventory
from django.core.cache import cache
from django.conf import settings
from loguru import logger

@login_required
def pos(request):
    form = CashWithdrawForm()
    invoice_count = Invoice.objects.filter(issue_date=timezone.now(), branch=request.user.branch).count()
    held_invoices_count = Invoice.objects.filter(hold_status=True, branch=request.user.branch).count()

    return render(request, 'pos.html', {
        'invoice_count':invoice_count,
        'form':form,
        'count':held_invoices_count,
    })

@login_required
def new_pos(request):
    cache_key = f'pos_data_{request.user.branch.id}'
    cached_data = cache.get(cache_key)

    if cached_data is None:
        product_categories = ProductCategory.objects.all().values('id', 'name')
        products = Inventory.objects.filter(branch=request.user.branch).select_related('product_category', 'branch').values(
            'id', 'name', 'category__name', 'quantity', 'price', 'dealer_price', 'image')

        cached_data = {
            'product_categories': list(product_categories),
            'products': list(products)
        }

        cache.set(cache_key, cached_data, settings.CACHE_TTL)

        logger.info("Data fetched from database and cached")
    else:
        logger.info("Data fetched from cache")
        product_categories = cached_data['product_categories']
        products = cached_data['products']

    return render(request, 'new_pos.html',
        {
            'product_categories': product_categories,
            'products': products
        }
    )
