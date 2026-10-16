"""
Full functional test matrix for Phase 1.

Covers every URL, every form field (valid / invalid / edge values),
every button/action, and the full role x view permission matrix.
Run: python manage.py test speaking_practice.test_functional
"""
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.conf import settings
import os

from .models import (
    Chapter, Course, Exercise, Lesson, ParentProfile, SpeakingAttempt,
    StudentLesson, StudentParent, StudentProfile, TeacherProfile,
    TeacherStudent,
)

User = get_user_model()
PW = 'TestPass123!'


def make_world():
    """Build a complete fixture world. Returns a dict of objects."""
    admin = User.objects.create_superuser('w_admin', 'a@x.com', PW, role='admin')
    t1 = User.objects.create_user('w_teacher1', password=PW, role='teacher')
    tp1 = TeacherProfile.objects.create(user=t1)
    t2 = User.objects.create_user('w_teacher2', password=PW, role='teacher')
    tp2 = TeacherProfile.objects.create(user=t2)
    s1 = User.objects.create_user('w_student1', password=PW, role='student')
    sp1 = StudentProfile.objects.create(user=s1)
    s2 = User.objects.create_user('w_student2', password=PW, role='student')
    sp2 = StudentProfile.objects.create(user=s2)
    p1 = User.objects.create_user('w_parent1', password=PW, role='parent')
    pp1 = ParentProfile.objects.create(user=p1)
    p2 = User.objects.create_user('w_parent2', password=PW, role='parent')
    pp2 = ParentProfile.objects.create(user=p2)  # no children linked

    course = Course.objects.create(title='W Course')
    ch_active = Chapter.objects.create(course=course, title='W Ch Active', order=1)
    ch_inactive = Chapter.objects.create(
        course=course, title='W Ch Inactive', order=2, is_active=False)
    les1 = Lesson.objects.create(
        chapter=ch_active, teacher=tp1, title='W Lesson 1', order=1)
    les2 = Lesson.objects.create(
        chapter=ch_active, teacher=tp2, title='W Lesson 2', order=2)
    ex_active = Exercise.objects.create(
        lesson=les1, title='W Ex Active', order=1, is_active=True)
    ex_inactive = Exercise.objects.create(
        lesson=les1, title='W Ex Inactive', order=2, is_active=False)

    TeacherStudent.objects.create(teacher=tp1, student=sp1)
    StudentParent.objects.create(student=sp1, parent=pp1)
    StudentLesson.objects.create(student=sp1, lesson=les1)
    return {
        'admin': admin, 't1': t1, 'tp1': tp1, 't2': t2, 'tp2': tp2,
        's1': s1, 'sp1': sp1, 's2': s2, 'sp2': sp2,
        'p1': p1, 'pp1': pp1, 'p2': p2, 'pp2': pp2,
        'course': course, 'ch_active': ch_active, 'ch_inactive': ch_inactive,
        'les1': les1, 'les2': les2,
        'ex_active': ex_active, 'ex_inactive': ex_inactive,
    }


class WorldTestCase(TestCase):
    def setUp(self):
        self.w = make_world()
        self.urls = {
            'home': reverse('home'),
            'dashboard': reverse('dashboard'),
            'lesson_list': reverse('lesson_list'),
            'lesson_detail': reverse('lesson_detail', args=[self.w['les1'].id]),
            'attempt': reverse('create_speaking_attempt',
                               args=[self.w['les1'].id, self.w['ex_active'].id]),
            't_create': reverse('teacher_create_lesson'),
            't_edit': reverse('teacher_edit_lesson', args=[self.w['les1'].id]),
            't_delete': reverse('teacher_delete_lesson', args=[self.w['les1'].id]),
            'profile': reverse('profile'),
            'login': reverse('login'),
            'logout': reverse('logout'),
            'signup': reverse('signup'),
        }

    def login(self, username):
        self.client.force_login(User.objects.get(username=username))


