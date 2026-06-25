"""
Views của app classrooms — Class-based Views.

Phân quyền:
- Quản lý lớp/lịch/ghi danh: chỉ Admin.
- Điểm danh & nhận xét: Admin + Giáo viên (giáo viên chỉ thao tác lớp mình phụ trách).
- Xem lịch học & dòng thời gian: Học sinh.
"""
from collections import defaultdict
from datetime import datetime

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from accounts.models import User
from accounts.permissions import (
    AdminRequiredMixin, StaffRequiredMixin, StudentRequiredMixin,
)

from .forms import ClassroomForm, EnrollmentForm, ScheduleForm
from .models import Attendance, Classroom, ClassEnrollment, DailyComment, Schedule


def _can_access_classroom(user, classroom):
    """Admin xem mọi lớp; giáo viên chỉ thao tác lớp mình phụ trách."""
    return user.is_admin or (user.is_teacher and classroom.teacher_id == user.id)


# ===================================================================
# QUẢN LÝ LỚP HỌC (UC04) — Admin
# ===================================================================
class ClassroomListView(AdminRequiredMixin, ListView):
    template_name = 'classrooms/classroom_list.html'
    context_object_name = 'classes'

    def get_queryset(self):
        return (Classroom.objects
                .select_related('teacher')
                .annotate(student_count=Count('enrollments'))
                .order_by('-id'))


class ClassroomCreateView(AdminRequiredMixin, CreateView):
    model = Classroom
    form_class = ClassroomForm
    template_name = 'classrooms/classroom_form.html'
    extra_context = {'title': 'Tạo lớp học mới'}

    def get_initial(self):
        return {'teacher': self.request.user}

    def form_valid(self, form):
        self.object = form.save()
        messages.success(
            self.request,
            f"Đã tạo lớp học {self.object.name} thành công. Hãy thêm học sinh và lịch học!",
        )
        return redirect('classroom_detail', pk=self.object.id)


class ClassroomUpdateView(AdminRequiredMixin, UpdateView):
    model = Classroom
    form_class = ClassroomForm
    template_name = 'classrooms/classroom_form.html'
    success_url = reverse_lazy('classroom_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Sửa lớp {self.object.name}'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f"Đã cập nhật lớp {form.instance.name}")
        return super().form_valid(form)


class ClassroomDeleteView(AdminRequiredMixin, View):
    def post(self, request, pk):
        classroom = get_object_or_404(Classroom, pk=pk)
        name = classroom.name
        classroom.delete()
        messages.success(request, f"Đã xóa lớp {name} thành công.")
        return redirect('classroom_list')

    def get(self, request, pk):
        return redirect('classroom_list')


