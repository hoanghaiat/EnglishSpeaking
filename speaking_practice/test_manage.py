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
    StudyClass,
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

    def test_teacher_allowed_scoped(self):
        # Teachers get scoped access: classes inside Links & Practice,
        # no Learning Content tab.
        self.client.force_login(self.teacher)
        r = self.client.get(self.hub_url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Links &amp; Practice')
        self.assertContains(r, 'classes-card')
        self.assertNotContains(r, 'id="pane-learning"')

    def test_teacher_cannot_touch_content_models(self):
        self.client.force_login(self.teacher)
        r = self.client.post(
            reverse('manage_add', kwargs={'model_name': 'course'}),
            {'title': 'Nope'})
        self.assertRedirects(r, reverse('manage_center'))

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
            {'title': 'Nope 2'})
        self.assertRedirects(r, reverse('manage_center'))

    def test_admin_sees_full_tree(self):
        self.client.force_login(self.admin)
        r = self.client.get(self.hub_url)
        self.assertEqual(r.status_code, 200)
        for text in ['MC Course', 'MC Chapter', 'MC Lesson', 'MC Exercise']:
            self.assertContains(r, text)

    def test_admin_app_index_redirects_to_management_center(self):
        self.client.force_login(self.admin)
        r = self.client.get('/admin/speaking_practice/')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, reverse('manage_center'))

    def test_admin_pages_load_brand_theme(self):
        self.client.force_login(self.admin)
        for url in ('/admin/', '/admin/speaking_practice/teacherstudent/'):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200)
            self.assertContains(r, 'css/admin-theme.css')
        # The retired app overview redirects to the Management Center.
        r = self.client.get('/admin/speaking_practice/')
        self.assertEqual(r.status_code, 302)

    def test_admin_header_redesigned(self):
        self.client.force_login(self.admin)
        r = self.client.get('/admin/speaking_practice/teacherstudent/')
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

    def test_center_forbidden_for_non_manager(self):
        # Teachers now get scoped access; students/parents are still out.
        self.client.force_login(self.teacher)
        r = self.client.get(reverse('manage_center'))
        self.assertEqual(r.status_code, 200)
        self.client.force_login(self.student)
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

    def test_site_header_management_link(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('manage_center'))
        self.assertContains(r, '&#128218; Management</a>')
        self.assertNotContains(r, 'mgmtDropdown')
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
        self.assertContains(r, 'Change History')  # replaces My Account
        self.assertNotContains(r, 'Open Content Manager')
        self.assertNotContains(r, 'Student Practice Status')


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


