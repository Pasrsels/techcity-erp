from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from ..models import Branch
from ..forms import BranchForm
from loguru import logger

@login_required
def branch_list(request):
    """ list all the branches in the system """
    form = BranchForm
    branches = Branch.objects.filter(disable=False)
    return render(request, 'branches.html', {
        'branches': branches,
        'form':form
    })

@login_required
def branch_switch(request, branch_id):
    """ Enables the admin or the ownwe to switch between branches """
    user = request.user
    if user.role == 'Admin' or user.role == 'admin':
        user.branch = Branch.objects.get(id=branch_id)
        user.save()
    else:
        messages.error(request, 'You are not authorized')
    return redirect('pos:pos')

@login_required
def add_branch(request):
    if request.method == 'POST':
        form = BranchForm(request.POST)
        merge_from_branch = request.POST.get('from_branch')
        try:
            if form.is_valid():
                form.save()
                return JsonResponse({'success': True, 'message': 'Branch added successfully!'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'{e}'})
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


@login_required
def edit_branch(request, branch_id):
    """ edit/branch update view"""
    branch = get_object_or_404(Branch, id=branch_id)
    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            messages.success(request, 'Branch updated successfully!')
            return redirect('company:branch_list')
    else:
        form = BranchForm(instance=branch)
    return render(
        request,
        'edit_branch.html',
        {
            'form': form,
            'branch': branch
        }
    )

@login_required
def delete_branch(request, branch_id):
    try:
        branch = Branch.objects.get(id=branch_id)
        logger.info(branch)
        branch.disable=True
        branch.save()
        return redirect('company:branch_list')
    except Exception as e:
        messages(request, f'{e}')
    return redirect('company:branch_list')