class PermissionMatrixTest(WorldTestCase):
    """Every role x every view: expected HTTP status."""

    def test_anonymous_redirects(self):
        # Anonymous users: everything protected -> login; logout/login ok.
        for name in ['home', 'dashboard', 'lesson_list', 'lesson_detail',
                     'attempt', 't_create', 't_edit', 't_delete', 'profile']:
            r = self.client.get(self.urls[name])
            self.assertEqual(r.status_code, 302, f'anon GET {name}')
        self.assertEqual(self.client.get(self.urls['login']).status_code, 200)
        self.assertEqual(self.client.get(self.urls['signup']).status_code, 200)
        self.assertEqual(self.client.get(self.urls['logout']).status_code, 302)

    def test_home_dashboard_profile_lessonlist_all_roles(self):
        for username in ['w_admin', 'w_teacher1', 'w_student1', 'w_parent1']:
            self.login(username)
            for name in ['home', 'dashboard', 'lesson_list', 'profile']:
                r = self.client.get(self.urls[name])
                self.assertEqual(r.status_code, 200, f'{username} GET {name}')
            self.client.logout()

    def test_lesson_detail_matrix(self):
        cases = [
            ('w_admin', 200), ('w_teacher1', 200), ('w_teacher2', 302),
            ('w_student1', 200), ('w_student2', 302),
            ('w_parent1', 200), ('w_parent2', 302),
        ]
        for username, expected in cases:
            self.login(username)
            r = self.client.get(self.urls['lesson_detail'])
            self.assertEqual(r.status_code, expected, username)
            self.client.logout()

    def test_lesson_detail_404(self):
        self.login('w_admin')
        r = self.client.get(reverse('lesson_detail', args=[99999]))
        self.assertEqual(r.status_code, 404)

    def test_lesson_detail_shows_only_active_exercises(self):
        self.login('w_student1')
        r = self.client.get(self.urls['lesson_detail'])
        self.assertContains(r, 'W Ex Active')
        self.assertNotContains(r, 'W Ex Inactive')

    def test_attempt_page_matrix(self):
        cases = [
            ('w_admin', 302), ('w_teacher1', 302), ('w_student1', 200),
            ('w_student2', 302), ('w_parent1', 302),
        ]
        for username, expected in cases:
            self.login(username)
            r = self.client.get(self.urls['attempt'])
            self.assertEqual(r.status_code, expected, username)
            self.client.logout()

    def test_teacher_views_matrix(self):
        # t_create / t_edit / t_delete reachable only by teachers;
        # edit/delete only for the owning teacher.
        for username, expected in [('w_teacher1', 200), ('w_teacher2', 200),
                                   ('w_admin', 302), ('w_student1', 302),
                                   ('w_parent1', 302)]:
            self.login(username)
            r = self.client.get(self.urls['t_create'])
            self.assertEqual(r.status_code, expected, f'{username} create')
            self.client.logout()
        for username, expected in [('w_teacher1', 200), ('w_teacher2', 302),
                                   ('w_admin', 302), ('w_student1', 302)]:
            self.login(username)
            for name in ['t_edit', 't_delete']:
                r = self.client.get(self.urls[name])
                self.assertEqual(r.status_code, expected,
                                 f'{username} {name}')
            self.client.logout()

    def test_login_signup_redirect_when_authenticated(self):
        self.login('w_student1')
        self.assertEqual(self.client.get(self.urls['login']).status_code, 302)
        self.assertEqual(self.client.get(self.urls['signup']).status_code, 302)


