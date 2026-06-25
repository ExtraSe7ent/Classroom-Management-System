from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class Classroom(models.Model):
    STATUS_CHOICES = (
        (True,  'Active'),
        (False, 'Completed'),
    )
    name = models.CharField(max_length=255, verbose_name="Class name", db_index=True)
    description = models.TextField(blank=True, verbose_name="Class description")
    tuition = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Tuition fee (VND)")
    is_active = models.BooleanField(choices=STATUS_CHOICES, default=True, verbose_name="Status", db_index=True)
    # PTYC - Set Null Rule: deleting a teacher's account sets this field to Null but preserves the classroom.
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='managed_classes',
        limit_choices_to={'role__in': ['teacher', 'admin']},
        verbose_name="Teacher in charge",
    )

    class Meta:
        verbose_name = "Classroom"
        verbose_name_plural = "Classrooms"
        ordering = ['-id']

    def __str__(self):
        return self.name


class ClassEnrollment(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='enrollments', verbose_name="Classroom")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='class_registrations', verbose_name="Student",
    )
    enrolled_at = models.DateTimeField(auto_now_add=True, verbose_name="Enrolled date")

    class Meta:
        unique_together = ('classroom', 'student')
        verbose_name = "Enrollment"
        verbose_name_plural = "Enrollments"
        ordering = ['-enrolled_at']

    def __str__(self):
        return f"{self.student.get_full_name() or self.student.username} → {self.classroom.name}"


class Schedule(models.Model):
    DAY_CHOICES = [
        (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'),
        (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday'),
    ]
    classroom  = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='schedules', verbose_name="Classroom")
    day_of_week = models.IntegerField(choices=DAY_CHOICES, verbose_name="Day of week", db_index=True)
    start_time  = models.TimeField(verbose_name="Start time")
    end_time    = models.TimeField(verbose_name="End time")
    room_name   = models.CharField(max_length=100, blank=True, verbose_name="Classroom room")

    class Meta:
        verbose_name = "Schedule"
        verbose_name_plural = "Schedules"
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        return f"{self.classroom.name} — {self.get_day_of_week_display()} {self.start_time:%H:%M}–{self.end_time:%H:%M}"

    def clean(self):
        # 1. Basic time boundary validation
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError("End time must be after start time.")

        # 2. BR_SCHEDULE_VALIDATION: Block duplicate schedules (same day + same room + overlapping time slots)
        # Overlap Algorithm: (StartA < EndB) AND (EndA > StartB)
        if self.day_of_week is not None and self.room_name:
            overlapping = Schedule.objects.filter(
                day_of_week=self.day_of_week,
                room_name=self.room_name,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time,
            )
            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)
            if overlapping.exists():
                raise ValidationError(
                    "The classroom is already booked for this time slot. Please choose another room or time!"
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Attendance(models.Model):
    STATUS_CHOICES = (
        ('present',          'Present'),
        ('absent_excused',   'Absent (Excused)'),
        ('absent_unexcused', 'Absent (Unexcused)'),
        ('late',             'Late'),
    )
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, verbose_name="Classroom")
    student   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Student")
    schedule  = models.ForeignKey(Schedule, on_delete=models.CASCADE, verbose_name="Session")
    date      = models.DateField(verbose_name="Attendance date", db_index=True)
    status    = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present', verbose_name="Status", db_index=True)
    remark    = models.TextField(blank=True, verbose_name="Remark")

    class Meta:
        unique_together = ('student', 'schedule', 'date')
        verbose_name = "Attendance"
        verbose_name_plural = "Attendances"
        ordering = ['-date']

    def __str__(self):
        return f"{self.student.get_full_name() or self.student.username} — {self.date} ({self.get_status_display()})"


class DailyComment(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, verbose_name="Classroom")
    student    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='received_comments', verbose_name="Student",
    )
    schedule   = models.ForeignKey(Schedule, on_delete=models.CASCADE, null=True, verbose_name="Session")
    date       = models.DateField(null=True, verbose_name="Comment date", db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='created_comments', verbose_name="Teacher",
    )
    content    = models.TextField(verbose_name="Comment content")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created time")

    class Meta:
        verbose_name = "Daily Comment"
        verbose_name_plural = "Daily Comments"
        ordering = ['-date', '-created_at']

    def __str__(self):
        name = self.student.get_full_name() or self.student.username
        return f"Comment: {name} — {self.date}"