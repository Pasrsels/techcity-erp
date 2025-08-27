from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from apps.finance.models import Currency
from apps.finance.forms import CurrencyForm

@login_required
def currency(request):
    return render(request, 'currency/currency.html')

@login_required
def currency_json(request):
    currency_id = request.GET.get('id', '')
    currency = Currency.objects.filter(id=currency_id).values()
    return JsonResponse(list(currency), safe=False)


@login_required
def add_currency(request):
    if request.method == 'POST':
        form = CurrencyForm(request.POST)
        if form.is_valid():
            default = request.POST['default']
            try:
                form.save()
                messages.success(request, 'Currency added successfully!')
            except Exception as e:
                messages.error(request, f'Error adding currency: {e}')
            return redirect('finance:currency')
    else:
        form = CurrencyForm()

    return render(request, 'currency/currency_add.html', {'form': form})


@login_required
def update_currency(request, currency_id):
    currency = get_object_or_404(Currency, id=currency_id)

    if request.method == 'POST':
        form = CurrencyForm(request.POST, instance=currency)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Currency updated successfully')
            except Exception as e:
                messages.error(request, f'Error updating currency: {e}')
            return redirect('finance:currency')
    else:
        form = CurrencyForm(instance=currency)

    return render(request, 'currency/currency_add.html', {'form': form})

@login_required
def delete_currency(request, currency_id):
    if request.method == 'POST':
        currency = get_object_or_404(Currency, id=currency_id)

        try:
            if currency.invoice_set.exists() or currency.accountbalance_set.exists() or currency.expense_set.exists():
                raise Exception("Currency is in use and cannot be deleted.")

            currency.delete()
            return JsonResponse({'message': 'Currency deleted successfully'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'message':'Deletion Failed'})
