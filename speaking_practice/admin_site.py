"""
Custom Django admin site for English Speaking Practice.

Content models (Course / Chapter / Lesson / Exercise) are managed through
the friendly Content Manager hub (/manage/content/) instead of four
separate raw admin tables. This site therefore replaces those four models
in the admin navigation with a single "Content Manager" link, and groups
the remaining models by job (content / people / links & practice) so the
menu reflects how the admin actually works.
"""
from django.contrib.admin import AdminSite
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
                'admin_url': reverse('manage_content'),
                'add_url': None,
                'view_only': False,
            })
            for model in models:
                model['esp_group'] = group_of.get(model['object_name'], '')
            models.sort(key=lambda m: order.get(m['object_name'], (99, 99)))
            app['models'] = models
        return app_list


esp_admin_site = ESPAdminSite()