class ClassroomDetailView(AdminRequiredMixin, View):
    """Chi tiết lớp: lịch học, danh sách HS, ghi danh/xóa học sinh."""
    template_name = 'classrooms/classroom_detail.html'

    def get(self, request, pk):
        classroom = get_object_or_404(Classroom, pk=pk)
        return render(request, self.template_name, self._context(request, classroom))

    def post(self, request, pk):
        classroom = get_object_or_404(Classroom, pk=pk)

        if 'remove_student' in request.POST:
            enroll_obj = get_object_or_404(
                ClassEnrollment, id=request.POST.get('enrollment_id'), classroom=classroom
            )
            enroll_obj.delete()
            messages.success(request, "Đã xóa học sinh khỏi lớp.")
            return redirect('classroom_detail', pk=pk)

        if 'bulk_remove' in request.POST:
            ids = request.POST.getlist('enrollment_ids')
            if ids:
                deleted, _ = ClassEnrollment.objects.filter(
                    id__in=ids, classroom=classroom
                ).delete()
                messages.success(request, f"Đã xóa {deleted} học sinh khỏi lớp.")
            else:
                messages.warning(request, "Vui lòng chọn ít nhất một học sinh để xóa.")
            return redirect('classroom_detail', pk=pk)

        if 'add_to_class' in request.POST:
            student_ids = request.POST.getlist('student')
            if not student_ids:
                messages.error(request, "Vui lòng chọn ít nhất một học sinh để thêm.")
                return redirect(f"{reverse('classroom_detail', kwargs={'pk': pk})}?open_modal=1")
            added = 0
            for s_id in student_ids:
                _, created = ClassEnrollment.objects.get_or_create(
                    classroom=classroom, student_id=int(s_id)
                )
                if created:
                    added += 1
            messages.success(request, f"Đã ghi danh thành công {added} học sinh mới.")
            return redirect('classroom_detail', pk=pk)

        return redirect('classroom_detail', pk=pk)

    def _context(self, request, classroom):
        schedules = classroom.schedules.all().order_by('day_of_week', 'start_time')
        today = timezone.localdate()
        attended_ids = set(
            Attendance.objects.filter(classroom=classroom, date=today)
            .values_list('schedule_id', flat=True)
        )

        q_enrolled = request.GET.get('q_enrolled', '')
        enrollments = classroom.enrollments.select_related('student')
        if q_enrolled:
            enrollments = enrollments.filter(
                Q(student__username__icontains=q_enrolled)
                | Q(student__first_name__icontains=q_enrolled)
                | Q(student__last_name__icontains=q_enrolled)
            )

        q_potential = request.GET.get('q_potential', '')
        already = classroom.enrollments.values_list('student_id', flat=True)
        potential = (User.objects.filter(role=User.ROLE_STUDENT)
                     .exclude(id__in=already).select_related('student_profile'))
        if q_potential:
            potential = potential.filter(
                Q(username__icontains=q_potential)
                | Q(first_name__icontains=q_potential)
                | Q(last_name__icontains=q_potential)
                | Q(student_profile__student_code__icontains=q_potential)
            )
        else:
            potential = potential.order_by('-date_joined')[:10]

        ctx = {
            'classroom': classroom,
            'schedules': schedules,
            'attended_schedule_ids': attended_ids,
            'enrollments': enrollments,
            'enroll_form': EnrollmentForm(),
            'potential_students': potential,
            'q_enrolled': q_enrolled,
            'q_potential': q_potential,
        }
        if request.GET.get('open_modal') == '1':
            ctx['open_enroll_modal'] = True
        return ctx


# ===================================================================
# XẾP LỊCH HỌC (UC04) — Admin
# ===================================================================
class ScheduleCreateView(AdminRequiredMixin, View):
    template_name = 'classrooms/schedule_form.html'

    def get(self, request, classroom_id):
        classroom = get_object_or_404(Classroom, id=classroom_id)
        return render(request, self.template_name,
                      {'form': ScheduleForm(), 'classroom': classroom})

    def post(self, request, classroom_id):
        classroom = get_object_or_404(Classroom, id=classroom_id)
        form = ScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.classroom = classroom
            try:
                schedule.save()  # kích hoạt clean() kiểm tra trùng lịch phòng
                messages.success(request, "Xếp lịch học thành công!")
                return redirect('classroom_detail', pk=classroom_id)
            except ValidationError as e:
                messages.error(request, e.messages[0] if e.messages else str(e))
        return render(request, self.template_name, {'form': form, 'classroom': classroom})


class ScheduleDeleteView(AdminRequiredMixin, View):
    def post(self, request, pk):
        schedule = get_object_or_404(Schedule, pk=pk)
        classroom_id = schedule.classroom_id
        schedule.delete()
        messages.success(request, "Đã xóa buổi học thành công.")
        return redirect('classroom_detail', pk=classroom_id)

    def get(self, request, pk):
        schedule = get_object_or_404(Schedule, pk=pk)
        return redirect('classroom_detail', pk=schedule.classroom_id)


# ===================================================================
# ĐIỂM DANH (UC05) & NHẬN XÉT (UC06) — Admin + Giáo viên
# ===================================================================
class AttendanceClassListView(StaffRequiredMixin, View):
    """Chọn lớp/buổi để điểm danh — ưu tiên buổi diễn ra trong ngày được chọn."""
    template_name = 'classrooms/attendance_class_list.html'

    def get(self, request):
        date_str = request.GET.get('date')
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                target_date = timezone.localdate()
        else:
            target_date = timezone.localdate()

        weekday = target_date.weekday()
        schedules = Schedule.objects.filter(day_of_week=weekday).select_related('classroom')
        all_classrooms = Classroom.objects.all()

        # Giáo viên chỉ thấy lớp mình phụ trách
        if request.user.is_teacher:
            schedules = schedules.filter(classroom__teacher=request.user)
            all_classrooms = all_classrooms.filter(teacher=request.user)

        schedules = list(schedules)
        attended_ids = set(
            Attendance.objects.filter(date=target_date)
            .values_list('schedule_id', flat=True).distinct()
        )
        for s in schedules:
            s.is_attended = s.id in attended_ids

        return render(request, self.template_name, {
            'schedules_today': schedules,
            'all_classrooms': all_classrooms.order_by('name'),
            'today': target_date,
            'is_real_today': target_date == timezone.localdate(),
        })


