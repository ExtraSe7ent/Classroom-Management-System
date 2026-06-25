from django.db import models
from django.contrib.auth.models import User


DAY_CHOICES = [
    ('Monday', 'Monday'),
    ('Tuesday', 'Tuesday'),
    ('Wednesday', 'Wednesday'),
    ('Thursday', 'Thursday'),
    ('Friday', 'Friday'),
    ('Saturday', 'Saturday'),
    ('Sunday', 'Sunday'),
]


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('teacher', 'Teacher'),
        ('student', 'Students'),
        ('parent', 'Parents'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)  # Contact/emergency phone number
    address = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'User_Profiles'
        verbose_name = 'User profile'
        verbose_name_plural = 'User profile'

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.role})"

    def get_role_display_custom(self):
        return dict(self.ROLE_CHOICES).get(self.role, self.role)


class Class(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='classes')
    teacher_name = models.CharField(max_length=100, blank=True)  # Teacher display name
    room = models.CharField(max_length=100, blank=True)           # Fixed classroom
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'Classes'
        verbose_name = 'Classroom'
        verbose_name_plural = 'Classes'

    def __str__(self):
        return self.name

    def get_schedule_display(self):
        """Returns the aggregated schedule string from the linked Schedules."""
        schedules = self.schedules.all().order_by('day_of_week')
        parts = []
        for s in schedules:
            parts.append(f"{s.get_day_of_week_display()} ({s.start_time.strftime('%H:%M')} - {s.end_time.strftime('%H:%M')})")
        return ', '.join(parts) if parts else 'Not scheduled yet'

    def get_student_count(self):
        return self.students.count()


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    student_id = models.CharField(max_length=50, unique=True)
    classes = models.ManyToManyField(Class, related_name='students', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'Students'
        verbose_name = 'Students'
        verbose_name_plural = 'Students'

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.student_id})"

    def get_classes_display(self):
        return ', '.join([c.name for c in self.classes.all()]) or 'Not yet placed in class'


class Schedule(models.Model):
    """Fixed schedule of a class."""
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.CharField(max_length=20, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=100, blank=True)  # Leave blank = online learning

    class Meta:
        db_table = 'Schedules'
        verbose_name = 'Class schedule'
        verbose_name_plural = 'Class schedules'
        unique_together = ('class_obj', 'day_of_week', 'start_time')

    def __str__(self):
        return f"{self.class_obj.name} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"


class Assignment(models.Model):
    """Assignments are assigned to a class by a teacher/admin."""
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='assignments')
    due_date = models.DateTimeField()
    file = models.FileField(upload_to='assignments/', blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_assignments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'Assignments'
        verbose_name = 'Exercises'
        verbose_name_plural = 'Exercises'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.class_obj.name})"

    def get_submission_count(self):
        return self.submissions.exclude(status='missing').count()

    def get_total_students(self):
        return self.class_obj.students.count()


class Submission(models.Model):
    """A student's submission for an assignment."""
    STATUS_CHOICES = [
        ('pending', 'Waiting for scoring'),
        ('graded', 'Got points'),
        ('missing', 'Missing / Overdue papers'),
    ]

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='submissions')
    file = models.FileField(upload_to='submissions/', blank=True, null=True)
    note = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.FloatField(null=True, blank=True)   # None = not scored yet
    feedback = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    class Meta:
        db_table = 'Submissions'
        verbose_name = 'Submissions'
        verbose_name_plural = 'Submissions'
        unique_together = ('assignment', 'student')

    def __str__(self):
        return f"{self.student} - {self.assignment.title}"


class Attendance(models.Model):
    """Student attendance record during a class session."""
    STATUS_CHOICES = [
        ('present', 'Go to school'),
        ('excused', 'Absence of leave'),
        ('absent', 'Absence without permission'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendances')
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    remarks = models.TextField(blank=True)  # Teacher comments

    class Meta:
        db_table = 'Attendances'
        verbose_name = 'Attendance'
        verbose_name_plural = 'Attendance records'
        unique_together = ('student', 'class_obj', 'date')

    def __str__(self):
        return f"{self.student} - {self.class_obj.name} - {self.date} ({self.status})"
