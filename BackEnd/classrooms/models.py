from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class Classroom(models.Model):
    STATUS_CHOICES = (
        (True,  'Đang hoạt động'),
        (False, 'Đã kết thúc'),
    )
    name = models.CharField(max_length=255, verbose_name="Tên lớp", db_index=True)
    description = models.TextField(blank=True, verbose_name="Mô tả lớp học")
    tuition = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Học phí (VNĐ)")
    is_active = models.BooleanField(choices=STATUS_CHOICES, default=True, verbose_name="Trạng thái", db_index=True)
    # PTYC - Quy tắc Set Null: xóa tài khoản giáo viên thì lớp vẫn giữ nguyên.
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='managed_classes',
        limit_choices_to={'role__in': ['teacher', 'admin']},
        verbose_name="Giáo viên phụ trách",
    )

    class Meta:
        verbose_name = "Lớp học"
        verbose_name_plural = "Danh sách lớp học"
        ordering = ['-id']

    def __str__(self):
        return self.name


class ClassEnrollment(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='enrollments', verbose_name="Lớp học")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='class_registrations', verbose_name="Học sinh",
    )
    enrolled_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày ghi danh")

    class Meta:
        unique_together = ('classroom', 'student')
        verbose_name = "Ghi danh"
        verbose_name_plural = "Danh sách ghi danh"
        ordering = ['-enrolled_at']

    def __str__(self):
        return f"{self.student.get_full_name() or self.student.username} → {self.classroom.name}"


class Schedule(models.Model):
    DAY_CHOICES = [
        (0, 'Thứ 2'), (1, 'Thứ 3'), (2, 'Thứ 4'), (3, 'Thứ 5'),
        (4, 'Thứ 6'), (5, 'Thứ 7'), (6, 'Chủ nhật'),
    ]
    classroom  = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='schedules', verbose_name="Lớp học")
    day_of_week = models.IntegerField(choices=DAY_CHOICES, verbose_name="Thứ trong tuần", db_index=True)
    start_time  = models.TimeField(verbose_name="Giờ bắt đầu")
    end_time    = models.TimeField(verbose_name="Giờ kết thúc")
    room_name   = models.CharField(max_length=100, blank=True, verbose_name="Phòng học")

    class Meta:
        verbose_name = "Lịch học"
        verbose_name_plural = "Lịch học"
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        return f"{self.classroom.name} — {self.get_day_of_week_display()} {self.start_time:%H:%M}–{self.end_time:%H:%M}"

    def clean(self):
        # 1. Kiểm tra logic thời gian cơ bản
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError("Thời gian kết thúc phải sau thời gian bắt đầu.")

        # 2. BR_SCHEDULE_VALIDATION: Chặn trùng lịch (Thứ + Phòng + Khung giờ)
        # Thuật toán Overlap: (BắtĐầuA < KếtThúcB) AND (KếtThúcA > BắtĐầuB)
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
                    "Phòng học đã bận vào khung giờ này. Vui lòng chọn phòng hoặc thời gian khác!"
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Attendance(models.Model):
    STATUS_CHOICES = (
        ('present',          'Có mặt'),
        ('absent_excused',   'Vắng (Có phép)'),
        ('absent_unexcused', 'Vắng (Không phép)'),
        ('late',             'Đi muộn'),
    )
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, verbose_name="Lớp học")
    student   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Học sinh")
    schedule  = models.ForeignKey(Schedule, on_delete=models.CASCADE, verbose_name="Buổi học")
    date      = models.DateField(verbose_name="Ngày điểm danh", db_index=True)
    status    = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present', verbose_name="Trạng thái", db_index=True)
    remark    = models.TextField(blank=True, verbose_name="Ghi chú")

    class Meta:
        unique_together = ('student', 'schedule', 'date')
        verbose_name = "Điểm danh"
        verbose_name_plural = "Bảng điểm danh"
        ordering = ['-date']

    def __str__(self):
        return f"{self.student.get_full_name() or self.student.username} — {self.date} ({self.get_status_display()})"


class DailyComment(models.Model):
    classroom  = models.ForeignKey(Classroom, on_delete=models.CASCADE, verbose_name="Lớp học")
    student    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='received_comments', verbose_name="Học sinh",
    )
    schedule   = models.ForeignKey(Schedule, on_delete=models.CASCADE, null=True, verbose_name="Buổi học")
    date       = models.DateField(null=True, verbose_name="Ngày nhận xét", db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='created_comments', verbose_name="Giáo viên",
    )
    content    = models.TextField(verbose_name="Nội dung nhận xét")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian tạo")

    class Meta:
        verbose_name = "Nhận xét hàng ngày"
        verbose_name_plural = "Nhận xét hàng ngày"
        ordering = ['-date', '-created_at']

    def __str__(self):
        name = self.student.get_full_name() or self.student.username
        return f"Nhận xét: {name} — {self.date}"