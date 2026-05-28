from django.urls import path
from . import views

urlpatterns = [
    path('list/', views.classroom_list, name='classroom_list'),
    path('attendance/', views.attendance_class_list, name='attendance_class_list'),
    path('add/', views.classroom_add, name='classroom_add'),
    path('edit/<int:pk>/', views.classroom_update, name='classroom_edit'),
    path('delete/<int:pk>/', views.classroom_delete, name='classroom_delete'),
    path('detail/<int:pk>/', views.classroom_detail, name='classroom_detail'),
    path('schedule/<int:classroom_id>/', views.schedule_create, name='schedule_create'),
    path('schedule/delete/<int:pk>/', views.schedule_delete, name='schedule_delete'),
    path('attendance/<int:classroom_id>/<int:schedule_id>/<str:date_str>/', views.attendance_manage, name='attendance_manage'),
    path('review/<int:classroom_id>/<int:schedule_id>/<str:date_str>/', views.daily_review_manage, name='daily_review_manage'),
    path('my-timeline/', views.student_timeline, name='student_timeline'),
]