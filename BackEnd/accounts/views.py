"""
Views của app accounts — viết theo Class-based Views (CBV).

Bao gồm: đăng nhập/đăng xuất, điều hướng dashboard theo role,
dashboard admin/giáo viên & học sinh, CRUD học sinh, hồ sơ cá nhân.
"""
import random
import re

from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView, ListView, RedirectView, TemplateView, UpdateView,
)

from assignments.models import Assignment, Submission
from classrooms.models import Attendance, ClassEnrollment, Classroom, Schedule

from .forms import (
    ForgotPasswordForm, LoginForm, PasswordUpdateForm, StudentManageForm,
    UserExtraInfoForm, UserProfileForm, validate_strong_password,
)
from .models import User, UserProfile
from .permissions import AdminRequiredMixin, StaffRequiredMixin, StudentRequiredMixin


# ===================================================================
# XÁC THỰC (UC01)
# ===================================================================
class AppLoginView(LoginView):
    """Đăng nhập — dùng LoginView built-in của Django."""
    template_name = 'accounts/login.html'
    form_class = LoginForm
    redirect_authenticated_user = True  # đã đăng nhập thì khỏi vào lại trang login

    def form_valid(self, form):
        user = form.get_user()
        full_name = user.get_full_name() or user.username
        messages.success(self.request, f"Xin chào {full_name}, hệ thống đã sẵn sàng!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Tên đăng nhập hoặc mật khẩu không chính xác.")
        return super().form_invalid(form)


class AppLogoutView(RedirectView):
    """Đăng xuất — chấp nhận GET (vì menu dùng link) rồi hủy session."""
    pattern_name = 'login'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)
            messages.info(request, "Bạn đã đăng xuất thành công.")
        return super().get(request, *args, **kwargs)


class DashboardRedirectView(LoginRequiredMixin, RedirectView):
    """Điều hướng người dùng về trang chủ tương ứng với vai trò."""
    def get_redirect_url(self, *args, **kwargs):
        user = self.request.user
        if user.is_admin or user.is_teacher:
            return reverse('admin_dashboard')
        return reverse('user_dashboard')


class ForgotPasswordView(View):
    """UC01-C — Quên mật khẩu qua SĐT + OTP (OTP mô phỏng cho bản demo)."""
    template_name = 'accounts/forgot_password.html'

    def get(self, request):
        return render(request, self.template_name, {'form': ForgotPasswordForm()})

    def post(self, request):
        form = ForgotPasswordForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form, 'otp_sent': 'send_otp' not in request.POST})
        phone = form.cleaned_data['phone']

        # Bước 1: "Gửi mã OTP"
        if 'send_otp' in request.POST:
            if not User.objects.filter(phone_number=phone).exists():
                messages.error(request, "Số điện thoại này chưa được đăng ký trong hệ thống.")
                return render(request, self.template_name, {'form': form})
            otp = f"{random.randint(0, 999999):06d}"
            request.session['reset_phone'] = phone
            request.session['reset_otp'] = otp
            messages.info(request, f"[DEMO] Mã OTP gửi tới {phone} là: {otp}")
            return render(request, self.template_name, {'form': form, 'otp_sent': True})

        # Bước 2: "Đổi mật khẩu"
        otp = (form.cleaned_data.get('otp') or '').strip()
        new_pw = form.cleaned_data.get('new_password') or ''
        confirm = form.cleaned_data.get('confirm_password') or ''
        ctx = {'form': form, 'otp_sent': True}

        if not re.fullmatch(r'\d{6}', otp):
            messages.error(request, "Mã OTP phải gồm đúng 6 chữ số.")
            return render(request, self.template_name, ctx)
        if request.session.get('reset_phone') != phone or request.session.get('reset_otp') != otp:
            messages.error(request, "Mã OTP không đúng hoặc đã hết hạn. Vui lòng lấy lại mã.")
            return render(request, self.template_name, ctx)
        if new_pw != confirm:
            messages.error(request, "Xác nhận mật khẩu mới không trùng khớp.")
            return render(request, self.template_name, ctx)
        try:
            validate_strong_password(new_pw)
        except ValidationError as e:
            messages.error(request, e.messages[0])
            return render(request, self.template_name, ctx)

        user = User.objects.filter(phone_number=phone).first()
        user.set_password(new_pw)
        user.save()
        request.session.pop('reset_phone', None)
        request.session.pop('reset_otp', None)
        messages.success(request, "Đổi mật khẩu thành công! Vui lòng đăng nhập lại.")
        return redirect('login')


