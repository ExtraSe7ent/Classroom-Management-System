from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

class Classroom(models.Model):
    STATUS_CHOICES = (
        (True, 'Đang hoạt động'),
        (False, 'Đã kết thúc'),
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, verbose_name="Mô tả lớp học")
    tuition = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Học phí (VNĐ)")
    is_active = models.BooleanField(choices=STATUS_CHOICES, default=True, verbose_name="Trạng thái")
    # Giáo viên (Admin) quản lý lớp
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='managed_classes')

    class Meta:
        verbose_name = "Lớp học"

    def __str__(self):
        return self.name

class ClassEnrollment(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='enrollments')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='class_registrations')
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('classroom', 'student') # Một học sinh không đăng ký 1 lớp 2 lần

class Schedule(models.Model):
    DAY_CHOICES = [
        (0, 'Thứ 2'), (1, 'Thứ 3'), (2, 'Thứ 4'), (3, 'Thứ 5'),
        (4, 'Thứ 6'), (5, 'Thứ 7'), (6, 'Chủ nhật'),
    ]
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room_name = models.CharField(max_length=50)

    def clean(self):
        # 1. Kiểm tra logic thời gian cơ bản
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError("Thời gian kết thúc phải sau thời gian bắt đầu")

        # 2. Quy tắc BR_SCHEDULE_VALIDATION: Chặn trùng lịch (Thứ + Phòng + Khung giờ)
        # Thuật toán Overlap: (Bắt đầu A < Kết thúc B) AND (Kết thúc A > Bắt đầu B)
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
                raise ValidationError("Phòng học đã bận vào khung giờ này. Vui lòng chọn phòng hoặc thời gian khác!")

    def save(self, *args, **kwargs):
        self.full_clean()  # Chạy hàm clean() để thực hiện validation trước khi save
        super().save(*args, **kwargs)

class Attendance(models.Model):
    STATUS_CHOICES = (
        ('present', 'Có mặt'),
        ('absent_excused', 'Vắng (Có phép)'),
        ('absent_unexcused', 'Vắng (Không phép)'),
        ('late', 'Đi muộn'),
    )
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    remark = models.TextField(blank=True, verbose_name="Ghi chú")

    class Meta:
        unique_together = ('student', 'schedule', 'date')

class DailyComment(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_comments')
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, null=True) # Liên kết buổi học
    date = models.DateField(null=True) # Ngày nhận xét
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_comments')
    content = models.TextField(verbose_name="Nội dung nhận xét")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for {self.student.username} on {self.date}"