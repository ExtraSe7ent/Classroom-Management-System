import re
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User, UserProfile, Student


# =====================================================================
# QUY TẮC DÙNG CHUNG (theo PTYC)
# =====================================================================
def validate_strong_password(password):
    """
    Mật khẩu hợp lệ theo PTYC: dài 8–50, ít nhất 1 chữ hoa, 1 chữ số, 1 ký tự đặc biệt.
    Dùng chung cho cả ForgotPasswordView và PasswordUpdateForm.
    """
    if not (8 <= len(password) <= 50):
        raise forms.ValidationError("Mật khẩu phải dài từ 8 đến 50 ký tự.")
    if not re.search(r'[A-Z]', password):
        raise forms.ValidationError("Mật khẩu phải có ít nhất 1 chữ in hoa.")
    if not re.search(r'\d', password):
        raise forms.ValidationError("Mật khẩu phải có ít nhất 1 chữ số.")
    if not re.search(r'[^A-Za-z0-9]', password):
        raise forms.ValidationError("Mật khẩu phải có ít nhất 1 ký tự đặc biệt (@, #, !, ...).")


def validate_phone_number(phone):
    """Số điện thoại hợp lệ theo PTYC: đúng 10 số, bắt đầu bằng 0."""
    if not re.fullmatch(r'0\d{9}', phone):
        raise forms.ValidationError("Số điện thoại phải gồm đúng 10 chữ số và bắt đầu bằng số 0.")


# =====================================================================
# ĐĂNG NHẬP
# =====================================================================
class LoginForm(AuthenticationForm):
    """Form đăng nhập tùy chỉnh với style Bootstrap 5."""
    username = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Tên đăng nhập', 'autofocus': True,
            'minlength': '3', 'maxlength': '30',
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 'placeholder': 'Mật khẩu',
            'minlength': '8',
        }),
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        if not re.match(r'^[A-Za-z0-9_]+$', username):
            raise forms.ValidationError(
                "Tên đăng nhập chỉ được chứa chữ cái, chữ số và dấu gạch dưới (không dấu tiếng Việt, không ký tự đặc biệt)."
            )
        return username


# =====================================================================
# HỒ SƠ CÁ NHÂN
# =====================================================================
class UserProfileForm(forms.ModelForm):
    """Form cập nhật thông tin cá nhân cơ bản (User model)."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'avatar']
        widgets = {
            'first_name':    forms.TextInput(attrs={'class': 'form-control', 'maxlength': '150'}),
            'last_name':     forms.TextInput(attrs={'class': 'form-control', 'maxlength': '150'}),
            'email':         forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0xxxxxxxxx', 'maxlength': '10'}),
            'avatar':        forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def clean_phone_number(self):
        phone = (self.cleaned_data.get('phone_number') or '').strip()
        if phone:  # SĐT không bắt buộc khi cập nhật profile, nhưng nếu nhập phải đúng định dạng
            validate_phone_number(phone)
        return phone


class UserExtraInfoForm(forms.ModelForm):
    """Form cập nhật thông tin bổ sung (Nơi ở, Ngày sinh) từ bảng UserProfile."""
    class Meta:
        model = UserProfile
        fields = ['address', 'date_of_birth']
        widgets = {
            'address':       forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2,
                'placeholder': 'Số nhà, đường, quận/huyện, tỉnh/thành phố',
                'maxlength': '200',  # PTYC: MaxLength=200
            }),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


# =====================================================================
# ĐỔI MẬT KHẨU
# =====================================================================
class PasswordUpdateForm(forms.Form):
    """Form đổi mật khẩu — áp dụng đúng quy tắc mật khẩu mạnh theo PTYC."""
    old_password = forms.CharField(
        label="Mật khẩu cũ",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 'placeholder': 'Nhập mật khẩu hiện tại',
        }),
    )
    new_password = forms.CharField(
        label="Mật khẩu mới",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 'placeholder': 'Ít nhất 8 ký tự, 1 hoa, 1 số, 1 ký tự đặc biệt',
        }),
    )
    confirm_password = forms.CharField(
        label="Xác nhận mật khẩu mới",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 'placeholder': 'Nhập lại mật khẩu mới',
        }),
    )

    def clean_new_password(self):
        """Áp dụng đúng quy tắc mật khẩu mạnh (8–50 ký tự, 1 hoa, 1 số, 1 ký tự đặc biệt)."""
        new_password = self.cleaned_data.get('new_password', '')
        validate_strong_password(new_password)
        return new_password

    def clean(self):
        cleaned_data = super().clean()
        new_password    = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError("Mật khẩu mới và xác nhận mật khẩu không khớp.")
        return cleaned_data


# =====================================================================
# QUẢN LÝ HỌC SINH (Admin)
# =====================================================================
class StudentAddForm(forms.ModelForm):
    """Form để Admin thêm học sinh mới (deprecated — dùng StudentManageForm)."""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Mật khẩu",
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'password']
        widgets = {
            'username':     forms.TextInput(attrs={'class': 'form-control'}),
            'first_name':   forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':    forms.TextInput(attrs={'class': 'form-control'}),
            'email':        forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_password(self):
        validate_strong_password(self.cleaned_data.get('password', ''))
        return self.cleaned_data['password']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = 'student'
        if commit:
            user.save()
        return user


class StudentManageForm(forms.ModelForm):
    """Form quản lý học sinh — dùng cho cả thêm (Create) và sửa (Update)."""
    student_code = forms.CharField(
        label="Mã định danh học sinh",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ví dụ: HS2024-001'}),
    )
    password = forms.CharField(
        label="Mật khẩu truy cập",
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Để trống nếu không đổi mật khẩu',
        }),
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number']
        widgets = {
            'username':     forms.TextInput(attrs={'class': 'form-control', 'maxlength': '30'}),
            'first_name':   forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':    forms.TextInput(attrs={'class': 'form-control'}),
            'email':        forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0xxxxxxxxx', 'maxlength': '10'}),
        }

    def clean_phone_number(self):
        phone = (self.cleaned_data.get('phone_number') or '').strip()
        if phone:
            validate_phone_number(phone)
        return phone

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        if password:  # Chỉ validate nếu có nhập mật khẩu mới
            validate_strong_password(password)
        return password

    def clean_student_code(self):
        code = self.cleaned_data.get('student_code')
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
            Student.objects.update_or_create(
                user=user,
                defaults={'student_code': self.cleaned_data.get('student_code')},
            )
        return user


# =====================================================================
# QUÊN MẬT KHẨU (OTP)
# =====================================================================
class ForgotPasswordForm(forms.Form):
    """UC01-C: Quên mật khẩu bằng SĐT + mã OTP (OTP mô phỏng cho bản demo local)."""
    phone = forms.CharField(
        label="Số điện thoại",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'SĐT đã đăng ký (10 số, bắt đầu bằng 0)',
            'maxlength': '10',
        }),
    )
    otp = forms.CharField(
        label="Mã OTP", required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Nhập 6 chữ số',
            'maxlength': '6',
        }),
    )
    new_password = forms.CharField(
        label="Mật khẩu mới", required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ít nhất 8 ký tự, 1 hoa, 1 số, 1 ký tự đặc biệt',
        }),
    )
    confirm_password = forms.CharField(
        label="Nhập lại mật khẩu mới", required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        validate_phone_number(phone)
        return phone