from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # Define roles in the system (3 roles)
    ROLE_ADMIN = 'admin'
    ROLE_TEACHER = 'teacher' 
    ROLE_STUDENT = 'student'
    ROLE_CHOICES = (
        (ROLE_ADMIN, 'Administrator / Principal'),
        (ROLE_TEACHER, 'Teacher'),
        (ROLE_STUDENT, 'Student / Parent'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name="Phone number")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Avatar")

    def __str__(self):
        return f"{self.username} - {self.get_role_display()}"

    # ===== Role check utilities (used for authorization) =====
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
        """Admin or Teacher — group with administrative permissions."""
        return self.is_admin or self.is_teacher

class Student(models.Model):
    # A Student profile is linked to a User. When the User is deleted, the Student profile is cascade deleted.
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    student_code = models.CharField(max_length=20, unique=True, verbose_name="Student code")

    def __str__(self):
        return f"{self.student_code} - {self.user.get_full_name()}"

class UserProfile(models.Model):
    """
    Extended user profile information — only stores fields not present in auth.User.
    Phone number is already stored in User.phone_number, so it is not duplicated here.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='profile')
    address = models.TextField(blank=True, null=True, verbose_name="Address")
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="Date of birth")

    def __str__(self):
        return f"Profile of {self.user.username}"
