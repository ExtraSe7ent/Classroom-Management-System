"""
Views for accounts app — written using Class-based Views (CBV).

Includes: login/logout, dashboard routing by role,
admin/teacher & student dashboard, student CRUD, and user profile management.
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
# AUTHENTICATION (UC01)
# ===================================================================
class AppLoginView(LoginView):
    """Login — uses Django's built-in LoginView."""
    template_name = 'accounts/login.html'
    form_class = LoginForm
    redirect_authenticated_user = True  # if already authenticated, redirect away from login page

    def form_valid(self, form):
        user = form.get_user()
        full_name = user.get_full_name() or user.username
        messages.success(self.request, f"Welcome {full_name}, system is ready!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Incorrect username or password.")
        return super().form_invalid(form)


class AppLogoutView(RedirectView):
    """Logout — accepts GET then destroys session."""
    pattern_name = 'login'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)
            messages.info(request, "You have logged out successfully.")
        return super().get(request, *args, **kwargs)


class DashboardRedirectView(LoginRequiredMixin, RedirectView):
    """Redirect users to their respective dashboard based on their role."""
    def get_redirect_url(self, *args, **kwargs):
        user = self.request.user
        if user.is_admin or user.is_teacher:
            return reverse('admin_dashboard')
        return reverse('user_dashboard')


class ForgotPasswordView(View):
    """UC01-C — Forgot password via phone + OTP (simulated OTP for demo)."""
    template_name = 'accounts/forgot_password.html'

    def get(self, request):
        return render(request, self.template_name, {'form': ForgotPasswordForm()})

    def post(self, request):
        form = ForgotPasswordForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form, 'otp_sent': 'send_otp' not in request.POST})
        phone = form.cleaned_data['phone']

        # Step 1: "Send OTP"
        if 'send_otp' in request.POST:
            if not User.objects.filter(phone_number=phone).exists():
                messages.error(request, "This phone number is not registered in the system.")
                return render(request, self.template_name, {'form': form})
            otp = f"{random.randint(0, 999999):06d}"
            request.session['reset_phone'] = phone
            request.session['reset_otp'] = otp
            messages.info(request, f"[DEMO] OTP code sent to {phone} is: {otp}")
            return render(request, self.template_name, {'form': form, 'otp_sent': True})

        # Step 2: "Change Password"
        otp = (form.cleaned_data.get('otp') or '').strip()
        new_pw = form.cleaned_data.get('new_password') or ''
        confirm = form.cleaned_data.get('confirm_password') or ''
        ctx = {'form': form, 'otp_sent': True}

        if not re.fullmatch(r'\d{6}', otp):
            messages.error(request, "OTP code must be exactly 6 digits.")
            return render(request, self.template_name, ctx)
        if request.session.get('reset_phone') != phone or request.session.get('reset_otp') != otp:
            messages.error(request, "Invalid or expired OTP. Please try again.")
            return render(request, self.template_name, ctx)
        if new_pw != confirm:
            messages.error(request, "Confirm password does not match.")
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
        messages.success(request, "Password changed successfully! Please log in again.")
        return redirect('login')


# ===================================================================
# DASHBOARD
# ===================================================================
class AdminDashboardView(StaffRequiredMixin, TemplateView):
    """
    Dashboard for Admin & Teacher.
    - Admin: center-wide statistics.
    - Teacher: restricted statistics for classrooms they are assigned to.
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
    """Student/parent homepage: assignment reminders, attendance rate, today's schedule."""
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
# STUDENT MANAGEMENT (UC03) — Admin only
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
    success_message = "New student added successfully!"
    extra_context = {'title': 'Add Student'}


class StudentUpdateView(AdminRequiredMixin, SuccessMessageMixin, UpdateView):
    form_class = StudentManageForm
    template_name = 'accounts/student_form.html'
    success_url = reverse_lazy('student_list')
    success_message = "Student information updated successfully!"
    extra_context = {'title': 'Edit Student Info'}

    def get_queryset(self):
        return User.objects.filter(role=User.ROLE_STUDENT)

    def get_initial(self):
        initial = super().get_initial()
        profile = getattr(self.object, 'student_profile', None)
        if profile:
            initial['student_code'] = profile.student_code
        return initial


class StudentDeleteView(AdminRequiredMixin, View):
    """Delete student (Cascade Delete). Deletes on POST, redirects to list on GET."""
    def post(self, request, pk):
        student = get_object_or_404(User, pk=pk, role=User.ROLE_STUDENT)
        username = student.username
        student.delete()
        messages.success(
            request, f"Successfully deleted student {username} and all related data."
        )
        return redirect('student_list')

    def get(self, request, pk):
        return redirect('student_list')


# ===================================================================
# PERSONAL PROFILE (UC02) — all roles
# ===================================================================
class ProfileView(LoginRequiredMixin, View):
    """
    View & update profile. Handles 3 distinct operations determined by the submit button name:
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

        # 1) Update personal info
        if 'update_profile' in request.POST:
            profile_form = UserProfileForm(request.POST, request.FILES, instance=user)
            extra_form = UserExtraInfoForm(request.POST, instance=user_profile)
            if profile_form.is_valid() and extra_form.is_valid():
                profile_form.save()
                extra_form.save()
                messages.success(request, "Profile updated successfully!")
                return redirect('profile')
            return render(request, self.template_name, self._context(
                request, profile_form=profile_form, extra_form=extra_form))

        # 2) Reset avatar to default
        if 'reset_avatar' in request.POST:
            if user.avatar:
                user.avatar.delete(save=False)
                user.avatar = None
                user.save()
                messages.success(request, "Avatar deleted successfully. Default icon will be used.")
            return redirect('profile')

        # 3) Change password (BR_PASSWORD_CHANGE: must match old password)
        if 'change_password' in request.POST:
            password_form = PasswordUpdateForm(request.POST)
            if password_form.is_valid():
                old_password = password_form.cleaned_data['old_password']
                new_password = password_form.cleaned_data['new_password']
                if user.check_password(old_password):
                    user.set_password(new_password)
                    user.save()
                    update_session_auth_hash(request, user)  # don't logout
                    messages.success(request, "Password changed successfully!")
                    return redirect('profile')
                messages.error(request, "Incorrect old password. Please try again.")
            return render(request, self.template_name, self._context(
                request, password_form=password_form))

        return redirect('profile')
