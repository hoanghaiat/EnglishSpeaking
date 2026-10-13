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


# ---------------------------------------------------------------------------
# Content management forms (used by the admin-only Content Manager pages).
# ---------------------------------------------------------------------------
from .models import Course, Chapter, Lesson, Exercise, TeacherProfile  # noqa: E402


class _BootstrapModelForm(forms.ModelForm):
    """ModelForm that applies Bootstrap 5 classes to its widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            css = widget.attrs.get('class', '')
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs['class'] = (css + ' form-check-input').strip()
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs['class'] = (css + ' form-select').strip()
            else:
                widget.attrs['class'] = (css + ' form-control').strip()


class CourseForm(_BootstrapModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'is_active']
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}


class ChapterForm(_BootstrapModelForm):
    class Meta:
        model = Chapter
        fields = ['course', 'title', 'description', 'order', 'is_active']
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}


class LessonForm(_BootstrapModelForm):
    class Meta:
        model = Lesson
        fields = ['chapter', 'title', 'description', 'teacher', 'order', 'is_active']
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teacher'].queryset = TeacherProfile.objects.select_related('user')
        self.fields['teacher'].required = False


class ExerciseForm(_BootstrapModelForm):
    class Meta:
        model = Exercise
        fields = [
            'lesson', 'title', 'description', 'instructions', 'expected_text',
            'reference_audio', 'image', 'order', 'is_active',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'instructions': forms.Textarea(attrs={'rows': 3}),
            'expected_text': forms.Textarea(attrs={'rows': 3}),
        }
