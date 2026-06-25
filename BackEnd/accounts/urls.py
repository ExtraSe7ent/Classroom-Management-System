from django.urls import path

from . import views

urlpatterns = [
    # Authentication
    path('', views.DashboardRedirectView.as_view(), name='home'),
    path('login/', views.AppLoginView.as_view(), name='login'),
    path('logout/', views.AppLogoutView.as_view(), name='logout'),
    path('forgot-password/', views.ForgotPasswordView.as_view(), name='forgot_password'),
    path('dashboard/', views.DashboardRedirectView.as_view(), name='dashboard_redirect'),

    # Dashboard
    path('admin-dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('user-dashboard/', views.UserDashboardView.as_view(), name='user_dashboard'),

    # Student Management (Admin)
    path('students/', views.StudentListView.as_view(), name='student_list'),
    path('students/add/', views.StudentCreateView.as_view(), name='student_add'),
    path('students/edit/<int:pk>/', views.StudentUpdateView.as_view(), name='student_edit'),
    path('students/delete/<int:pk>/', views.StudentDeleteView.as_view(), name='student_delete'),

    # Personal Profile (Shared)
    path('profile/', views.ProfileView.as_view(), name='profile'),
]
