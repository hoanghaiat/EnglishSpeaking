from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django.db.models import Max
from .models import (
    User, StudentProfile, TeacherProfile, ParentProfile,
    StudentLesson, Lesson, Exercise, SpeakingAttempt, Chapter
)

# Max upload size for a recorded speaking attempt (20 MB)
MAX_AUDIO_UPLOAD_BYTES = 20 * 1024 * 1024


def _profile_or_none(user, relation):
    """Return user.<relation> or None when the profile does not exist."""
    try:
        return getattr(user, relation)
    except ObjectDoesNotExist:
        return None


@login_required
def home(request):
    return render(request, 'home.html')


@login_required
def dashboard(request):
    user = request.user

    if user.role == 'admin':
        context = {
            'user_count': User.objects.count(),
            'student_count': StudentProfile.objects.count(),
            'teacher_count': TeacherProfile.objects.count(),
            'parent_count': ParentProfile.objects.count(),
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
        return render(request, 'dashboard_teacher.html', {'students': students, 'lessons': lessons})

    elif user.role == 'student':
        student_profile = _profile_or_none(user, 'student_profile')
        if student_profile is None:
            messages.error(request, 'Student profile not found. Please contact an administrator.')
            return redirect('home')
        assigned_lessons = student_profile.assigned_lessons.select_related('lesson').all()
        return render(request, 'dashboard_student.html', {'student': student_profile, 'assigned_lessons': assigned_lessons})

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
    return render(request, 'profile.html')


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
        if audio_file and audio_file.size > MAX_AUDIO_UPLOAD_BYTES:
            messages.error(request, 'The audio file is too large (max 20 MB).')
            return render(request, 'create_speaking_attempt.html', {'exercise': exercise, 'lesson': lesson})

        SpeakingAttempt.objects.create(
            student=student_profile,
            exercise=exercise,
            recorded_audio=audio_file,
            transcript=request.POST.get('transcript', '').strip(),
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

        lesson.title = title
        lesson.description = request.POST.get('description', '').strip()
        lesson.save()

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
        lesson.delete()
        messages.success(request, 'Lesson deleted successfully!')
        return redirect('lesson_list')

    context = {
        'lesson': lesson
    }
    return render(request, 'teacher_delete_lesson.html', context)
