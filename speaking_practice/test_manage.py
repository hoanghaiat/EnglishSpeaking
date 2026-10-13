"""Tests for the admin-only Learning Content Manager (manage/content/)."""
from django.test import TestCase
from django.urls import reverse

from .models import (
    Chapter,
    Course,
    Exercise,
    Lesson,
    ParentProfile,
    StudentProfile,
    TeacherProfile,
    User,
)


def make_user(username, role, **kwargs):
    return User.objects.create_user(
        username=username, password='pw123456', role=role, **kwargs)


class ManageContentAccessTests(TestCase):
    def setUp(self):
        self.admin = make_user('m_adm', 'admin', is_staff=True, is_superuser=True)
        self.teacher = make_user('m_tch', 'teacher')
        self.teacher_profile = TeacherProfile.objects.create(user=self.teacher)
        self.student = make_user('m_stu', 'student')
        StudentProfile.objects.create(user=self.student)
        self.parent = make_user('m_par', 'parent')
        ParentProfile.objects.create(user=self.parent)

        self.course = Course.objects.create(title='MC Course')
        self.chapter = Chapter.objects.create(course=self.course, title='MC Chapter', order=1)
        self.lesson = Lesson.objects.create(
            chapter=self.chapter, teacher=self.teacher_profile,
            title='MC Lesson', order=1)
        self.exercise = Exercise.objects.create(
            lesson=self.lesson, title='MC Exercise', order=1)

        self.hub_url = reverse('manage_content')

    def test_anonymous_redirected_to_login(self):
        r = self.client.get(self.hub_url)
        self.assertEqual(r.status_code, 302)
        self.assertIn('/accounts/login/', r.url)

    def test_teacher_forbidden(self):
        self.client.force_login(self.teacher)
        r = self.client.get(self.hub_url)
        self.assertRedirects(r, reverse('dashboard'))

    def test_student_forbidden(self):
        self.client.force_login(self.student)
        r = self.client.get(self.hub_url)
        self.assertRedirects(r, reverse('dashboard'))

    def test_parent_forbidden(self):
        self.client.force_login(self.parent)
        r = self.client.get(self.hub_url)
        self.assertRedirects(r, reverse('dashboard'))

    def test_teacher_cannot_post_add(self):
        self.client.force_login(self.teacher)
        r = self.client.post(
            reverse('manage_add', kwargs={'model_name': 'course'}),
            {'title': 'Sneaky', 'description': ''})
        self.assertRedirects(r, reverse('dashboard'))
        self.assertFalse(Course.objects.filter(title='Sneaky').exists())

    def test_admin_sees_full_tree(self):
        self.client.force_login(self.admin)
        r = self.client.get(self.hub_url)
        self.assertEqual(r.status_code, 200)
        for text in ['MC Course', 'MC Chapter', 'MC Lesson', 'MC Exercise']:
            self.assertContains(r, text)

    def test_admin_app_index_links_to_hub(self):
        self.client.force_login(self.admin)
        r = self.client.get('/admin/speaking_practice/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.hub_url)

    def test_admin_app_index_shows_overview(self):
        self.client.force_login(self.admin)
        r = self.client.get('/admin/speaking_practice/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('esp_stats', r.context)
        self.assertEqual(r.context['esp_stats']['courses'], 1)
        self.assertEqual(r.context['esp_stats']['lessons'], 1)
        # lively overview, not the duplicated group cards
        self.assertContains(r, 'Quick actions')
        self.assertContains(r, 'Latest speaking attempts')
        self.assertNotContains(r, 'Links &amp; practice')


class ManageContentCrudTests(TestCase):
    def setUp(self):
        self.admin = make_user('c_adm', 'admin', is_staff=True, is_superuser=True)
        self.client.force_login(self.admin)
        self.course = Course.objects.create(title='C Course')
        self.chapter = Chapter.objects.create(course=self.course, title='C Chapter', order=1)
        self.lesson = Lesson.objects.create(chapter=self.chapter, title='C Lesson', order=1)
        self.exercise = Exercise.objects.create(lesson=self.lesson, title='C Exercise', order=1)
        self.hub_url = reverse('manage_content')

    def test_add_course(self):
        r = self.client.post(
            reverse('manage_add', kwargs={'model_name': 'course'}),
            {'title': 'Brand New Course', 'description': 'Desc'})
        self.assertRedirects(r, self.hub_url)
        self.assertTrue(Course.objects.filter(title='Brand New Course').exists())

    def test_add_course_invalid_shows_errors(self):
        r = self.client.post(
            reverse('manage_add', kwargs={'model_name': 'course'}),
            {'title': '', 'description': ''})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Course.objects.count(), 1)  # nothing created

    def test_add_chapter_prefills_parent_and_next_order(self):
        url = reverse('manage_add', kwargs={'model_name': 'chapter'})
        r = self.client.get(url + f'?course={self.course.pk}')
        self.assertEqual(r.status_code, 200)
        form = r.context['form']
        self.assertEqual(form.initial['course'], self.course.pk)
        self.assertEqual(form.initial['order'], 2)

    def test_add_chapter_post(self):
        r = self.client.post(
            reverse('manage_add', kwargs={'model_name': 'chapter'}),
            {'course': self.course.pk, 'title': 'Second Chapter', 'order': 2})
        self.assertRedirects(r, self.hub_url)
        ch = Chapter.objects.get(title='Second Chapter')
        self.assertEqual(ch.course, self.course)
        self.assertEqual(ch.order, 2)

    def test_edit_lesson(self):
        url = reverse('manage_edit', kwargs={'model_name': 'lesson', 'pk': self.lesson.pk})
        r = self.client.post(url, {
            'chapter': self.chapter.pk, 'title': 'Renamed Lesson',
            'description': '', 'order': 1})
        self.assertRedirects(r, self.hub_url)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, 'Renamed Lesson')

    def test_delete_exercise(self):
        url = reverse('manage_delete', kwargs={'model_name': 'exercise', 'pk': self.exercise.pk})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Delete Exercise')
        r = self.client.post(url)
        self.assertRedirects(r, self.hub_url)
        self.assertFalse(Exercise.objects.filter(pk=self.exercise.pk).exists())

    def test_delete_course_warns_about_cascade(self):
        url = reverse('manage_delete', kwargs={'model_name': 'course', 'pk': self.course.pk})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'chapter(s)')
        self.assertContains(r, 'lesson(s)')

    def test_invalid_model_name_404(self):
        for url in [
            reverse('manage_add', kwargs={'model_name': 'nope'}),
            reverse('manage_edit', kwargs={'model_name': 'nope', 'pk': 1}),
            reverse('manage_delete', kwargs={'model_name': 'nope', 'pk': 1}),
        ]:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 404)

    def test_edit_missing_object_404(self):
        url = reverse('manage_edit', kwargs={'model_name': 'course', 'pk': 99999})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)
