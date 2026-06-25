"""
Views của app assignments — Class-based Views.

Phân quyền:
- Giao/sửa/xóa/chấm bài: Admin + Giáo viên (giáo viên chỉ thao tác lớp mình phụ trách).
- Xem & nộp bài, xem điểm: Học sinh (chỉ với lớp mình đã ghi danh).
"""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from accounts.permissions import StaffRequiredMixin, StudentRequiredMixin
from classrooms.models import Classroom, ClassEnrollment

from .forms import AssignmentForm, GradeForm, SubmissionForm
from .models import Assignment, Submission


def _can_manage_assignment(user, assignment):
    """Admin quản lý mọi bài; giáo viên chỉ bài thuộc lớp mình phụ trách."""
    return user.is_admin or (user.is_teacher and assignment.classroom.teacher_id == user.id)


class _AssignmentFormMixin:
    """Giới hạn danh sách lớp trong form: giáo viên chỉ chọn được lớp mình phụ trách."""
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.request.user.is_teacher:
            form.fields['classroom'].queryset = Classroom.objects.filter(teacher=self.request.user)
        return form


# ===================================================================
# QUẢN LÝ BÀI TẬP (UC07) — Admin + Giáo viên
# ===================================================================
class AssignmentListView(StaffRequiredMixin, ListView):
    template_name = 'assignments/assignment_list.html'
    context_object_name = 'assignments'

    def get_queryset(self):
        qs = Assignment.objects.select_related('classroom').order_by('-created_at')
        if self.request.user.is_teacher:
            qs = qs.filter(classroom__teacher=self.request.user)
        return qs