# ===================================================================
# DASHBOARD
# ===================================================================
class AdminDashboardView(StaffRequiredMixin, TemplateView):
    """
    Bảng điều khiển cho Admin & Giáo viên.
    - Admin: thống kê toàn trung tâm.
    - Giáo viên: thống kê thu hẹp trong các lớp mình phụ trách.
    """
    template_name = 'accounts/admin_dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        if user.is_teacher:
            classes = Classroom.objects.filter(teacher=user)
            student_ids = ClassEnrollment.objects.filter(
                classroom__in=classes
            ).values_list('student_id', flat=True).distinct()
            students = User.objects.filter(id__in=student_ids, role=User.ROLE_STUDENT)
            ctx['class_count'] = classes.count()
            ctx['student_count'] = students.count()
            ctx['recent_students'] = students.order_by('-date_joined')[:5]
            ctx['recent_classes'] = classes.order_by('-id')[:5]
        else:
            students = User.objects.filter(role=User.ROLE_STUDENT)
            ctx['class_count'] = Classroom.objects.count()
            ctx['student_count'] = students.count()
            ctx['recent_students'] = students.order_by('-date_joined')[:5]
            ctx['recent_classes'] = Classroom.objects.order_by('-id')[:5]
        return ctx


class UserDashboardView(StudentRequiredMixin, TemplateView):
    """Trang chủ học sinh/phụ huynh: nhắc bài tập, tỉ lệ chuyên cần, lịch hôm nay."""
    template_name = 'accounts/user_dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        now = timezone.now()
        class_ids = list(
            ClassEnrollment.objects.filter(student=user).values_list('classroom_id', flat=True)
        )

        submitted_ids = set(
            Submission.objects.filter(student=user).values_list('assignment_id', flat=True)
        )
        ctx['upcoming_assignments'] = (
            Assignment.objects.filter(classroom_id__in=class_ids, due_date__gte=now)
            .exclude(id__in=submitted_ids)
            .select_related('classroom').order_by('due_date')[:5]
        )

        atts = Attendance.objects.filter(student=user)
        total = atts.count()
        present = atts.filter(status__in=['present', 'late']).count()
        ctx['attendance_rate'] = round(present / total * 100) if total else 0
        ctx['class_count'] = len(class_ids)

        ctx['today_sessions'] = (
            Schedule.objects.filter(
                classroom_id__in=class_ids, day_of_week=timezone.localdate().weekday()
            ).select_related('classroom').order_by('start_time')
        )
        return ctx


