from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.models import Group

class User(AbstractUser):
    """
    Custom User model with role-based access control.
    """
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('parent', 'Parent'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    
    def __str__(self):
        return f"{self.username} ({self.role})"

class TeacherProfile(models.Model):
    """
    Profile model for teachers.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    bio = models.TextField(blank=True, null=True)
    qualifications = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Teacher: {self.user.username}"

class StudentProfile(models.Model):
    """
    Profile model for students.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    date_of_birth = models.DateField(blank=True, null=True)
    grade_level = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Student: {self.user.username}"

class ParentProfile(models.Model):
    """
    Profile model for parents.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='parent_profile')
    relationship_to_child = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Parent: {self.user.username}"

class StudentParent(models.Model):
    """
    Through model to link students and parents.
    """
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='parent_links')
    parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, related_name='student_links')
    relationship_type = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        unique_together = ('student', 'parent')

    def __str__(self):
        return f"{self.student.user.username} - {self.parent.user.username}"

class Course(models.Model):
    """
    A course that contains chapters.
    """
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title

class Chapter(models.Model):
    """
    A chapter within a course.
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='chapters')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        unique_together = ('course', 'order')

    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Lesson(models.Model):
    """
    A lesson within a chapter.
    """
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        unique_together = ('chapter', 'order')

    def __str__(self):
        return f"{self.chapter.title} - {self.title}"

class Exercise(models.Model):
    """
    An exercise within a lesson.
    """
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='exercises')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    instructions = models.TextField(blank=True, null=True)
    expected_text = models.TextField(blank=True, null=True)
    reference_audio = models.FileField(upload_to='reference_audios/', blank=True, null=True)
    image = models.ImageField(upload_to='exercise_images/', blank=True, null=True)
    order = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        unique_together = ('lesson', 'order')

    def __str__(self):
        return f"{self.lesson.title} - {self.title}"

class TeacherStudent(models.Model):
    """
    Through model to link teachers and students.
    """
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='assigned_students')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='assigned_teachers')
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('teacher', 'student')

    def __str__(self):
        return f"{self.teacher.user.username} - {self.student.user.username}"

class SpeakingAttempt(models.Model):
    """
    A speaking attempt by a student for an exercise.
    """
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='speaking_attempts')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='speaking_attempts')
    recorded_audio = models.FileField(upload_to='recorded_audios/', blank=True, null=True)
    transcript = models.TextField(blank=True, null=True)
    grammar_score = models.FloatField(blank=True, null=True)
    pronunciation_score = models.FloatField(blank=True, null=True)
    fluency_score = models.FloatField(blank=True, null=True)
    accuracy_score = models.FloatField(blank=True, null=True)
    total_score = models.FloatField(blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.user.username} - {self.exercise.title}"