class AssignmentCreateView(StaffRequiredMixin, _AssignmentFormMixin, CreateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = 'assignments/assignment_form.html'
    success_url = reverse_lazy('assignment_list')
    extra_context = {'title': 'Giao bài tập về nhà'}

    def form_valid(self, form):
        messages.success(self.request, "Hệ thống đã gửi thông báo bài tập mới đến học sinh!")
        return super().form_valid(form)


class AssignmentUpdateView(StaffRequiredMixin, _AssignmentFormMixin, UpdateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = 'assignments/assignment_form.html'
    success_url = reverse_lazy('assignment_list')

    def get_queryset(self):
        qs = Assignment.objects.all()
        if self.request.user.is_teacher:
            qs = qs.filter(classroom__teacher=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Sửa bài tập: {self.object.title}'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f"Đã cập nhật bài tập: {form.instance.title}")
        return super().form_valid(form)


class AssignmentDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        assignment = get_object_or_404(Assignment, pk=pk)
        if not _can_manage_assignment(request.user, assignment):
            messages.error(request, "Bạn không có quyền xóa bài tập này.")
            return redirect('assignment_list')
        title = assignment.title
        assignment.delete()
        messages.success(request, f"Đã xóa bài tập '{title}' thành công.")
        return redirect('assignment_list')

    def get(self, request, pk):
        return redirect('assignment_list')


class AssignmentDetailView(StaffRequiredMixin, View):
    template_name = 'assignments/assignment_detail.html'

    def get(self, request, pk):
        assignment = get_object_or_404(Assignment.objects.select_related('classroom'), pk=pk)
        if not _can_manage_assignment(request.user, assignment):
            messages.error(request, "Bạn không có quyền xem bài tập này.")
            return redirect('assignment_list')
        submissions = assignment.submissions.select_related('student')
        return render(request, self.template_name,
                      {'assignment': assignment, 'submissions': submissions})


# ===================================================================
# CHẤM ĐIỂM (UC08) — Admin + Giáo viên
# ===================================================================
class GradeAssignmentListView(StaffRequiredMixin, View):
    template_name = 'assignments/grade_form.html'

    def get(self, request, pk):
        assignment = get_object_or_404(Assignment, pk=pk)
        if not _can_manage_assignment(request.user, assignment):
            messages.error(request, "Bạn không có quyền chấm bài tập này.")
            return redirect('assignment_list')
        enrollments = ClassEnrollment.objects.filter(
            classroom=assignment.classroom
        ).select_related('student')
        submissions_map = {s.student_id: s for s in Submission.objects.filter(assignment=assignment)}
        grading_data = [
            {'student': e.student, 'submission': submissions_map.get(e.student.id)}
            for e in enrollments
        ]
        return render(request, self.template_name,
                      {'assignment': assignment, 'grading_data': grading_data})


class SubmitGradeView(StaffRequiredMixin, View):
    def post(self, request, submission_id):
        submission = get_object_or_404(Submission, id=submission_id)
        if not _can_manage_assignment(request.user, submission.assignment):
            messages.error(request, "Bạn không có quyền chấm bài này.")
            return redirect('assignment_list')
        form = GradeForm(request.POST, instance=submission)
        if form.is_valid():
            graded_sub = form.save(commit=False)
            graded_sub.status = Submission.STATUS_GRADED  # đánh dấu đã chấm xong
            graded_sub.save()
            messages.success(
                request,
                f"Đã lưu điểm cho học sinh {submission.student.get_full_name() or submission.student.username}.",
            )
        else:
            messages.error(request, form.errors.get('grade', ["Dữ liệu không hợp lệ"])[0])
        return redirect('grade_assignment_list', pk=submission.assignment_id)

    def get(self, request, submission_id):
        submission = get_object_or_404(Submission, id=submission_id)
        return redirect('grade_assignment_list', pk=submission.assignment_id)


# ===================================================================
# PHÍA HỌC SINH (UC11, UC12)
# ===================================================================
class StudentAssignmentListView(StudentRequiredMixin, View):
    """Danh sách bài tập theo tab trạng thái: Chưa làm / Đang chấm / Đã có điểm."""
    template_name = 'assignments/student_assignment_list.html'

    def get(self, request):
        enrolled_ids = ClassEnrollment.objects.filter(
            student=request.user
        ).values_list('classroom_id', flat=True)
        assignments = (Assignment.objects.filter(classroom_id__in=enrolled_ids)
                       .select_related('classroom').order_by('-created_at'))
        subs = {s.assignment_id: s for s in Submission.objects.filter(student=request.user)}
        now = timezone.now()

        todo, grading, graded = [], [], []
        for a in assignments:
            sub = subs.get(a.id)
            item = {'a': a, 'sub': sub, 'is_overdue': now > a.due_date}
            if sub and sub.status == Submission.STATUS_GRADED:
                graded.append(item)
            elif sub:  # status == pending
                grading.append(item)
            else:
                todo.append(item)

        return render(request, self.template_name, {
            'todo': todo, 'grading': grading, 'graded': graded, 'now': now,
        })


class StudentSubmitAssignmentView(StudentRequiredMixin, View):
    """Xem chi tiết + nộp bài (UC11) và xem điểm (UC12)."""
    template_name = 'assignments/student_assignment_detail.html'

    def _get_assignment(self, request, pk):
        assignment = get_object_or_404(Assignment, pk=pk)
        enrolled = ClassEnrollment.objects.filter(
            student=request.user, classroom=assignment.classroom
        ).exists()
        return assignment, enrolled

    def get(self, request, pk):
        assignment, enrolled = self._get_assignment(request, pk)
        if not enrolled:
            messages.error(request, "Bạn không thuộc lớp của bài tập này.")
            return redirect('student_assignment_list')
        submission = Submission.objects.filter(assignment=assignment, student=request.user).first()
        return render(request, self.template_name, {
            'assignment': assignment, 'submission': submission,
            'form': SubmissionForm(instance=submission),
            'is_overdue': timezone.now() > assignment.due_date, 'now': timezone.now(),
        })

    def post(self, request, pk):
        assignment, enrolled = self._get_assignment(request, pk)
        if not enrolled:
            messages.error(request, "Bạn không thuộc lớp của bài tập này.")
            return redirect('student_assignment_list')

        # BR_DUE_DATE_LOCK: chặn nộp khi đã quá hạn (bảo vệ tầng backend)
        if timezone.now() > assignment.due_date:
            messages.error(request, "Hệ thống đã khóa tính năng nộp bài do quá hạn.")
            return redirect('student_submit_assignment', pk=pk)

        submission = Submission.objects.filter(assignment=assignment, student=request.user).first()
        form = SubmissionForm(request.POST, request.FILES, instance=submission)
        if form.is_valid():
            new_sub = form.save(commit=False)
            new_sub.assignment = assignment
            new_sub.student = request.user
            new_sub.save()
            messages.success(request, "Nộp bài làm thành công!")
            return redirect('student_assignment_list')

        return render(request, self.template_name, {
            'assignment': assignment, 'submission': submission, 'form': form,
            'is_overdue': False, 'now': timezone.now(),
        })