class ManageClassesTests(TestCase):
    def setUp(self):
        self.admin = make_user('cl_adm', 'admin', is_staff=True, is_superuser=True)
        self.teacher = make_user('cl_tch', 'teacher')
        self.teacher_profile = TeacherProfile.objects.create(user=self.teacher)
        self.other_teacher = make_user('cl_tch2', 'teacher')
        self.other_profile = TeacherProfile.objects.create(user=self.other_teacher)
        self.student = make_user('cl_stu', 'student')
        self.student_profile = StudentProfile.objects.create(user=self.student)
        TeacherStudent.objects.create(
            teacher=self.teacher_profile, student=self.student_profile)

    def test_teacher_creates_class(self):
        self.client.force_login(self.teacher)
        r = self.client.post(reverse('class_add'), {
            'name': '7/13', 'students': [self.student_profile.pk],
        })
        self.assertRedirects(r, reverse('manage_center'))
        cls = StudyClass.objects.get(name='7/13')
        self.assertEqual(cls.teacher, self.teacher_profile)
        self.assertEqual(list(cls.students.all()), [self.student_profile])

    def test_teacher_cannot_use_other_teachers_students(self):
        outsider = make_user('cl_out', 'student')
        outsider_profile = StudentProfile.objects.create(user=outsider)
        self.client.force_login(self.teacher)
        r = self.client.post(reverse('class_add'), {
            'name': '7/14', 'students': [outsider_profile.pk],
        })
        # The outsider is not a valid choice for this teacher -> form error,
        # nothing is created.
        self.assertEqual(r.status_code, 200)
        self.assertFalse(StudyClass.objects.filter(name='7/14').exists())

    def test_teacher_cannot_edit_other_teachers_class(self):
        cls = StudyClass.objects.create(
            name='X', teacher=self.other_profile)
        self.client.force_login(self.teacher)
        r = self.client.get(
            reverse('class_edit', kwargs={'pk': cls.pk}))
        self.assertRedirects(r, reverse('manage_center'))

    def test_admin_creates_class_for_any_teacher(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse('class_add'), {
            'teacher': self.teacher_profile.pk,
            'name': '8/1', 'students': [self.student_profile.pk],
        })
        self.assertRedirects(r, reverse('manage_center'))
        cls = StudyClass.objects.get(name='8/1')
        self.assertEqual(cls.teacher, self.teacher_profile)

    def test_class_name_unique_per_teacher(self):
        StudyClass.objects.create(
            name='7/13', teacher=self.teacher_profile)
        self.client.force_login(self.teacher)
        r = self.client.post(reverse('class_add'), {'name': '7/13'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'already exists')

    def test_teacher_deletes_own_class(self):
        cls = StudyClass.objects.create(
            name='Temp', teacher=self.teacher_profile)
        cls.students.add(self.student_profile)
        self.client.force_login(self.teacher)
        r = self.client.post(reverse('class_delete', kwargs={'pk': cls.pk}))
        self.assertRedirects(r, reverse('manage_center'))
        self.assertFalse(StudyClass.objects.filter(pk=cls.pk).exists())
        # Students themselves are kept.
        self.assertTrue(
            StudentProfile.objects.filter(pk=self.student_profile.pk).exists())

    def test_class_changes_are_logged(self):
        from .models import ChangeLog
        self.client.force_login(self.teacher)
        self.client.post(reverse('class_add'), {'name': 'Logged'})
        entry = ChangeLog.objects.latest('created_at')
        self.assertEqual(entry.category, 'class')
        self.assertIn("created class 'Logged'", entry.summary)
        self.assertEqual(entry.actor, self.teacher)


class ManageAssignTests(TestCase):
    def setUp(self):
        self.admin = make_user('as_adm', 'admin', is_staff=True, is_superuser=True)
        self.teacher = make_user('as_tch', 'teacher')
        self.teacher_profile = TeacherProfile.objects.create(user=self.teacher)
        self.student = make_user('as_stu', 'student')
        self.student_profile = StudentProfile.objects.create(user=self.student)
        TeacherStudent.objects.create(
            teacher=self.teacher_profile, student=self.student_profile)
        self.study_class = StudyClass.objects.create(
            name='7/13', teacher=self.teacher_profile)
        self.study_class.students.add(self.student_profile)
        course = Course.objects.create(title='AS Course')
        chapter = Chapter.objects.create(course=course, title='AS Ch', order=1)
        self.lesson = Lesson.objects.create(
            chapter=chapter, title='AS Lesson', order=1)

    def test_assign_by_class(self):
        self.client.force_login(self.teacher)
        r = self.client.post(reverse('manage_assign'), {
            'lesson': self.lesson.pk, 'target': 'class',
            'study_class': self.study_class.pk,
        })
        self.assertRedirects(r, reverse('manage_center'))
        self.assertTrue(StudentLesson.objects.filter(
            student=self.student_profile, lesson=self.lesson).exists())

    def test_assign_by_individual_students(self):
        self.client.force_login(self.teacher)
        r = self.client.post(reverse('manage_assign'), {
            'lesson': self.lesson.pk, 'target': 'students',
            'students': [self.student_profile.pk],
        })
        self.assertRedirects(r, reverse('manage_center'))
        self.assertTrue(StudentLesson.objects.filter(
            student=self.student_profile, lesson=self.lesson).exists())

    def test_assign_is_idempotent(self):
        self.client.force_login(self.teacher)
        url = reverse('manage_assign')
        data = {'lesson': self.lesson.pk, 'target': 'class',
                'study_class': self.study_class.pk}
        self.client.post(url, data)
        self.client.post(url, data)
        self.assertEqual(StudentLesson.objects.filter(
            lesson=self.lesson).count(), 1)

    def test_teacher_cannot_assign_to_other_teachers_class(self):
        other = make_user('as_tch2', 'teacher')
        other_profile = TeacherProfile.objects.create(user=other)
        other_class = StudyClass.objects.create(
            name='X', teacher=other_profile)
        self.client.force_login(self.teacher)
        r = self.client.post(reverse('manage_assign'), {
            'lesson': self.lesson.pk, 'target': 'class',
            'study_class': other_class.pk,
        })
        # Rejected by the scoped queryset -> form error, no assignment.
        self.assertEqual(r.status_code, 200)
        self.assertFalse(StudentLesson.objects.exists())

    def test_assign_requires_admin_or_teacher(self):
        student = make_user('as_stu2', 'student')
        self.client.force_login(student)
        r = self.client.get(reverse('manage_assign'))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, reverse('dashboard'))

    def test_max_two_parents_per_student(self):
        self.client.force_login(self.admin)
        parent1 = make_user('as_par1', 'parent')
        p1 = ParentProfile.objects.create(user=parent1)
        parent2 = make_user('as_par2', 'parent')
        p2 = ParentProfile.objects.create(user=parent2)
        parent3 = make_user('as_par3', 'parent')
        p3 = ParentProfile.objects.create(user=parent3)
        add = reverse('manage_add', kwargs={'model_name': 'studentparent'})
        self.client.post(add, {'student': self.student_profile.pk,
                               'parent': p1.pk})
        self.client.post(add, {'student': self.student_profile.pk,
                               'parent': p2.pk})
        r = self.client.post(add + '?modal=1',
                             {'student': self.student_profile.pk,
                              'parent': p3.pk},
                             HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'at most 2 parents')
        self.assertEqual(StudentParent.objects.filter(
            student=self.student_profile).count(), 2)


