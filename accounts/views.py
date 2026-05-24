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
    # Nếu đã đăng nhập rồi mà cố truy cập lại trang login, điều hướng thẳng về dashboard
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
                    messages.success(request, f"Xin chào {full_name}, hệ thống đã sẵn sàng!")
                    return redirect('dashboard_redirect')
                else:
                    messages.error(request, "Tài khoản của bạn đã bị vô hiệu hóa.")
            else:
                messages.error(request, "Tên đăng nhập hoặc mật khẩu không chính xác.")
        else:
            messages.error(request, "Tên đăng nhập hoặc mật khẩu không chính xác.")
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "Bạn đã đăng xuất thành công.")
    return redirect('login')

@login_required
def dashboard_redirect(request):
    """Điều hướng người dùng về trang chủ tương ứng với vai trò của họ."""
    if request.user.role == 'admin' or request.user.is_superuser:
        return redirect('admin_dashboard')
    
    # Mặc định hoặc là student thì về trang học sinh
    return redirect('student_timeline')

@login_required
def admin_dashboard(request):
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('user_dashboard')
    # Lấy số lượng thực tế từ Database
    student_count = User.objects.filter(role='student').count()
    class_count = Classroom.objects.count()
    
    # Lấy dữ liệu mới nhất
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
    """Hiển thị danh sách học sinh - Chỉ dành cho Admin"""
    if not (request.user.role == 'admin' or request.user.is_superuser):
        messages.error(request, "Bạn không có quyền truy cập trang này.")
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

    paginator = Paginator(student_list, 10) # 10 học sinh mỗi trang
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
            messages.success(request, "Thêm học sinh mới thành công!")
            return redirect('student_list')
    else:
        form = StudentManageForm()
    return render(request, 'accounts/student_form.html', {'form': form, 'title': 'Thêm học sinh'})

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
            messages.success(request, "Cập nhật thông tin học sinh thành công!")
            return redirect('student_list')
    else:
        form = StudentManageForm(instance=student_user, initial=initial_data)
    return render(request, 'accounts/student_form.html', {'form': form, 'title': 'Sửa thông tin học sinh'})

@login_required
@transaction.atomic
def student_delete(request, pk):
    if not (request.user.role == 'admin' or request.user.is_superuser):
        messages.error(request, "Bạn không có quyền thực hiện hành động này.")
        return redirect('user_dashboard')
    
    # Sử dụng QuerySet để xóa nhanh hơn (Bulk delete ở mức DB)
    student_qs = User.objects.filter(id=pk, role='student')
    student_user = student_qs.first()
    
    if not student_user:
        messages.error(request, "Không tìm thấy học sinh hoặc đối tượng đã bị xóa trước đó.")
        return redirect('student_list')

    if request.method == 'POST':
        username = student_user.username
        # Xóa trực tiếp từ QuerySet giúp SQL Server xử lý Cascade nhanh hơn nhiều so với xóa instance
        student_qs.delete()
        messages.success(request, f"Đã xóa học sinh {username} và toàn bộ dữ liệu liên quan.")
    
    return redirect('student_list')

@login_required
def profile_view(request):
    """Xử lý xem và cập nhật hồ sơ cá nhân UC02"""
    user = request.user
    # Lấy hoặc tạo hồ sơ bổ sung nếu chưa có
    user_profile, created = UserProfile.objects.get_or_create(user=user)
    
    profile_form = UserProfileForm(instance=user)
    extra_form = UserExtraInfoForm(instance=user_profile)
    password_form = PasswordUpdateForm()

    if request.method == 'POST':
        # Trường hợp người dùng nhấn nút cập nhật thông tin
        if 'update_profile' in request.POST:
            profile_form = UserProfileForm(request.POST, request.FILES, instance=user)
            extra_form = UserExtraInfoForm(request.POST, instance=user_profile)
            if profile_form.is_valid() and extra_form.is_valid():
                profile_form.save()
                extra_form.save()
                messages.success(request, "Cập nhật thành công!")
                return redirect('profile')

        # Tính năng mới: Xóa ảnh và dùng mặc định
        elif 'reset_avatar' in request.POST:
            if user.avatar:
                user.avatar.delete(save=False) # Xóa file vật lý khỏi thư mục media
                user.avatar = None
                user.save()
                messages.success(request, "Đã xóa ảnh đại diện, hệ thống sẽ sử dụng biểu tượng mặc định.")
                return redirect('profile')
        
        # Trường hợp người dùng nhấn nút đổi mật khẩu
        elif 'change_password' in request.POST:
            password_form = PasswordUpdateForm(request.POST)
            if password_form.is_valid():
                old_password = password_form.cleaned_data['old_password']
                new_password = password_form.cleaned_data['new_password']
                
                # Kiểm tra mật khẩu cũ (BR_PASSWORD_CHANGE)
                if user.check_password(old_password):
                    user.set_password(new_password)
                    user.save()
                    # Giữ cho người dùng không bị đăng xuất sau khi đổi mật khẩu
                    update_session_auth_hash(request, user)
                    messages.success(request, "Đổi mật khẩu thành công!")
                    return redirect('profile')
                else:
                    messages.error(request, "Mật khẩu cũ không chính xác, vui lòng thử lại.")

    context = {
        'profile_form': profile_form,
        'extra_form': extra_form,
        'password_form': password_form,
    }
    return render(request, 'accounts/profile.html', context)
