from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from django.core.paginator import Paginator
from .forms import LoginForm, StudentAddForm, UserProfileForm, PasswordUpdateForm, UserExtraInfoForm, StudentManageForm
from .models import User, UserProfile, Student
from classrooms.models import Classroom

def login_view(request):
    # If you are already logged in and try to access the login page again, navigate straight to the dashboard
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    full_name = user.get_full_name() or user.username
                    messages.success(request, f"Hello {full_name}, the system is ready!")
                    return redirect('dashboard_redirect')
                else:
                    messages.error(request, "Your account has been disabled.")
            else:
                messages.error(request, "Username or password is incorrect.")
        else:
            messages.error(request, "Username or password is incorrect.")
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect('login')

@login_required
def dashboard_redirect(request):
    """Navigate users to the home page corresponding to their role."""
    if request.user.role == 'admin' or request.user.is_superuser:
        return redirect('admin_dashboard')
    
    # By default, or student, it returns to the student page
    return redirect('student_timeline')

@login_required
def admin_dashboard(request):
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('user_dashboard')
    # Get actual quantity from Database
    student_count = User.objects.filter(role='student').count()
    class_count = Classroom.objects.count()
    
    # Get the latest data
    recent_students = User.objects.filter(role='student').order_by('-date_joined')[:5]
    recent_classes = Classroom.objects.all().order_by('-id')[:5]

    context = {
        'student_count': student_count,
        'class_count': class_count,
        'recent_students': recent_students,
        'recent_classes': recent_classes,
    }
    return render(request, 'accounts/admin_dashboard.html', context)

@login_required
def user_dashboard(request): return render(request, 'accounts/user_dashboard.html')

@login_required
def student_list(request):
    """Display student list - Only for Admin"""
    if not (request.user.role == 'admin' or request.user.is_superuser):
        messages.error(request, "You do not have permission to access this page.")
        return redirect('user_dashboard')
        
    query = request.GET.get('q', '')
    student_list = User.objects.filter(role='student').select_related('student_profile').order_by('-date_joined')
    
    if query:
        student_list = student_list.filter(
            Q(username__icontains=query) | 
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) |
            Q(student_profile__student_code__icontains=query)
        )

    paginator = Paginator(student_list, 10) # 10 students per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'accounts/student_list.html', {'page_obj': page_obj, 'query': query})

@login_required
@transaction.atomic
def student_create(request):
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('user_dashboard')
    
    if request.method == 'POST':
        form = StudentManageForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Successfully adding new students!")
            return redirect('student_list')
    else:
        form = StudentManageForm()
    return render(request, 'accounts/student_form.html', {'form': form, 'title': 'Add students'})

@login_required
@transaction.atomic
def student_update(request, pk):
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('user_dashboard')
    
    student_user = get_object_or_404(User, pk=pk, role='student')
    profile = getattr(student_user, 'student_profile', None)
    initial_data = {'student_code': profile.student_code if profile else ''}
    
    if request.method == 'POST':
        form = StudentManageForm(request.POST, instance=student_user)
        if form.is_valid():
            form.save()
            messages.success(request, "Successfully updated student information!")
            return redirect('student_list')
    else:
        form = StudentManageForm(instance=student_user, initial=initial_data)
    return render(request, 'accounts/student_form.html', {'form': form, 'title': 'Edit student information'})

@login_required
@transaction.atomic
def student_delete(request, pk):
    if not (request.user.role == 'admin' or request.user.is_superuser):
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('user_dashboard')
    
    # Use QuerySet for faster deletion (Bulk delete at DB level)
    student_qs = User.objects.filter(id=pk, role='student')
    student_user = student_qs.first()
    
    if not student_user:
        messages.error(request, "Previously deleted students or objects were not found.")
        return redirect('student_list')

    if request.method == 'POST':
        username = student_user.username
        # Deleting directly from the QuerySet helps SQL Server process the Cascade much faster than deleting the instance
        student_qs.delete()
        messages.success(request, f"Student {username} and all related data have been deleted.")
    
    return redirect('student_list')

@login_required
def profile_view(request):
    """Handle viewing and updating personal records UC02"""
    user = request.user
    # Get or create additional profiles if you don't already have them
    user_profile, created = UserProfile.objects.get_or_create(user=user)
    
    profile_form = UserProfileForm(instance=user)
    extra_form = UserExtraInfoForm(instance=user_profile)
    password_form = PasswordUpdateForm()

    if request.method == 'POST':
        # In case the user presses the button to update information
        if 'update_profile' in request.POST:
            profile_form = UserProfileForm(request.POST, request.FILES, instance=user)
            extra_form = UserExtraInfoForm(request.POST, instance=user_profile)
            if profile_form.is_valid() and extra_form.is_valid():
                profile_form.save()
                extra_form.save()
                messages.success(request, "Updated successfully!")
                return redirect('profile')

        # New feature: Delete image and use default
        elif 'reset_avatar' in request.POST:
            if user.avatar:
                user.avatar.delete(save=False) # Delete physical files from the media folder
                user.avatar = None
                user.save()
                messages.success(request, "Deleted avatar, the system will use the default icon.")
                return redirect('profile')
        
        # In case the user presses the password change button
        elif 'change_password' in request.POST:
            password_form = PasswordUpdateForm(request.POST)
            if password_form.is_valid():
                old_password = password_form.cleaned_data['old_password']
                new_password = password_form.cleaned_data['new_password']
                
                # Check old password (BR_PASSWORD_CHANGE)
                if user.check_password(old_password):
                    user.set_password(new_password)
                    user.save()
                    # Keep users from being logged out after changing their password
                    update_session_auth_hash(request, user)
                    messages.success(request, "Password changed successfully!")
                    return redirect('profile')
                else:
                    messages.error(request, "The old password is incorrect, please try again.")

    context = {
        'profile_form': profile_form,
        'extra_form': extra_form,
        'password_form': password_form,
    }
    return render(request, 'accounts/profile.html', context)
