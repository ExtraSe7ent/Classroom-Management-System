import os
from django import forms
from django.utils import timezone
from .models import Assignment, Submission


class AssignmentForm(forms.ModelForm):
    """Form to post assignment — validates all constraints from PTYC."""
    class Meta:
        model = Assignment
        fields = ['classroom', 'title', 'description', 'due_date', 'file_attachment']
        widgets = {
            'classroom': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Assignment title (5–255 characters)...',
                'minlength': '5', 'maxlength': '255',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'Detailed assignment requirements...',
                'maxlength': '20000',   # PTYC: InstructionText MaxLength = 20000
            }),
            'due_date': forms.DateTimeInput(attrs={
                'class': 'form-control', 'type': 'datetime-local',
            }),
            'file_attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_title(self):
        title = (self.cleaned_data.get('title') or '').strip()
        if len(title) < 5:
            raise forms.ValidationError("Assignment title must have at least 5 characters.")
        if len(title) > 255:
            raise forms.ValidationError("Assignment title cannot exceed 255 characters.")
        return title

    def clean_description(self):
        desc = self.cleaned_data.get('description') or ''
        if len(desc) > 20000:
            raise forms.ValidationError("Requirement details cannot exceed 20,000 characters.")
        return desc

    def clean_due_date(self):
        due_date = self.cleaned_data.get('due_date')
        if due_date and due_date <= timezone.now():
            raise forms.ValidationError("Due date must be in the future!")
        return due_date

    def clean_file_attachment(self):
        file = self.cleaned_data.get('file_attachment')
        if file:
            ext = os.path.splitext(file.name)[1].lower()
            allowed = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.zip', '.rar']
            blocked  = ['.exe', '.bat', '.sh', '.msi', '.cmd', '.ps1']
            if ext in blocked:
                raise forms.ValidationError(
                    "For security reasons, executable files (.exe, .bat, etc.) are blocked."
                )
            if ext not in allowed:
                raise forms.ValidationError(
                    f"File format {ext} is not supported. Please attach PDF, Word, Image, or Zip/Rar."
                )
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size too large. Please upload files smaller than 10MB.")
        return file


class SubmissionForm(forms.ModelForm):
    """Form for student to submit homework."""
    class Meta:
        model = Submission
        fields = ['content', 'submitted_file']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'Enter a message or submission content (max 500 characters)...',
                'maxlength': '500',   # PTYC: Student Message MaxLength = 500
            }),
            'submitted_file': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_content(self):
        content = self.cleaned_data.get('content') or ''
        if len(content) > 500:
            raise forms.ValidationError("Message cannot exceed 500 characters.")
        return content

    def clean_submitted_file(self):
        file = self.cleaned_data.get('submitted_file')
        if file:
            ext = os.path.splitext(file.name)[1].lower()
            allowed = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.zip', '.rar']
            if ext not in allowed:
                raise forms.ValidationError(
                    f"File format {ext} is not allowed. Please submit a document or image file."
                )
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("Submission file size cannot exceed 10MB.")
        return file


class GradeForm(forms.ModelForm):
    """Form for teacher to grade and comment on submissions (UC08)."""
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
                'placeholder': 'Feedback on student work (max 1000 characters)...',
                'maxlength': '1000',   # PTYC: Teacher feedback MaxLength = 1000
            }),
        }

    def clean_grade(self):
        grade = self.cleaned_data.get('grade')
        if grade is not None:
            if grade < 0 or grade > 10:
                raise forms.ValidationError(
                    "Invalid grade! Please input a score from 0.0 to 10.0."
                )
        return grade

    def clean_teacher_comment(self):
        comment = self.cleaned_data.get('teacher_comment') or ''
        if len(comment) > 1000:
            raise forms.ValidationError("Feedback cannot exceed 1000 characters.")
        return comment