class ChangeLogTests(TestCase):
    def setUp(self):
        from .models import ChangeLog
        self.ChangeLog = ChangeLog
        self.admin = make_user('hg_adm', 'admin', is_staff=True, is_superuser=True)
        self.teacher = make_user('hg_tch', 'teacher')
        self.teacher_profile = TeacherProfile.objects.create(user=self.teacher)
        self.student = make_user('hg_stu', 'student')
        self.student_profile = StudentProfile.objects.create(user=self.student)
        TeacherStudent.objects.create(
            teacher=self.teacher_profile, student=self.student_profile)

    def _log(self, actor, summary, **kwargs):
        from .changelog import log_change
        return log_change(actor, 'relationship', 'link', summary, **kwargs)

    def test_crud_writes_specific_entries(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('manage_add', kwargs={'model_name': 'course'}),
                         {'title': 'Logged Course'})
        entry = self.ChangeLog.objects.latest('created_at')
        self.assertEqual(entry.category, 'content')
        self.assertIn("created course 'Logged Course'", entry.summary)

    def test_role_change_logged_as_role(self):
        self.client.force_login(self.admin)
        url = reverse('manage_edit',
                      kwargs={'model_name': 'user', 'pk': self.student.pk})
        self.client.post(url, {'role': 'teacher', 'email': '',
                               'first_name': '', 'last_name': '',
                               'phone_number': '', 'is_active': 'on'})
        entry = self.ChangeLog.objects.latest('created_at')
        self.assertEqual(entry.category, 'role')
        self.assertIn('from Student to Teacher', entry.summary)

    def test_teacher_sees_own_and_related_admin_entries(self):
        from .changelog import changelog_for
        # Teacher's own entry.
        self._log(self.teacher, 'teacher did X')
        # Admin entry related to the teacher's student.
        self._log(self.admin, 'admin did Y',
                  related_student=self.student_profile)
        # Admin entry unrelated.
        other = make_user('hg_tch2', 'teacher')
        self._log(self.admin, 'admin did Z', related_teacher=None)
        visible = list(changelog_for(self.teacher))
        summaries = [e.summary for e in visible]
        self.assertIn('teacher did X', summaries)
        self.assertIn('admin did Y', summaries)
        self.assertNotIn('admin did Z', summaries)

    def test_admin_sees_everything(self):
        from .changelog import changelog_for
        self._log(self.teacher, 'teacher did X')
        self._log(self.admin, 'admin did Z')
        self.assertEqual(changelog_for(self.admin).count(), 2)

    def test_changelog_page_requires_admin_or_teacher(self):
        student = make_user('hg_stu2', 'student')
        self.client.force_login(student)
        r = self.client.get(reverse('changelog_list'))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, reverse('dashboard'))

    def test_dashboard_shows_changelog(self):
        self.client.force_login(self.admin)
        self._log(self.admin, 'visible entry')
        r = self.client.get(reverse('dashboard'))
        self.assertContains(r, 'Change History')
        self.assertContains(r, 'visible entry')
        self.assertNotContains(r, 'My Account')

    def test_teacher_dashboard_shows_changelog(self):
        self.client.force_login(self.teacher)
        self._log(self.teacher, 'teacher entry')
        r = self.client.get(reverse('dashboard'))
        self.assertContains(r, 'Change History')
        self.assertContains(r, 'teacher entry')


