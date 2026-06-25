from django.contrib import admin
from .models import Assignment, Submission


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display  = ('title', 'classroom', 'due_date', 'created_at', 'submission_count')
    list_filter   = ('classroom', 'due_date')
    search_fields = ('title', 'classroom__name', 'description')
    ordering      = ('-created_at',)
    date_hierarchy = 'due_date'

    @admin.display(description='Số bài nộp')
    def submission_count(self, obj):
        return obj.submissions.count()


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display  = ('assignment', 'student', 'submitted_at', 'status', 'grade')
    list_filter   = ('status', 'assignment__classroom')
    search_fields = ('student__username', 'student__first_name', 'student__last_name', 'assignment__title')
    ordering      = ('-submitted_at',)
    date_hierarchy = 'submitted_at'
    readonly_fields = ('submitted_at',)
