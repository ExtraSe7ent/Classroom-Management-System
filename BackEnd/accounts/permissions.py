"""
Tầng phân quyền dùng chung cho 3 role: admin / teacher / student.

- Mixin: dùng cho Class-based Views (kế thừa cùng các generic view).
- Decorator: dùng cho function-based view nếu còn (ví dụ view trả JsonResponse).

Cách dùng (CBV):
    class ClassroomListView(StaffRequiredMixin, ListView): ...

Cách dùng (decorator):
    @role_required('admin')
    def my_view(request): ...
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


# ===================================================================
# MIXINS cho Class-based Views
# ===================================================================
class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin nền: chỉ cho phép user có role nằm trong `allowed_roles` truy cập.
    Superuser luôn được phép (tiện cho tài khoản quản trị gốc).
    """
    allowed_roles = ()
    permission_denied_message = "Bạn không có quyền truy cập chức năng này."

    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True
        return getattr(user, 'role', None) in self.allowed_roles

    def handle_no_permission(self):
        # Chưa đăng nhập -> để LoginRequiredMixin đưa về trang login.
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        # Đã đăng nhập nhưng sai quyền -> báo lỗi, đưa về dashboard phù hợp.
        messages.error(self.request, self.permission_denied_message)
        return redirect('dashboard_redirect')


class AdminRequiredMixin(RoleRequiredMixin):
    """Chỉ Quản trị/Hiệu trưởng."""
    allowed_roles = ('admin',)


class TeacherRequiredMixin(RoleRequiredMixin):
    """Chỉ Giáo viên."""
    allowed_roles = ('teacher',)


class StaffRequiredMixin(RoleRequiredMixin):
    """Admin hoặc Giáo viên — nhóm có quyền vận hành nghiệp vụ (lớp, điểm danh, bài tập)."""
    allowed_roles = ('admin', 'teacher')


class StudentRequiredMixin(RoleRequiredMixin):
    """Chỉ Học sinh/Phụ huynh."""
    allowed_roles = ('student',)


# ===================================================================
# DECORATORS cho function-based views (dự phòng)
# ===================================================================
def role_required(*roles):
    """Chặn truy cập nếu user không thuộc một trong các role cho trước."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.is_superuser or getattr(request.user, 'role', None) in roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, "Bạn không có quyền truy cập chức năng này.")
            return redirect('dashboard_redirect')
        return _wrapped
    return decorator
