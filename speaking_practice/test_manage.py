"""Tests for the Management Center (manage/) and its modal CRUD."""
from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from .models import (
    Chapter,
    Course,
    Exercise,
    Lesson,
    ParentProfile,
    SpeakingAttempt,
    StudentLesson,
    StudentParent,
    StudentProfile,
    TeacherProfile,
    TeacherStudent,
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

        self.hub_url = reverse('manage_center')

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

    def test_admin_pages_load_brand_theme(self):
        self.client.force_login(self.admin)
        for url in ('/admin/', '/admin/speaking_practice/',
                    '/admin/speaking_practice/teacherstudent/'):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200)
            self.assertContains(r, 'css/admin-theme.css')

    def test_admin_header_redesigned(self):
        self.client.force_login(self.admin)
        r = self.client.get('/admin/speaking_practice/')
        self.assertContains(r, 'esp-user-chip')
        self.assertContains(r, 'esp-utool')
        self.assertContains(r, 'logout-form')

    def test_admin_popup_centering_js_present(self):
        self.client.force_login(self.admin)
        r = self.client.get('/admin/')
        self.assertContains(r, 'js/admin-ux.js')
        js_path = settings.BASE_DIR / 'static' / 'js' / 'admin-ux.js'
        self.assertIn('/* ESP: center admin popups */', js_path.read_text())

    def test_manage_add_modal_returns_fragment(self):
        self.client.force_login(self.admin)
        r = self.client.get('/manage/lesson/add/?modal=1',
                            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'data-esp-modal-form')
        self.assertNotContains(r, 'id="esp-modal"')

    def test_manage_add_modal_post_valid_returns_json(self):
        self.client.force_login(self.admin)
        r = self.client.post(
            '/manage/lesson/add/?modal=1',
            {'title': 'Modal Test Lesson', 'chapter': self.chapter.pk,
             'order': 50, 'is_active': 'on'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/json')
        self.assertEqual(r.json(), {'ok': True})
        self.assertTrue(Lesson.objects.filter(title='Modal Test Lesson').exists())

    def test_manage_add_modal_post_invalid_returns_html(self):
        self.client.force_login(self.admin)
        r = self.client.post(
            '/manage/lesson/add/?modal=1',
            {'title': '', 'chapter': self.chapter.pk},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 200)
        self.assertNotEqual(r['Content-Type'], 'application/json')
        self.assertContains(r, 'data-esp-modal-form')

    def test_manage_delete_modal_post_returns_json(self):
        self.client.force_login(self.admin)
        lesson = Lesson.objects.create(
            title='Delete Me', chapter=self.chapter, order=51)
        r = self.client.post(
            f'/manage/lesson/{lesson.pk}/delete/?modal=1',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {'ok': True})
        self.assertFalse(Lesson.objects.filter(pk=lesson.pk).exists())

    def test_manage_add_full_page_still_works(self):
        # Without the modal flag the classic full-page flow is unchanged.
        self.client.force_login(self.admin)
        r = self.client.get('/manage/lesson/add/')
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, 'data-esp-modal-form')

    def test_old_content_url_redirects_to_center(self):
        self.client.force_login(self.admin)
        r = self.client.get('/manage/content/')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, '/manage/')

    def test_center_has_three_tabs(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('manage_center'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'id="mgmtTabs"')
        self.assertContains(r, 'Learning Content')
        self.assertContains(r, 'id="pane-people"')
        self.assertContains(r, 'id="pane-links"')
        self.assertContains(r, 'Recent Speaking Attempts')

    def test_center_forbidden_for_non_admin(self):
        self.client.force_login(self.teacher)
        r = self.client.get(reverse('manage_center'))
        self.assertEqual(r.status_code, 302)

    def test_admin_logout_goes_straight_to_login(self):
        self.client.force_login(self.admin)
        r = self.client.post('/admin/logout/')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, '/admin/login/')
        # No intermediate "Logged out" page anymore.
        r = self.client.get('/admin/logout/')
        self.assertEqual(r.status_code, 302)

    def test_admin_login_has_remember_me(self):
        r = self.client.get('/admin/login/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'name="remember_me"')

    def test_admin_login_remember_me_controls_session_expiry(self):
        # Unchecked -> session expires when the browser closes.
        self.client.post('/admin/login/',
                         {'username': 'm_adm', 'password': 'pw123456'})
        self.assertEqual(self.client.session.get('_session_expiry'), 0)
        self.client.logout()
        # Checked -> persistent session.
        self.client.post('/admin/login/',
                         {'username': 'm_adm', 'password': 'pw123456',
                          'remember_me': 'on'})
        self.assertEqual(
            self.client.session.get('_session_expiry'),
            settings.SESSION_COOKIE_AGE)

    def test_admin_unified_header(self):
        self.client.force_login(self.admin)
        r = self.client.get('/admin/speaking_practice/teacherstudent/')
        self.assertContains(r, 'id="esp-topnav"')
        self.assertContains(r, 'My Dashboard')
        self.assertContains(r, 'Management')
        self.assertContains(r, 'esp-user-chip')
        # The old Django admin header is gone.
        self.assertNotContains(r, 'id="user-tools"')

    def test_site_header_management_dropdown(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('manage_center'))
        self.assertContains(r, 'mgmtDropdown')
        self.assertContains(r, 'Learning Content')
        self.assertNotContains(r, '&#128218; Manage Content</a>')

    def test_site_notifications_are_toasts(self):
        self.client.get('/accounts/logout/')  # sets a "logged out" message
        r = self.client.get('/accounts/login/')
        self.assertContains(r, 'esp-toasts')
        self.assertContains(r, 'esp-toast')

    def test_home_has_no_action_buttons_for_members(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('home'))
        self.assertNotContains(r, 'Continue Practicing')
        self.assertNotContains(r, 'Browse Lessons')
        self.assertContains(r, 'Speak English with Confidence')

    def test_admin_dashboard_slimmed_down(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('dashboard'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Total Users')  # stats stay
        self.assertContains(r, 'My Account')
        self.assertNotContains(r, 'Open Content Manager')


class ManageContentCrudTests(TestCase):
    def setUp(self):
        self.admin = make_user('c_adm', 'admin', is_staff=True, is_superuser=True)
        self.client.force_login(self.admin)
        self.course = Course.objects.create(title='C Course')
        self.chapter = Chapter.objects.create(course=self.course, title='C Chapter', order=1)
        self.lesson = Lesson.objects.create(chapter=self.chapter, title='C Lesson', order=1)
        self.exercise = Exercise.objects.create(lesson=self.lesson, title='C Exercise', order=1)
        self.hub_url = reverse('manage_center')

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


class ManagePeopleTests(TestCase):
    """People tab: user add/edit/delete through the modal CRUD."""

    def setUp(self):
        self.admin = make_user('p_adm', 'admin', is_staff=True, is_superuser=True)
        self.client.force_login(self.admin)

    def _add_url(self):
        return reverse('manage_add', kwargs={'model_name': 'user'})

    def test_add_user_creates_matching_profile(self):
        r = self.client.post(self._add_url(), {
            'username': 'p_new_teacher',
            'password1': 'pw12345678', 'password2': 'pw12345678',
            'role': 'teacher', 'email': 't@example.com',
            'first_name': 'New', 'last_name': 'Teacher',
            'phone_number': '0123', 'is_active': 'on',
        })
        self.assertRedirects(r, reverse('manage_center'))
        user = User.objects.get(username='p_new_teacher')
        self.assertTrue(user.check_password('pw12345678'))
        self.assertTrue(hasattr(user, 'teacher_profile'))

    def test_add_user_password_mismatch(self):
        r = self.client.post(self._add_url() + '?modal=1', {
            'username': 'p_bad', 'password1': 'pw12345678',
            'password2': 'different', 'role': 'student',
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "don&#x27;t match")
        self.assertFalse(User.objects.filter(username='p_bad').exists())

    def test_edit_user_role_creates_new_profile(self):
        student = make_user('p_stu', 'student')
        StudentProfile.objects.create(user=student)
        url = reverse('manage_edit', kwargs={'model_name': 'user', 'pk': student.pk})
        r = self.client.post(url, {
            'role': 'teacher', 'email': '', 'first_name': '',
            'last_name': '', 'phone_number': '', 'is_active': 'on',
        })
        self.assertRedirects(r, reverse('manage_center'))
        student.refresh_from_db()
        self.assertEqual(student.role, 'teacher')
        self.assertTrue(hasattr(student, 'teacher_profile'))

    def test_admin_cannot_delete_self(self):
        url = reverse('manage_delete',
                      kwargs={'model_name': 'user', 'pk': self.admin.pk})
        r = self.client.post(url)
        self.assertRedirects(r, reverse('manage_center'))
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_admin_cannot_remove_own_admin_access(self):
        url = reverse('manage_edit',
                      kwargs={'model_name': 'user', 'pk': self.admin.pk})
        r = self.client.post(url, {
            'role': 'student', 'email': '', 'first_name': '',
            'last_name': '', 'phone_number': '', 'is_active': 'on',
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'own admin access')
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, 'admin')

    def test_delete_user_modal(self):
        victim = make_user('p_victim', 'student')
        StudentProfile.objects.create(user=victim)
        url = reverse('manage_delete', kwargs={'model_name': 'user', 'pk': victim.pk})
        r = self.client.get(url + '?modal=1',
                            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertContains(r, 'student profile')
        r = self.client.post(url + '?modal=1',
                             HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.json(), {'ok': True})
        self.assertFalse(User.objects.filter(pk=victim.pk).exists())

    def test_people_crud_requires_admin(self):
        teacher = make_user('p_tch2', 'teacher')
        self.client.force_login(teacher)
        self.assertEqual(self.client.get(self._add_url()).status_code, 302)


class ManageLinksTests(TestCase):
    """Links & Practice tab: link add/delete through the modal CRUD."""

    def setUp(self):
        self.admin = make_user('l_adm', 'admin', is_staff=True, is_superuser=True)
        self.client.force_login(self.admin)
        self.teacher = make_user('l_tch', 'teacher')
        self.teacher_profile = TeacherProfile.objects.create(user=self.teacher)
        self.student = make_user('l_stu', 'student')
        self.student_profile = StudentProfile.objects.create(user=self.student)
        self.parent = make_user('l_par', 'parent')
        self.parent_profile = ParentProfile.objects.create(user=self.parent)
        course = Course.objects.create(title='L Course')
        chapter = Chapter.objects.create(course=course, title='L Ch', order=1)
        self.lesson = Lesson.objects.create(chapter=chapter, title='L Lesson', order=1)
        self.exercise = Exercise.objects.create(
            lesson=self.lesson, title='L Ex', order=1)

    def test_add_teacher_student_link(self):
        url = reverse('manage_add', kwargs={'model_name': 'teacherstudent'})
        r = self.client.post(url + '?modal=1', {
            'teacher': self.teacher_profile.pk,
            'student': self.student_profile.pk,
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.json(), {'ok': True})
        self.assertTrue(TeacherStudent.objects.filter(
            teacher=self.teacher_profile, student=self.student_profile).exists())

    def test_duplicate_teacher_student_link_rejected(self):
        TeacherStudent.objects.create(
            teacher=self.teacher_profile, student=self.student_profile)
        url = reverse('manage_add', kwargs={'model_name': 'teacherstudent'})
        r = self.client.post(url + '?modal=1', {
            'teacher': self.teacher_profile.pk,
            'student': self.student_profile.pk,
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'already exists')

    def test_delete_teacher_student_link(self):
        link = TeacherStudent.objects.create(
            teacher=self.teacher_profile, student=self.student_profile)
        url = reverse('manage_delete',
                      kwargs={'model_name': 'teacherstudent', 'pk': link.pk})
        r = self.client.post(url + '?modal=1',
                             HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.json(), {'ok': True})
        self.assertFalse(TeacherStudent.objects.filter(pk=link.pk).exists())

    def test_add_and_delete_student_parent_link(self):
        add = reverse('manage_add', kwargs={'model_name': 'studentparent'})
        r = self.client.post(add, {
            'student': self.student_profile.pk,
            'parent': self.parent_profile.pk,
            'relationship_type': 'Mother',
        })
        self.assertRedirects(r, reverse('manage_center'))
        link = StudentParent.objects.get(student=self.student_profile)
        self.assertEqual(link.relationship_type, 'Mother')
        delete = reverse('manage_delete',
                         kwargs={'model_name': 'studentparent', 'pk': link.pk})
        self.client.post(delete)
        self.assertFalse(StudentParent.objects.filter(pk=link.pk).exists())

    def test_add_and_delete_student_lesson(self):
        add = reverse('manage_add', kwargs={'model_name': 'studentlesson'})
        r = self.client.post(add, {
            'student': self.student_profile.pk, 'lesson': self.lesson.pk,
        })
        self.assertRedirects(r, reverse('manage_center'))
        link = StudentLesson.objects.get(student=self.student_profile)
        delete = reverse('manage_delete',
                         kwargs={'model_name': 'studentlesson', 'pk': link.pk})
        r = self.client.post(delete + '?modal=1',
                             HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.json(), {'ok': True})
        self.assertFalse(StudentLesson.objects.filter(pk=link.pk).exists())

    def test_attempt_cannot_be_added_but_can_be_deleted(self):
        attempt = SpeakingAttempt.objects.create(
            student=self.student_profile, exercise=self.exercise,
            transcript='hello')
        add = reverse('manage_add', kwargs={'model_name': 'speakingattempt'})
        self.assertEqual(self.client.get(add).status_code, 404)
        delete = reverse('manage_delete',
                         kwargs={'model_name': 'speakingattempt', 'pk': attempt.pk})
        r = self.client.post(delete)
        self.assertRedirects(r, reverse('manage_center'))
        self.assertFalse(SpeakingAttempt.objects.filter(pk=attempt.pk).exists())

    def test_center_shows_links_and_attempts(self):
        TeacherStudent.objects.create(
            teacher=self.teacher_profile, student=self.student_profile)
        SpeakingAttempt.objects.create(
            student=self.student_profile, exercise=self.exercise,
            transcript='hi')
        r = self.client.get(reverse('manage_center'))
        self.assertContains(r, 'l_tch')
        self.assertContains(r, 'Recent Speaking Attempts')
