from django.urls import path
from . import views

urlpatterns = [
    path('list/', views.assignment_list, name='assignment_list'),
    path('create/', views.assignment_create, name='assignment_create'),
    path('edit/<int:pk>/', views.assignment_update, name='assignment_edit'),
    path('delete/<int:pk>/', views.assignment_delete, name='assignment_delete'),
    path('detail/<int:pk>/', views.assignment_detail, name='assignment_detail'),
    # URLs dành cho học sinh
    path('my-list/', views.student_assignment_list, name='student_assignment_list'),
    path('submit/<int:pk>/', views.student_submit_assignment, name='student_submit_assignment'),
    # Chấm điểm (Admin)
    path('grade/<int:pk>/', views.grade_assignment_list, name='grade_assignment_list'),
    path('submit-grade/<int:submission_id>/', views.submit_grade, name='submit_grade'),
]