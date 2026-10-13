from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from .models import (
    User, StudentProfile, TeacherProfile, ParentProfile,
    Course, Chapter, Lesson, Exercise, StudentLesson,
    TeacherStudent, SpeakingAttempt,
)

User = get_user_model()


def make_user(username, role, password='testpass123'):
    user = User.objects.create_user(username=username, password=password, role=role)
    if role == 'student':
        StudentProfile.objects.create(user=user)
    elif role == 'teacher':
        TeacherProfile.objects.create(user=user)
    elif role == 'parent':
        ParentProfile.objects.create(user=user)
    return user


def make_lesson(teacher_profile=None, order=1):
    course = Course.objects.create(title='Course 1')
    chapter = Chapter.objects.create(course=course, title='Chapter 1', order=1)
    return Lesson.objects.create(
        chapter=chapter, teacher=teacher_profile, title='Lesson 1', order=order
    )


class UserModelTest(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='student'
        )
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpass123'))
        self.assertEqual(user.role, 'student')


class SignupTest(TestCase):
    def test_signup_invalid_role_does_not_create_broken_user(self):
        response = self.client.post(reverse('signup'), {
            'username': 'norole',
            'email': 'norole@example.com',
            'password1': 'strongpass123',
            'password2': 'strongpass123',
            'role': 'hacker',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='norole').exists())

    def test_signup_valid_role_creates_profile(self):
        response = self.client.post(reverse('signup'), {
            'username': 'newstudent',
            'email': 'newstudent@example.com',
            'password1': 'strongpass123',
            'password2': 'strongpass123',
            'role': 'student',
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username='newstudent')
        self.assertEqual(user.role, 'student')
        self.assertTrue(StudentProfile.objects.filter(user=user).exists())


class DashboardTest(TestCase):
    def test_dashboard_without_profile_redirects_instead_of_500(self):
        # A teacher user with no TeacherProfile must not crash the dashboard.
        user = User.objects.create_user(username='lonely', password='testpass123', role='teacher')
        self.client.force_login(user)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_admin_dashboard_renders(self):
        admin = User.objects.create_superuser(
            username='boss', password='testpass123', role='admin', email='boss@example.com'
        )
        self.client.force_login(admin)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Total Users')


class TeacherLessonTest(TestCase):
    def setUp(self):
        self.teacher = make_user('teacher1', 'teacher')
        self.client.force_login(self.teacher)
        self.chapter = Chapter.objects.create(
            course=Course.objects.create(title='C'), title='Ch', order=1
        )

    def test_create_lesson_without_order_auto_assigns(self):
        response = self.client.post(reverse('teacher_create_lesson'), {
            'title': 'Auto Order Lesson',
            'description': 'desc',
            'chapter': str(self.chapter.id),
            'order': '',
        })
        lesson = Lesson.objects.get(title='Auto Order Lesson')
        self.assertEqual(lesson.order, 1)
        self.assertEqual(response.status_code, 302)

    def test_create_lesson_invalid_order_shows_error(self):
        response = self.client.post(reverse('teacher_create_lesson'), {
            'title': 'Bad Order Lesson',
            'description': 'desc',
            'chapter': str(self.chapter.id),
            'order': 'not-a-number',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Lesson.objects.filter(title='Bad Order Lesson').exists())

    def test_create_lesson_duplicate_order_shows_error(self):
        Lesson.objects.create(
            chapter=self.chapter, teacher=self.teacher.teacher_profile,
            title='Existing', order=1,
        )
        response = self.client.post(reverse('teacher_create_lesson'), {
            'title': 'Duplicate',
            'description': 'desc',
            'chapter': str(self.chapter.id),
            'order': '1',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Lesson.objects.filter(title='Duplicate').exists())

    def test_student_cannot_create_lesson(self):
        student = make_user('studentx', 'student')
        self.client.force_login(student)
        response = self.client.post(reverse('teacher_create_lesson'), {
            'title': 'Nope', 'chapter': str(self.chapter.id), 'order': '1',
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Lesson.objects.filter(title='Nope').exists())


class LessonPermissionTest(TestCase):
    def setUp(self):
        self.teacher = make_user('t1', 'teacher')
        self.student = make_user('s1', 'student')
        self.lesson = make_lesson(self.teacher.teacher_profile)

    def test_unassigned_student_cannot_view_lesson(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('lesson_detail', args=[self.lesson.id]))
        self.assertEqual(response.status_code, 302)

    def test_assigned_student_can_view_lesson(self):
        StudentLesson.objects.create(
            student=self.student.student_profile, lesson=self.lesson
        )
        self.client.force_login(self.student)
        response = self.client.get(reverse('lesson_detail', args=[self.lesson.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.lesson.title)

    def test_other_teacher_cannot_view_lesson(self):
        other = make_user('t2', 'teacher')
        self.client.force_login(other)
        response = self.client.get(reverse('lesson_detail', args=[self.lesson.id]))
        self.assertEqual(response.status_code, 302)


class AdminTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='root', password='testpass123',
            role='admin', email='root@example.com',
        )
        self.client.force_login(self.admin)

    def test_admin_add_user_page_renders(self):
        # Regression test: on Django 5.x, inheriting UserAdmin.add_fieldsets
        # (which references 'usable_password') crashed this page with
        # FieldError: Unknown field(s) (usable_password).
        response = self.client.get('/admin/speaking_practice/user/add/')
        self.assertEqual(response.status_code, 200)

    def test_admin_can_create_user_with_role(self):
        response = self.client.post('/admin/speaking_practice/user/add/', {
            'username': 'newteacher',
            'email': 'newteacher@example.com',
            'password1': 'StrongPass123',
            'password2': 'StrongPass123',
            'role': 'teacher',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            User.objects.filter(username='newteacher', role='teacher').exists()
        )


class SpeakingAttemptTest(TestCase):
    def setUp(self):
        self.teacher = make_user('t1', 'teacher')
        self.student = make_user('s1', 'student')
        self.lesson = make_lesson(self.teacher.teacher_profile)
        self.exercise = Exercise.objects.create(
            lesson=self.lesson, title='Ex 1', order=1, is_active=True
        )
        StudentLesson.objects.create(
            student=self.student.student_profile, lesson=self.lesson
        )

    def test_exercise_lesson_mismatch_returns_404(self):
        other_lesson = make_lesson(self.teacher.teacher_profile, order=2)
        self.client.force_login(self.student)
        url = reverse('create_speaking_attempt', args=[other_lesson.id, self.exercise.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_student_can_create_attempt(self):
        self.client.force_login(self.student)
        url = reverse('create_speaking_attempt', args=[self.lesson.id, self.exercise.id])
        response = self.client.post(url, {'transcript': 'hello world'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            SpeakingAttempt.objects.filter(
                student=self.student.student_profile, exercise=self.exercise
            ).exists()
        )

    def test_teacher_cannot_create_attempt(self):
        self.client.force_login(self.teacher)
        url = reverse('create_speaking_attempt', args=[self.lesson.id, self.exercise.id])
        response = self.client.post(url, {'transcript': 'hello'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SpeakingAttempt.objects.exists())