class AuthFieldTest(WorldTestCase):
    """Every login/signup field: valid, invalid and edge values."""

    def test_login_valid(self):
        r = self.client.post(self.urls['login'],
                             {'username': 'w_student1', 'password': PW})
        # Every role lands on Home after a successful login.
        self.assertRedirects(r, reverse('home'))

    def test_login_wrong_password(self):
        r = self.client.post(self.urls['login'],
                             {'username': 'w_student1', 'password': 'Wrong!'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Invalid username or password.')

    def test_login_unknown_user(self):
        r = self.client.post(self.urls['login'],
                             {'username': 'nobody', 'password': PW})
        self.assertEqual(r.status_code, 200)

    def test_login_empty_fields(self):
        r = self.client.post(self.urls['login'], {'username': '', 'password': ''})
        self.assertEqual(r.status_code, 200)

    def test_login_inactive_user(self):
        u = User.objects.get(username='w_student1')
        u.is_active = False
        u.save()
        r = self.client.post(self.urls['login'],
                             {'username': 'w_student1', 'password': PW})
        self.assertEqual(r.status_code, 200)
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_logout(self):
        self.login('w_student1')
        r = self.client.get(self.urls['logout'])
        self.assertEqual(r.status_code, 302)
        self.assertFalse('_auth_user_id' in self.client.session)

    def _signup(self, **overrides):
        data = {'username': 'newuser1', 'email': 'n@n.com',
                'password1': 'StrongPass123', 'password2': 'StrongPass123',
                'role': 'student'}
        data.update(overrides)
        return self.client.post(self.urls['signup'], data)

    def test_signup_each_role(self):
        for i, role in enumerate(['student', 'teacher', 'parent']):
            self.client.logout()  # signup redirects when already logged in
            r = self._signup(username=f'role_{role}', role=role)
            self.assertEqual(r.status_code, 302, role)
            u = User.objects.get(username=f'role_{role}')
            self.assertEqual(u.role, role)

    def test_signup_missing_role(self):
        r = self._signup(role='')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser1').exists())

    def test_signup_invalid_roles(self):
        for role in ['admin', 'hacker', 'STUDENT']:
            r = self._signup(username=f'bad_{role}', role=role)
            self.assertEqual(r.status_code, 200, role)
            self.assertFalse(User.objects.filter(username=f'bad_{role}').exists())

    def test_signup_password_mismatch(self):
        r = self._signup(password2='Different123')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser1').exists())

    def test_signup_duplicate_username(self):
        r = self._signup(username='w_student1')
        self.assertEqual(r.status_code, 200)

    def test_signup_weak_password(self):
        r = self._signup(password1='abc', password2='abc')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser1').exists())

    def test_signup_missing_username(self):
        r = self._signup(username='')
        self.assertEqual(r.status_code, 200)


class TeacherLessonFieldTest(WorldTestCase):
    """Every field of the teacher create/edit lesson forms."""

    def setUp(self):
        super().setUp()
        self.login('w_teacher1')
        self.ch = self.w['ch_active']

    def _create(self, **overrides):
        data = {'title': 'Field Test', 'description': 'd',
                'chapter': str(self.ch.id), 'order': ''}
        data.update(overrides)
        return self.client.post(self.urls['t_create'], data)

    def test_create_valid_with_order(self):
        r = self._create(title='With Order', order='5')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Lesson.objects.get(title='With Order').order, 5)

    def test_create_blank_order_auto_assigns(self):
        r = self._create(title='Auto Order')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Lesson.objects.get(title='Auto Order').order, 3)

    def test_create_missing_title(self):
        r = self._create(title='')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Title is required.')

    def test_create_whitespace_title(self):
        r = self._create(title='   ')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Title is required.')

    def test_create_title_too_long(self):
        r = self._create(title='x' * 201)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'at most 200 characters')

    def test_create_invalid_chapters(self):
        for ch in ['', 'abc', '99999', str(self.w['ch_inactive'].id)]:
            r = self._create(title=f'CH-{ch}', chapter=ch)
            self.assertEqual(r.status_code, 200, f'chapter={ch}')
            self.assertContains(r, 'valid chapter', msg_prefix=f'chapter={ch}')

    def test_create_bad_orders(self):
        for order in ['0', '-3', 'abc', '1.5']:
            r = self._create(title=f'ORD-{order}', order=order)
            self.assertEqual(r.status_code, 200, f'order={order}')
            self.assertFalse(Lesson.objects.filter(title=f'ORD-{order}').exists())

    def test_create_duplicate_order(self):
        r = self._create(title='Dup Order', order='1')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'already used')
        self.assertFalse(Lesson.objects.filter(title='Dup Order').exists())

    def test_create_form_renders_chapters(self):
        r = self.client.get(self.urls['t_create'])
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'W Ch Active')

    def test_edit_valid(self):
        r = self.client.post(self.urls['t_edit'],
                             {'title': 'Renamed', 'description': 'new'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Lesson.objects.get(id=self.w['les1'].id).title, 'Renamed')

    def test_edit_empty_title(self):
        r = self.client.post(self.urls['t_edit'], {'title': '', 'description': ''})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Title is required.')

    def test_edit_title_too_long(self):
        r = self.client.post(self.urls['t_edit'],
                             {'title': 'x' * 201, 'description': ''})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'at most 200 characters')

    def test_edit_other_teachers_lesson_blocked(self):
        url = reverse('teacher_edit_lesson', args=[self.w['les2'].id])
        r = self.client.post(url, {'title': 'Hacked', 'description': ''})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Lesson.objects.get(id=self.w['les2'].id).title, 'W Lesson 2')

    def test_delete_flow(self):
        les = Lesson.objects.create(chapter=self.ch, teacher=self.w['tp1'],
                                    title='To Delete', order=9)
        url = reverse('teacher_delete_lesson', args=[les.id])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        r = self.client.post(url)
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Lesson.objects.filter(id=les.id).exists())

    def test_delete_other_teachers_lesson_blocked(self):
        url = reverse('teacher_delete_lesson', args=[self.w['les2'].id])
        r = self.client.post(url)
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Lesson.objects.filter(id=self.w['les2'].id).exists())


