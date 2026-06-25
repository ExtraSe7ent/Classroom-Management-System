from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserProfile, Student


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Thông tin mở rộng"
    fields = ('address', 'date_of_birth')


class StudentInline(admin.StackedInline):
    model = Student
    can_delete = False
    verbose_name_plural = "Hồ sơ học sinh"
    fields = ('student_code',)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline, StudentInline)
    list_display  = ('username', 'get_full_name', 'email', 'role', 'phone_number', 'is_active')
    list_filter   = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone_number')
    ordering      = ('-date_joined',)
    fieldsets = UserAdmin.fieldsets + (
        ('Phân quyền hệ thống', {'fields': ('role', 'phone_number', 'avatar')}),
    )

    @admin.display(description='Họ và tên')
    def get_full_name(self, obj):
        return obj.get_full_name() or '—'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'date_of_birth', 'address')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display  = ('student_code', 'user', 'get_full_name')
    search_fields = ('student_code', 'user__username', 'user__first_name', 'user__last_name')
    ordering      = ('student_code',)

    @admin.display(description='Họ và tên')
    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
