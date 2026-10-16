from django.urls import path
from django.views.generic import RedirectView
from . import views
from . import views_auth
from . import views_manage

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('lessons/', views.lesson_list, name='lesson_list'),
    path('lesson/<int:lesson_id>/', views.lesson_detail, name='lesson_detail'),
    path('lesson/<int:lesson_id>/attempt/<int:exercise_id>/', views.create_speaking_attempt, name='create_speaking_attempt'),
    path('attempt/<int:attempt_id>/edit/', views.update_speaking_attempt, name='update_speaking_attempt'),
    
    # Teacher lesson management URLs
    path('teacher/lesson/create/', views.teacher_create_lesson, name='teacher_create_lesson'),
    path('teacher/lesson/<int:lesson_id>/edit/', views.teacher_edit_lesson, name='teacher_edit_lesson'),
    path('teacher/lesson/<int:lesson_id>/delete/', views.teacher_delete_lesson, name='teacher_delete_lesson'),

    # Management Center: one page, three tabs
    # (Learning Content | People | Links & Practice).
    path('manage/', views_manage.management_center, name='manage_center'),
    path('manage/content/', RedirectView.as_view(pattern_name='manage_center'),
         name='manage_content'),
    path('manage/class/add/', views_manage.class_add, name='class_add'),
    path('manage/class/<int:pk>/edit/', views_manage.class_edit, name='class_edit'),
    path('manage/class/<int:pk>/delete/', views_manage.class_delete, name='class_delete'),
    path('manage/class/<int:pk>/remove-student/<int:student_pk>/',
         views_manage.class_remove_student, name='class_remove_student'),
    path('manage/lesson/<int:pk>/preview/',
         views_manage.lesson_preview, name='lesson_preview'),
    path('manage/assign/', views_manage.assign_lessons, name='manage_assign'),
    path('manage/changelog/', views_manage.changelog_list, name='changelog_list'),
    path('manage/<str:model_name>/add/', views_manage.manage_add, name='manage_add'),
    path('manage/<str:model_name>/<int:pk>/edit/', views_manage.manage_edit, name='manage_edit'),
    path('manage/<str:model_name>/<int:pk>/delete/', views_manage.manage_delete, name='manage_delete'),
    
    path('profile/', views.profile, name='profile'),

    path('accounts/login/', views_auth.login_view, name='login'),
    path('accounts/logout/', views_auth.logout_view, name='logout'),
    path('accounts/signup/', views_auth.signup, name='signup'),
]
