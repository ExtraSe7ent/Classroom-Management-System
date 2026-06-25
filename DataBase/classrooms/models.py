from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

class Classroom(models.Model):
    STATUS_CHOICES = (
        (True, 'Active'),
        (False, 'It's over'),
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, verbose_name="Class description")
    tuition = models.DecimalField(max_gogits=12, decimal_places=0, default=0, verbose_name="Tuition (VND)")
    is_active = models.BooleanField(choices=STATUS_CHOICES, default=True, verbose_name="Status")
    # The teacher (Admin) manages the class
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='managed_classes')

    class Meta:
        verbose_name = "Classroom"

    def __str__(self):
        return self.name

class ClassEnrollment(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='enrollments')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='class_registrations')
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('classroom', 'student') # A student cannot register for the same class twice

class Schedule(models.Model):
    DAY_CHOICES = [
        (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'),
        (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday'),
    ]
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room_name = models.CharField(max_length=50)

    def clean(self):
        # 1. Check basic timing logic
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError("The end time must be after the start time")

        # 2. BR_SCHEDULE_VALIDATION rule: Prevent duplicate schedules (Day + Room + Time frame)
        # Overlap Algorithm: (Start A < End B) AND (End A > Start B)
        if self.day_of_week is not None and self.room_name:
            overlapping_schedules = Schedule.objects.filter(
                day_of_week=self.day_of_week,
                room_name=self.room_name,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time
            )

            if self.pk:
                overlapping_schedules = overlapping_schedules.exclude(pk=self.pk)

            if overlapping_schedules.exists():
                raise ValidationError("The classroom is busy at this time. Please choose another room or time!")

    def save(self, *args, **kwargs):
        self.full_clean()  # Run the clean() function to perform validation before saving
        super().save(*args, **kwargs)

class Attendance(models.Model):
    STATUS_CHOICES = (
        ('present', 'Be present'),
        ('absent_excused', 'Absence (With permission)'),
        ('absent_unexcused', 'Absent (Unauthorized)'),
        ('late', 'Going late'),
    )
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    remark = models.TextField(blank=True, verbose_name="Notes")

    class Meta:
        unique_together = ('student', 'schedule', 'date')

class DailyComment(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_comments')
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, null=True) # Link study session
    date = models.DateField(null=True) # Comment date
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_comments')
    content = models.TextField(verbose_name="Comment content")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for {self.student.username} on {self.date}"