class ManageFilterTests(TestCase):
    def setUp(self):
        self.admin = make_user('fl_adm', 'admin', is_staff=True, is_superuser=True)
        self.client.force_login(self.admin)
        self.course = Course.objects.create(title='Alpha Course')
        Course.objects.create(title='Beta Course')
        make_user('fl_zed', 'student', email='zed@example.com')

    def test_learning_filter(self):
        r = self.client.get(reverse('manage_center') + '?q_learning=alpha')
        self.assertContains(r, 'Alpha Course')
        self.assertNotContains(r, 'Beta Course')

    def test_people_search_and_role_filter(self):
        r = self.client.get(
            reverse('manage_center') + '?tab=people&q_people=zed')
        self.assertContains(r, 'fl_zed')
        r = self.client.get(
            reverse('manage_center') + '?tab=people&role=admin')
        self.assertContains(r, 'fl_adm')
        self.assertNotContains(r, 'fl_zed')

    def test_links_filter(self):
        teacher = make_user('fl_tch', 'teacher')
        tp = TeacherProfile.objects.create(user=teacher)
        student = make_user('fl_stu', 'student')
        sp = StudentProfile.objects.create(user=student)
        TeacherStudent.objects.create(teacher=tp, student=sp)
        r = self.client.get(
            reverse('manage_center') + '?tab=links&q_links=fl_tch')
        self.assertContains(r, 'fl_tch')
        self.assertContains(r, 'fl_stu')


class MiscBehaviorTests(TestCase):
    def setUp(self):
        self.admin = make_user('mb_adm', 'admin', is_staff=True, is_superuser=True)

    def test_login_redirects_to_home(self):
        r = self.client.post(reverse('login'),
                             {'username': 'mb_adm', 'password': 'pw123456'})
        self.assertRedirects(r, reverse('home'))

    def test_timestamps_use_vietnam_timezone(self):
        from django.conf import settings
        self.assertEqual(settings.TIME_ZONE, 'Asia/Ho_Chi_Minh')

    def test_admin_nav_has_no_standalone_speaking_lessons(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('manage_center'))
        # Management link present; the standalone nav item is gone for admin
        # (lessons live in the Management Center's Speaking Lessons tab).
        self.assertContains(r, '&#128218; Management</a>')
        self.assertNotContains(r, '>Speaking Lessons</a>')
        self.assertContains(r, '&#127908; Speaking Lessons</button>')

    def test_remember_me_cookie_persists(self):
        # Checked -> the session cookie carries an expiry (survives restart).
        r = self.client.post(reverse('login'),
                             {'username': 'mb_adm', 'password': 'pw123456',
                              'remember_me': 'on'})
        self.assertRedirects(r, reverse('home'))
        cookie = r.cookies.get('sessionid')
        self.assertTrue(cookie.get('expires'))

    def test_without_remember_me_cookie_is_session_only(self):
        r = self.client.post(reverse('login'),
                             {'username': 'mb_adm', 'password': 'pw123456'})
        self.assertRedirects(r, reverse('home'))
        cookie = r.cookies.get('sessionid')
        self.assertFalse(cookie.get('expires'))

    def test_logout_destroys_session_even_when_remembered(self):
        self.client.post(reverse('login'),
                         {'username': 'mb_adm', 'password': 'pw123456',
                          'remember_me': 'on'})
        self.assertIn('_auth_user_id', self.client.session)
        self.client.get(reverse('logout'))
        self.assertNotIn('_auth_user_id', self.client.session)


