from django import forms
from django.db.models import Q
from .models import Classroom, Schedule, ClassEnrollment
from accounts.models import User


class ClassroomForm(forms.ModelForm):
    """Form tạo/sửa lớp học."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Giáo viên phụ trách: tài khoản Teacher hoặc Admin/Hiệu trưởng
        self.fields['teacher'].queryset = User.objects.filter(
            Q(role='teacher') | Q(role='admin') | Q(is_superuser=True)
        ).order_by('last_name', 'first_name')
        self.fields['teacher'].label = "Giáo viên phụ trách"
        self.fields['teacher'].empty_label = "— Chưa phân công —"

    class Meta:
        model  = Classroom
        fields = ['name', 'tuition', 'is_active', 'description', 'teacher']
        widgets = {
            'name':        forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Tên lớp học...', 'maxlength': '255',
            }),
            'tuition':     forms.NumberInput(attrs={
                'class': 'form-control', 'placeholder': 'Ví dụ: 1200000', 'min': '0',
            }),
            'is_active':   forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Mô tả ngắn về lớp học...',
            }),
            'teacher':     forms.Select(attrs={'class': 'form-select'}),
        }


class ScheduleForm(forms.ModelForm):
    """Form xếp lịch học — validate overlap được xử lý ở model.clean()."""
    class Meta:
        model  = Schedule
        fields = ['day_of_week', 'start_time', 'end_time', 'room_name']
        widgets = {
            'day_of_week': forms.Select(attrs={'class': 'form-select'}),
            'start_time':  forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time':    forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'room_name':   forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ví dụ: P.201 (để trống nếu học online)',
                'maxlength': '100',  # PTYC: InputRoom MaxLength = 100
            }),
        }


class EnrollmentForm(forms.ModelForm):
    """Form ghi danh học sinh vào lớp."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = User.objects.filter(role='student').order_by('last_name', 'first_name')

    class Meta:
        model  = ClassEnrollment
        fields = ['student']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
        }