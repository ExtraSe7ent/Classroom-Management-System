from django.db import models
from django.conf import settings
from classrooms.models import Classroom


class Assignment(models.Model):
    """Bài tập được giáo viên giao cho một lớp học."""
    classroom       = models.ForeignKey(
        Classroom, on_delete=models.CASCADE,
        related_name='assignments', verbose_name="Lớp học",
    )
    title           = models.CharField(
        max_length=255, verbose_name="Tiêu đề bài tập", db_index=True,
    )
    description     = models.TextField(
        verbose_name="Nội dung yêu cầu", max_length=20000,
    )
    file_attachment = models.FileField(
        upload_to='assignments/', blank=True, null=True,
        verbose_name="Tệp đính kèm hướng dẫn",
    )
    due_date        = models.DateTimeField(verbose_name="Hạn nộp", db_index=True)
    created_at      = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")

    class Meta:
        verbose_name        = "Bài tập"
        verbose_name_plural = "Danh sách bài tập"
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.title} [{self.classroom.name}]"


class Submission(models.Model):
    """Bài làm của học sinh nộp lên cho một bài tập."""
    STATUS_PENDING = 'pending'
    STATUS_GRADED  = 'graded'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Đang chờ chấm'),
        (STATUS_GRADED,  'Đã có điểm'),
    ]

    assignment      = models.ForeignKey(
        Assignment, on_delete=models.CASCADE,
        related_name='submissions', verbose_name="Bài tập",
    )
    student         = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        verbose_name="Học sinh",
    )
    content         = models.TextField(
        blank=True, verbose_name="Lời nhắn / Nội dung bài làm",
        max_length=500,   # PTYC: Student Message MaxLength = 500
    )
    submitted_file  = models.FileField(
        upload_to='submissions/', blank=True, null=True,
        verbose_name="Tệp bài làm",
    )
    submitted_at    = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian nộp", db_index=True)
    status          = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING,
        verbose_name="Trạng thái", db_index=True,
    )
    grade           = models.FloatField(null=True, blank=True, verbose_name="Điểm số")
    teacher_comment = models.TextField(
        blank=True, verbose_name="Nhận xét của giáo viên",
        max_length=1000,  # PTYC: Teacher feedback MaxLength = 1000
    )

    class Meta:
        unique_together     = ('assignment', 'student')  # Mỗi học sinh nộp 1 lần / 1 bài tập
        verbose_name        = "Bài nộp"
        verbose_name_plural = "Bài nộp của học sinh"
        ordering            = ['-submitted_at']

    def __str__(self):
        return (
            f"{self.student.get_full_name() or self.student.username}"
            f" → {self.assignment.title}"
        )