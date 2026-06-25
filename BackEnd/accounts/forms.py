import re
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User, UserProfile, Student


# =====================================================================
# COMMON RULES (according to PTYC)
# =====================================================================
def validate_strong_password(password):
    """
    Validate password strength according to constraints.
    """
    if not (8 <= len(password) <= 50):
        raise forms.ValidationError("Password must be between 8 and 50 characters long.")
    if not re.search(r'[A-Z]', password):
        raise forms.ValidationError("Password must contain at least one uppercase letter.")
    if not re.search(r'\d', password):
        raise forms.ValidationError("Password must contain at least one digit.")
    if not re.search(r'[^A-Za-z0-9]', password):
        raise forms.ValidationError("Password must contain at least one special character (@, #, !, ...).")


def validate_phone_number(phone):
    """Validate phone number constraint."""
    if not re.fullmatch(r'0\d{9}', phone):
        raise forms.ValidationError("Phone number must contain exactly 10 digits and start with 0.")


# =====================================================================
# LOGIN
# =====================================================================
class LoginForm(AuthenticationForm):
    """Custom login form with Bootstrap 5 styling."""
    username = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Username', 'autofocus': True,
            'minlength': '3', 'maxlength': '30',
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 'placeholder': 'Password',
            'minlength': '8',
        }),
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        if not re.match(r'^[A-Za-z0-9_]+$', username):
            raise forms.ValidationError(
                "Username can only contain letters, numbers, and underscores (no spaces or special characters)."
            )
        return username


# =====================================================================
# PERSONAL PROFILE
# =====================================================================
class UserProfileForm(forms.ModelForm):
    """Form to update basic personal info (User model)."""
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
        if phone:  # Phone number is not required for profile updates, but if entered it must match the format
            validate_phone_number(phone)
        return phone


class UserExtraInfoForm(forms.ModelForm):
    """Form for extra profile info from UserProfile."""
    class Meta:
        model = UserProfile
        fields = ['address', 'date_of_birth']
        widgets = {
            'address':       forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2,
                'placeholder': 'House number, street, district, city',
                'maxlength': '200',  # PTYC: MaxLength=200
            }),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


# =====================================================================
# CHANGE PASSWORD
# =====================================================================
class PasswordUpdateForm(forms.Form):
    """Form for updating password."""
    old_password = forms.CharField(
        label="Old password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 'placeholder': 'Enter current password',
        }),
    )
    new_password = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 'placeholder': 'At least 8 chars, 1 uppercase, 1 digit, 1 special',
        }),
    )
    confirm_password = forms.CharField(
        label="Confirm new password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 'placeholder': 'Confirm new password',
        }),
    )

    def clean_new_password(self):
        new_password = self.cleaned_data.get('new_password', '')
        validate_strong_password(new_password)
        return new_password

    def clean(self):
        cleaned_data = super().clean()
        new_password    = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError("New password and confirmation password do not match.")
        return cleaned_data


# =====================================================================
# STUDENT MANAGEMENT (Admin)
# =====================================================================
class StudentAddForm(forms.ModelForm):
    """Form for Admin to add new student (deprecated — use StudentManageForm instead)."""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Password",
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
    """Form to manage students."""
    student_code = forms.CharField(
        label="Student code",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. HS2026-001'}),
    )
    password = forms.CharField(
        label="Password",
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Leave blank to keep current password',
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

    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        if not (3 <= len(username) <= 30):
            raise forms.ValidationError("Username must be between 3 and 30 characters long.")
        if not re.match(r'^[A-Za-z0-9_]+$', username):
            raise forms.ValidationError(
                "Username can only contain letters, numbers, and underscores (no spaces or special characters)."
            )
        return username

    def clean_phone_number(self):
        phone = (self.cleaned_data.get('phone_number') or '').strip()
        if phone:
            validate_phone_number(phone)
        return phone

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        if password:  # Only validate if a new password is provided
            validate_strong_password(password)
        return password

    def clean_student_code(self):
        code = self.cleaned_data.get('student_code')
        qs = Student.objects.filter(student_code=code)
        if self.instance.pk:
            qs = qs.exclude(user=self.instance)
        if qs.exists():
            raise forms.ValidationError("Student code already exists in the system.")
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
# FORGOT PASSWORD (OTP)
# =====================================================================
class ForgotPasswordForm(forms.Form):
    """UC01-C: Forgot password with phone + simulated OTP."""
    phone = forms.CharField(
        label="Phone number",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Registered phone number (10 digits, starts with 0)',
            'maxlength': '10',
        }),
    )
    otp = forms.CharField(
        label="OTP Code", required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Enter 6 digits',
            'maxlength': '6',
        }),
    )
    new_password = forms.CharField(
        label="New password", required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'At least 8 chars, 1 uppercase, 1 digit, 1 special',
        }),
    )
    confirm_password = forms.CharField(
        label="Confirm new password", required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        validate_phone_number(phone)
        return phone