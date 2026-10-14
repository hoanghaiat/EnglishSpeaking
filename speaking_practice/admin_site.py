"""
Custom Django admin site for English Speaking Practice.

Content models (Course / Chapter / Lesson / Exercise) are managed through
the friendly Content Manager hub (/manage/content/) instead of four
separate raw admin tables. This site therefore replaces those four models
in the admin navigation with a single "Content Manager" link, and groups
the remaining models by job (content / people / links & practice) so the
menu reflects how the admin actually works.
"""
from django.conf import settings
from django.contrib.admin import AdminSite
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect
from django.urls import reverse

CONTENT_MODEL_NAMES = {'course', 'chapter', 'lesson', 'exercise'}

NAV_GROUPS = [
    ('\U0001F4DA Learning Content', ['ContentManager']),
    ('\U0001F465 People', ['User', 'TeacherProfile', 'StudentProfile', 'ParentProfile']),
    ('\U0001F517 Links & Practice', ['TeacherStudent', 'StudentParent', 'StudentLesson', 'SpeakingAttempt']),
]


class ESPAdminSite(AdminSite):
    site_header = 'English Speaking Practice'
    site_title = 'ESP Admin'
    index_title = 'Site administration'

    def login(self, request, extra_context=None):
        """Honor the opt-in 'Remember me' checkbox.

        Without it the session expires when the browser closes, so the
        account is never kept logged in without explicit permission.
        """
        response = super().login(request, extra_context)
        if request.method == 'POST' and request.user.is_authenticated:
            if request.POST.get('remember_me'):
                request.session.set_expiry(settings.SESSION_COOKIE_AGE)
            else:
                request.session.set_expiry(0)
        return response

    def logout(self, request, extra_context=None):
        """Skip the intermediate 'Logged out' page — go straight to login."""
        auth_logout(request)
        return redirect(reverse('admin:login'))

    def app_index(self, request, app_label, extra_context=None):
        """The old app overview is retired: the Management Center
        (/manage/) now covers it, so redirect there."""
        if app_label == 'speaking_practice':
            return redirect('manage_center')
        return super().app_index(request, app_label, extra_context)

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        order = {}
        group_of = {}
        for gi, (group_name, object_names) in enumerate(NAV_GROUPS):
            for mi, object_name in enumerate(object_names):
                order[object_name] = (gi, mi)
                group_of[object_name] = group_name
        for app in app_list:
            if app['app_label'] != 'speaking_practice':
                continue
            models = [
                model for model in app['models']
                if model['object_name'].lower() not in CONTENT_MODEL_NAMES
            ]
            models.insert(0, {
                'object_name': 'ContentManager',
                'name': 'Content Manager',
                'admin_url': reverse('manage_center'),
                'add_url': None,
                'view_only': False,
            })
            for model in models:
                model['esp_group'] = group_of.get(model['object_name'], '')
            models.sort(key=lambda m: order.get(m['object_name'], (99, 99)))
            app['models'] = models
        return app_list


esp_admin_site = ESPAdminSite()
