from django.contrib import admin
from .models import UserProfile, Class, Student

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone', 'updated_at')
    list_filter = ('role', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'phone')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'teacher', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'teacher__first_name', 'teacher__last_name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('user', 'student_id', 'created_at')
    list_filter = ('created_at', 'classes')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'student_id')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('classes',)
