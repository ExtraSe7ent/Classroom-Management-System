from django import forms
from django.contrib.auth.models import User
from .models import UserProfile, Class, Student, Schedule, Assignment, Submission, Attendance


# ===== USER PROFILE & AUTH =====

class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=False, label='Name')
    last_name = forms.CharField(max_length=150, required=False, label='Last name')
    email = forms.EmailField(required=False, label='Email')

    class Meta:
        model = UserProfile
        fields = ['phone', 'contact_phone', 'address', 'date_of_birth']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 2}),
        }


class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(widget=forms.PasswordInput, required=False)
    new_password = forms.CharField(widget=forms.PasswordInput, required=False)
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=False)


# ===== CLASS =====

class ClassForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = ['name', 'teacher_name', 'room', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError('Class name cannot be empty.')
        return name

    def clean_teacher_name(self):
        teacher_name = self.cleaned_data.get('teacher_name', '').strip()
        if not teacher_name:
            raise forms.ValidationError('Please select the teacher in charge.')
        return teacher_name


# ===== STUDENT =====

class StudentForm(forms.Form):
    """New student addition form — automatically creates Django User account."""
    student_id = forms.CharField(max_length=50, label='Student code')
    username = forms.CharField(max_length=30, label='Login name')
    last_name = forms.CharField(max_length=150, label='Student family')
    first_name = forms.CharField(max_length=150, label='Student name')
    phone = forms.CharField(max_length=20, required=False, label='Phone number')
    email = forms.EmailField(required=False, label='Email')
    date_of_birth = forms.DateField(required=False, label='Date of birth',
                                    widget=forms.DateInput(attrs={'type': 'date'}))
    address = forms.CharField(required=False, max_length=200, label='Address')

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Username already exists.')
        return username

    def clean_student_id(self):
        student_id = self.cleaned_data.get('student_id', '').strip()
        if Student.objects.filter(student_id=student_id).exists():
            raise forms.ValidationError('Student code already exists.')
        return student_id

    def save(self):
        """Create User account and Student profile, default password Student@123."""
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data['username'],
            password='Student@123',
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data.get('email', ''),
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.phone = data.get('phone', '')
        profile.date_of_birth = data.get('date_of_birth')
        profile.address = data.get('address', '')
        profile.role = 'student'
        profile.save()

        student = Student.objects.create(
            user=user,
            student_id=data['student_id'],
        )
        return student


class StudentEditForm(forms.Form):
    """Form to edit student information — Admin can edit class information."""
    last_name = forms.CharField(max_length=150, label='Student family')
    first_name = forms.CharField(max_length=150, label='Student name')
    phone = forms.CharField(max_length=20, required=False, label='Phone number')
    email = forms.EmailField(required=False, label='Email')
    date_of_birth = forms.DateField(required=False, label='Date of birth',
                                    widget=forms.DateInput(attrs={'type': 'date'}))
    address = forms.CharField(required=False, max_length=200, label='Address')


# ===== SCHEDULE =====

class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = ['day_of_week', 'start_time', 'end_time', 'room']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')
        if start and end and end <= start:
            raise forms.ValidationError('The end time must be greater than the start time.')
        return cleaned_data


# ===== ASSIGNMENT =====

class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['title', 'class_obj', 'due_date', 'file', 'description']
        widgets = {
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            raise forms.ValidationError('Assignment title cannot be blank.')
        return title


# ===== GRADING =====

class GradeSubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['grade', 'feedback', 'status']
        widgets = {
            'feedback': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_grade(self):
        grade = self.cleaned_data.get('grade')
        if grade is not None and (grade < 0 or grade > 10):
            raise forms.ValidationError('Scores must be between 0 and 10.')
        return grade


# ===== SUBMISSION (student submits work) =====

class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['file', 'note']
        widgets = {
            'note': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            max_size = 10 * 1024 * 1024  # 10MB
            if file.size > max_size:
                raise forms.ValidationError('File must not exceed 10MB.')
        return file
