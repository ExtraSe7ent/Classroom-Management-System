"""
Common permission layers for the three roles: admin / teacher / student.

- Mixin: used for Class-based Views.
- Decorator: used for function-based views.

Usage (CBV):
    class ClassroomListView(StaffRequiredMixin, ListView): ...

Usage (decorator):
    @role_required('admin')
    def my_view(request): ...
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


# ===================================================================
# MIXINS for Class-based Views
# ===================================================================
class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Base Mixin: only allows access for users whose role is in `allowed_roles`.
    Superuser is always allowed.
    """
    allowed_roles = ()
    permission_denied_message = "You do not have permission to access this feature."

    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True
        return getattr(user, 'role', None) in self.allowed_roles

    def handle_no_permission(self):
        # Not logged in -> let LoginRequiredMixin handle redirect to login.
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        # Logged in but insufficient permissions -> error message and redirect to dashboard.
        messages.error(self.request, self.permission_denied_message)
        return redirect('dashboard_redirect')


class AdminRequiredMixin(RoleRequiredMixin):
    """Only Administrator/Principal."""
    allowed_roles = ('admin',)


class TeacherRequiredMixin(RoleRequiredMixin):
    """Only Teacher."""
    allowed_roles = ('teacher',)


class StaffRequiredMixin(RoleRequiredMixin):
    """Admin or Teacher — group authorized to operate business logic (classes, attendance, assignments)."""
    allowed_roles = ('admin', 'teacher')


class StudentRequiredMixin(RoleRequiredMixin):
    """Only Student/Parent."""
    allowed_roles = ('student',)


# ===================================================================
# DECORATORS for function-based views
# ===================================================================
def role_required(*roles):
    """Blocks access if user does not belong to one of the specified roles."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.is_superuser or getattr(request.user, 'role', None) in roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, "You do not have permission to access this feature.")
            return redirect('dashboard_redirect')
        return _wrapped
    return decorator
