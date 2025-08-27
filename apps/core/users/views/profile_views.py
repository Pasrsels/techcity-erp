from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from ..models import User
from ..forms import UserDetailsForm2, UserRegistrationForm, UserPermissionsForm
from loguru import logger
from django.db.models import Q
from apps.core.company.models import Branch


@login_required
def users(request):
    form = UserRegistrationForm()
    user_details_form = UserDetailsForm2()
    formPermissions = UserPermissionsForm()

    search_query = request.GET.get('q', '')

    users = User.objects.filter(
        Q(username__icontains=search_query) | Q(email__icontains=search_query),
        is_deleted=False
    ).select_related(
        'branch',
        'company'
    ).order_by(
        'first_name',
        'last_name'
    )

    if request.method == 'POST':
        try:
            data = request.POST
            user = User()

            user.first_name = data.get('first_name')
            user.email = data.get('email')
            user.phonenumber = data.get('phonenumber')
            user.username = data.get('username')
            user.role = data.get('role')
            user.company_id = data.get('company')
            user.branch_id = data.get('branch')

            raw_password = data.get('password')
            if not raw_password:
                return JsonResponse({'success': False, 'message': 'Password is required'}, status=400)

            user.set_password(raw_password)
            user.is_active = True
            user.save()

            return JsonResponse({'success': True, 'message': 'User registered successfully'})

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    return render(request, 'auth/users.html', {
            'users': users,
            'form': form,
            'user_details_form': user_details_form,
            'PermData':formPermissions
        }
    )


@login_required
def load_branches(request):
    """
    we use this view to load branches using js
    """
    company_id = request.GET.get('company_id')
    branches = Branch.objects.filter(company_id=company_id).order_by('name')
    logger.info(f'Branches: {branches.values("id", "name")}')
    return JsonResponse(list(branches.values('id', 'name')), safe=False)


@login_required
def get_user_data(request, user_id):

    user = User.objects.get(id=user_id)

    user_data = {
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'username': user.username,
        'phonenumber': user.phonenumber,
        'company': user.company.id if user.company else None,
        'branch': user.branch.id if user.branch else None,
        'role': user.role,
    }

    logger.info(f'User data: {user_data}')

    return JsonResponse(user_data)

@login_required
def delete_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        user.is_active = False
        user.is_deleted = True

        user.save()
        return JsonResponse({'success': True, 'message': 'User deleted successfully'})

    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'User not found'})

    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})

@login_required
def user_profile(request):
    user = request.user
    return render(request, 'profile.html', {'user': user})

@login_required
def user_edit(request, user_id):

    user = User.objects.select_for_update().get(id=user_id)

    logger.info(f'Editing User: {user.first_name + " " + user.email}')

    if request.method == 'POST':
        form = UserDetailsForm2(request.POST, instance=user)

        if form.is_valid():
            form.save()

            logger.info('provide')
            messages.success(request, 'User details updated successfully')
            return redirect('users:user_detail', user_id=user.id)

        messages.error(request, 'Invalid form data')
        form = UserDetailsForm2(instance=user)

    return render(request, 'auth/users.html', {'user': user, 'form': form})

@login_required
def upload_profile(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

    if 'profile_image' not in request.FILES:
        logger.warning('No profile_image key in request.FILES')
        return JsonResponse({'success': False, 'message': 'No image uploaded'}, status=400)

    image_file = request.FILES['profile_image']
    logger.info(f"Uploaded file: {image_file.name}, type: {image_file.content_type}, size: {image_file.size}")

    if not image_file.content_type.startswith('image/'):
        return JsonResponse({'success': False, 'message': 'Invalid file type. Only images are allowed.'}, status=400)

    print('here')

    if image_file.size > 5 * 1024 * 1024:
        return JsonResponse({'success': False, 'message': 'Image too large (max 5MB)'}, status=400)

    print('here')

    try:
        # profile = getattr(request.user, 'profile_image', None)
        user = request.user

        user.profile_image = image_file
        user.save()

        print('saved')

        return JsonResponse({
            'success': True,
            'image_url': user.profile_image.url
        })
    except Exception as e:
        logger.error(f"Error uploading profile image: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while uploading the image.'
        }, status=500)

@login_required
def user_detail(request, user_id):

    user = User.objects.get(id=user_id)
    form = UserDetailsForm2()

    logger.info(f'User details: {user.first_name + " " + user.email}')

    if request.method == 'GET':
        return render(request, 'profile.html', {'user': user, 'form': form})

    if request.method == 'POST':
        form = UserDetailsForm2(request.POST, instance=user)

        if form.is_valid():
            form.save()
            messages.success(request, 'User details updated successfully')
        else:
            messages.error(request, 'Invalid form data')

        return render(request, 'users/profile.html', {'user': user, 'form': form})
