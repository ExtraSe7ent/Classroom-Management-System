from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # Định nghĩa các vai trò trong hệ thống
    ROLE_CHOICES = (
        ('admin', 'Giáo viên/Quản trị'),
        ('student', 'Học sinh/Phụ huynh'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name="Số điện thoại")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Ảnh đại diện")

    def __str__(self):
        return f"{self.username} - {self.get_role_display()}"

class Student(models.Model):
    # Một Student gắn với một User. Khi User bị xóa, Student profile này cũng biến mất.
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    student_code = models.CharField(max_length=20, unique=True, verbose_name="Mã học sinh")

    def __str__(self):
        return f"{self.student_code} - {self.user.get_full_name()}"

class UserProfile(models.Model):
    # Mối quan hệ 1-1 với User: Khi User bị xóa, Profile cũng bị xóa (Cascade Delete)
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='profile')
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"
