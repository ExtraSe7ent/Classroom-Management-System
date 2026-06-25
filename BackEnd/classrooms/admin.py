from django.contrib import admin
from .models import Classroom, ClassEnrollment, Schedule, Attendance, DailyComment


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display  = ('name', 'teacher', 'tuition', 'is_active', 'enrolled_count')
    list_filter   = ('is_active', 'teacher')
    search_fields = ('name', 'teacher__first_name', 'teacher__last_name', 'teacher__username')
    ordering      = ('-id',)

    @admin.display(description='Số học sinh')
    def enrolled_count(self, obj):
        return obj.enrollments.count()


@admin.register(ClassEnrollment)
class ClassEnrollmentAdmin(admin.ModelAdmin):
    list_display  = ('student', 'classroom', 'enrolled_at')
    list_filter   = ('classroom',)
    search_fields = ('student__username', 'student__first_name', 'student__last_name', 'classroom__name')
    ordering      = ('-enrolled_at',)


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display  = ('classroom', 'day_of_week', 'start_time', 'end_time', 'room_name')
    list_filter   = ('day_of_week', 'room_name', 'classroom')
    search_fields = ('classroom__name', 'room_name')


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display  = ('student', 'classroom', 'date', 'status', 'remark')
    list_filter   = ('date', 'status', 'classroom')
    search_fields = ('student__username', 'student__first_name', 'student__last_name', 'classroom__name')
    ordering      = ('-date',)
    date_hierarchy = 'date'


@admin.register(DailyComment)
class DailyCommentAdmin(admin.ModelAdmin):
    list_display  = ('student', 'classroom', 'date', 'created_by', 'short_content')
    list_filter   = ('date', 'classroom', 'created_by')
    search_fields = ('student__username', 'student__first_name', 'student__last_name', 'content')
    ordering      = ('-date', '-created_at')
    date_hierarchy = 'date'

    @admin.display(description='Nội dung')
    def short_content(self, obj):
        return obj.content[:60] + '…' if len(obj.content) > 60 else obj.content
