from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    UserCreationForm as BaseUserCreationForm,
    UserChangeForm as BaseUserChangeForm,
)
from django.db.models import Q

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
from .models import (
    Course, Chapter, Lesson, Exercise, TeacherProfile, StudentProfile,
    ParentProfile, TeacherStudent, StudentParent, StudentLesson,
    StudyClass,
)  # noqa: E402


class _BootstrapModelForm(forms.ModelForm):
    """ModelForm that applies Bootstrap 5 classes to its widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            css = widget.attrs.get('class', '')
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs['class'] = (css + ' form-check-input').strip()
            elif isinstance(widget, forms.CheckboxSelectMultiple):
                # Marker for the checklist branch in _form_fields.html.
                # Sub-inputs inherit attrs (option_inherits_attrs).
                widget.is_esp_checklist = True
                widget.attrs['class'] = (css + ' form-check-input').strip()
            elif isinstance(widget, forms.RadioSelect):
                # Marker for the radiogroup branch in _form_fields.html.
                # (The class must NOT land on the group container div.)
                widget.is_esp_radiogroup = True
                widget.attrs['class'] = (css + ' form-check-input').strip()
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs['class'] = (css + ' form-select').strip()
            else:
                widget.attrs['class'] = (css + ' form-control').strip()
            if name == 'is_active':
                field.label = 'Active'


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
        help_texts = {
            'order': 'Display order inside the course: 1, 2, 3\u2026 appear top to bottom.',
        }


class LessonForm(_BootstrapModelForm):
    class Meta:
        model = Lesson
        fields = ['chapter', 'title', 'description', 'teacher', 'order', 'is_active']
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}
        help_texts = {
            'order': 'Display order inside the chapter: 1, 2, 3\u2026 appear top to bottom.',
        }

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
        help_texts = {
            'order': 'Display order inside the lesson: 1, 2, 3\u2026 appear top to bottom.',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'instructions': forms.Textarea(attrs={'rows': 3}),
            'expected_text': forms.Textarea(attrs={'rows': 3}),
        }


# ---------------------------------------------------------------------------
# Management Center forms: People (users) and Links & Practice.
# ---------------------------------------------------------------------------
from django.contrib.auth.password_validation import validate_password  # noqa: E402

PROFILE_MODELS = {
    'teacher': TeacherProfile,
    'student': StudentProfile,
    'parent': ParentProfile,
}


def ensure_profile(user):
    """Create the matching profile for the user's role when missing."""
    model = PROFILE_MODELS.get(user.role)
    if model is not None:
        model.objects.get_or_create(user=user)


class ManagedUserCreateForm(_BootstrapModelForm):
    """Admin-only user creation inside the Management Center."""

    password1 = forms.CharField(
        label='Password', widget=forms.PasswordInput,
        help_text='Minimum 6 characters.')
    password2 = forms.CharField(
        label='Confirm password', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'role', 'email', 'first_name', 'last_name',
                  'phone_number', 'is_active']

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("The two passwords don't match.")
        validate_password(p2, self.instance)
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
            ensure_profile(user)
        return user


class ManagedUserEditForm(_BootstrapModelForm):
    """Admin-only user edit (password changes stay in Django admin)."""

    class Meta:
        model = User
        fields = ['role', 'email', 'first_name', 'last_name',
                  'phone_number', 'is_active']

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            ensure_profile(user)
        return user


def _own_students(teacher_profile):
    return StudentProfile.objects.filter(
        assigned_teachers__teacher=teacher_profile
    ).distinct().select_related('user').order_by('user__username')


class TeacherStudentForm(_BootstrapModelForm):
    class Meta:
        model = TeacherStudent
        fields = ['teacher', 'student']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teacher'].queryset = TeacherProfile.objects.select_related(
            'user').order_by('user__username')
        self.fields['student'].queryset = StudentProfile.objects.select_related(
            'user').order_by('user__username')


