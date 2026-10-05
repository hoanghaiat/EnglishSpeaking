from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import StudentProfile, TeacherProfile, ParentProfile

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
        # Get assigned students
        teacher_profile = user.teacher_profile
        students = teacher_profile.assigned_students.all()
        
        context = {
            'students': students,
        }
        return render(request, 'dashboard_teacher.html', context)
    
    elif user.role == 'student':
        # Get assigned lessons for the student
        student_profile = user.student_profile
        context = {
            'student': student_profile,
        }
        return render(request, 'dashboard_student.html', context)
    
    elif user.role == 'parent':
        # Get children of this parent
        parent_profile = user.parent_profile
        students = [link.student for link in parent_profile.student_links.all()]
        
        context = {
            'students': students,
        }
        return render(request, 'dashboard_parent.html', context)
    
    else:
        return render(request, 'dashboard.html')

@login_required
def lesson_list(request):
    # This will be implemented later with proper filtering based on user role
    return render(request, 'lesson_list.html')

@login_required
def lesson_detail(request, lesson_id):
    # This will be implemented later
    return render(request, 'lesson_detail.html')

@login_required
def profile(request):
    return render(request, 'profile.html')
