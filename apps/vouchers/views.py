from apps.vouchers.models import *
from django.db.models import Q
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required 
from apps.vouchers.forms import addVoucherFileForm, voucherUserForm

@login_required
def voucherFiles(request):
    files = voucherFile.objects.all()
    form = addVoucherFileForm()
    if request.method == 'POST':
        form = addVoucherFileForm(request.POST, request.FILES)
        if form.is_valid():
            voucher_object = form.save(commit = False)
            voucher_object.user = request.user
            voucher_log = voucherLogs(
                user = request.user,
                action = f"{request.user} created {request.POST['name']}"
            )
            voucher_object.save()
            voucher_log.save()

    return render(request, 'vouchers/vouchers.html', {
        'voucherFiles': files,
        'form': form
    })

@login_required
def vouchersList(request):
    vou = vouchers.objects.all()
    categories = voucherCategory.objects.all()
    q =  request.GET.get('q') if request.GET.get('q') != None else ''
    try:
        filtered_vouchers = vou.filter(file__category = q) & vou.filter(status = 'unused')
    except:
        filtered_vouchers = vou.all() & vou.filter(status = 'unused')

    return render(request, 'vouchers/vouchers_list.html', {
        'vouchers': filtered_vouchers,
        'categories':categories
    })

@login_required
def addCategory(request):
    if request.method  == 'POST':
        print(request.POST['name'])
        category_name = request.POST['name']
        if voucherCategory.objects.filter(name = category_name).exists():
            messages.warning(request, 'category exists')
            return redirect('vouchers:voucherFiles')
        new_category = voucherCategory(
            name = category_name
        )
        new_category.save()
    messages.success(request, 'category successfully added')
    return redirect('vouchers:voucherFiles')

@login_required    
def populateVouchers(request, pk):
    files = voucherFile.objects.all()
    try:
        file = voucherFile.objects.get(pk=pk)
    except:
        return render(request, '404.html')

    if file.status == 'not populated':
        with open('staticfiles/media/'+ str(file.file), "r") as f:
            for voucher_number in f:
                voucher = vouchers(
                    user_id = request.user.id,
                    voucher_no = voucher_number.strip(),
                    file = file
                )
                voucher.save()
                voucher_log = voucherLogs(
                    user = request.user,
                    action = f"{request.user} populated {file.name}"
                )
                voucher_log.save()
            file.status = 'populated'
            file.save()
            messages.success(request, "Vouchers Successfully Populates." )
            return redirect('vouchers:voucherList')
    else:
        messages.error(request, "File is already populated")
    return render(request, 'vouchers/vouchers.html', {'voucherFiles': files}) 

@login_required
def addVoucherUser(request, pk):
    voucher_users = voucherUser.objects.all()
    try:
        voucher = vouchers.objects.get(id = pk)
    except:
        return render(request, '404.html')
    form =  voucherUserForm()
    if request.method == 'POST':
        form =  voucherUserForm(request.POST)
        if form.is_valid():
            vu_object = form.save(commit = False)
            vu_object.voucher_no = voucher.voucher_no,
            vu_object.save()
            return redirect('vouchers:printVoucher', voucher.id)
    return render(request, 'vouchers/addVoucherUser.html', {
        'form':form,
        'voucher_users':voucher_users
    })

@login_required 
def printVoucher(request, pk):
    try:
        voucher = vouchers.objects.get(pk=pk) 
    except:
        return render(request, '404.html')
    
    if request.method == 'POST':
        if request.POST['status'] != '':
            voucher.status = request.POST['status']
            voucher_log = voucherLogs(
                user = request.user,
                action = f"{request.user} printed voucher {voucher.voucher_no} ({voucher.file.category.name})"
            )
            voucher.save()
            voucher_log.save()
            return redirect('vouchers:voucherList')
    return render(request, 'vouchers/printVoucher.html', {'voucher':voucher})

@login_required
def voucherLog(request):
    logs = voucherLogs.objects.all()
    q = request.GET.get('q') if request.GET.get('q') != None else ''

    if q == 'create':
        return render(request, 'vouchers/voucherLogs.html', {
            'logs': logs.filter(Q(action__icontains = q ))
        })
    elif q == 'print':
        return render(request, 'vouchers/voucherLogs.html', {
            'logs': logs.filter(Q(action__icontains = q ))
        })
    elif q == 'populate':
        return render(request, 'vouchers/voucherLogs.html', {
            'logs': logs.filter(Q(action__icontains = q ))
        })
    
    return render(request, 'vouchers/voucherLogs.html',
        {'logs': logs or voucherLogs.objects.filter(
            Q(user__username__icontains = q) |
            Q(action__icontains = q)|
            Q(date_created__icontains = q)
        )}
    )
