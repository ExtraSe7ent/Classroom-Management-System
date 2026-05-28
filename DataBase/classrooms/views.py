from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime
from .models import Classroom, Schedule, ClassEnrollment, Attendance, DailyComment
from accounts.models import User
from .forms import ClassroomForm, ScheduleForm, EnrollmentForm

@login_required
def classroom_list(request):
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('user_dashboard')
    
    # Sử dụng annotate để đếm sĩ số học sinh trực tiếp từ SQL Server
    classes = Classroom.objects.select_related('teacher').annotate(student_count=Count('enrollments')).all().order_by('-id')
    return render(request, 'classrooms/classroom_list.html', {'classes': classes})

@login_required
def classroom_add(request):
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('user_dashboard')
    
    if request.method == 'POST':
        form = ClassroomForm(request.POST)
        if form.is_valid():
            new_class = form.save()
            messages.success(request, f"Đã tạo lớp học {new_class.name} thành công. Hãy thêm học sinh và lịch học!")
            # Điều hướng thẳng vào trang chi tiết để add học sinh luôn
            return redirect('classroom_detail', pk=new_class.id)
    else:
        # Mặc định chọn giáo viên là người đang đăng nhập
        form = ClassroomForm(initial={'teacher': request.user})
    return render(request, 'classrooms/classroom_form.html', {'form': form, 'title': 'Tạo lớp học mới'})

@login_required
def classroom_update(request, pk):
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('user_dashboard')
    
    classroom = get_object_or_404(Classroom, pk=pk)
    if request.method == 'POST':
        form = ClassroomForm(request.POST, instance=classroom)
        if form.is_valid():
            form.save()
            messages.success(request, f"Đã cập nhật lớp {classroom.name}")
            return redirect('classroom_list')
    else:
        form = ClassroomForm(instance=classroom)
    return render(request, 'classrooms/classroom_form.html', {'form': form, 'title': f'Sửa lớp {classroom.name}'})

@login_required
def classroom_delete(request, pk):
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('user_dashboard')
    
    classroom = get_object_or_404(Classroom, pk=pk)
    if request.method == 'POST':
        name = classroom.name
        classroom.delete()
        messages.success(request, f"Đã xóa lớp {name} thành công.")
    return redirect('classroom_list')

@login_required
def schedule_create(request, classroom_id):
    """Xử lý xếp lịch học cho một lớp cụ thể với validation trùng lịch"""
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('user_dashboard')
    
    classroom = get_object_or_404(Classroom, id=classroom_id)
    form = ScheduleForm() # Khởi tạo form mặc định cho phương thức GET

    if request.method == 'POST':
        form = ScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.classroom = classroom
            try:
                schedule.save() # Trigger clean() and save()
                messages.success(request, "Xếp lịch học thành công!")
                return redirect('classroom_detail', pk=classroom_id) # Chuyển hướng về chi tiết lớp để xem kết quả
            except ValidationError as e:
                # Lấy lỗi đầu tiên từ ValidationError để hiển thị cho người dùng
                error_msg = e.messages[0] if hasattr(e, 'messages') else str(e)
                messages.error(request, error_msg)
            except Exception as e:
                messages.error(request, "Có lỗi xảy ra trong quá trình lưu dữ liệu.")
    
    return render(request, 'classrooms/schedule_form.html', {'form': form, 'classroom': classroom})

@login_required
def schedule_delete(request, pk):
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('user_dashboard')
    schedule = get_object_or_404(Schedule, pk=pk)
    classroom_id = schedule.classroom.id
    schedule.delete()
    messages.success(request, "Đã xóa buổi học thành công.")
    return redirect('classroom_detail', pk=classroom_id)

