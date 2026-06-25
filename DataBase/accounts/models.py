from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # Define roles in the system
    ROLE_CHOICES = (
        ('admin', 'Teacher/Administrator'),
        ('student', 'Students/Parents'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name="Phone number")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Representative photo")

    def __str__(self):
        return f"{self.username} - {self.get_role_display()}"

class Student(models.Model):
    # A Student is associated with a User. When the User is deleted, this Student profile also disappears.
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    student_code = models.CharField(max_length=20, unique=True, verbose_name="Student code")

    def __str__(self):
        return f"{self.student_code} - {self.user.get_full_name()}"

class UserProfile(models.Model):
    # One-to-one relationship with User: When User is deleted, Profile is also deleted (Cascade Delete)
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='profile')
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"
