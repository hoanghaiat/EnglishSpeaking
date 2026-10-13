from django.urls import path
from . import views
from . import views_auth
from . import views_manage

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('lessons/', views.lesson_list, name='lesson_list'),
    path('lesson/<int:lesson_id>/', views.lesson_detail, name='lesson_detail'),
    path('lesson/<int:lesson_id>/attempt/<int:exercise_id>/', views.create_speaking_attempt, name='create_speaking_attempt'),
    
    # Teacher lesson management URLs
    path('teacher/lesson/create/', views.teacher_create_lesson, name='teacher_create_lesson'),
    path('teacher/lesson/<int:lesson_id>/edit/', views.teacher_edit_lesson, name='teacher_edit_lesson'),
    path('teacher/lesson/<int:lesson_id>/delete/', views.teacher_delete_lesson, name='teacher_delete_lesson'),

    # Admin content management: one hub for Course > Chapter > Lesson > Exercise
    path('manage/content/', views_manage.content_hub, name='manage_content'),
    path('manage/<str:model_name>/add/', views_manage.manage_add, name='manage_add'),
    path('manage/<str:model_name>/<int:pk>/edit/', views_manage.manage_edit, name='manage_edit'),
    path('manage/<str:model_name>/<int:pk>/delete/', views_manage.manage_delete, name='manage_delete'),
    
    path('profile/', views.profile, name='profile'),

    path('accounts/login/', views_auth.login_view, name='login'),
    path('accounts/logout/', views_auth.logout_view, name='logout'),
    path('accounts/signup/', views_auth.signup, name='signup'),
]