class AttendanceManageView(StaffRequiredMixin, View):
    """Điểm danh học sinh cho một buổi học cụ thể (UC05)."""
    template_name = 'classrooms/attendance_form.html'

    def _setup(self, request, classroom_id, schedule_id, date_str):
        classroom = get_object_or_404(Classroom, pk=classroom_id)
        if not _can_access_classroom(request.user, classroom):
            return None, None, None, redirect('attendance_class_list')
        schedule = get_object_or_404(Schedule, pk=schedule_id, classroom=classroom)
        try:
            target_date = (timezone.localdate() if date_str == 'today'
                           else datetime.strptime(date_str, '%Y-%m-%d').date())
        except ValueError:
            messages.error(request, "Định dạng ngày không hợp lệ.")
            return classroom, schedule, None, redirect('classroom_detail', pk=classroom_id)
        return classroom, schedule, target_date, None

    def get(self, request, classroom_id, schedule_id, date_str):
        classroom, schedule, target_date, resp = self._setup(request, classroom_id, schedule_id, date_str)
        if resp:
            return resp
        if target_date > timezone.localdate():
            messages.error(request, "Không thể điểm danh cho buổi học chưa diễn ra!")
            return redirect('classroom_detail', pk=classroom_id)

        enrollments = ClassEnrollment.objects.filter(classroom=classroom).select_related('student')
        if not enrollments.exists():
            messages.warning(request, "Lớp học hiện tại chưa có học sinh nào để điểm danh.")
            return redirect('classroom_detail', pk=classroom_id)

        existing = Attendance.objects.filter(
            classroom=classroom, schedule=schedule, date=target_date
        ).values('student_id', 'status', 'remark')
        attendance_map = {i['student_id']: i for i in existing}

        return render(request, self.template_name, {
            'classroom': classroom, 'schedule': schedule, 'target_date': target_date,
            'enrollments': enrollments, 'attendance_map': attendance_map,
            'status_choices': Attendance.STATUS_CHOICES,
        })

    def post(self, request, classroom_id, schedule_id, date_str):
        classroom, schedule, target_date, resp = self._setup(request, classroom_id, schedule_id, date_str)
        if resp:
            return resp
        if target_date > timezone.localdate():
            messages.error(request, "Không thể điểm danh cho buổi học chưa diễn ra!")
            return redirect('classroom_detail', pk=classroom_id)

        enrollments = ClassEnrollment.objects.filter(classroom=classroom).select_related('student')
        with transaction.atomic():
            for enr in enrollments:
                status = request.POST.get(f'status_{enr.student.id}')
                remark = request.POST.get(f'remark_{enr.student.id}', '')
                if status:
                    Attendance.objects.update_or_create(
                        classroom=classroom, student=enr.student, schedule=schedule,
                        date=target_date, defaults={'status': status, 'remark': remark},
                    )
        messages.success(request, f"Đã cập nhật bảng điểm danh ngày {target_date} thành công.")
        return redirect('classroom_detail', pk=classroom_id)


