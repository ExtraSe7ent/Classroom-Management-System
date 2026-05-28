from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Admin
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('classes/', views.class_list, name='class_list'),
    path('classes/<int:pk>/', views.class_detail, name='class_detail'),
    path('classes/<int:pk>/schedule/', views.schedule, name='schedule'),
    path('students/', views.student_list, name='student_list'),
    path('attendance/', views.attendance, name='attendance'),
    path('assignments/', views.assignment_list, name='assignment_list'),
    path('assignments/<int:pk>/grading/', views.grading, name='grading'),

    # User
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('my-schedule/', views.user_schedule, name='user_schedule'),
    path('my-attendance/', views.user_attendance, name='user_attendance'),
    path('my-assignments/', views.user_assignment_list, name='user_assignment_list'),
    path('my-assignments/<int:pk>/', views.user_assignment_detail, name='user_assignment_detail'),

    # Chung
    path('profile/', views.profile, name='profile'),
]