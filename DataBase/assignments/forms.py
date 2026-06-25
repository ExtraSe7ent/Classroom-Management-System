import os
from django import forms
from django.utils import timezone
from .models import Assignment, Submission

class AssignmentForm(forms.ModelForm):
    """Form giao bài tập với logic kiểm tra ngoại lệ chuẩn Senior"""
    class Meta:
        model = Assignment
        fields = ['classroom', 'title', 'description', 'due_date', 'file_attachment']
        widgets = {
            'classroom': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tiêu đề bài tập...'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Mô tả chi tiết yêu cầu bài tập...'}),
            'due_date': forms.DateTimeInput(attrs={
                'class': 'form-control', 
                'type': 'datetime-local'
            }),
            'file_attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_due_date(self):
        """EX_PAST_DUE_DATE: Kiểm tra hạn nộp không được ở quá khứ"""
        due_date = self.cleaned_data.get('due_date')
        if due_date and due_date < timezone.now():
            raise forms.ValidationError("Hạn nộp bài tập không được chọn một thời gian trong quá khứ!")
        return due_date

    def clean_file_attachment(self):
        """EX_INVALID_FILE: Kiểm tra định dạng file an toàn"""
        file = self.cleaned_data.get('file_attachment')
        if file:
            ext = os.path.splitext(file.name)[1].lower()
            valid_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.zip', '.rar']
            
            # Chặn các file thực thi nguy hiểm
            if ext in ['.exe', '.bat', '.sh', '.msi']:
                raise forms.ValidationError("Vì lý do bảo mật, hệ thống không chấp nhận tệp tin thực thi (.exe, .bat,...).")
            
            if ext not in valid_extensions:
                raise forms.ValidationError(f"Định dạng file {ext} không hỗ trợ. Vui lòng đính kèm PDF, Word, Ảnh hoặc Zip.")
            
            # Kiểm tra dung lượng (Ví dụ: giới hạn 10MB)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("Dung lượng file quá lớn. Vui lòng upload file nhỏ hơn 10MB.")
                
        return file

class SubmissionForm(forms.ModelForm):
    """Form nộp bài tập dành cho học sinh"""
    class Meta:
        model = Submission
        fields = ['content', 'submitted_file']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Nhập lời nhắn hoặc nội dung bài làm (nếu có)...'}),
            'submitted_file': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_submitted_file(self):
        """EX_INVALID_SUBMISSION_FILE: Kiểm tra file bài nộp"""
        file = self.cleaned_data.get('submitted_file')
        if file:
            ext = os.path.splitext(file.name)[1].lower()
            valid_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.zip', '.rar']
            if ext not in valid_extensions:
                raise forms.ValidationError(f"Định dạng {ext} không được phép. Vui lòng nộp file tài liệu hoặc ảnh.")
            if file.size > 15 * 1024 * 1024:
                raise forms.ValidationError("Dung lượng bài nộp không được vượt quá 15MB.")
        return file

class GradeForm(forms.ModelForm):
    """Form xử lý chấm điểm và nhận xét cho giáo viên (UC08)"""
    class Meta:
        model = Submission
        fields = ['grade', 'teacher_comment']
        widgets = {
            'teacher_comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean_grade(self):
        grade = self.cleaned_data.get('grade')
        # EX_INVALID_GRADE: Kiểm tra logic thang điểm từ 0 đến 10
        if grade is not None and (grade < 0 or grade > 10):
            raise forms.ValidationError("Điểm số nhập vào không hợp lệ, vui lòng nhập trong thang điểm từ 0 đến 10!")
        return grade