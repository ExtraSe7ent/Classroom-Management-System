import re
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User, UserProfile, Student

class LoginForm(AuthenticationForm):
    """Custom login form with Bootstrap 5 style"""
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Login name', 'autofocus': True
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Password'
    }))

class StudentAddForm(forms.ModelForm):
    """Form for Admin to add new students"""
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Password")
    
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
        user.set_password(self.cleaned_data["password"]) # Hash the password
        user.role = 'student' # Fixed role as student
        if commit:
            user.save()
        return user

class UserProfileForm(forms.ModelForm):
    """Form to update basic personal information"""
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
            raise forms.ValidationError("Phone numbers must contain only digits.")
        return phone

class UserExtraInfoForm(forms.ModelForm):
    """Form to update additional information (Address, Date of Birth)"""
    class Meta:
        model = UserProfile
        fields = ['address', 'date_of_birth']
        widgets = {
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

class PasswordUpdateForm(forms.Form):
    """Form to process password change according to business requirements BR_PASSWORD_CHANGE"""
    old_password = forms.CharField(
        label="Old password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter current password'})
    )
    new_password = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter a new password'})
    )
    confirm_password = forms.CharField(
        label="Confirm new password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Re-enter the new password'})
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError("New password and confirm password do not match.")
        
        if new_password and len(new_password) < 6:
            raise forms.ValidationError("The new password must have at least 6 characters.")
            
        return cleaned_data

class StudentManageForm(forms.ModelForm):
    """Student management form is used for both adding and editing"""
    student_code = forms.CharField(label="Student identification code", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'For example: HS2024-001'}))
    password = forms.CharField(label="Access password", required=False, widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter a new password or leave it blank'}))

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
        # Check for duplicate student codes (exclude current students if editing)
        qs = Student.objects.filter(student_code=code)
        if self.instance.pk:
            qs = qs.exclude(user=self.instance)
        if qs.exists():
            raise forms.ValidationError("The student code already exists in the system.")
        return code

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'student'
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
            # Create or update Student profile
            Student.objects.update_or_create(user=user, defaults={'student_code': self.cleaned_data.get('student_code')})
        return user