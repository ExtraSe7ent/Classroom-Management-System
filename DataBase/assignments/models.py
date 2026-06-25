from django.db import models
from django.conf import settings
from classrooms.models import Classroom

class Assignment(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=255)
    description = models.TextField(verbose_name="Nội dung yêu cầu")
    file_attachment = models.FileField(upload_to='assignments/', blank=True, null=True, verbose_name="Tệp đính kèm")
    due_date = models.DateTimeField(verbose_name="Hạn nộp")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField(blank=True, verbose_name="Nội dung bài làm")
    submitted_file = models.FileField(upload_to='submissions/', blank=True, null=True, verbose_name="Tệp bài làm")
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.FloatField(null=True, blank=True, verbose_name="Điểm số") 
    teacher_comment = models.TextField(blank=True, verbose_name="Nhận xét của giáo viên")

    class Meta:
        unique_together = ('assignment', 'student') # Mỗi học sinh nộp 1 lần cho 1 bài tập

    def __str__(self):
        return f"Submission by {self.student.username} for {self.assignment.title}"