from django.urls import path

from . import views

urlpatterns = [
    # Quản lý lớp (Admin)
    path('list/', views.ClassroomListView.as_view(), name='classroom_list'),
    path('add/', views.ClassroomCreateView.as_view(), name='classroom_add'),
    path('edit/<int:pk>/', views.ClassroomUpdateView.as_view(), name='classroom_edit'),
    path('delete/<int:pk>/', views.ClassroomDeleteView.as_view(), name='classroom_delete'),
    path('detail/<int:pk>/', views.ClassroomDetailView.as_view(), name='classroom_detail'),

    # Xếp lịch (Admin)
    path('schedule/<int:classroom_id>/', views.ScheduleCreateView.as_view(), name='schedule_create'),
    path('schedule/delete/<int:pk>/', views.ScheduleDeleteView.as_view(), name='schedule_delete'),

    # Điểm danh & nhận xét (Admin + Giáo viên)
    path('attendance/', views.AttendanceClassListView.as_view(), name='attendance_class_list'),
    path('attendance/<int:classroom_id>/<int:schedule_id>/<str:date_str>/',
         views.AttendanceManageView.as_view(), name='attendance_manage'),
    path('review/<int:classroom_id>/<int:schedule_id>/<str:date_str>/',
         views.DailyReviewManageView.as_view(), name='daily_review_manage'),

    # Phía học sinh
    path('my-schedule/', views.StudentScheduleView.as_view(), name='student_schedule'),
    path('my-timeline/', views.StudentTimelineView.as_view(), name='student_timeline'),
]
