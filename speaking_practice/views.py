from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone
from datetime import timedelta
from .changelog import changelog_for, log_change
from .models import (
    User, StudentProfile, TeacherProfile, ParentProfile,
    StudentLesson, Lesson, Exercise, SpeakingAttempt, Chapter,
    StudyClass,
)

# Max upload size for a recorded speaking attempt (20 MB)
MAX_AUDIO_UPLOAD_BYTES = 20 * 1024 * 1024

# Mirrors Lesson.title max_length; SQLite does not enforce varchar limits,
# so validate server-side to stay compatible with PostgreSQL.
MAX_TITLE_LENGTH = 200


def _profile_or_none(user, relation):
    """Return user.<relation> or None when the profile does not exist."""
    try:
        return getattr(user, relation)
    except ObjectDoesNotExist:
        return None


@login_required
def home(request):
    return render(request, 'home.html', {
        'stat_students': StudentProfile.objects.count(),
        'stat_lessons': Lesson.objects.count(),
        'stat_attempts': SpeakingAttempt.objects.count(),
    })


@login_required
def dashboard(request):
    user = request.user

    if user.role == 'admin':
        context = {
            'user_count': User.objects.count(),
            'student_count': StudentProfile.objects.count(),
            'teacher_count': TeacherProfile.objects.count(),
            'parent_count': ParentProfile.objects.count(),
            'class_count': StudyClass.objects.count(),
            'changelog': changelog_for(user, limit=15),
        }
        return render(request, 'dashboard_admin.html', context)

    elif user.role == 'teacher':
        teacher_profile = _profile_or_none(user, 'teacher_profile')
        if teacher_profile is None:
            messages.error(request, 'Teacher profile not found. Please contact an administrator.')
            return redirect('home')
        students = StudentProfile.objects.filter(
            assigned_teachers__teacher=teacher_profile
        ).distinct()
        lessons = teacher_profile.lessons.all()
        return render(request, 'dashboard_teacher.html', {
            'students': students,
            'lessons': lessons,
            'class_count': StudyClass.objects.filter(
                teacher=teacher_profile).count(),
            'changelog': changelog_for(user, limit=10),
        })

    elif user.role == 'student':
        student_profile = _profile_or_none(user, 'student_profile')
        if student_profile is None:
            messages.error(request, 'Student profile not found. Please contact an administrator.')
            return redirect('home')
        assigned_lessons = student_profile.assigned_lessons.select_related('lesson').all()
        recent_attempts = SpeakingAttempt.objects.filter(
            student=student_profile).select_related(
                'exercise__lesson').order_by('-created_at')[:5]
        # Attempts per day for the last 7 days (for the weekly chart).
        today = timezone.localdate()
        vn_weekdays = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']
        week_activity = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            count = SpeakingAttempt.objects.filter(
                student=student_profile, created_at__date=day).count()
            week_activity.append({
                'label': vn_weekdays[day.weekday()],
                'count': count,
                'is_today': i == 0,
            })
        max_count = max([d['count'] for d in week_activity] + [1])
        for d in week_activity:
            d['height'] = round(d['count'] / max_count * 100)
        return render(request, 'dashboard_student.html', {
            'student': student_profile,
            'assigned_lessons': assigned_lessons,
            'attempt_count': SpeakingAttempt.objects.filter(
                student=student_profile).count(),
            'recent_attempts': recent_attempts,
            'week_activity': week_activity,
        })

    elif user.role == 'parent':
        parent_profile = _profile_or_none(user, 'parent_profile')
        if parent_profile is None:
            messages.error(request, 'Parent profile not found. Please contact an administrator.')
            return redirect('home')
        students = [link.student for link in parent_profile.student_links.all()]
        return render(request, 'dashboard_parent.html', {'students': students})

    messages.error(request, 'Your account has no valid role. Please contact an administrator.')
    return redirect('home')


