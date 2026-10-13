from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    UserCreationForm as BaseUserCreationForm,
    UserChangeForm as BaseUserChangeForm,
)

User = get_user_model()

# 'admin' is intentionally excluded: admin accounts are created by existing
# admins / createsuperuser, never through public signup.
SIGNUP_ROLE_CHOICES = [
    ('student', 'Student'),
    ('teacher', 'Teacher'),
    ('parent', 'Parent'),
]


class CustomUserCreationForm(BaseUserCreationForm):
    """
    Signup form bound to the project's custom User model.

    NOTE: Django's built-in UserCreationForm hard-codes
    django.contrib.auth.models.User, which is broken when a custom
    AUTH_USER_MODEL is in use. Always use this form instead.
    """

    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=SIGNUP_ROLE_CHOICES, required=True)

    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'role')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.role = self.cleaned_data['role']
        if commit:
            user.save()
        return user


class CustomUserChangeForm(BaseUserChangeForm):
    """User change form bound to the project's custom User model."""

    class Meta(BaseUserChangeForm.Meta):
        model = User
