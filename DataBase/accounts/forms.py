import re
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User, UserProfile, Student

class LoginForm(AuthenticationForm):
    """Form đăng nhập tùy chỉnh với style Bootstrap 5"""
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Tên đăng nhập', 'autofocus': True
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Mật khẩu'
    }))

class StudentAddForm(forms.ModelForm):
    """Form để Admin thêm học sinh mới"""
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Mật khẩu")
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"]) # Băm mật khẩu
        user.role = 'student' # Cố định vai trò là học sinh
        if commit:
            user.save()
        return user

class UserProfileForm(forms.ModelForm):
    """Form cập nhật thông tin cá nhân cơ bản"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone and not re.match(r'^\d+$', phone):
            raise forms.ValidationError("Số điện thoại chỉ được chứa các chữ số.")
        return phone

class UserExtraInfoForm(forms.ModelForm):
    """Form cập nhật thông tin bổ sung (Địa chỉ, Ngày sinh)"""
    class Meta:
        model = UserProfile
        fields = ['address', 'date_of_birth']
        widgets = {
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

class PasswordUpdateForm(forms.Form):
    """Form xử lý đổi mật khẩu theo yêu cầu nghiệp vụ BR_PASSWORD_CHANGE"""
    old_password = forms.CharField(
        label="Mật khẩu cũ",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nhập mật khẩu hiện tại'})
    )
    new_password = forms.CharField(
        label="Mật khẩu mới",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nhập mật khẩu mới'})
    )
    confirm_password = forms.CharField(
        label="Xác nhận mật khẩu mới",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nhập lại mật khẩu mới'})
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError("Mật khẩu mới và xác nhận mật khẩu không khớp.")
        
        if new_password and len(new_password) < 6:
            raise forms.ValidationError("Mật khẩu mới phải có ít nhất 6 ký tự.")
            
        return cleaned_data

class StudentManageForm(forms.ModelForm):
    """Form quản lý học sinh dùng cho cả thêm và sửa"""
    student_code = forms.CharField(label="Mã định danh học sinh", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ví dụ: HS2024-001'}))
    password = forms.CharField(label="Mật khẩu truy cập", required=False, widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nhập mật khẩu mới hoặc để trống'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_student_code(self):
        code = self.cleaned_data.get('student_code')
        # Kiểm tra trùng mã học sinh (loại trừ học sinh hiện tại nếu đang edit)
        qs = Student.objects.filter(student_code=code)
        if self.instance.pk:
            qs = qs.exclude(user=self.instance)
        if qs.exists():
            raise forms.ValidationError("Mã học sinh đã tồn tại trong hệ thống.")
        return code

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'student'
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
            # Tạo hoặc cập nhật Student profile
            Student.objects.update_or_create(user=user, defaults={'student_code': self.cleaned_data.get('student_code')})
        return user