import os
from django import forms
from django.utils import timezone
from .models import Assignment, Submission

class AssignmentForm(forms.ModelForm):
    """Assignment form with Senior standard exception checking logic"""
    class Meta:
        model = Assignment
        fields = ['classroom', 'title', 'description', 'due_date', 'file_attachment']
        widgets = {
            'classroom': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Lesson title...'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Detailed description of assignment requirements...'}),
            'due_date': forms.DateTimeInput(attrs={
                'class': 'form-control', 
                'type': 'datetime-local'
            }),
            'file_attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_due_date(self):
        """EX_PAST_DUE_DATE: Check the due date cannot be in the past"""
        due_date = self.cleaned_data.get('due_date')
        if due_date and due_date < timezone.now():
            raise forms.ValidationError("The assignment deadline cannot be chosen at a time in the past!")
        return due_date

    def clean_file_attachment(self):
        """EX_INVALID_FILE: Check for safe file formats"""
        file = self.cleaned_data.get('file_attachment')
        if file:
            ext = os.path.splitext(file.name)[1].lower()
            valid_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.zip', '.rar']
            
            # Block dangerous executable files
            if ext in ['.exe', '.bat', '.sh', '.msi']:
                raise forms.ValidationError("For security reasons, the system does not accept executable files (.exe, .bat,...).")
            
            if ext not in valid_extensions:
                raise forms.ValidationError(f"File format {ext} is not supported. Please attach PDF, Word, Photo or Zip.")
            
            # Check capacity (Example: 10MB limit)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size is too large. Please upload files smaller than 10MB.")
                
        return file

class SubmissionForm(forms.ModelForm):
    """Assignment submission form for students"""
    class Meta:
        model = Submission
        fields = ['content', 'submitted_file']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter a message or assignment content (if any)...'}),
            'submitted_file': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_submitted_file(self):
        """EX_INVALID_SUBMISSION_FILE: Check the submission file"""
        file = self.cleaned_data.get('submitted_file')
        if file:
            ext = os.path.splitext(file.name)[1].lower()
            valid_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.zip', '.rar']
            if ext not in valid_extensions:
                raise forms.ValidationError(f"The {ext} format is not allowed. Please submit documents or photos.")
            if file.size > 15 * 1024 * 1024:
                raise forms.ValidationError("Submission size must not exceed 15MB.")
        return file

class GradeForm(forms.ModelForm):
    """Form for handling grading and comments for teachers (UC08)"""
    class Meta:
        model = Submission
        fields = ['grade', 'teacher_comment']
        widgets = {
            'teacher_comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean_grade(self):
        grade = self.cleaned_data.get('grade')
        # EX_INVALID_GRADE: Check the scale logic from 0 to 10
        if grade is not None and (grade < 0 or grade > 10):
            raise forms.ValidationError("The score entered is invalid, please enter on a scale from 0 to 10!")
        return grade