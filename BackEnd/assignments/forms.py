import os
from django import forms
from django.utils import timezone
from .models import Assignment, Submission


class AssignmentForm(forms.ModelForm):
    """Form giao bài tập — validate đầy đủ theo PTYC."""
    class Meta:
        model = Assignment
        fields = ['classroom', 'title', 'description', 'due_date', 'file_attachment']
        widgets = {
            'classroom': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tiêu đề bài tập (5–255 ký tự)...',
                'minlength': '5', 'maxlength': '255',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'Mô tả chi tiết yêu cầu bài tập...',
                'maxlength': '20000',   # PTYC: InstructionText MaxLength = 20000
            }),
            'due_date': forms.DateTimeInput(attrs={
                'class': 'form-control', 'type': 'datetime-local',
            }),
            'file_attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_title(self):
        """PTYC: title dài 5–255 ký tự."""
        title = (self.cleaned_data.get('title') or '').strip()
        if len(title) < 5:
            raise forms.ValidationError("Tiêu đề bài tập phải có ít nhất 5 ký tự.")
        if len(title) > 255:
            raise forms.ValidationError("Tiêu đề bài tập không được vượt quá 255 ký tự.")
        return title

    def clean_description(self):
        """PTYC: description maxlength = 20000."""
        desc = self.cleaned_data.get('description') or ''
        if len(desc) > 20000:
            raise forms.ValidationError("Nội dung yêu cầu không được vượt quá 20.000 ký tự.")
        return desc

    def clean_due_date(self):
        """EX_PAST_DUE_DATE: Hạn nộp phải lớn hơn thời gian hiện tại."""
        due_date = self.cleaned_data.get('due_date')
        if due_date and due_date <= timezone.now():
            raise forms.ValidationError("Hạn nộp bài tập phải lớn hơn thời gian hiện tại!")
        return due_date

    def clean_file_attachment(self):
        """EX_INVALID_FILE: Kiểm tra định dạng và kích thước file."""
        file = self.cleaned_data.get('file_attachment')
        if file:
            ext = os.path.splitext(file.name)[1].lower()
            # PTYC: chỉ chấp nhận .pdf, .doc, .docx, .png, .jpg
            allowed = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.zip', '.rar']
            blocked  = ['.exe', '.bat', '.sh', '.msi', '.cmd', '.ps1']
            if ext in blocked:
                raise forms.ValidationError(
                    "Vì lý do bảo mật, hệ thống không chấp nhận tệp thực thi (.exe, .bat,...)."
                )
            if ext not in allowed:
                raise forms.ValidationError(
                    f"Định dạng {ext} không được hỗ trợ. Hãy đính kèm PDF, Word, Ảnh hoặc Zip."
                )
            # PTYC: dung lượng < 10MB
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("Dung lượng file quá lớn. Vui lòng upload file nhỏ hơn 10MB.")
        return file


class SubmissionForm(forms.ModelForm):
    """Form nộp bài tập dành cho học sinh."""
    class Meta:
        model = Submission
        fields = ['content', 'submitted_file']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'Nhập lời nhắn hoặc nội dung bài làm (tối đa 500 ký tự)...',
                'maxlength': '500',   # PTYC: Student Message MaxLength = 500
            }),
            'submitted_file': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_content(self):
        """PTYC: Student Message maxlength = 500."""
        content = self.cleaned_data.get('content') or ''
        if len(content) > 500:
            raise forms.ValidationError("Lời nhắn không được vượt quá 500 ký tự.")
        return content

    def clean_submitted_file(self):
        """EX_INVALID_SUBMISSION_FILE: Kiểm tra file bài nộp."""
        file = self.cleaned_data.get('submitted_file')
        if file:
            ext = os.path.splitext(file.name)[1].lower()
            # PTYC: .pdf, .doc, .docx, .png, .jpg
            allowed = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.zip', '.rar']
            if ext not in allowed:
                raise forms.ValidationError(
                    f"Định dạng {ext} không được phép. Vui lòng nộp file tài liệu hoặc ảnh."
                )
            # PTYC: dung lượng < 10MB
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("Dung lượng bài nộp không được vượt quá 10MB.")
        return file


class GradeForm(forms.ModelForm):
    """Form chấm điểm và nhận xét cho giáo viên (UC08)."""
    class Meta:
        model = Submission
        fields = ['grade', 'teacher_comment']
        widgets = {
            'grade': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1', 'min': '0', 'max': '10',
                'placeholder': '0.0 – 10.0',
            }),
            'teacher_comment': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Nhận xét bài làm của học sinh (tối đa 1000 ký tự)...',
                'maxlength': '1000',   # PTYC: Teacher feedback MaxLength = 1000
            }),
        }

    def clean_grade(self):
        """EX_INVALID_GRADE: Điểm phải là float trong khoảng 0.0 đến 10.0."""
        grade = self.cleaned_data.get('grade')
        if grade is not None:
            if grade < 0 or grade > 10:
                raise forms.ValidationError(
                    "Điểm số không hợp lệ! Vui lòng nhập trong thang điểm từ 0.0 đến 10.0."
                )
        return grade

    def clean_teacher_comment(self):
        """PTYC: Teacher feedback MaxLength = 1000."""
        comment = self.cleaned_data.get('teacher_comment') or ''
        if len(comment) > 1000:
            raise forms.ValidationError("Nhận xét không được vượt quá 1000 ký tự.")
        return comment