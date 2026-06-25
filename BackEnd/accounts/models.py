from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # Định nghĩa các vai trò trong hệ thống (3 role)
    ROLE_ADMIN = 'admin'
    ROLE_TEACHER = 'teacher' 
    ROLE_STUDENT = 'student'
    ROLE_CHOICES = (
        (ROLE_ADMIN, 'Quản trị/Hiệu trưởng'),
        (ROLE_TEACHER, 'Giáo viên'),
        (ROLE_STUDENT, 'Học sinh/Phụ huynh'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name="Số điện thoại")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Ảnh đại diện")

    def __str__(self):
        return f"{self.username} - {self.get_role_display()}"

    # ===== Tiện ích kiểm tra vai trò (dùng cho phân quyền) =====
    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser

    @property
    def is_teacher(self):
        return self.role == self.ROLE_TEACHER

    @property
    def is_student(self):
        return self.role == self.ROLE_STUDENT

    @property
    def is_staff_member(self):
        """Admin hoặc Giáo viên — nhóm có quyền quản trị nghiệp vụ."""
        return self.is_admin or self.is_teacher

class Student(models.Model):
    # Một Student gắn với một User. Khi User bị xóa, Student profile này cũng biến mất.
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    student_code = models.CharField(max_length=20, unique=True, verbose_name="Mã học sinh")

    def __str__(self):
        return f"{self.student_code} - {self.user.get_full_name()}"

class UserProfile(models.Model):
    """
    Thông tin mở rộng của User — chỉ lưu những gì KHÔNG có trên auth.User.
    Số điện thoại đã được lưu tại User.phone_number, không lưu lại ở đây.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='profile')
    address = models.TextField(blank=True, null=True, verbose_name="Địa chỉ")
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="Ngày sinh")

    def __str__(self):
        return f"Profile of {self.user.username}"
