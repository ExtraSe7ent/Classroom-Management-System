from django.db import models
from django.contrib.auth.models import User


DAY_CHOICES = [
    ('Monday', 'Thứ Hai'),
    ('Tuesday', 'Thứ Ba'),
    ('Wednesday', 'Thứ Tư'),
    ('Thursday', 'Thứ Năm'),
    ('Friday', 'Thứ Sáu'),
    ('Saturday', 'Thứ Bảy'),
    ('Sunday', 'Chủ Nhật'),
]


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('teacher', 'Giáo viên'),
        ('student', 'Học sinh'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'User_Profiles'
        verbose_name = 'Hồ sơ người dùng'
        verbose_name_plural = 'Hồ sơ người dùng'

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.role})"


class Class(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='classes')
    teacher_name = models.CharField(max_length=100, blank=True)
    room = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'Classes'
        verbose_name = 'Lớp học'
        verbose_name_plural = 'Các lớp học'

    def __str__(self):
        return self.name

    def get_schedule_display(self):
        schedules = self.schedules.all().order_by('day_of_week')
        parts = []
        for s in schedules:
            parts.append(f"{s.get_day_of_week_display()} ({s.start_time.strftime('%H:%M')} - {s.end_time.strftime('%H:%M')})")
        return ', '.join(parts) if parts else 'Chưa xếp lịch'

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
        verbose_name = 'Học sinh'
        verbose_name_plural = 'Các học sinh'

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.student_id})"

    def get_classes_display(self):
        return ', '.join([c.name for c in self.classes.all()]) or 'Chưa xếp lớp'


class Schedule(models.Model):
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.CharField(max_length=20, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'Schedules'
        verbose_name = 'Lịch học'
        verbose_name_plural = 'Các lịch học'
        unique_together = ('class_obj', 'day_of_week', 'start_time')

    def __str__(self):
        return f"{self.class_obj.name} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"


class Assignment(models.Model):
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
        verbose_name = 'Bài tập'
        verbose_name_plural = 'Các bài tập'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.class_obj.name})"

    def get_submission_count(self):
        return self.submissions.exclude(status='missing').count()

    def get_total_students(self):
        return self.class_obj.students.count()


class Submission(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Chờ chấm điểm'),
        ('graded', 'Đã có điểm'),
        ('missing', 'Thiếu bài / Quá hạn'),
    ]

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='submissions')
    file = models.FileField(upload_to='submissions/', blank=True, null=True)
    note = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.FloatField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    class Meta:
        db_table = 'Submissions'
        verbose_name = 'Bài nộp'
        verbose_name_plural = 'Các bài nộp'
        unique_together = ('assignment', 'student')

    def __str__(self):
        return f"{self.student} - {self.assignment.title}"


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'Đi học'),
        ('excused', 'Vắng phép'),
        ('absent', 'Vắng không phép'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendances')
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')

    class Meta:
        db_table = 'Attendances'
        verbose_name = 'Điểm danh'
        verbose_name_plural = 'Các bản ghi điểm danh'
        unique_together = ('student', 'class_obj', 'date')
        indexes = [
            models.Index(fields=['student', 'date']),
        ]

    def __str__(self):
        return f"{self.student} - {self.class_obj.name} - {self.date} ({self.status})"


class DailyComment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='daily_comments')
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='daily_comments')
    comment_date = models.DateField()
    comment_text = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='daily_comments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'Daily_Comments'
        verbose_name = 'Nhận xét hàng ngày'
        verbose_name_plural = 'Các nhận xét hàng ngày'
        unique_together = ('student', 'class_obj', 'comment_date')
        indexes = [
            models.Index(fields=['student', 'comment_date']),
        ]

    def __str__(self):
        return f"{self.student} - {self.comment_date}"


class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_otps')
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = 'Password_Reset_OTP'
        verbose_name = 'Mã OTP đặt lại mật khẩu'
        verbose_name_plural = 'Các mã OTP đặt lại mật khẩu'
        ordering = ['-created_at']

    def __str__(self):
        return f"OTP {self.otp_code} - {self.user.username}"

    def is_valid(self):
        from django.utils import timezone
        return (not self.is_used) and timezone.now() < self.expires_at