class DailyReviewManageView(StaffRequiredMixin, View):
    """Nhập nhận xét hàng ngày hàng loạt (UC06)."""
    template_name = 'classrooms/daily_review_form.html'

    def _setup(self, request, classroom_id, schedule_id, date_str):
        classroom = get_object_or_404(Classroom, pk=classroom_id)
        if not _can_access_classroom(request.user, classroom):
            return None, None, None, redirect('attendance_class_list')
        schedule = get_object_or_404(Schedule, pk=schedule_id, classroom=classroom)
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return classroom, schedule, None, redirect('classroom_detail', pk=classroom_id)
        return classroom, schedule, target_date, None

    def get(self, request, classroom_id, schedule_id, date_str):
        classroom, schedule, target_date, resp = self._setup(request, classroom_id, schedule_id, date_str)
        if resp:
            return resp
        if target_date > timezone.localdate():
            messages.error(request, "Không thể nhập nhận xét cho buổi học chưa diễn ra!")
            return redirect('classroom_detail', pk=classroom_id)
        return render(request, self.template_name, self._context(classroom, schedule, target_date))

    def post(self, request, classroom_id, schedule_id, date_str):
        classroom, schedule, target_date, resp = self._setup(request, classroom_id, schedule_id, date_str)
        if resp:
            return resp
        enrollments = ClassEnrollment.objects.filter(classroom=classroom).select_related('student')
        has_content = False
        with transaction.atomic():
            for enr in enrollments:
                content = request.POST.get(f'comment_{enr.student.id}', '').strip()
                if content:
                    has_content = True
                    DailyComment.objects.update_or_create(
                        classroom=classroom, student=enr.student, schedule=schedule,
                        date=target_date,
                        defaults={'content': content, 'created_by': request.user},
                    )
        if not has_content:
            messages.warning(request, "Vui lòng nhập ít nhất một nhận xét trước khi lưu!")
            return render(request, self.template_name, self._context(classroom, schedule, target_date))
        messages.success(request, f"Đã lưu nhận xét ngày {target_date} thành công.")
        return redirect('classroom_detail', pk=classroom_id)

    def _context(self, classroom, schedule, target_date):
        enrollments = ClassEnrollment.objects.filter(classroom=classroom).select_related('student')
        attendance_records = Attendance.objects.filter(
            classroom=classroom, schedule=schedule, date=target_date
        )
        attendance_map = {a.student_id: a for a in attendance_records}
        existing = DailyComment.objects.filter(
            classroom=classroom, schedule=schedule, date=target_date
        )
        comment_map = {c.student_id: c.content for c in existing}
        return {
            'classroom': classroom, 'schedule': schedule, 'target_date': target_date,
            'enrollments': enrollments, 'attendance_map': attendance_map,
            'comment_map': comment_map,
        }


# ===================================================================
# PHÍA HỌC SINH (UC09, UC10)
# ===================================================================
class StudentScheduleView(StudentRequiredMixin, View):
    """UC09 — Thời khóa biểu tuần của học sinh."""
    template_name = 'classrooms/student_schedule.html'

    def get(self, request):
        class_ids = ClassEnrollment.objects.filter(
            student=request.user
        ).values_list('classroom_id', flat=True)
        schedules = (Schedule.objects.filter(classroom_id__in=class_ids)
                     .select_related('classroom').order_by('day_of_week', 'start_time'))
        by_day = defaultdict(list)
        for s in schedules:
            by_day[s.day_of_week].append(s)
        week = [{'label': label, 'slots': by_day.get(day, [])}
                for day, label in Schedule.DAY_CHOICES]
        return render(request, self.template_name,
                      {'week': week, 'has_schedule': bool(schedules)})


class StudentTimelineView(StudentRequiredMixin, View):
    """UC10 — Dòng thời gian điểm danh + nhận xét, kèm tỉ lệ chuyên cần."""
    template_name = 'classrooms/student_timeline.html'

    def get(self, request):
        user = request.user
        attendances = (Attendance.objects.filter(student=user)
                       .select_related('classroom', 'schedule')
                       .order_by('-date', '-schedule__start_time'))
        comments = (DailyComment.objects.filter(student=user)
                    .select_related('classroom', 'created_by').order_by('-date'))

        total = attendances.count()
        present = attendances.filter(status='present').count()
        late = attendances.filter(status='late').count()
        excused = attendances.filter(status='absent_excused').count()
        unexcused = attendances.filter(status='absent_unexcused').count()
        rate = round((present + late) / total * 100) if total else 0

        events = []
        for a in attendances:
            events.append({
                'kind': 'attendance', 'date': a.date,
                'time': a.schedule.start_time if a.schedule else None,
                'classroom': a.classroom, 'status': a.status,
                'status_display': a.get_status_display(), 'remark': a.remark,
            })
        for c in comments:
            events.append({
                'kind': 'comment', 'date': c.date,
                'time': c.created_at.time() if c.created_at else None,
                'classroom': c.classroom, 'content': c.content, 'teacher': c.created_by,
            })
        events.sort(key=lambda e: (e['date'] or timezone.localdate()), reverse=True)

        return render(request, self.template_name, {
            'events': events,
            'stats': {
                'total': total, 'present': present, 'late': late,
                'excused': excused, 'unexcused': unexcused, 'rate': rate,
            },
        })