@login_required
def lesson_list(request):
    user = request.user

    if user.role == 'admin':
        lessons = Lesson.objects.select_related('teacher__user', 'chapter__course').all()
    elif user.role == 'teacher':
        teacher_profile = _profile_or_none(user, 'teacher_profile')
        if teacher_profile is None:
            messages.error(request, 'Teacher profile not found. Please contact an administrator.')
            return redirect('home')
        lessons = teacher_profile.lessons.select_related('teacher__user', 'chapter__course').all()
    elif user.role == 'student':
        student_profile = _profile_or_none(user, 'student_profile')
        if student_profile is None:
            messages.error(request, 'Student profile not found. Please contact an administrator.')
            return redirect('home')
        # Get lessons assigned to this student
        lesson_ids = student_profile.assigned_lessons.values_list('lesson_id', flat=True)
        lessons = Lesson.objects.filter(id__in=lesson_ids).select_related('teacher__user', 'chapter__course')
    elif user.role == 'parent':
        parent_profile = _profile_or_none(user, 'parent_profile')
        if parent_profile is None:
            messages.error(request, 'Parent profile not found. Please contact an administrator.')
            return redirect('home')
        # Get lessons for children of this parent
        student_ids = [link.student.id for link in parent_profile.student_links.all()]
        lesson_ids = StudentLesson.objects.filter(student_id__in=student_ids).values_list('lesson_id', flat=True)
        lessons = Lesson.objects.filter(id__in=lesson_ids).select_related('teacher__user', 'chapter__course')
    else:
        lessons = Lesson.objects.none()

    return render(request, 'lesson_list.html', {'lessons': lessons})


@login_required
def lesson_detail(request, lesson_id):
    user = request.user
    lesson = get_object_or_404(Lesson, id=lesson_id)

    # Check permissions based on role
    if user.role == 'admin':
        pass  # Admin can access everything
    elif user.role == 'teacher':
        teacher_profile = _profile_or_none(user, 'teacher_profile')
        if teacher_profile is None or lesson.teacher != teacher_profile:
            messages.error(request, 'You do not have permission to view this lesson.')
            return redirect('lesson_list')
    elif user.role == 'student':
        # Check if student is assigned to this lesson
        student_profile = _profile_or_none(user, 'student_profile')
        if student_profile is None or not StudentLesson.objects.filter(student=student_profile, lesson=lesson).exists():
            messages.error(request, 'You do not have permission to view this lesson.')
            return redirect('lesson_list')
    elif user.role == 'parent':
        # Check if parent is linked to a student who has access to this lesson
        parent_profile = _profile_or_none(user, 'parent_profile')
        if parent_profile is None:
            messages.error(request, 'You do not have permission to view this lesson.')
            return redirect('lesson_list')
        student_ids = [link.student.id for link in parent_profile.student_links.all()]
        if not StudentLesson.objects.filter(student_id__in=student_ids, lesson=lesson).exists():
            messages.error(request, 'You do not have permission to view this lesson.')
            return redirect('lesson_list')
    else:
        messages.error(request, 'You do not have permission to view this lesson.')
        return redirect('lesson_list')

    # Get exercises for the lesson
    exercises = lesson.exercises.filter(is_active=True).order_by('order')

    context = {
        'lesson': lesson,
        'exercises': exercises,
    }

    return render(request, 'lesson_detail.html', context)


