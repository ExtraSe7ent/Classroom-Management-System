import os
import re

from django import forms
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from .models import UserProfile, Class, Student, Schedule, Assignment, Submission

ALLOWED_UPLOAD_EXTENSIONS = ['.pdf', '.doc', '.docx', '.png', '.jpg']
MAX_UPLOAD_SIZE = 10 * 1024 * 1024


def validate_password_strength(password):
    if not (8 <= len(password) <= 50):
        raise forms.ValidationError('Mật khẩu phải từ 8 đến 50 ký tự.')
    if not re.search(r'[A-Z]', password):
        raise forms.ValidationError('Mật khẩu phải chứa ít nhất 1 chữ viết hoa.')
    if not re.search(r'[0-9]', password):
        raise forms.ValidationError('Mật khẩu phải chứa ít nhất 1 chữ số.')
    if not re.search(r'[^A-Za-z0-9]', password):
        raise forms.ValidationError('Mật khẩu phải chứa ít nhất 1 ký tự đặc biệt.')
    return password


def validate_phone(phone):
    if not re.fullmatch(r'0\d{9}', phone or ''):
        raise forms.ValidationError('Số điện thoại phải đúng 10 số và bắt đầu bằng số 0.')
    return phone


def validate_upload_file(file):
    if not file:
        return file
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise forms.ValidationError(
            'Tải lên tệp không hợp lệ. Hệ thống chỉ chấp nhận định dạng: '
            '.pdf, .doc, .docx, .png, .jpg.'
        )
    if file.size > MAX_UPLOAD_SIZE:
        raise forms.ValidationError('Dung lượng tệp không được vượt quá 10MB.')
    return file



# --- FORM TÀI KHOẢN & XÁC THỰC ---

class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=False, label='Tên')
    last_name = forms.CharField(max_length=150, required=False, label='Họ')
    email = forms.EmailField(required=False, label='Email')

    class Meta:
        model = UserProfile
        fields = ['phone', 'contact_phone', 'address', 'date_of_birth']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 2}),
        }


class RegisterForm(forms.Form):
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập họ'}),
    )
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập tên'}),
    )
    username = forms.CharField(
        min_length=3, max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tối thiểu 3 ký tự', 'autocomplete': 'username'}),
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Tuỳ chọn'}),
    )
    phone = forms.CharField(
        validators=[validate_phone],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ví dụ: 0912345678'}),
    )
    password = forms.CharField(
        validators=[validate_password_strength],
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Từ 8 ký tự, có chữ hoa, số, ký tự đặc biệt', 'autocomplete': 'new-password'}),
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nhập lại mật khẩu', 'autocomplete': 'new-password'}),
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Tên đăng nhập này đã được sử dụng.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email này đã được sử dụng.')
        return email

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get('password')
        cpw = cleaned.get('confirm_password')
        if pw and cpw and pw != cpw:
            self.add_error('confirm_password', 'Xác nhận mật khẩu không trùng khớp.')
        return cleaned

    def save(self):
        d = self.cleaned_data
        with transaction.atomic():
            user = User.objects.create_user(
                username=d['username'],
                password=d['password'],
                first_name=d['first_name'],
                last_name=d['last_name'],
                email=d.get('email', ''),
                is_staff=False,
            )
            UserProfile.objects.create(user=user, phone=d['phone'], role='student')
            count = Student.objects.count() + 1
            Student.objects.create(user=user, student_id=f'HS{count:03d}')
        return user


class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(widget=forms.PasswordInput, required=False)
    new_password = forms.CharField(widget=forms.PasswordInput, required=False)
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=False)

    def clean(self):
        cleaned = super().clean()
        new_password = cleaned.get('new_password')
        confirm_password = cleaned.get('confirm_password')
        if new_password:
            validate_password_strength(new_password)
            if new_password != confirm_password:
                raise forms.ValidationError(
                    'Lỗi nhập liệu/Xác nhận mật khẩu mới không trùng khớp.'
                )
        return cleaned



# --- FORM QUẢN LÝ (GIÁO VIÊN) ---

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
            raise forms.ValidationError('Tên lớp học không được để trống.')
        return name

    def clean_teacher_name(self):
        teacher_name = self.cleaned_data.get('teacher_name', '').strip()
        if not teacher_name:
            raise forms.ValidationError('Vui lòng chọn giáo viên phụ trách.')
        return teacher_name


