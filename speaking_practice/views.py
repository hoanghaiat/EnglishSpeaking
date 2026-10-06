from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import User, StudentProfile, TeacherProfile, ParentProfile

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
        return render(request, 'dashboard_teacher.html', {'students': students})

    elif user.role == 'student':
        student_profile = user.student_profile
        return render(request, 'dashboard_student.html', {'student': student_profile})

    elif user.role == 'parent':
        parent_profile = user.parent_profile
        students = [link.student for link in parent_profile.student_links.all()]
        return render(request, 'dashboard_parent.html', {'students': students})

    return render(request, 'home.html')

@login_required
def lesson_list(request):
    return render(request, 'lesson_list.html')

@login_required
def lesson_detail(request, lesson_id):
    return render(request, 'lesson_detail.html')

@login_required
def profile(request):
    return render(request, 'profile.html')