@login_required
def profile(request):
    user = request.user
    role_profile = None
    for relation in ('teacher_profile', 'student_profile', 'parent_profile'):
        role_profile = _profile_or_none(user, relation)
        if role_profile is not None:
            break

    password_form = PasswordChangeForm(user)
    for pwd_field in password_form.fields.values():
        pwd_field.widget.attrs['class'] = 'form-control'
    if request.method == 'POST' and 'change_password' in request.POST:
        password_form = PasswordChangeForm(user, request.POST)
        for pwd_field in password_form.fields.values():
            pwd_field.widget.attrs['class'] = 'form-control'
        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password has been changed.')
            return redirect('profile')
        messages.error(request, 'Please fix the errors below.')

    capabilities = {
        'admin': [
            'Management Center: manage courses, chapters, lessons, exercises',
            'Management Center: manage users, roles and accounts',
            'Management Center: manage teacher\u2013student, student\u2013parent links and lesson assignments',
            'Django admin: full access to all data',
        ],
        'teacher': [
            'Create, edit and delete own lessons',
            'View assigned students',
        ],
        'student': [
            'Browse lessons and practice speaking exercises',
            'Submit speaking attempts and track own progress',
        ],
        'parent': [
            "View linked children's practice activity",
        ],
    }.get(user.role, [])
    if user.is_staff:
        capabilities = capabilities + ['Can sign in to Django admin (/admin/)']
    if user.is_superuser:
        capabilities = capabilities + ['Superuser: unrestricted system access']

    return render(request, 'profile.html', {
        'role_profile': role_profile,
        'capabilities': capabilities,
        'password_form': password_form,
    })


@login_required
def create_speaking_attempt(request, lesson_id, exercise_id):
    user = request.user
    lesson = get_object_or_404(Lesson, id=lesson_id)
    # The exercise must belong to the lesson in the URL and be active.
    exercise = get_object_or_404(Exercise, id=exercise_id, is_active=True, lesson=lesson)

    # Only students can create speaking attempts.
    if user.role != 'student':
        messages.error(request, 'You do not have permission to create speaking attempts.')
        return redirect('dashboard')

    student_profile = _profile_or_none(user, 'student_profile')
    if student_profile is None:
        messages.error(request, 'Student profile not found. Please contact an administrator.')
        return redirect('lesson_list')

    # Verify that the student has access to this lesson
    if not StudentLesson.objects.filter(student=student_profile, lesson=lesson).exists():
        messages.error(request, 'You do not have permission to create an attempt for this exercise.')
        return redirect('lesson_list')

    if request.method == 'POST':
        audio_file = request.FILES.get('recorded_audio')
        transcript = request.POST.get('transcript', '').strip()
        if audio_file and audio_file.size > MAX_AUDIO_UPLOAD_BYTES:
            messages.error(request, 'The audio file is too large (max 20 MB).')
            return render(request, 'create_speaking_attempt.html', {'exercise': exercise, 'lesson': lesson})
        if not transcript:
            messages.error(request, 'Transcript is required.')
            return render(request, 'create_speaking_attempt.html', {'exercise': exercise, 'lesson': lesson})

        SpeakingAttempt.objects.create(
            student=student_profile,
            exercise=exercise,
            recorded_audio=audio_file,
            transcript=transcript,
            feedback=request.POST.get('feedback', '').strip(),
        )

        messages.success(request, 'Speaking attempt created successfully!')
        return redirect('lesson_detail', lesson_id=lesson.id)

    context = {
        'exercise': exercise,
        'lesson': lesson,
    }
    return render(request, 'create_speaking_attempt.html', context)


