from django.contrib import admin
from .models import Classroom, ClassEnrollment, Schedule, Attendance, DailyComment

@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('name', 'teacher')
    search_fields = ('name',)

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('classroom', 'day_of_week', 'start_time', 'end_time', 'room_name')
    list_filter = ('day_of_week', 'room_name')

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'classroom', 'date', 'status')
    list_filter = ('date', 'status')

admin.site.register(ClassEnrollment)
admin.site.register(DailyComment)
