from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .forms import AssignmentForm, SubmissionForm, GradeForm
from .models import Assignment, Submission
from classrooms.models import ClassEnrollment

@login_required
def assignment_list(request):
    """Trang danh sách bài tập dành cho Admin/Giáo viên"""
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('dashboard_redirect')
    
    assignments = Assignment.objects.all().select_related('classroom').order_by('-created_at')
    return render(request, 'assignments/assignment_list.html', {'assignments': assignments})

@login_required
def assignment_create(request):
    """View xử lý tạo bài tập mới cho Admin/Giáo viên"""
    if not (request.user.role == 'admin' or request.user.is_superuser):
        messages.error(request, "Bạn không có quyền thực hiện chức năng này.")
        return redirect('dashboard_redirect')

    if request.method == 'POST':
        # Xử lý cả dữ liệu text và file (request.FILES)
        form = AssignmentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Hệ thống đã gửi thông báo bài tập mới đến học sinh!")
            return redirect('assignment_list')
    else:
        form = AssignmentForm()

    return render(request, 'assignments/assignment_form.html', {
        'form': form,
        'title': 'Giao bài tập về nhà'
    })

@login_required
def assignment_update(request, pk):
    """Cập nhật nội dung bài tập"""
    assignment = get_object_or_404(Assignment, pk=pk)
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('dashboard_redirect')

    if request.method == 'POST':
        form = AssignmentForm(request.POST, request.FILES, instance=assignment)
        if form.is_valid():
            form.save()
            messages.success(request, f"Đã cập nhật bài tập: {assignment.title}")
            return redirect('assignment_list')
    else:
        form = AssignmentForm(instance=assignment)

    return render(request, 'assignments/assignment_form.html', {
        'form': form,
        'title': f'Sửa bài tập: {assignment.title}'
    })

@login_required
def assignment_delete(request, pk):
    """Xóa bài tập"""
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('dashboard_redirect')
    
    assignment = get_object_or_404(Assignment, pk=pk)
    if request.method == 'POST':
        title = assignment.title
        assignment.delete()
        messages.success(request, f"Đã xóa bài tập '{title}' thành công.")
    return redirect('assignment_list')

@login_required
def assignment_detail(request, pk):
    """Xem chi tiết bài tập và danh sách học sinh nộp bài"""
    assignment = get_object_or_404(Assignment.objects.select_related('classroom'), pk=pk)
    submissions = assignment.submissions.all().select_related('student')
    
    return render(request, 'assignments/assignment_detail.html', {
        'assignment': assignment,
        'submissions': submissions
    })

@login_required
def student_assignment_list(request):
    """Danh sách bài tập của các lớp học sinh đã tham gia"""
    if request.user.role != 'student':
        return redirect('dashboard_redirect')

    # Lấy danh sách ID các lớp học sinh đã tham gia
    enrolled_class_ids = ClassEnrollment.objects.filter(student=request.user).values_list('classroom_id', flat=True)
    
    # Lấy bài tập thuộc các lớp đó
    assignments = Assignment.objects.filter(classroom_id__in=enrolled_class_ids).select_related('classroom').order_by('-created_at')
    
    # Lấy danh sách ID các bài đã nộp để hiển thị trạng thái
    submitted_ids = Submission.objects.filter(student=request.user).values_list('assignment_id', flat=True)
    
    now = timezone.now()

    return render(request, 'assignments/student_assignment_list.html', {
        'assignments': assignments,
        'submitted_ids': submitted_ids,
        'now': now
    })

@login_required
def student_submit_assignment(request, pk):
    """Chi tiết và nộp bài tập dành cho học sinh"""
    assignment = get_object_or_404(Assignment, pk=pk)
    submission = Submission.objects.filter(assignment=assignment, student=request.user).first()
    
    now = timezone.now()
    # BR_DUE_DATE_LOCK: Kiểm tra xem đã quá hạn chưa
    is_overdue = now > assignment.due_date

    if request.method == 'POST':
        # Chặn submit nếu quá hạn (Bảo mật tầng Backend)
        if is_overdue:
            messages.error(request, "Hệ thống đã khóa tính năng nộp bài do quá hạn.")
            return redirect('student_submit_assignment', pk=pk)

        form = SubmissionForm(request.POST, request.FILES, instance=submission)
        if form.is_valid():
            new_submission = form.save(commit=False)
            new_submission.assignment = assignment
            new_submission.student = request.user
            new_submission.save()
            messages.success(request, "Nộp bài làm thành công!")
            return redirect('student_assignment_list')
    else:
        form = SubmissionForm(instance=submission)

    return render(request, 'assignments/student_assignment_detail.html', {
        'assignment': assignment,
        'submission': submission,
        'form': form,
        'is_overdue': is_overdue,
        'now': now
    })

@login_required
def grade_assignment_list(request, pk):
    """Trang xem danh sách học sinh và trạng thái nộp bài để chấm điểm (UC08)"""
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('dashboard_redirect')
    
    assignment = get_object_or_404(Assignment, pk=pk)
    # Lấy toàn bộ học sinh trong lớp của bài tập này
    enrollments = ClassEnrollment.objects.filter(classroom=assignment.classroom).select_related('student')
    
    # Ánh xạ Submission theo student_id để tra cứu nhanh (Optimization)
    submissions_qs = Submission.objects.filter(assignment=assignment)
    submissions_map = {s.student_id: s for s in submissions_qs}
    
    grading_data = []
    for enr in enrollments:
        grading_data.append({
            'student': enr.student,
            'submission': submissions_map.get(enr.student.id)
        })
        
    return render(request, 'assignments/grade_form.html', {
        'assignment': assignment,
        'grading_data': grading_data
    })

@login_required
def submit_grade(request, submission_id):
    """Xử lý lưu điểm và nhận xét cho một học sinh (UC08)"""
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('dashboard_redirect')
        
    submission = get_object_or_404(Submission, id=submission_id)
    if request.method == 'POST':
        form = GradeForm(request.POST, instance=submission)
        if form.is_valid():
            form.save()
            messages.success(request, f"Đã lưu điểm cho học sinh {submission.student.get_full_name()}.")
        else:
            # Lấy lỗi đầu tiên từ EX_INVALID_GRADE gửi về UI
            messages.error(request, form.errors.get('grade', ["Lỗi dữ liệu"])[0])
            
    return redirect('grade_assignment_list', pk=submission.assignment.id)