@login_required
def classroom_detail(request, pk):
    """Trang quản trị chi tiết một lớp học: Xem lịch, danh sách HS và Ghi danh"""
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('user_dashboard')
    
    classroom = get_object_or_404(Classroom, pk=pk)
    schedules = classroom.schedules.all().order_by('day_of_week', 'start_time')
    
    # Lấy danh sách các buổi học đã được điểm danh trong ngày hôm nay của lớp này
    today = timezone.now().date()
    attended_ids = set(Attendance.objects.filter(classroom=classroom, date=today).values_list('schedule_id', flat=True))

    # 1. Quản lý danh sách học sinh ĐANG TRONG LỚP
    q_enrolled = request.GET.get('q_enrolled', '')
    enrollments = classroom.enrollments.all().select_related('student')
    if q_enrolled:
        enrollments = enrollments.filter(
            # Tìm kiếm theo username, first_name, last_name của học sinh
            Q(student__username__icontains=q_enrolled) | 
            Q(student__first_name__icontains=q_enrolled) | 
            Q(student__last_name__icontains=q_enrolled)
        )

    # 2. Xử lý TÌM KIẾM HỌC SINH ĐỂ ADD (Chưa có trong lớp)
    q_potential = request.GET.get('q_potential', '')
    already_enrolled = classroom.enrollments.values_list('student_id', flat=True)
    potential_students = User.objects.filter(role='student').exclude(id__in=already_enrolled).select_related('student_profile')
    
    if q_potential:
        # Tìm kiếm theo username, first_name, last_name, student_code của học sinh tiềm năng
        potential_students = potential_students.filter(
            Q(username__icontains=q_potential) | 
            Q(first_name__icontains=q_potential) | 
            Q(last_name__icontains=q_potential) |
            Q(student_profile__student_code__icontains=q_potential)
        )
    else:
        # Mặc định lấy 10 học sinh mới nhất chưa có lớp để hiển thị sẵn nếu không có query
        potential_students = potential_students.order_by('-date_joined')[:10]

    enroll_form = EnrollmentForm()

    if request.method == 'POST':
        # Xử lý xóa học sinh khỏi lớp
        if 'remove_student' in request.POST:
            enrollment_id = request.POST.get('enrollment_id')
            enroll_obj = get_object_or_404(ClassEnrollment, id=enrollment_id, classroom=classroom)
            enroll_obj.delete()
            messages.success(request, "Đã xóa học sinh khỏi lớp.")
            return redirect('classroom_detail', pk=pk)
            
        # Xử lý XÓA HÀNG LOẠT học sinh khỏi lớp
        if 'bulk_remove' in request.POST:
            enrollment_ids = request.POST.getlist('enrollment_ids')
            if enrollment_ids:
                deleted_count, _ = ClassEnrollment.objects.filter(id__in=enrollment_ids, classroom=classroom).delete()
                messages.success(request, f"Đã xóa {deleted_count} học sinh khỏi lớp.")
            else:
                messages.warning(request, "Vui lòng chọn ít nhất một học sinh để xóa.")
            return redirect('classroom_detail', pk=pk)

        # Xử lý ADD NHIỀU HỌC SINH VÀO LỚP (Ghi danh hàng loạt)
        if 'add_to_class' in request.POST:
            student_ids = request.POST.getlist('student') # Lấy danh sách ID từ checkbox
            base_url = reverse('classroom_detail', kwargs={'pk': pk})
            
            if not student_ids:
                messages.error(request, "Vui lòng chọn ít nhất một học sinh để thêm.")
                return redirect(f"{base_url}?open_modal=1")
            
            added_count = 0
            for s_id in student_ids:
                if not ClassEnrollment.objects.filter(classroom=classroom, student_id=s_id).exists():
                    ClassEnrollment.objects.create(classroom=classroom, student_id=int(s_id))
                    added_count += 1
            
            messages.success(request, f"Đã ghi danh thành công {added_count} học sinh mới.")
            return redirect('classroom_detail', pk=pk)
    
    context = {
        'classroom': classroom,
        'schedules': schedules,
        'attended_schedule_ids': attended_ids,
        'enrollments': enrollments,
        'enroll_form': enroll_form,
        'potential_students': potential_students,
        'q_enrolled': q_enrolled,
        'q_potential': q_potential,
    }
    # Kiểm tra nếu có tham số open_modal từ GET request, thêm vào context để JS mở modal
    if request.GET.get('open_modal') == '1':
        context['open_enroll_modal'] = True
    return render(request, 'classrooms/classroom_detail.html', context)

@login_required
def attendance_class_list(request):
    """Trang chọn lớp học để điểm danh - Ưu tiên các lớp có lịch hôm nay"""
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('user_dashboard')

    # Lấy ngày từ tham số GET (nếu có), mặc định là ngày hôm nay
    date_str = request.GET.get('date')
    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            target_date = timezone.localdate()
    else:
        target_date = timezone.localdate()

    weekday = target_date.weekday() # Python: 0 (T2) -> 6 (CN)

    # 1. Lấy các buổi học diễn ra vào ngày được chọn
    schedules_target_day = list(Schedule.objects.filter(day_of_week=weekday).select_related('classroom'))
    
    # Lấy danh sách ID các buổi học đã được điểm danh trong ngày đó
    attended_ids = set(Attendance.objects.filter(date=target_date).values_list('schedule_id', flat=True).distinct())

    for s in schedules_target_day:
        s.is_attended = s.id in attended_ids

    # 2. Lấy tất cả các lớp khác để xem lại lịch sử nếu cần
    all_classrooms = Classroom.objects.all().order_by('name')

    return render(request, 'classrooms/attendance_class_list.html', {
        'schedules_today': schedules_target_day,
        'all_classrooms': all_classrooms,
        'today': target_date,
        'is_real_today': target_date == timezone.localdate()
    })

