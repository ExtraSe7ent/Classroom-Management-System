from django.urls import path

from . import views

urlpatterns = [
    # Quản lý bài tập (Admin + Giáo viên)
    path('list/', views.AssignmentListView.as_view(), name='assignment_list'),
    path('create/', views.AssignmentCreateView.as_view(), name='assignment_create'),
    path('edit/<int:pk>/', views.AssignmentUpdateView.as_view(), name='assignment_edit'),
    path('delete/<int:pk>/', views.AssignmentDeleteView.as_view(), name='assignment_delete'),
    path('detail/<int:pk>/', views.AssignmentDetailView.as_view(), name='assignment_detail'),

    # Chấm điểm (Admin + Giáo viên)
    path('grade/<int:pk>/', views.GradeAssignmentListView.as_view(), name='grade_assignment_list'),
    path('submit-grade/<int:submission_id>/', views.SubmitGradeView.as_view(), name='submit_grade'),

    # Phía học sinh
    path('my-list/', views.StudentAssignmentListView.as_view(), name='student_assignment_list'),
    path('submit/<int:pk>/', views.StudentSubmitAssignmentView.as_view(), name='student_submit_assignment'),
]
