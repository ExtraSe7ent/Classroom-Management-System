from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    path('register/', views.RegisterView.as_view(), name='register'),
    path('forgot-password/send-otp/', views.SendOTPView.as_view(), name='send_otp'),
    path('forgot-password/reset/', views.ResetPasswordView.as_view(), name='reset_password'),

    # Teacher
    path('teacher-dashboard/', views.TeacherDashboardView.as_view(), name='teacher_dashboard'),
    path('classes/', views.ClassListView.as_view(), name='class_list'),
    path('classes/<int:pk>/', views.ClassDetailView.as_view(), name='class_detail'),
    path('classes/<int:pk>/schedule/', views.ScheduleView.as_view(), name='schedule'),
    path('students/', views.StudentListView.as_view(), name='student_list'),
    path('attendance/', views.AttendanceView.as_view(), name='attendance'),
    path('assignments/', views.AssignmentListView.as_view(), name='assignment_list'),
    path('assignments/<int:pk>/grading/', views.GradingView.as_view(), name='grading'),

    # Student
    path('student-dashboard/', views.StudentDashboardView.as_view(), name='student_dashboard'),
    path('my-schedule/', views.StudentScheduleView.as_view(), name='student_schedule'),
    path('my-attendance/', views.StudentAttendanceView.as_view(), name='student_attendance'),
    path('my-assignments/', views.StudentAssignmentListView.as_view(), name='student_assignment_list'),
    path('my-assignments/<int:pk>/', views.StudentAssignmentDetailView.as_view(), name='student_assignment_detail'),

    # Chung
    path('profile/', views.ProfileView.as_view(), name='profile'),
]
