from django.db import models
from django.conf import settings
from classrooms.models import Classroom


class Assignment(models.Model):
    """Assignment given to a classroom by the teacher."""
    classroom       = models.ForeignKey(
        Classroom, on_delete=models.CASCADE,
        related_name='assignments', verbose_name="Classroom",
    )
    title           = models.CharField(
        max_length=255, verbose_name="Assignment title", db_index=True,
    )
    description     = models.TextField(
        verbose_name="Requirement details", max_length=20000,
    )
    file_attachment = models.FileField(
        upload_to='assignments/', blank=True, null=True,
        verbose_name="Attached guide file",
    )
    due_date        = models.DateTimeField(verbose_name="Due date", db_index=True)
    created_at      = models.DateTimeField(auto_now_add=True, verbose_name="Created date")

    class Meta:
        verbose_name        = "Assignment"
        verbose_name_plural = "Assignments"
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.title} [{self.classroom.name}]"


class Submission(models.Model):
    """Submission of homework uploaded by a student."""
    STATUS_PENDING = 'pending'
    STATUS_GRADED  = 'graded'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending grading'),
        (STATUS_GRADED,  'Graded'),
    ]

    assignment      = models.ForeignKey(
        Assignment, on_delete=models.CASCADE,
        related_name='submissions', verbose_name="Assignment",
    )
    student         = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        verbose_name="Student",
    )
    content         = models.TextField(
        blank=True, verbose_name="Submission content / Student message",
        max_length=500,   # PTYC: Student Message MaxLength = 500
    )
    submitted_file  = models.FileField(
        upload_to='submissions/', blank=True, null=True,
        verbose_name="Submission file",
    )
    submitted_at    = models.DateTimeField(auto_now_add=True, verbose_name="Submission time", db_index=True)
    status          = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING,
        verbose_name="Status", db_index=True,
    )
    grade           = models.FloatField(null=True, blank=True, verbose_name="Grade")
    teacher_comment = models.TextField(
        blank=True, verbose_name="Teacher feedback",
        max_length=1000,  # PTYC: Teacher feedback MaxLength = 1000
    )

    class Meta:
        unique_together     = ('assignment', 'student')  # Each student submits only once per assignment
        verbose_name        = "Submission"
        verbose_name_plural = "Submissions"
        ordering            = ['-submitted_at']

    def __str__(self):
        return (
            f"{self.student.get_full_name() or self.student.username}"
            f" → {self.assignment.title}"
        )