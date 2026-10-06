from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from .models import StudentProfile, TeacherProfile, ParentProfile

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Ensure the user is active before logging in
            if user.is_active:
                login(request, user)
                messages.success(request, 'Login successful!')
                return redirect('dashboard')
            else:
                messages.error(request, 'Account is disabled.')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'registration/login.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')

def signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()

            user.email = request.POST.get('email', '').strip()
            role = request.POST.get('role')

            if role in ['student', 'teacher', 'parent']:
                user.role = role
                user.save()

                # Create appropriate profile based on role
                if role == 'student':
                    StudentProfile.objects.create(user=user)
                elif role == 'teacher':
                    TeacherProfile.objects.create(user=user)
                elif role == 'parent':
                    ParentProfile.objects.create(user=user)

            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('dashboard')
    else:
        form = UserCreationForm()

    return render(request, 'registration/signup.html', {'form': form})