@login_required
def teacher_create_lesson(request):
    user = request.user

    # Only teachers can create lessons
    if user.role != 'teacher':
        messages.error(request, 'You do not have permission to create lessons.')
        return redirect('dashboard')

    teacher_profile = _profile_or_none(user, 'teacher_profile')
    if teacher_profile is None:
        messages.error(request, 'Teacher profile not found. Please contact an administrator.')
        return redirect('dashboard')

    chapters = Chapter.objects.filter(is_active=True).select_related('course')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        chapter_id = request.POST.get('chapter')
        order_raw = request.POST.get('order', '').strip()

        chapter = None
        if chapter_id:
            try:
                chapter = Chapter.objects.get(id=chapter_id, is_active=True)
            except (Chapter.DoesNotExist, ValueError):
                chapter = None

        error = None
        order = None
        if not title:
            error = 'Title is required.'
        elif len(title) > MAX_TITLE_LENGTH:
            error = f'Title must be at most {MAX_TITLE_LENGTH} characters.'
        elif chapter is None:
            error = 'Please select a valid chapter.'
        elif order_raw:
            try:
                order = int(order_raw)
                if order < 1:
                    raise ValueError
            except ValueError:
                error = 'Order must be a positive whole number.'

        if error is None:
            if order is None:
                # Auto-assign the next available order within the chapter.
                max_order = Lesson.objects.filter(chapter=chapter).aggregate(Max('order'))['order__max'] or 0
                order = max_order + 1
            elif Lesson.objects.filter(chapter=chapter, order=order).exists():
                error = f'Order {order} is already used in this chapter. Please choose another order.'

        if error is None:
            try:
                # The inner atomic block rolls back to a savepoint on
                # IntegrityError so the outer transaction stays usable.
                with transaction.atomic():
                    lesson = Lesson.objects.create(
                        title=title,
                        description=description,
                        teacher=teacher_profile,
                        chapter=chapter,
                        order=order,
                    )
            except IntegrityError:
                error = f'Order {order} is already used in this chapter. Please choose another order.'
            else:
                log_change(request.user, 'content', 'create',
                           f"{request.user.username} created lesson "
                           f"'{lesson.title}'.")
                messages.success(request, 'Lesson created successfully!')
                return redirect('lesson_detail', lesson_id=lesson.id)

        messages.error(request, error)
        return render(request, 'teacher_create_lesson.html', {
            'chapters': chapters,
            'form_title': title,
            'form_description': description,
            'form_chapter_id': chapter_id,
            'form_order': order_raw,
        })

    return render(request, 'teacher_create_lesson.html', {'chapters': chapters})


@login_required
def teacher_edit_lesson(request, lesson_id):
    user = request.user

    # Only teachers can edit lessons
    if user.role != 'teacher':
        messages.error(request, 'You do not have permission to edit lessons.')
        return redirect('dashboard')

    lesson = get_object_or_404(Lesson, id=lesson_id)

    # Check that this teacher owns the lesson
    teacher_profile = _profile_or_none(user, 'teacher_profile')
    if teacher_profile is None or lesson.teacher != teacher_profile:
        messages.error(request, 'You do not have permission to edit this lesson.')
        return redirect('dashboard')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, 'Title is required.')
            return render(request, 'teacher_edit_lesson.html', {'lesson': lesson})
        if len(title) > MAX_TITLE_LENGTH:
            messages.error(request, f'Title must be at most {MAX_TITLE_LENGTH} characters.')
            return render(request, 'teacher_edit_lesson.html', {'lesson': lesson})

        lesson.title = title
        lesson.description = request.POST.get('description', '').strip()
        lesson.save()

        log_change(request.user, 'content', 'update',
                   f"{request.user.username} updated lesson "
                   f"'{lesson.title}'.")
        messages.success(request, 'Lesson updated successfully!')
        return redirect('lesson_detail', lesson_id=lesson.id)

    context = {
        'lesson': lesson
    }
    return render(request, 'teacher_edit_lesson.html', context)


@login_required
def teacher_delete_lesson(request, lesson_id):
    user = request.user

    # Only teachers can delete lessons
    if user.role != 'teacher':
        messages.error(request, 'You do not have permission to delete lessons.')
        return redirect('dashboard')

    lesson = get_object_or_404(Lesson, id=lesson_id)

    # Check that this teacher owns the lesson
    teacher_profile = _profile_or_none(user, 'teacher_profile')
    if teacher_profile is None or lesson.teacher != teacher_profile:
        messages.error(request, 'You do not have permission to delete this lesson.')
        return redirect('dashboard')

    if request.method == 'POST':
        title = lesson.title
        lesson.delete()
        log_change(request.user, 'content', 'delete',
                   f"{request.user.username} deleted lesson '{title}'.")
        messages.success(request, 'Lesson deleted successfully!')
        return redirect('lesson_list')

    context = {
        'lesson': lesson
    }
    return render(request, 'teacher_delete_lesson.html', context)
