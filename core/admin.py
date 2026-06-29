from django.contrib import admin
from .models import (
    UserProfile, Class, Student, Schedule, Assignment, Submission,
    Attendance, DailyComment, PasswordResetOTP,
)

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


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('class_obj', 'day_of_week', 'start_time', 'end_time', 'room')
    list_filter = ('day_of_week',)
    search_fields = ('class_obj__name', 'room')


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'class_obj', 'due_date', 'created_by', 'created_at')
    list_filter = ('class_obj', 'created_at')
    search_fields = ('title', 'class_obj__name')


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'assignment', 'status', 'grade', 'submitted_at')
    list_filter = ('status',)
    search_fields = ('student__student_id', 'assignment__title')


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'class_obj', 'date', 'status')
    list_filter = ('status', 'date', 'class_obj')
    search_fields = ('student__student_id',)


@admin.register(DailyComment)
class DailyCommentAdmin(admin.ModelAdmin):
    list_display = ('student', 'class_obj', 'comment_date', 'created_by')
    list_filter = ('comment_date', 'class_obj')
    search_fields = ('student__student_id', 'comment_text')


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ('user', 'otp_code', 'created_at', 'expires_at', 'is_used')
    list_filter = ('is_used',)
    search_fields = ('user__username',)