class StudentParentForm(_BootstrapModelForm):
    class Meta:
        model = StudentParent
        fields = ['student', 'parent', 'relationship_type']

    def __init__(self, *args, teacher_profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        if teacher_profile is not None:
            own = _own_students(teacher_profile)
            self.fields['student'].queryset = own
            self.fields['parent'].queryset = ParentProfile.objects.filter(
                Q(student_links__student__in=own)
                | Q(student_links__isnull=True)
            ).select_related('user').distinct().order_by('user__username')
        else:
            self.fields['student'].queryset = StudentProfile.objects.select_related(
                'user').order_by('user__username')
            self.fields['parent'].queryset = ParentProfile.objects.select_related(
                'user').order_by('user__username')

    def clean(self):
        cleaned = super().clean()
        student = cleaned.get('student')
        if student is not None:
            existing = StudentParent.objects.filter(student=student)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.count() >= 2:
                raise forms.ValidationError(
                    'A student can be linked to at most 2 parents.')
        return cleaned


class StudentLessonForm(_BootstrapModelForm):
    class Meta:
        model = StudentLesson
        fields = ['student', 'lesson']

    def __init__(self, *args, teacher_profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        if teacher_profile is not None:
            self.fields['student'].queryset = _own_students(teacher_profile)
        else:
            self.fields['student'].queryset = StudentProfile.objects.select_related(
                'user').order_by('user__username')
        self.fields['lesson'].queryset = Lesson.objects.select_related(
            'chapter__course').order_by('chapter__course__title',
                                        'chapter__order', 'order')


class StudyClassForm(_BootstrapModelForm):
    """Create / edit a study class. The student queryset is scoped by the view."""

    class Meta:
        model = StudyClass
        fields = ['name', 'students']
        widgets = {'students': forms.CheckboxSelectMultiple}

    def __init__(self, *args, teacher_profile=None, is_admin=False, **kwargs):
        super().__init__(*args, **kwargs)
        if is_admin:
            teacher_field = forms.ModelChoiceField(
                queryset=TeacherProfile.objects.select_related(
                    'user').order_by('user__username'),
                widget=forms.Select(attrs={'class': 'form-select'}),
                label='Teacher')
            self.fields = {'teacher': teacher_field, **self.fields}
            self.fields['students'].queryset = (
                StudentProfile.objects.select_related('user')
                .order_by('user__username'))
        else:
            self.fields['students'].queryset = _own_students(teacher_profile)
        self.fields['students'].required = False
        if is_admin and self.instance and self.instance.pk:
            # Show the previously chosen teacher instead of a blank dropdown.
            self.fields['teacher'].initial = self.instance.teacher_id

    def _get_validation_exclusions(self):
        # 'teacher' is set by the view (teachers), not by a form field, so
        # keep it in unique validation: names must be unique per teacher.
        # But when the teacher field itself failed form validation (e.g. left
        # empty), leave it excluded so the model doesn't pile a technical
        # "cannot be null" error on top of the form's own message.
        exclude = super()._get_validation_exclusions()
        if 'teacher' not in self._errors:
            exclude.discard('teacher')
        return exclude


class AssignLessonsForm(forms.Form):
    """Assign one lesson to a whole class or to individually picked students."""

    TARGET_CHOICES = [('class', 'Whole class'), ('students', 'Individual students')]

    lesson = forms.ModelChoiceField(
        queryset=Lesson.objects.select_related(
            'chapter__course').order_by('chapter__course__title',
                                       'chapter__order', 'order'),
        widget=forms.Select(attrs={'class': 'form-select'}))
    target = forms.ChoiceField(
        choices=TARGET_CHOICES, initial='class',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}))
    study_class = forms.ModelChoiceField(
        queryset=StudyClass.objects.none(), required=False,
        widget=forms.Select(attrs={'class': 'form-select'}))
    students = forms.ModelMultipleChoiceField(
        queryset=StudentProfile.objects.none(), required=False,
        widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, teacher_profile=None, is_admin=False, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendering markers for _form_fields.html (plain Form, not _BootstrapModelForm).
        self.fields['target'].widget.is_esp_radiogroup = True
        self.fields['students'].widget.is_esp_checklist = True
        if is_admin:
            classes = StudyClass.objects.select_related(
                'teacher__user').order_by('name')
            students = StudentProfile.objects.select_related(
                'user').order_by('user__username')
        else:
            classes = StudyClass.objects.filter(
                teacher=teacher_profile).order_by('name')
            students = StudentProfile.objects.filter(
                assigned_teachers__teacher=teacher_profile
            ).select_related('user').distinct().order_by('user__username')
        self.fields['study_class'].queryset = classes
        self.fields['students'].queryset = students

    def clean(self):
        cleaned = super().clean()
        target = cleaned.get('target')
        if target == 'class' and not cleaned.get('study_class'):
            self.add_error('study_class', 'Pick a class to assign the lesson to.')
        if target == 'students' and not cleaned.get('students'):
            self.add_error('students', 'Pick at least one student.')
        return cleaned
