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
        ('parent', 'Phụ huynh'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)  # SĐT liên hệ/khẩn cấp
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

    def get_role_display_custom(self):
        return dict(self.ROLE_CHOICES).get(self.role, self.role)


class Class(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='classes')
    teacher_name = models.CharField(max_length=100, blank=True)  # Tên hiển thị của giáo viên
    room = models.CharField(max_length=100, blank=True)           # Phòng học cố định
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'Classes'
        verbose_name = 'Lớp học'
        verbose_name_plural = 'Các lớp học'

    def __str__(self):
        return self.name

    def get_schedule_display(self):
        """Trả về chuỗi lịch học tổng hợp từ các Schedule liên kết."""
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
    """Lịch học cố định của một lớp học."""
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.CharField(max_length=20, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=100, blank=True)  # Để trống = học online

    class Meta:
        db_table = 'Schedules'
        verbose_name = 'Lịch học'
        verbose_name_plural = 'Các lịch học'
        unique_together = ('class_obj', 'day_of_week', 'start_time')

    def __str__(self):
        return f"{self.class_obj.name} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"


class Assignment(models.Model):
    """Bài tập được giáo viên/admin giao cho một lớp học."""
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
    """Bài nộp của một học sinh cho một bài tập."""
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
    grade = models.FloatField(null=True, blank=True)   # None = chưa chấm
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
    """Bản ghi điểm danh của học sinh trong một buổi học."""
    STATUS_CHOICES = [
        ('present', 'Đi học'),
        ('excused', 'Vắng phép'),
        ('absent', 'Vắng không phép'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendances')
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    remarks = models.TextField(blank=True)  # Nhận xét của giáo viên

    class Meta:
        db_table = 'Attendances'
        verbose_name = 'Điểm danh'
        verbose_name_plural = 'Các bản ghi điểm danh'
        unique_together = ('student', 'class_obj', 'date')

    def __str__(self):
        return f"{self.student} - {self.class_obj.name} - {self.date} ({self.status})"
