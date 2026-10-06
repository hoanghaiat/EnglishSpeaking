from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import (
    User, StudentProfile, TeacherProfile, ParentProfile,
    StudentLesson, Lesson, Exercise, SpeakingAttempt
)

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
        teacher_profile = user.teacher_profile
        students = teacher_profile.assigned_students.all()
        lessons = teacher_profile.lessons.all()
        return render(request, 'dashboard_teacher.html', {'students': students, 'lessons': lessons})

    elif user.role == 'student':
        student_profile = user.student_profile
        assigned_lessons = student_profile.assigned_lessons.select_related('lesson').all()
        return render(request, 'dashboard_student.html', {'student': student_profile, 'assigned_lessons': assigned_lessons})

    elif user.role == 'parent':
        parent_profile = user.parent_profile
        students = [link.student for link in parent_profile.student_links.all()]
        return render(request, 'dashboard_parent.html', {'students': students})

    return render(request, 'home.html')

@login_required
def lesson_list(request):
    user = request.user
    
    if user.role == 'admin':
        lessons = Lesson.objects.select_related('teacher__user', 'chapter__course').all()
    elif user.role == 'teacher':
        teacher_profile = user.teacher_profile
        lessons = teacher_profile.lessons.select_related('teacher__user', 'chapter__course').all()
    elif user.role == 'student':
        student_profile = user.student_profile
        # Get lessons assigned to this student
        lesson_ids = student_profile.assigned_lessons.values_list('lesson_id', flat=True)
        lessons = Lesson.objects.filter(id__in=lesson_ids).select_related('teacher__user', 'chapter__course')
    elif user.role == 'parent':
        parent_profile = user.parent_profile
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
        if lesson.teacher != user.teacher_profile:
            messages.error(request, 'You do not have permission to view this lesson.')
            return redirect('lesson_list')
    elif user.role == 'student':
        # Check if student is assigned to this lesson
        student_profile = user.student_profile
        if not StudentLesson.objects.filter(student=student_profile, lesson=lesson).exists():
            messages.error(request, 'You do not have permission to view this lesson.')
            return redirect('lesson_list')
    elif user.role == 'parent':
        # Check if parent is linked to a student who has access to this lesson
        parent_profile = user.parent_profile
        student_ids = [link.student.id for link in parent_profile.student_links.all()]
        if not StudentLesson.objects.filter(student_id__in=student_ids, lesson=lesson).exists():
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
def create_speaking_attempt(request, exercise_id):
    user = request.user
    exercise = get_object_or_404(Exercise, id=exercise_id)
    
    # Check if the user can access this exercise
    if user.role == 'student':
        student_profile = user.student_profile
        
        # Verify that the student has access to this lesson
        lesson = exercise.lesson
        if not StudentLesson.objects.filter(student=student_profile, lesson=lesson).exists():
            messages.error(request, 'You do not have permission to create an attempt for this exercise.')
            return redirect('lesson_list')
        
        # Create a new speaking attempt
        if request.method == 'POST':
            # In a real implementation, we would process the audio file here
            # For now, just create the basic structure
            speaking_attempt = SpeakingAttempt.objects.create(
                student=student_profile,
                exercise=exercise,
                transcript=request.POST.get('transcript', ''),
                feedback=request.POST.get('feedback', '')
            )
            
            messages.success(request, 'Speaking attempt created successfully!')
            return redirect('lesson_detail', lesson_id=lesson.id)
        
        context = {
            'exercise': exercise,
            'lesson': lesson
        }
        return render(request, 'create_speaking_attempt.html', context)
    
    elif user.role == 'parent':
        # Parents can't create speaking attempts directly
        messages.error(request, 'You do not have permission to create speaking attempts.')
        return redirect('dashboard')
    
    else:
        messages.error(request, 'You do not have permission to create speaking attempts.')
        return redirect('dashboard')