class AttemptFieldTest(WorldTestCase):
    """Every field of the speaking-attempt form + URL edge cases."""

    def setUp(self):
        super().setUp()
        self.login('w_student1')
        self.les = self.w['les1']
        self.ex = self.w['ex_active']

    def _post(self, **overrides):
        data = {'transcript': 'Hello world', 'feedback': ''}
        data.update(overrides)
        return self.client.post(
            reverse('create_speaking_attempt', args=[self.les.id, self.ex.id]),
            data)

    def test_form_renders(self):
        r = self.client.get(self.urls['attempt'])
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'W Ex Active')

    def test_create_valid(self):
        r = self._post()
        self.assertEqual(r.status_code, 302)
        self.assertEqual(SpeakingAttempt.objects.count(), 1)

    def test_empty_transcript_rejected(self):
        for t in ['', '   ']:
            r = self._post(transcript=t)
            self.assertEqual(r.status_code, 200, repr(t))
            self.assertContains(r, 'Transcript is required.', msg_prefix=repr(t))
        self.assertEqual(SpeakingAttempt.objects.count(), 0)

    def test_audio_upload_saved(self):
        audio = SimpleUploadedFile('test.mp3', b'fake-audio-bytes',
                                   content_type='audio/mpeg')
        r = self.client.post(
            reverse('create_speaking_attempt', args=[self.les.id, self.ex.id]),
            {'transcript': 'hi', 'recorded_audio': audio})
        self.assertEqual(r.status_code, 302)
        attempt = SpeakingAttempt.objects.get()
        self.assertTrue(bool(attempt.recorded_audio))

    def test_oversize_audio_rejected(self):
        big = SimpleUploadedFile('big.mp3', b'x' * (21 * 1024 * 1024),
                                 content_type='audio/mpeg')
        r = self.client.post(
            reverse('create_speaking_attempt', args=[self.les.id, self.ex.id]),
            {'transcript': 'hi', 'recorded_audio': big})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'too large')
        self.assertEqual(SpeakingAttempt.objects.count(), 0)

    def test_inactive_exercise_404(self):
        url = reverse('create_speaking_attempt',
                      args=[self.les.id, self.w['ex_inactive'].id])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_mismatched_lesson_404(self):
        url = reverse('create_speaking_attempt',
                      args=[self.w['les2'].id, self.ex.id])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_nonexistent_ids_404(self):
        url = reverse('create_speaking_attempt', args=[99999, 99999])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_unassigned_student_blocked(self):
        self.client.force_login(User.objects.get(username='w_student2'))
        r = self.client.get(self.urls['attempt'])
        self.assertEqual(r.status_code, 302)
        r = self.client.post(self.urls['attempt'], {'transcript': 'hi'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(SpeakingAttempt.objects.count(), 0)


class DashboardEdgeTest(WorldTestCase):
    """Dashboards with missing data / broken accounts must not 500."""

    def test_missing_profiles_no_crash(self):
        for username, role in [('np_t', 'teacher'), ('np_s', 'student'),
                               ('np_p', 'parent')]:
            User.objects.create_user(username, password=PW, role=role)
            self.client.force_login(User.objects.get(username=username))
            r = self.client.get(reverse('dashboard'))
            self.assertEqual(r.status_code, 302, username)
            self.client.logout()

    def test_roleless_user_no_crash(self):
        u = User.objects.create_user('norole', password=PW, role='')
        self.client.force_login(u)
        r = self.client.get(reverse('dashboard'))
        self.assertEqual(r.status_code, 302)

    def test_empty_dashboards_render(self):
        # Teacher with nothing assigned, parent with no children.
        t = User.objects.create_user('empty_t', password=PW, role='teacher')
        TeacherProfile.objects.create(user=t)
        self.client.force_login(t)
        self.assertEqual(
            self.client.get(reverse('dashboard')).status_code, 200)
        self.client.logout()
        self.login('w_parent2')
        r = self.client.get(reverse('dashboard'))
        self.assertEqual(r.status_code, 200)

    def test_admin_dashboard_counts(self):
        self.login('w_admin')
        r = self.client.get(reverse('dashboard'))
        self.assertContains(r, 'Total Users')

    def test_student_with_no_lessons(self):
        self.login('w_student2')
        r = self.client.get(reverse('dashboard'))
        self.assertEqual(r.status_code, 200)
        r = self.client.get(reverse('lesson_list'))
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, 'W Lesson 1')


class SiteLoginRememberMeTests(WorldTestCase):
    """Site login page: remember-me checkbox + session expiry semantics."""

    def test_login_page_has_remember_me(self):
        r = self.client.get(self.urls['login'])
        self.assertContains(r, 'name="remember_me"')
        self.assertContains(r, 'autocomplete="new-password"')

    def test_login_without_remember_me_expires_on_browser_close(self):
        self.client.post(self.urls['login'],
                         {'username': 'w_student1', 'password': PW})
        self.assertEqual(self.client.session.get('_session_expiry'), 0)

    def test_login_with_remember_me_is_persistent(self):
        from django.conf import settings
        self.client.post(self.urls['login'],
                         {'username': 'w_student1', 'password': PW,
                          'remember_me': 'on'})
        self.assertEqual(self.client.session.get('_session_expiry'),
                         settings.SESSION_COOKIE_AGE)


class ProfilePageTests(WorldTestCase):
    """Profile page shows full account info and granted permissions."""

    def test_admin_profile_shows_everything(self):
        self.login('w_admin')
        r = self.client.get(reverse('profile'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Granted permissions')
        self.assertContains(r, 'Management Center')
        self.assertContains(r, 'Staff status')
        self.assertContains(r, 'Superuser status')
        self.assertContains(r, 'Last login')

    def test_teacher_profile_shows_bio_and_capabilities(self):
        self.login('w_teacher1')
        r = self.client.get(reverse('profile'))
        self.assertContains(r, 'teacher profile')
        self.assertContains(r, 'Create, edit and delete own lessons')

    def test_student_profile_shows_grade_and_capabilities(self):
        self.login('w_student1')
        r = self.client.get(reverse('profile'))
        self.assertContains(r, 'student profile')
        self.assertContains(r, 'Submit speaking attempts')

    def test_parent_profile_shows_relationship(self):
        self.login('w_parent1')
        r = self.client.get(reverse('profile'))
        self.assertContains(r, 'parent profile')
        self.assertContains(r, "children")


class ToastPositionTests(WorldTestCase):
    """Notifications float at the top-center of the viewport, below the navbar."""

    def test_toasts_are_top_centered(self):
        self.login('w_student1')
        r = self.client.get(reverse('dashboard'))
        # Toast styling now lives in the theme stylesheet.
        self.assertContains(r, 'css/esp-theme.css')
        css = open(os.path.join(settings.BASE_DIR, 'static', 'css',
                                'esp-theme.css')).read()
        self.assertIn('top: 76px', css)
        self.assertIn('translateX(-50%)', css)