class StudentForm(forms.Form):
    student_id = forms.CharField(max_length=50, label='Mã học sinh')
    username = forms.CharField(max_length=30, label='Tên đăng nhập')
    last_name = forms.CharField(max_length=150, label='Họ học sinh')
    first_name = forms.CharField(max_length=150, label='Tên học sinh')
    phone = forms.CharField(max_length=20, required=False, label='Số điện thoại')
    email = forms.EmailField(required=False, label='Email')
    date_of_birth = forms.DateField(required=False, label='Ngày sinh',
                                    widget=forms.DateInput(attrs={'type': 'date'}))
    address = forms.CharField(required=False, max_length=200, label='Địa chỉ')

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not (3 <= len(username) <= 30):
            raise forms.ValidationError('Tên đăng nhập phải từ 3 đến 30 ký tự.')
        if not re.fullmatch(r'[A-Za-z0-9_]+', username):
            raise forms.ValidationError(
                'Tên đăng nhập không được chứa ký tự đặc biệt hoặc dấu tiếng Việt.'
            )
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Username đã tồn tại. Vui lòng nhập tên đăng nhập khác.')
        return username

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone:
            validate_phone(phone)
        return phone

    def clean_student_id(self):
        student_id = self.cleaned_data.get('student_id', '').strip()
        if Student.objects.filter(student_id=student_id).exists():
            raise forms.ValidationError('Mã học sinh đã tồn tại.')
        return student_id

    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data['username'],
            password=f"{data['username']}@123",
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
    last_name = forms.CharField(max_length=150, label='Họ học sinh')
    first_name = forms.CharField(max_length=150, label='Tên học sinh')
    phone = forms.CharField(max_length=20, required=False, label='Số điện thoại')
    email = forms.EmailField(required=False, label='Email')
    date_of_birth = forms.DateField(required=False, label='Ngày sinh',
                                    widget=forms.DateInput(attrs={'type': 'date'}))
    address = forms.CharField(required=False, max_length=200, label='Địa chỉ')

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone:
            validate_phone(phone)
        return phone



# --- FORM LỊCH HỌC & BÀI TẬP ---

class ScheduleForm(forms.ModelForm):
    class_obj = forms.ModelChoiceField(queryset=Class.objects.all(), required=False)

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
        room = cleaned_data.get('room')
        day = cleaned_data.get('day_of_week')
        class_obj = cleaned_data.get('class_obj')

        if start and end and end <= start:
            raise forms.ValidationError('Giờ kết thúc phải lớn hơn giờ bắt đầu.')

        if room and day and start and end:
            conflict = Schedule.objects.filter(day_of_week=day, room__iexact=room)
            if class_obj:
                conflict = conflict.exclude(class_obj=class_obj)
            for s in conflict:
                if max(start, s.start_time) < min(end, s.end_time):
                    raise forms.ValidationError(f'Phòng {room} đã có lớp {s.class_obj.name} đăng ký trong thời gian này.')

        return cleaned_data


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
        if not (5 <= len(title) <= 255):
            raise forms.ValidationError('Tiêu đề bài tập phải từ 5 đến 255 ký tự.')
        return title

    def clean_description(self):
        description = self.cleaned_data.get('description', '')
        if len(description) > 20000:
            raise forms.ValidationError('Mô tả/hướng dẫn không được vượt quá 20000 ký tự.')
        return description

    def clean_due_date(self):
        due_date = self.cleaned_data.get('due_date')
        if not due_date:
            raise forms.ValidationError('Vui lòng thiết lập mốc thời gian Hạn nộp bài.')
        if due_date <= timezone.now():
            raise forms.ValidationError('Hạn nộp bài phải lớn hơn thời gian hiện tại.')
        return due_date

    def clean_file(self):
        return validate_upload_file(self.cleaned_data.get('file'))


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
            raise forms.ValidationError('Điểm số không hợp lệ. Khung điểm chấp nhận từ 0.0 đến 10.0.')
        return grade

    def clean_feedback(self):
        feedback = self.cleaned_data.get('feedback', '')
        if len(feedback) > 1000:
            raise forms.ValidationError('Lời phê/nhận xét không được vượt quá 1000 ký tự.')
        return feedback



# --- FORM BÀI LÀM (HỌC SINH) ---

class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['file', 'note']
        widgets = {
            'note': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_file(self):
        return validate_upload_file(self.cleaned_data.get('file'))

    def clean_note(self):
        note = self.cleaned_data.get('note', '')
        if len(note) > 500:
            raise forms.ValidationError('Lời nhắn không được vượt quá 500 ký tự.')
        return note
