from django import forms
from django.db.models import Q
from .models import Classroom, Schedule, ClassEnrollment
from accounts.models import User

class ClassroomForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Displays users with the role of admin OR superuser (like adminboss)
        self.fields['teacher'].queryset = User.objects.filter(Q(role='admin') | Q(is_superuser=True))

    class Meta:
        model = Classroom
        fields = ['name', 'tuition', 'is_active', 'description', 'teacher']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'tuition': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'For example: 500000'}),
            'is_active': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'teacher': forms.Select(attrs={'class': 'form-select'}),
        }

class ScheduleForm(forms.ModelForm):
    """Class scheduling form for teachers"""
    class Meta:
        model = Schedule
        fields = ['day_of_week', 'start_time', 'end_time', 'room_name']
        widgets = {
            'day_of_week': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'room_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Example: P.201'}),
        }

class EnrollmentForm(forms.ModelForm):
    """Form to enroll students in class"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only shows users whose role is student
        self.fields['student'].queryset = User.objects.filter(role='student')

    class Meta:
        model = ClassEnrollment
        fields = ['student']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
        }