# ===================================================================
# QUẢN LÝ HỌC SINH (UC03) — chỉ Admin
# ===================================================================
class StudentListView(AdminRequiredMixin, ListView):
    template_name = 'accounts/student_list.html'
    paginate_by = 10
    context_object_name = 'students'

    def get_queryset(self):
        qs = (User.objects.filter(role=User.ROLE_STUDENT)
              .select_related('student_profile')
              .order_by('-date_joined'))
        query = self.request.GET.get('q', '').strip()
        if query:
            qs = qs.filter(
                Q(username__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(student_profile__student_code__icontains=query)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['query'] = self.request.GET.get('q', '')
        return ctx


class StudentCreateView(AdminRequiredMixin, SuccessMessageMixin, CreateView):
    form_class = StudentManageForm
    template_name = 'accounts/student_form.html'
    success_url = reverse_lazy('student_list')
    success_message = "Thêm học sinh mới thành công!"
    extra_context = {'title': 'Thêm học sinh'}


class StudentUpdateView(AdminRequiredMixin, SuccessMessageMixin, UpdateView):
    form_class = StudentManageForm
    template_name = 'accounts/student_form.html'
    success_url = reverse_lazy('student_list')
    success_message = "Cập nhật thông tin học sinh thành công!"
    extra_context = {'title': 'Sửa thông tin học sinh'}

    def get_queryset(self):
        return User.objects.filter(role=User.ROLE_STUDENT)

    def get_initial(self):
        initial = super().get_initial()
        profile = getattr(self.object, 'student_profile', None)
        if profile:
            initial['student_code'] = profile.student_code
        return initial


class StudentDeleteView(AdminRequiredMixin, View):
    """Xóa học sinh (Cascade Delete). POST mới xóa, GET thì quay về danh sách."""
    def post(self, request, pk):
        student = get_object_or_404(User, pk=pk, role=User.ROLE_STUDENT)
        username = student.username
        student.delete()
        messages.success(
            request, f"Đã xóa học sinh {username} và toàn bộ dữ liệu liên quan."
        )
        return redirect('student_list')

    def get(self, request, pk):
        return redirect('student_list')


# ===================================================================
# HỒ SƠ CÁ NHÂN (UC02) — mọi vai trò
# ===================================================================
class ProfileView(LoginRequiredMixin, View):
    """
    Xem & cập nhật hồ sơ. Một trang có 3 thao tác phân biệt bằng tên nút submit:
    update_profile / reset_avatar / change_password.
    """
    template_name = 'accounts/profile.html'

    def _context(self, request, **overrides):
        user = request.user
        user_profile, _ = UserProfile.objects.get_or_create(user=user)
        ctx = {
            'profile_form': UserProfileForm(instance=user),
            'extra_form': UserExtraInfoForm(instance=user_profile),
            'password_form': PasswordUpdateForm(),
        }
        ctx.update(overrides)
        return ctx

    def get(self, request):
        return render(request, self.template_name, self._context(request))

    def post(self, request):
        user = request.user
        user_profile, _ = UserProfile.objects.get_or_create(user=user)

        # 1) Cập nhật thông tin cá nhân
        if 'update_profile' in request.POST:
            profile_form = UserProfileForm(request.POST, request.FILES, instance=user)
            extra_form = UserExtraInfoForm(request.POST, instance=user_profile)
            if profile_form.is_valid() and extra_form.is_valid():
                profile_form.save()
                extra_form.save()
                messages.success(request, "Cập nhật thành công!")
                return redirect('profile')
            return render(request, self.template_name, self._context(
                request, profile_form=profile_form, extra_form=extra_form))

        # 2) Xóa ảnh đại diện, về mặc định
        if 'reset_avatar' in request.POST:
            if user.avatar:
                user.avatar.delete(save=False)
                user.avatar = None
                user.save()
                messages.success(request, "Đã xóa ảnh đại diện, hệ thống dùng biểu tượng mặc định.")
            return redirect('profile')

        # 3) Đổi mật khẩu (BR_PASSWORD_CHANGE: phải đúng mật khẩu cũ)
        if 'change_password' in request.POST:
            password_form = PasswordUpdateForm(request.POST)
            if password_form.is_valid():
                old_password = password_form.cleaned_data['old_password']
                new_password = password_form.cleaned_data['new_password']
                if user.check_password(old_password):
                    user.set_password(new_password)
                    user.save()
                    update_session_auth_hash(request, user)  # không bị đăng xuất
                    messages.success(request, "Đổi mật khẩu thành công!")
                    return redirect('profile')
                messages.error(request, "Mật khẩu cũ không chính xác, vui lòng thử lại.")
            return render(request, self.template_name, self._context(
                request, password_form=password_form))

        return redirect('profile')