class ManageRound4Tests(TestCase):
    """Review round 4: classes in Links tab, preview modal, changelog
    tabs/table, people counts, profile password change, relaxed validators."""

    def setUp(self):
        self.admin = make_user('r4_adm', 'admin', is_staff=True, is_superuser=True)
        self.teacher = make_user('r4_tch', 'teacher')
        self.tp = TeacherProfile.objects.create(user=self.teacher)
        self.student = make_user('r4_stu', 'student')
        self.sp = StudentProfile.objects.create(user=self.student)
        TeacherStudent.objects.create(teacher=self.tp, student=self.sp)
        self.study_class = StudyClass.objects.create(name='7/13', teacher=self.tp)
        self.study_class.students.add(self.sp)
        course = Course.objects.create(title='R4 Course')
        chapter = Chapter.objects.create(course=course, title='R4 Ch', order=1)
        self.lesson = Lesson.objects.create(
            chapter=chapter, title='R4 Lesson', order=1, teacher=self.tp)
        self.exercise = Exercise.objects.create(
            lesson=self.lesson, title='R4 Exercise', order=1)

    def test_classes_live_in_links_tab(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('manage_center') + '?tab=links')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'classes-card')
        self.assertContains(r, '7/13')
        self.assertNotContains(r, 'id="tab-classes"')
        self.assertNotContains(r, 'id="pane-classes"')

    def test_remove_student_from_class(self):
        self.client.force_login(self.teacher)
        url = reverse('class_remove_student',
                      kwargs={'pk': self.study_class.pk,
                              'student_pk': self.sp.pk})
        r = self.client.post(url, {'next': '/manage/?tab=links'})
        self.assertRedirects(r, '/manage/?tab=links')
        self.assertFalse(
            self.study_class.students.filter(pk=self.sp.pk).exists())
        # The student account itself is kept.
        self.assertTrue(
            StudentProfile.objects.filter(pk=self.sp.pk).exists())

    def test_remove_student_logged(self):
        from .models import ChangeLog
        self.client.force_login(self.teacher)
        url = reverse('class_remove_student',
                      kwargs={'pk': self.study_class.pk,
                              'student_pk': self.sp.pk})
        self.client.post(url)
        entry = ChangeLog.objects.latest('created_at')
        self.assertIn("removed student 'r4_stu' from class '7/13'",
                      entry.summary)

    def test_teacher_cannot_remove_from_other_teachers_class(self):
        other = make_user('r4_tch2', 'teacher')
        other_tp = TeacherProfile.objects.create(user=other)
        other_class = StudyClass.objects.create(name='X', teacher=other_tp)
        other_class.students.add(self.sp)
        self.client.force_login(self.teacher)
        url = reverse('class_remove_student',
                      kwargs={'pk': other_class.pk, 'student_pk': self.sp.pk})
        r = self.client.post(url)
        self.assertRedirects(r, reverse('manage_center'))
        self.assertTrue(other_class.students.filter(pk=self.sp.pk).exists())

    def test_lesson_preview_modal_stays_on_page(self):
        self.client.force_login(self.admin)
        url = reverse('lesson_preview', kwargs={'pk': self.lesson.pk})
        r = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'R4 Lesson')
        self.assertContains(r, 'R4 Exercise')
        # No <form> and no redirect: pure preview fragment.
        self.assertNotContains(r, '<form')

    def test_lesson_preview_forbidden_for_teacher(self):
        self.client.force_login(self.teacher)
        url = reverse('lesson_preview', kwargs={'pk': self.lesson.pk})
        r = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 302)

    def test_changelog_category_filter(self):
        from .changelog import log_change
        log_change(self.admin, 'class', 'create', 'class entry')
        log_change(self.admin, 'user', 'create', 'user entry')
        self.client.force_login(self.admin)
        r = self.client.get(reverse('changelog_list') + '?category=class')
        self.assertContains(r, 'class entry')
        self.assertNotContains(r, 'user entry')
        r = self.client.get(reverse('changelog_list'))
        self.assertContains(r, 'class entry')
        self.assertContains(r, 'user entry')

    def test_changelog_renders_table(self):
        from .changelog import log_change
        log_change(self.admin, 'class', 'create', 'table entry')
        self.client.force_login(self.admin)
        r = self.client.get(reverse('changelog_list'))
        self.assertContains(r, '<table')
        # Template comments must never leak into the HTML.
        self.assertNotContains(r, '{#')

    def test_people_counts_label(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('manage_center') + '?tab=people')
        content = r.content.decode()
        # In-pane label shows total + per-role counts...
        self.assertIn('3 users', content)
        self.assertIn('1 Admin', content)
        # ...and the People tab itself no longer carries a count badge.
        tab_html = content.split('id="tab-people"')[1].split('</button>')[0]
        self.assertNotIn('badge', tab_html)

    def test_class_modal_checkbox_list_renders(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('class_add'),
                            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'esp-checklist')
        self.assertContains(r, 'esp-check-item')

    def test_class_edit_preselects_teacher(self):
        from .forms import StudyClassForm
        form = StudyClassForm(instance=self.study_class, is_admin=True)
        self.assertEqual(form.fields['teacher'].initial, self.tp.pk)

    def test_is_active_label_is_active(self):
        from .forms import CourseForm
        self.assertEqual(CourseForm().fields['is_active'].label, 'Active')

    def test_order_help_text(self):
        from .forms import ChapterForm, LessonForm, ExerciseForm
        for form_cls in (ChapterForm, LessonForm, ExerciseForm):
            self.assertIn('order', form_cls().fields['order'].help_text.lower())

    def test_profile_password_change(self):
        self.client.force_login(self.student)
        r = self.client.post(reverse('profile'), {
            'change_password': '1',
            'old_password': 'pw123456',
            'new_password1': 'brandnew1',
            'new_password2': 'brandnew1',
        })
        self.assertRedirects(r, reverse('profile'))
        # Still logged in after the change.
        self.assertIn('_auth_user_id', self.client.session)
        self.client.logout()
        self.assertTrue(
            self.client.login(username='r4_stu', password='brandnew1'))

    def test_profile_password_change_wrong_old(self):
        self.client.force_login(self.student)
        r = self.client.post(reverse('profile'), {
            'change_password': '1',
            'old_password': 'wrongpw',
            'new_password1': 'brandnew1',
            'new_password2': 'brandnew1',
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Change password')

    def test_relaxed_password_validators(self):
        # Previously-common passwords are now accepted (min length 6).
        r = self.client.post(reverse('signup'), {
            'username': 'r4_newuser', 'email': 'r4@n.com',
            'password1': 'qwerty123',
            'password2': 'qwerty123', 'role': 'student',
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(User.objects.filter(username='r4_newuser').exists())

    def test_short_password_still_rejected(self):
        r = self.client.post(reverse('signup'), {
            'username': 'r4_newuser2', 'email': 'r42@n.com',
            'password1': 'abc',
            'password2': 'abc', 'role': 'student',
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username='r4_newuser2').exists())

    def test_dashboard_total_classes(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('dashboard'))
        self.assertContains(r, 'Total Classes')

    def test_info_popover_present(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('manage_center') + '?tab=learning')
        self.assertContains(r, 'data-esp-info')
        self.assertContains(r, 'How it works:')

    def test_no_empty_course_nag(self):
        Course.objects.all().delete()
        self.client.force_login(self.admin)
        r = self.client.get(reverse('manage_center') + '?tab=learning')
        self.assertNotContains(r, 'No courses yet')
        # The template comment must not leak into the HTML.
        self.assertNotContains(r, 'Include once per page')


class ManageLinksUiTests(TestCase):
    """Links & Practice UI: sub-tabs, Teacher-Students add button, assign modal."""

    def setUp(self):
        self.admin = make_user('ui_adm', 'admin', is_staff=True, is_superuser=True)
        self.teacher = make_user('ui_tch', 'teacher')
        self.teacher_profile = TeacherProfile.objects.create(user=self.teacher)
        self.student = make_user('ui_stu', 'student')
        self.student_profile = StudentProfile.objects.create(user=self.student)
        course = Course.objects.create(title='UI Course')
        chapter = Chapter.objects.create(course=course, title='UI Ch', order=1)
        self.lesson = Lesson.objects.create(chapter=chapter, title='UI Lesson', order=1)
        self.center = reverse('manage_center') + '?tab=links'

    def test_links_tab_has_five_subtabs(self):
        self.client.force_login(self.admin)
        r = self.client.get(self.center)
        self.assertEqual(r.status_code, 200)
        for section in ('classes', 'teacherstudents', 'studentparents',
                        'assigned', 'attempts'):
            self.assertContains(r, f'id="subtab-{section}"')
            self.assertContains(r, f'id="subpane-{section}"')

    def test_teacher_student_add_button_visible_for_admin(self):
        self.client.force_login(self.admin)
        r = self.client.get(self.center)
        self.assertContains(
            r, reverse('manage_add', kwargs={'model_name': 'teacherstudent'}))

    def test_teacher_student_add_button_hidden_for_teacher(self):
        # Teachers cannot create teacher-student links (admin-only action).
        self.client.force_login(self.teacher)
        r = self.client.get(self.center)
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(
            r, reverse('manage_add', kwargs={'model_name': 'teacherstudent'}))

    def test_assign_modal_radio_group_renders_cleanly(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('manage_assign') + '?modal=1',
                            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 200)
        # Radios wrapped in .form-check inside a radiogroup container...
        self.assertContains(r, 'role="radiogroup"')
        self.assertContains(r, 'Whole class')
        self.assertContains(r, 'Individual students')
        # ...and the collapsing form-check-input class must NOT be on the
        # group container (it shrank the group to 16px and overlapped text).
        self.assertNotContains(r, 'id="id_target" class="form-check-input"')

    def test_assign_modal_students_use_checklist_and_toggle_wrappers(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('manage_assign') + '?modal=1',
                            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertContains(r, 'esp-checklist')
        self.assertContains(r, 'data-esp-field="study_class"')
        self.assertContains(r, 'data-esp-field="students"')
        self.assertContains(r, 'data-esp-field="target"')

    def test_tab_panes_nested_inside_tab_content(self):
        # Regression: unbalanced </div>s once pushed #pane-people and
        # #pane-lessons outside .tab-content, so the People table (and its
        # filter) leaked into every other tab.
        from html.parser import HTMLParser

        class PaneNesting(HTMLParser):
            def __init__(self):
                super().__init__()
                self.stack = []
                self.bad = []

            def handle_starttag(self, tag, attrs):
                if tag != 'div':
                    return
                attrs = dict(attrs)
                classes = attrs.get('class', '').split()
                self.stack.append((attrs.get('id'), classes))
                if 'tab-pane' in classes:
                    parent = self.stack[-2] if len(self.stack) > 1 else (None, [])
                    if 'tab-content' not in parent[1]:
                        self.bad.append(attrs.get('id'))

            def handle_endtag(self, tag):
                if tag == 'div' and self.stack:
                    self.stack.pop()

        for username, role in (('pn_adm', 'admin'), ('pn_tch', 'teacher')):
            user = make_user(username, role,
                             is_staff=(role == 'admin'),
                             is_superuser=(role == 'admin'))
            if role == 'teacher':
                TeacherProfile.objects.create(user=user)
            self.client.force_login(user)
            r = self.client.get(reverse('manage_center'))
            self.assertEqual(r.status_code, 200)
            checker = PaneNesting()
            checker.feed(r.content.decode())
            self.assertEqual(checker.bad, [], role)
            self.client.logout()

    def test_class_add_empty_teacher_single_error(self):
        # Empty teacher must show only the form's "required" error, not a
        # second technical "cannot be null" from model validation.
        self.client.force_login(self.admin)
        r = self.client.post(reverse('class_add'), {'name': '', 'teacher': ''},
                            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 200)
        content = r.content.decode()
        self.assertIn('This field is required.', content)
        self.assertNotIn('cannot be null', content)

    def test_class_add_duplicate_name_per_teacher_rejected(self):
        # Unique-per-teacher validation still works (teacher kept in the
        # unique check when it has no form error).
        from .models import StudyClass
        StudyClass.objects.create(name='7/13', teacher=self.teacher_profile)
        self.client.force_login(self.admin)
        r = self.client.post(
            reverse('class_add'),
            {'name': '7/13', 'teacher': str(self.teacher_profile.pk)},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 200)
        self.assertIn('already exists', r.content.decode().lower())

    def test_user_add_password_help_text_matches_policy(self):
        # Password policy is min-length 6; the help text must say so.
        self.client.force_login(self.admin)
        r = self.client.get(reverse('manage_add', kwargs={'model_name': 'user'}),
                            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 200)
        content = r.content.decode()
        self.assertIn('Minimum 6 characters', content)
        self.assertNotIn('Minimum 8 characters', content)

    def test_class_card_student_count_is_collapsible(self):
        # The student count is a dropdown toggle; chips live in a matching
        # collapse container (keeps cards compact with many students).
        from .models import StudyClass
        sc = StudyClass.objects.create(name='DD Class',
                                       teacher=self.teacher_profile)
        sc.students.add(self.student_profile)
        self.client.force_login(self.admin)
        r = self.client.get(reverse('manage_center') + '?tab=links')
        self.assertEqual(r.status_code, 200)
        content = r.content.decode()
        self.assertIn('esp-student-toggle', content)
        self.assertIn(f'data-bs-target="#class-students-{sc.pk}"', content)
        self.assertIn(f'id="class-students-{sc.pk}"', content)
        self.assertIn('1 student', content)


class SeedDemoDataTests(TestCase):
    """The seed_demo_data command builds a realistic demo dataset."""

    def test_seed_demo_data(self):
        from django.core.management import call_command
        from .models import (ParentProfile, StudentParent, StudentProfile,
                             StudyClass, TeacherProfile, TeacherStudent, User)
        call_command('seed_demo_data')
        self.assertEqual(
            User.objects.filter(username__startswith='demo_teacher').count(), 10)
        self.assertEqual(
            User.objects.filter(username__startswith='demo_student').count(), 40)
        self.assertEqual(
            User.objects.filter(username__startswith='demo_parent').count(), 40)
        self.assertEqual(TeacherProfile.objects.filter(
            user__username__startswith='demo_teacher').count(), 10)
        self.assertEqual(StudentProfile.objects.filter(
            user__username__startswith='demo_student').count(), 40)
        self.assertEqual(ParentProfile.objects.filter(
            user__username__startswith='demo_parent').count(), 40)
        # Every demo student has a teacher and exactly one parent.
        for sp in StudentProfile.objects.filter(
                user__username__startswith='demo_student'):
            self.assertTrue(
                TeacherStudent.objects.filter(student=sp).exists())
            self.assertEqual(StudentParent.objects.filter(student=sp).count(), 1)
        # One sample class per teacher.
        self.assertEqual(StudyClass.objects.filter(
            teacher__user__username__startswith='demo_teacher').count(), 10)
        # Passwords work.
        u = User.objects.get(username='demo_teacher1')
        self.assertTrue(u.check_password('Test12345!'))

    def test_seed_demo_data_idempotent(self):
        from django.core.management import call_command
        from .models import User
        call_command('seed_demo_data')
        call_command('seed_demo_data')
        self.assertEqual(
            User.objects.filter(username__startswith='demo_').count(), 90)


class ManageGroupingTests(TestCase):
    """Links & Practice lists are grouped (by teacher/student) with
    natural ordering: 'Class 2' before 'Class 10'."""

    def setUp(self):
        self.admin = make_user('g_adm', 'admin', is_staff=True, is_superuser=True)
        self.t1 = make_user('g_tch1', 'teacher')
        self.t2 = make_user('g_tch2', 'teacher')
        self.tp1 = TeacherProfile.objects.create(user=self.t1)
        self.tp2 = TeacherProfile.objects.create(user=self.t2)
        self.s1 = make_user('g_stu1', 'student')
        self.s2 = make_user('g_stu2', 'student')
        self.s10 = make_user('g_stu10', 'student')
        self.sp1 = StudentProfile.objects.create(user=self.s1)
        self.sp2 = StudentProfile.objects.create(user=self.s2)
        self.sp10 = StudentProfile.objects.create(user=self.s10)
        TeacherStudent.objects.create(teacher=self.tp1, student=self.sp1)
        TeacherStudent.objects.create(teacher=self.tp1, student=self.sp10)
        TeacherStudent.objects.create(teacher=self.tp2, student=self.sp2)
        p1u = make_user('g_par1', 'parent')
        p1 = ParentProfile.objects.create(user=p1u)
        StudentParent.objects.create(student=self.sp1, parent=p1,
                                     relationship_type='Father')
        p2u = make_user('g_par2', 'parent')
        p2 = ParentProfile.objects.create(user=p2u)
        StudentParent.objects.create(student=self.sp2, parent=p2,
                                     relationship_type='Mother')
        for name in ('Class 10', 'Class 2', 'Class 1'):
            StudyClass.objects.create(name=name, teacher=self.tp1)
        StudyClass.objects.create(name='Class 1', teacher=self.tp2)

    def _get(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('manage_center') + '?tab=links')
        self.assertEqual(r.status_code, 200)
        return r.content.decode()

    def test_classes_grouped_by_teacher_natural_order(self):
        html = self._get()
        # Teacher sections appear before their classes...
        t1_pos = html.find('g_tch1')
        t2_pos = html.find('g_tch2')
        self.assertGreater(t1_pos, 0)
        self.assertGreater(t2_pos, t1_pos)
        # ...and 'Class 2' sorts before 'Class 10' (natural order).
        c1 = html.find('>Class 1<', t1_pos)
        c2 = html.find('>Class 2<', t1_pos)
        c10 = html.find('>Class 10<', t1_pos)
        self.assertLess(c1, c2)
        self.assertLess(c2, c10)
        self.assertLess(c10, t2_pos)

    def test_teacher_students_grouped_by_teacher(self):
        html = self._get()
        t1_pos = html.find('id="subpane-teacherstudents"')
        g1 = html.find('g_tch1', t1_pos)
        g2 = html.find('g_tch2', t1_pos)
        self.assertLess(g1, g2)
        # g_tch1's students follow their teacher header.
        s1 = html.find('g_stu1', g1)
        s10 = html.find('g_stu10', g1)
        self.assertLess(s1, s10)
        self.assertLess(s10, g2)

    def test_student_parents_grouped_by_student(self):
        html = self._get()
        pos = html.find('id="subpane-studentparents"')
        # Two student groups, natural order: g_stu1 before g_stu2.
        s1 = html.find('&#127891; g_stu1', pos)
        s2 = html.find('&#127891; g_stu2', pos)
        self.assertGreater(s1, 0)
        self.assertLess(s1, s2)
        # Each parent sits under their student's header.
        par1 = html.find('g_par1', s1)
        par2 = html.find('g_par2', s2)
        self.assertLess(par1, s2)
        self.assertGreater(par2, s2)


class DashboardRedesignTests(TestCase):
    """Redesigned home + student dashboard expose the new context data."""

    def setUp(self):
        self.admin = make_user('r_adm', 'admin', is_staff=True, is_superuser=True)
        self.student = make_user('r_stu', 'student')
        self.sp = StudentProfile.objects.create(user=self.student)

    def test_home_shows_platform_stats(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('home'))
        self.assertEqual(r.status_code, 200)
        for key in ('stat_students', 'stat_lessons', 'stat_attempts'):
            self.assertIn(key, r.context)
        html = r.content.decode()
        self.assertIn('esp-stats-band', html)
        self.assertIn('Dành cho tất cả mọi người', html)

    def test_student_dashboard_week_activity(self):
        self.client.force_login(self.student)
        r = self.client.get(reverse('dashboard'))
        self.assertEqual(r.status_code, 200)
        week = r.context['week_activity']
        self.assertEqual(len(week), 7)
        self.assertTrue(week[-1]['is_today'])
        self.assertTrue(all('height' in d and 'label' in d for d in week))
        html = r.content.decode()
        self.assertIn('esp-week-chart', html)
        self.assertIn('Hoạt động 7 ngày qua', html)