@login_required
def attendance_manage(request, classroom_id, schedule_id, date_str):
    """Xử lý điểm danh học sinh cho một buổi học cụ thể UC05"""
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('user_dashboard')

    classroom = get_object_or_404(Classroom, pk=classroom_id)
    schedule = get_object_or_404(Schedule, pk=schedule_id, classroom=classroom)
    
    # Chuyển đổi date_str thành object date
    try:
        if date_str == 'today':
            target_date = timezone.localdate()
        else:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, "Định dạng ngày không hợp lệ.")
        return redirect('classroom_detail', pk=classroom_id)

    # EX_FUTURE_DATE: Chặn điểm danh cho ngày trong tương lai dựa trên localdate
    if target_date > timezone.localdate():
        messages.error(request, "Không thể điểm danh cho buổi học chưa diễn ra!")
        return redirect('classroom_detail', pk=classroom_id)

    # Lấy danh sách học sinh đã ghi danh vào lớp
    enrollments = ClassEnrollment.objects.filter(classroom=classroom).select_related('student')
    
    # EX_EMPTY_CLASS: Kiểm tra lớp trống
    if not enrollments.exists():
        messages.warning(request, "Lớp học hiện tại chưa có học sinh nào để điểm danh.")
        return redirect('classroom_detail', pk=classroom_id)

    # Lấy dữ liệu điểm danh đã tồn tại (nếu có) - EX_ALREADY_ATTENDED
    existing_attendance = Attendance.objects.filter(
        classroom=classroom, schedule=schedule, date=target_date
    ).values('student_id', 'status', 'remark')
    
    # Chuyển thành dictionary để lookup nhanh trong template
    attendance_map = {item['student_id']: item for item in existing_attendance}

    if request.method == 'POST':
        try:
            with transaction.atomic():
                for enrollment in enrollments:
                    student = enrollment.student
                    status = request.POST.get(f'status_{student.id}')
                    remark = request.POST.get(f'remark_{student.id}', '')

                    if status:
                        Attendance.objects.update_or_create(
                            classroom=classroom,
                            student=student,
                            schedule=schedule,
                            date=target_date,
                            defaults={'status': status, 'remark': remark}
                        )
                
                messages.success(request, f"Đã cập nhật bảng điểm danh ngày {target_date} thành công.")
                return redirect('classroom_detail', pk=classroom_id)
        except Exception as e:
            messages.error(request, f"Lỗi khi lưu dữ liệu: {str(e)}")

    # Định nghĩa context bên trong hàm và trước khi render
    context = {
        'classroom': classroom,
        'schedule': schedule,
        'target_date': target_date,
        'enrollments': enrollments,
        'attendance_map': attendance_map,
        'status_choices': Attendance.STATUS_CHOICES,
    }
    return render(request, 'classrooms/attendance_form.html', context)

@login_required
def student_timeline(request):
    """Dòng thời gian học tập dành cho Học sinh (UC10)"""
    if not request.user.role == 'student':
        return redirect('admin_dashboard')
    
    # Lấy lịch sử điểm danh của học sinh này
    attendances = Attendance.objects.filter(student=request.user).select_related('classroom', 'schedule').order_by('-date', '-schedule__start_time')
    
    # Có thể kết hợp với DailyComments sau này tại đây
    
    context = {'attendances': attendances}
    return render(request, 'classrooms/student_timeline.html', context)

@login_required
def daily_review_manage(request, classroom_id, schedule_id, date_str):
    """Xử lý nhập nhận xét hàng ngày hàng loạt UC06"""
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('user_dashboard')

    classroom = get_object_or_404(Classroom, pk=classroom_id)
    schedule = get_object_or_404(Schedule, pk=schedule_id, classroom=classroom)
    
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return redirect('classroom_detail', pk=classroom_id)

    # EX_FUTURE_DATE: Chặn nhận xét cho ngày tương lai
    if target_date > timezone.localdate():
        messages.error(request, "Không thể nhập nhận xét cho buổi học chưa diễn ra!")
        return redirect('classroom_detail', pk=classroom_id)

    enrollments = ClassEnrollment.objects.filter(classroom=classroom).select_related('student')
    
    # Lấy thông tin điểm danh để hiển thị (UX giúp giáo viên nhớ tình hình buổi học)
    attendance_records = Attendance.objects.filter(classroom=classroom, schedule=schedule, date=target_date)
    attendance_map = {att.student_id: att for att in attendance_records}

    # Lấy nhận xét cũ (nếu có) để hiển thị lên form
    existing_comments = DailyComment.objects.filter(classroom=classroom, schedule=schedule, date=target_date)
    comment_map = {comm.student_id: comm.content for comm in existing_comments}

    if request.method == 'POST':
        try:
            with transaction.atomic():
                has_any_content = False
                for enrollment in enrollments:
                    student_id = enrollment.student.id
                    content = request.POST.get(f'comment_{student_id}', '').strip()
                    
                    if content:
                        has_any_content = True
                        DailyComment.objects.update_or_create(
                            classroom=classroom,
                            student=enrollment.student,
                            schedule=schedule,
                            date=target_date,
                            defaults={'content': content, 'created_by': request.user}
                        )
                
                if not has_any_content:
                    messages.warning(request, "Vui lòng nhập ít nhất một nhận xét trước khi lưu!")
                else:
                    messages.success(request, f"Đã lưu nhận xét ngày {target_date} thành công.")
                    return redirect('classroom_detail', pk=classroom_id)
        except Exception as e:
            messages.error(request, f"Lỗi hệ thống: {str(e)}")

    context = {
        'classroom': classroom,
        'schedule': schedule,
        'target_date': target_date,
        'enrollments': enrollments,
        'attendance_map': attendance_map,
        'comment_map': comment_map,
    }
    return render(request, 'classrooms/daily_review_form.html', context)
