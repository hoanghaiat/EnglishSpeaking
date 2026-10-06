from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, TeacherProfile, StudentProfile, ParentProfile,
    StudentParent, Course, Chapter, Lesson, Exercise,
    TeacherStudent, SpeakingAttempt, StudentLesson
)

class CustomUserAdmin(UserAdmin):
    """
    Custom admin for the User model.
    """
    list_display = ('username', 'email', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Role', {'fields': ('role',)}),
        ('Additional Info', {'fields': ('phone_number',)}),
    )

admin.site.register(User, CustomUserAdmin)

@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    search_fields = ('user__username', 'user__email')

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'grade_level', 'created_at')
    search_fields = ('user__username', 'user__email')

@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    search_fields = ('user__username', 'user__email')

@admin.register(StudentParent)
class StudentParentAdmin(admin.ModelAdmin):
    list_display = ('student', 'parent', 'relationship_type')
    list_filter = ('relationship_type',)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')

@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'is_active')
    list_filter = ('course', 'is_active', 'created_at')

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'chapter', 'order', 'is_active')
    list_filter = ('teacher', 'chapter', 'is_active', 'created_at')

@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ('title', 'lesson', 'order', 'is_active')
    list_filter = ('lesson', 'is_active', 'created_at')

@admin.register(TeacherStudent)
class TeacherStudentAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'student', 'assigned_at')
    list_filter = ('assigned_at',)

@admin.register(StudentLesson)
class StudentLessonAdmin(admin.ModelAdmin):
    list_display = ('student', 'lesson', 'assigned_at')
    list_filter = ('assigned_at',)

@admin.register(SpeakingAttempt)
class SpeakingAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'exercise', 'created_at')
    list_filter = ('created_at',)
