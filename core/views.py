import json
import random
import re
from datetime import timedelta

from django import forms
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Count
from django.http import JsonResponse
from django.utils import timezone
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import (
    UserProfile, Class, Student, Schedule, Assignment, Submission, Attendance,
    DailyComment, PasswordResetOTP, DAY_CHOICES,
)
from .forms import (
    UserProfileForm, ChangePasswordForm, RegisterForm,
    ClassForm, StudentForm, StudentEditForm,
    ScheduleForm, AssignmentForm, GradeSubmissionForm, SubmissionForm,
    validate_password_strength,
)

DAY_NAMES = dict(DAY_CHOICES)

def get_display_name(user):
    parts = [user.last_name, user.first_name]
    return ' '.join(p for p in parts if p).strip() or user.username


# Khối xác thực (Auth)

class LoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            if request.user.is_staff:
                return redirect('teacher_dashboard')
            return redirect('student_dashboard')
        return render(request, 'auth/login.html')

    def post(self, request):
        if request.user.is_authenticated:
            if request.user.is_staff:
                return redirect('teacher_dashboard')
            return redirect('student_dashboard')

        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            if user.is_staff:
                return redirect('teacher_dashboard')
            return redirect('student_dashboard')
        else:
            messages.error(request, 'Tên đăng nhập hoặc mật khẩu không chính xác!')
        return render(request, 'auth/login.html')

class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect('login')


class RegisterView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('teacher_dashboard' if request.user.is_staff else 'student_dashboard')
        return render(request, 'auth/register.html', {'form': RegisterForm()})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect('teacher_dashboard' if request.user.is_staff else 'student_dashboard')
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('student_dashboard')
        return render(request, 'auth/register.html', {'form': form})

def _mask_email(email):
    try:
        name, domain = email.split('@', 1)
        visible = name[:2]
        return f"{visible}{'*' * max(len(name) - 2, 1)}@{domain}"
    except ValueError:
        return email

class SendOTPView(View):
    def post(self, request):
        phone = request.POST.get('phone', '').strip()
        if not re.fullmatch(r'0\d{9}', phone):
            return JsonResponse(
                {'status': 'error', 'message': 'Số điện thoại phải đúng 10 số và bắt đầu bằng số 0.'},
                status=400,
            )

        profile = UserProfile.objects.filter(phone=phone).select_related('user').first()
        if not profile:
            return JsonResponse(
                {'status': 'error', 'message': 'Không tìm thấy tài khoản với số điện thoại này.'},
                status=404,
            )

        user = profile.user
        if not user.email:
            return JsonResponse(
                {'status': 'error',
                 'message': 'Tài khoản này chưa có email để nhận OTP. Vui lòng liên hệ trung tâm.'},
                status=400,
            )

        otp_code = f'{random.randint(0, 999999):06d}'
        minutes = getattr(settings, 'OTP_EXPIRY_MINUTES', 5)
        PasswordResetOTP.objects.create(
            user=user,
            otp_code=otp_code,
            expires_at=timezone.now() + timedelta(minutes=minutes),
        )

        send_mail(
            subject='[EduManager] Mã OTP khôi phục mật khẩu',
            message=(
                f'Xin chào {user.get_full_name() or user.username},\n\n'
                f'Mã OTP khôi phục mật khẩu của bạn là: {otp_code}\n'
                f'Mã có hiệu lực trong {minutes} phút.\n\n'
                f'Nếu bạn không yêu cầu, vui lòng bỏ qua email này.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return JsonResponse({
            'status': 'ok',
            'message': f'Mã OTP đã được gửi tới email {_mask_email(user.email)}.',
        })

class ResetPasswordView(View):
    def post(self, request):
        phone = request.POST.get('phone', '').strip()
        otp = request.POST.get('otp', '').strip()
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not re.fullmatch(r'0\d{9}', phone):
            return JsonResponse({'status': 'error', 'message': 'Số điện thoại không hợp lệ.'}, status=400)
        if not re.fullmatch(r'\d{6}', otp):
            return JsonResponse({'status': 'error', 'message': 'Mã OTP phải đúng 6 chữ số.'}, status=400)
        if new_password != confirm_password:
            return JsonResponse(
                {'status': 'error', 'message': 'Lỗi nhập liệu/Xác nhận mật khẩu mới không trùng khớp.'},
                status=400,
            )
        try:
            validate_password_strength(new_password)
        except forms.ValidationError as e:
            return JsonResponse({'status': 'error', 'message': e.messages[0]}, status=400)

        profile = UserProfile.objects.filter(phone=phone).select_related('user').first()
        if not profile:
            return JsonResponse({'status': 'error', 'message': 'Không tìm thấy tài khoản.'}, status=404)

        user = profile.user
        otp_obj = (PasswordResetOTP.objects
                   .filter(user=user, otp_code=otp, is_used=False)
                   .order_by('-created_at')
                   .first())
        if not otp_obj or not otp_obj.is_valid():
            return JsonResponse(
                {'status': 'error', 'message': 'Mã OTP không đúng hoặc đã hết hạn.'}, status=400)

        user.set_password(new_password)
        user.save()
        otp_obj.is_used = True
        otp_obj.save()

        return JsonResponse({'status': 'ok', 'message': 'Đổi mật khẩu thành công!'})


# Khối giáo viên (Teacher)

class TeacherDashboardView(LoginRequiredMixin, View):
    def get(self, request):
        total_classes = Class.objects.filter(teacher=request.user).count()
        total_students = Student.objects.filter(classes__teacher=request.user).distinct().count()
        context = {
            'total_classes': total_classes,
            'total_students': total_students,
        }
        return render(request, 'teacher/dashboard.html', context)

class ClassListView(LoginRequiredMixin, View):
    def get(self, request):
        classes = Class.objects.filter(teacher=request.user).annotate(student_count=Count('students')).order_by('-created_at')
        class_list_data = []
        for c in classes:
            class_list_data.append({
                'id': c.id,
                'name': c.name,
                'description': c.description or '',
                'teacher_name': c.teacher_name,
                'schedule': c.get_schedule_display(),
                'room': c.room or 'Tự do',
                'student_count': c.student_count,
                'created_at': c.created_at.strftime('%d/%m/%Y'),
            })

        return render(request, 'teacher/class_list.html', {'classes': class_list_data})

    def post(self, request):
        form = ClassForm(request.POST)
        if form.is_valid():
            cls = form.save(commit=False)
            cls.teacher = request.user
            cls.save()
            return JsonResponse({
                'status': 'ok',
                'id': cls.id,
                'name': cls.name,
                'description': cls.description or '',
                'teacher_name': cls.teacher_name,
                'room': cls.room or 'Tự do',
                'student_count': 0,
                'created_at': cls.created_at.strftime('%d/%m/%Y'),
                'schedule': 'Chưa xếp lịch',
            })
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

class ClassDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        class_obj = get_object_or_404(Class, pk=pk, teacher=request.user)
        students_in_class = class_obj.students.select_related('user', 'user__profile').all()
        all_center_students = Student.objects.select_related('user', 'user__profile').all()

        students_in_class_data = [{
            'id': s.id,
            'student_id': s.student_id,
            'name': get_display_name(s.user),
            'phone': s.user.profile.phone or '' if hasattr(s.user, 'profile') else '',
            'email': s.user.email,
        } for s in students_in_class]

        all_students_data = [{
            'id': s.id,
            'student_id': s.student_id,
            'name': get_display_name(s.user),
            'phone': s.user.profile.phone or '' if hasattr(s.user, 'profile') else '',
            'email': s.user.email,
        } for s in all_center_students]

        context = {
            'class': {
                'id': class_obj.id,
                'name': class_obj.name,
                'description': class_obj.description or '',
                'teacher_name': class_obj.teacher_name,
                'schedule': class_obj.get_schedule_display(),
                'room': class_obj.room or 'Tự do',
                'created_at': class_obj.created_at.strftime('%d/%m/%Y'),
            },
            'students_in_class': students_in_class_data,
            'all_center_students': all_students_data,
        }
        return render(request, 'teacher/class_detail.html', context)

    def post(self, request, pk):
        class_obj = get_object_or_404(Class, pk=pk, teacher=request.user)
        action = request.POST.get('action')

        if action == 'enroll':
            student_ids = request.POST.getlist('student_ids[]')
            
            class_schedules = class_obj.schedules.all()
            
            errors = []
            students_to_enroll = []
            
            for sid in student_ids:
                try:
                    student = Student.objects.get(id=sid)
                    students_to_enroll.append(student)
                    
                    if class_schedules.exists():
                        student_schedules = Schedule.objects.filter(class_obj__students=student)
                        for cs in class_schedules:
                            has_conflict = False
                            for ss in student_schedules:
                                if cs.day_of_week == ss.day_of_week and max(cs.start_time, ss.start_time) < min(cs.end_time, ss.end_time):
                                    errors.append(f"{student.user.get_full_name()} (trùng với lớp {ss.class_obj.name})")
                                    has_conflict = True
                                    break
                            if has_conflict:
                                break
                except Student.DoesNotExist:
                    pass
            
            if errors:
                return JsonResponse({'status': 'error', 'message': "Không thể xếp lớp do học sinh sau bị trùng lịch: " + ", ".join(list(set(errors)))}, status=400)
                
            enrolled = []
            for student in students_to_enroll:
                class_obj.students.add(student)
                enrolled.append({
                    'id': student.id,
                    'student_id': student.student_id,
                    'name': get_display_name(student.user),
                    'phone': student.user.profile.phone or '' if hasattr(student.user, 'profile') else '',
                    'email': student.user.email,
                })
            return JsonResponse({'status': 'ok', 'enrolled': enrolled})

        if action == 'drop':
            student_id = request.POST.get('student_id')
            try:
                student = Student.objects.get(id=student_id)
                class_obj.students.remove(student)
                return JsonResponse({'status': 'ok'})
            except Student.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Học sinh không tồn tại.'}, status=404)
        return JsonResponse({'status': 'error', 'message': 'Invalid action.'}, status=400)

class ScheduleView(LoginRequiredMixin, View):
    def get(self, request, pk):
        class_obj = get_object_or_404(Class, pk=pk, teacher=request.user)
        existing_schedules = Schedule.objects.filter(class_obj=class_obj)
        all_schedules = Schedule.objects.filter(class_obj__teacher=request.user).select_related('class_obj')

        existing_data = [{
            'id': s.id,
            'class_name': s.class_obj.name,
            'day_of_week': s.day_of_week,
            'day_name': DAY_NAMES.get(s.day_of_week, s.day_of_week),
            'start_time': s.start_time.strftime('%H:%M'),
            'end_time': s.end_time.strftime('%H:%M'),
            'room': s.room or '',
        } for s in existing_schedules]

        all_schedules_data = [{
            'class_name': s.class_obj.name,
            'day_of_week': s.day_of_week,
            'start_time': s.start_time.strftime('%H:%M'),
            'end_time': s.end_time.strftime('%H:%M'),
            'room': s.room or '',
        } for s in all_schedules]

        context = {
            'class': {
                'id': class_obj.id,
                'name': class_obj.name,
                'room': class_obj.room or '',
            },
            'existing_schedules': existing_data,
            'all_schedules_json': json.dumps(all_schedules_data),
        }
        return render(request, 'teacher/schedule.html', context)

    def post(self, request, pk):
        class_obj = get_object_or_404(Class, pk=pk, teacher=request.user)
        action = request.POST.get('action', 'add')

        if action == 'delete':
            sched_id = request.POST.get('schedule_id')
            Schedule.objects.filter(id=sched_id, class_obj=class_obj).delete()
            return JsonResponse({'status': 'ok'})

        form = ScheduleForm(request.POST)
        if form.is_valid():
            day = form.cleaned_data['day_of_week']
            start = form.cleaned_data['start_time']
            end = form.cleaned_data['end_time']
            room = form.cleaned_data.get('room', '')

            if room:
                conflict = Schedule.objects.filter(
                    day_of_week=day, room__iexact=room
                ).exclude(class_obj=class_obj)
                for s in conflict:
                    if max(start, s.start_time) < min(end, s.end_time):
                        return JsonResponse({
                            'status': 'error',
                            'message': f'Lỗi trùng lịch phòng học. Phòng học đã có [{s.class_obj.name}] đăng ký học ở thời gian này.'
                        }, status=400)

            teacher_conflict = Schedule.objects.filter(
                class_obj__teacher=class_obj.teacher,
                day_of_week=day
            ).exclude(class_obj=class_obj)
            for s in teacher_conflict:
                if max(start, s.start_time) < min(end, s.end_time):
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Lỗi trùng lịch giáo viên. Bạn đã có lịch dạy lớp {s.class_obj.name} vào thời gian này.'
                    }, status=400)

            students = class_obj.students.all()
            if students.exists():
                student_conflict = Schedule.objects.filter(
                    class_obj__students__in=students,
                    day_of_week=day
                ).exclude(class_obj=class_obj).distinct()
                
                conflicting_students = []
                for s in student_conflict:
                    if max(start, s.start_time) < min(end, s.end_time):
                        overlapping = s.class_obj.students.filter(id__in=students.values_list('id', flat=True))
                        for st in overlapping:
                            conflicting_students.append(f"{st.user.get_full_name()} ({st.student_id})")
                
                if conflicting_students:
                    conflicting_students = list(set(conflicting_students))
                    msg = "Lịch học bị trùng với lịch của các học sinh sau: " + ", ".join(conflicting_students)
                    return JsonResponse({'status': 'error', 'message': msg}, status=400)

            sched = form.save(commit=False)
            sched.class_obj = class_obj
            sched.save()

            return JsonResponse({
                'status': 'ok',
                'id': sched.id,
                'day_of_week': day,
                'day_name': DAY_NAMES.get(day, day),
                'start_time': start.strftime('%H:%M'),
                'end_time': end.strftime('%H:%M'),
                'room': room or 'Online',
            })
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

class StudentListView(LoginRequiredMixin, View):
    def get(self, request):
        students = Student.objects.filter(classes__teacher=request.user).select_related('user', 'user__profile').prefetch_related('classes').distinct()

        students_data = [{
            'id': s.id,
            'student_id': s.student_id,
            'first_name': s.user.first_name,
            'last_name': s.user.last_name,
            'username': s.user.username,
            'phone': s.user.profile.phone or '' if hasattr(s.user, 'profile') else '',
            'email': s.user.email,
            'date_of_birth': str(s.user.profile.date_of_birth or '') if hasattr(s.user, 'profile') else '',
            'address': s.user.profile.address or '' if hasattr(s.user, 'profile') else '',
            'classes': ', '.join([c.name for c in s.classes.filter(teacher=request.user)]),
        } for s in students]

        next_num = Student.objects.count() + 1
        while Student.objects.filter(student_id=f'HS{str(next_num).zfill(3)}').exists():
            next_num += 1
        next_student_id = f'HS{str(next_num).zfill(3)}'

        context = {
            'students': students_data,
            'next_student_id': next_student_id,
        }
        return render(request, 'teacher/student_list.html', context)

    def post(self, request):
        action = request.POST.get('action', 'add')

        if action == 'add':
            form = StudentForm(request.POST)
            if form.is_valid():
                student = form.save()
                user = student.user
                return JsonResponse({
                    'status': 'ok',
                    'id': student.id,
                    'student_id': student.student_id,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'username': user.username,
                    'phone': user.profile.phone or '',
                    'email': user.email,
                    'classes': '',
                    'date_of_birth': str(user.profile.date_of_birth or ''),
                    'address': user.profile.address or '',
                    'default_password': f'{user.username}@123',
                })
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

        return JsonResponse({'status': 'error', 'message': 'Invalid action'}, status=400)

class AttendanceView(LoginRequiredMixin, View):
    def get(self, request):
        classes = Class.objects.filter(teacher=request.user)
        classes_data = [{'id': c.id, 'name': c.name} for c in classes]

        students_by_class = {}
        for c in classes:
            students_by_class[str(c.id)] = [{
                'student_id': s.student_id,
                'name': get_display_name(s.user),
            } for s in c.students.select_related('user').all()]

        context = {
            'classes': classes_data,
            'students_by_class_json': json.dumps(students_by_class),
        }
        return render(request, 'teacher/attendance.html', context)

    def post(self, request):
        class_id = request.POST.get('class_id')
        attendance_date = request.POST.get('date')
        class_obj = get_object_or_404(Class, id=class_id, teacher=request.user)

        students = class_obj.students.all()
        saved = 0
        for student in students:
            status = request.POST.get(f'status_{student.student_id}', 'present')
            remarks = request.POST.get(f'remarks_{student.student_id}', '').strip()[:500]

            Attendance.objects.update_or_create(
                student=student,
                class_obj=class_obj,
                date=attendance_date,
                defaults={'status': status}
            )

            if remarks:
                DailyComment.objects.update_or_create(
                    student=student,
                    class_obj=class_obj,
                    comment_date=attendance_date,
                    defaults={'comment_text': remarks, 'created_by': request.user}
                )
            else:
                DailyComment.objects.filter(
                    student=student, class_obj=class_obj, comment_date=attendance_date
                ).delete()
            saved += 1

        return JsonResponse({'status': 'ok', 'saved': saved})

class AssignmentListView(LoginRequiredMixin, View):
    def get(self, request):
        assignments = Assignment.objects.filter(class_obj__teacher=request.user).select_related('class_obj').prefetch_related('submissions').order_by('-created_at')
        classes = Class.objects.filter(teacher=request.user)

        assignments_data = [{
            'id': a.id,
            'title': a.title,
            'class_name': a.class_obj.name,
            'due_date': a.due_date.strftime('%Y-%m-%dT%H:%M'),
            'created_at': a.created_at.strftime('%d/%m/%Y'),
            'file_name': a.file.name.split('/')[-1] if a.file else '',
            'file_url': a.file.url if a.file else '',
            'file_size': '',
            'submission_count': a.get_submission_count(),
            'total_students': a.get_total_students(),
            'description': a.description or '',
        } for a in assignments]

        classes_data = [{'id': c.id, 'name': c.name} for c in classes]

        context = {
            'assignments': assignments_data,
            'classes': classes_data,
        }
        return render(request, 'teacher/assignment_list.html', context)

    def post(self, request):
        form = AssignmentForm(request.POST, request.FILES)
        if form.is_valid():
            assignment = form.save(commit=False)
            if assignment.class_obj.teacher != request.user:
                return JsonResponse({'status': 'error', 'message': 'Không có quyền giao bài cho lớp này'}, status=403)
            assignment.created_by = request.user
            assignment.save()
            return JsonResponse({
                'status': 'ok',
                'id': assignment.id,
                'title': assignment.title,
                'class_name': assignment.class_obj.name,
                'due_date': assignment.due_date.strftime('%Y-%m-%dT%H:%M'),
                'created_at': assignment.created_at.strftime('%d/%m/%Y'),
                'file_name': assignment.file.name.split('/')[-1] if assignment.file else '',
                'file_url': assignment.file.url if assignment.file else '',
                'submission_count': 0,
                'total_students': assignment.class_obj.students.count(),
                'description': assignment.description or '',
            })
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

class GradingView(LoginRequiredMixin, View):
    def get(self, request, pk):
        assignment = get_object_or_404(Assignment.objects.select_related('class_obj'), pk=pk, class_obj__teacher=request.user)
        students_in_class = assignment.class_obj.students.select_related('user').all()
        existing_subs = {s.student.id: s for s in Submission.objects.filter(assignment=assignment).select_related('student')}

        submissions_data = []
        for student in students_in_class:
            sub = existing_subs.get(student.id)
            submissions_data.append({
                'student_id': student.student_id,
                'name': get_display_name(student.user),
                'submitted_at': sub.submitted_at.strftime('%d/%m/%Y %H:%M') if sub and sub.status != 'missing' else '-',
                'student_note': sub.note if sub else '',
                'file_name': sub.file.name.split('/')[-1] if sub and sub.file else '',
                'file_url': sub.file.url if sub and sub.file else '',
                'file_size': '',
                'grade': sub.grade if sub else None,
                'feedback': sub.feedback if sub else '',
                'status': sub.status if sub else 'missing',
            })

        context = {
            'assignment': {
                'id': assignment.id,
                'title': assignment.title,
                'class_name': assignment.class_obj.name,
                'due_date': assignment.due_date.strftime('%Y-%m-%dT%H:%M'),
                'created_at': assignment.created_at.strftime('%d/%m/%Y'),
                'description': assignment.description or '',
            },
            'submissions_json': json.dumps(submissions_data),
        }
        return render(request, 'teacher/grading.html', context)

    def post(self, request, pk):
        assignment = get_object_or_404(Assignment.objects.select_related('class_obj'), pk=pk, class_obj__teacher=request.user)
        student_id = request.POST.get('student_id')
        student = get_object_or_404(Student, student_id=student_id)
        submission, _ = Submission.objects.get_or_create(
            assignment=assignment, student=student,
            defaults={'status': 'missing'}
        )
        form = GradeSubmissionForm(request.POST, instance=submission)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.status = 'graded'
            sub.save()
            return JsonResponse({'status': 'ok', 'grade': sub.grade, 'feedback': sub.feedback})
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)


def _get_student_or_none(request):
    try:
        return Student.objects.select_related('user').prefetch_related('classes').get(user=request.user)
    except Student.DoesNotExist:
        return None


# Khối học sinh (Student)

class StudentDashboardView(LoginRequiredMixin, View):
    def get(self, request):
        student = _get_student_or_none(request)

        if student:
            classes = student.classes.all()
            submissions = Submission.objects.filter(student=student).select_related('assignment')
            waiting_graded = submissions.filter(status='pending').count()
            graded = submissions.filter(status='graded').count()

            all_assignments = Assignment.objects.filter(class_obj__in=classes)
            submitted_ids = submissions.exclude(status='missing').values_list('assignment_id', flat=True)
            not_submitted_count = all_assignments.exclude(id__in=submitted_ids).count()

            total_att = Attendance.objects.filter(student=student).count()
            present_att = Attendance.objects.filter(student=student, status='present').count()
            att_rate = round(present_att / total_att * 100) if total_att > 0 else 0

            urgent_assignments = []
            for cls in classes:
                for a in Assignment.objects.filter(class_obj=cls).order_by('due_date')[:3]:
                    has_submitted = submissions.filter(assignment=a).exclude(status='missing').exists()
                    if not has_submitted:
                        urgent_assignments.append({
                            'id': a.id,
                            'title': a.title,
                            'class_name': cls.name,
                            'due_date': a.due_date.strftime('%Y-%m-%dT%H:%M'),
                            'status': 'not_submitted',
                        })

            student_info = {
                'name': get_display_name(request.user),
                'student_id': student.student_id,
                'username': request.user.username,
                'email': request.user.email,
                'classes': [c.name for c in classes],
            }
            stats = {
                'active_classes_count': classes.count(),
                'attendance_rate': att_rate,
                'not_submitted_count': not_submitted_count,
                'waiting_graded_count': waiting_graded,
                'graded_assignments_count': graded,
            }
        else:
            student_info = {'name': get_display_name(request.user), 'student_id': '', 'username': request.user.username, 'email': request.user.email, 'classes': []}
            stats = {'active_classes_count': 0, 'attendance_rate': 0, 'not_submitted_count': 0, 'waiting_graded_count': 0, 'graded_assignments_count': 0}
            urgent_assignments = []

        context = {
            'student': student_info,
            'urgent_assignments': urgent_assignments,
            'stats': stats,
        }
        return render(request, 'student/dashboard.html', context)


class StudentScheduleView(LoginRequiredMixin, View):
    def get(self, request):
        student = _get_student_or_none(request)

        colors = ['indigo', 'emerald', 'violet', 'amber', 'rose', 'cyan']

        student_schedule = []
        if student:
            schedules = Schedule.objects.filter(class_obj__in=student.classes.all()).select_related('class_obj')
            for i, s in enumerate(schedules):
                student_schedule.append({
                    'class_name': s.class_obj.name,
                    'day_of_week': s.day_of_week,
                    'day_name': DAY_NAMES.get(s.day_of_week, s.day_of_week),
                    'start_time': s.start_time.strftime('%H:%M'),
                    'end_time': s.end_time.strftime('%H:%M'),
                    'room': s.room or 'Online',
                    'teacher': s.class_obj.teacher_name,
                    'color': colors[i % len(colors)],
                })

        context = {
            'schedule': student_schedule,
            'student': {'name': get_display_name(request.user), 'student_id': student.student_id if student else ''},
        }
        return render(request, 'student/schedule.html', context)


class StudentAttendanceView(LoginRequiredMixin, View):
    def get(self, request):
        student = _get_student_or_none(request)

        logs = []
        stats = {'total_sessions': 0, 'present_sessions': 0, 'excused_sessions': 0, 'absent_sessions': 0, 'attendance_percentage': 0}

        if student:
            attendances = Attendance.objects.filter(student=student).select_related('class_obj').order_by('-date')

            comments_map = {
                (dc.class_obj_id, dc.comment_date): dc.comment_text
                for dc in DailyComment.objects.filter(student=student)
            }

            status_names = {'present': 'Đi học', 'excused': 'Vắng phép', 'absent': 'Vắng không phép'}
            for att in attendances:
                logs.append({
                    'date': att.date.strftime('%d/%m/%Y'),
                    'class_name': att.class_obj.name,
                    'status': att.status,
                    'status_name': status_names.get(att.status, att.status),
                    'feedback': comments_map.get((att.class_obj_id, att.date), ''),
                })

            total = attendances.count()
            present = attendances.filter(status='present').count()
            excused = attendances.filter(status='excused').count()
            absent = attendances.filter(status='absent').count()
            stats = {
                'total_sessions': total,
                'present_sessions': present,
                'excused_sessions': excused,
                'absent_sessions': absent,
                'attendance_percentage': round(present / total * 100) if total > 0 else 0,
            }

        context = {'stats': stats, 'logs': logs}
        return render(request, 'student/attendance.html', context)


class StudentAssignmentListView(LoginRequiredMixin, View):
    def get(self, request):
        student = _get_student_or_none(request)
        assignments_data = []

        if student:
            classes = student.classes.all()
            status_names = {'pending': 'Chờ chấm điểm', 'graded': 'Đã có điểm', 'missing': 'Quá hạn / Thiếu bài', 'not_submitted': 'Chưa làm'}

            for cls in classes:
                for a in Assignment.objects.filter(class_obj=cls).order_by('-created_at'):
                    try:
                        sub = Submission.objects.get(assignment=a, student=student)
                        status = sub.status
                        grade = sub.grade
                        feedback = sub.feedback
                        submitted_at = sub.submitted_at.strftime('%d/%m/%Y %H:%M')
                        file_name = sub.file.name.split('/')[-1] if sub.file else ''
                        file_url = sub.file.url if sub.file else ''
                    except Submission.DoesNotExist:
                        status = 'not_submitted'
                        grade = None
                        feedback = ''
                        submitted_at = ''
                        file_name = ''
                        file_url = ''

                    assignments_data.append({
                        'id': a.id,
                        'title': a.title,
                        'class_name': cls.name,
                        'due_date': a.due_date.strftime('%Y-%m-%dT%H:%M'),
                        'status': status,
                        'status_name': status_names.get(status, status),
                        'grade': grade,
                        'feedback': feedback,
                        'submitted_at': submitted_at,
                        'file_name': file_name,
                        'file_url': file_url,
                    })

        context = {'assignments': assignments_data}
        return render(request, 'student/assignment_list.html', context)


class StudentAssignmentDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        assignment = get_object_or_404(Assignment.objects.select_related('class_obj', 'created_by'), pk=pk)
        student = _get_student_or_none(request)
        submission = None
        if student:
            try:
                submission = Submission.objects.get(assignment=assignment, student=student)
            except Submission.DoesNotExist:
                pass

        assignment_data = {
            'id': assignment.id,
            'title': assignment.title,
            'class_name': assignment.class_obj.name,
            'due_date': assignment.due_date.strftime('%Y-%m-%dT%H:%M'),
            'created_at': assignment.created_at.strftime('%d/%m/%Y %H:%M'),
            'teacher': assignment.class_obj.teacher_name,
            'file_name': assignment.file.name.split('/')[-1] if assignment.file else '',
            'file_url': assignment.file.url if assignment.file else '',
            'file_size': '',
            'description': assignment.description or '',
            'status': 'not_submitted',
            'grade': None,
            'feedback': '',
            'submitted_at': '',
            'submitted_file': '',
            'submitted_file_url': '',
            'submitted_file_size': '',
            'student_note': '',
        }

        if submission:
            assignment_data.update({
                'status': submission.status,
                'grade': submission.grade,
                'feedback': submission.feedback,
                'submitted_at': submission.submitted_at.strftime('%d/%m/%Y %H:%M'),
                'submitted_file': submission.file.name.split('/')[-1] if submission.file else '',
                'submitted_file_url': submission.file.url if submission.file else '',
                'student_note': submission.note,
            })

        context = {'assignment': assignment_data}
        return render(request, 'student/assignment_detail.html', context)

    def post(self, request, pk):
        assignment = get_object_or_404(Assignment.objects.select_related('class_obj', 'created_by'), pk=pk)
        student = _get_student_or_none(request)

        if student:
            if timezone.now() > assignment.due_date:
                return JsonResponse(
                    {'status': 'error', 'message': 'Đã quá hạn nộp bài. Hệ thống đã khóa chức năng nộp.'},
                    status=400,
                )
            try:
                submission = Submission.objects.get(assignment=assignment, student=student)
                form = SubmissionForm(request.POST, request.FILES, instance=submission)
            except Submission.DoesNotExist:
                form = SubmissionForm(request.POST, request.FILES)

            if form.is_valid():
                sub = form.save(commit=False)
                sub.assignment = assignment
                sub.student = student
                sub.status = 'pending'
                sub.save()
                return JsonResponse({
                    'status': 'ok',
                    'submitted_at': sub.submitted_at.strftime('%d/%m/%Y %H:%M'),
                    'file_name': sub.file.name.split('/')[-1] if sub.file else '',
                    'file_url': sub.file.url if sub.file else '',
                })
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        return JsonResponse({'status': 'error', 'message': 'Not a student'}, status=403)



# Chức năng chung

class ProfileView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        profile_obj, created = UserProfile.objects.get_or_create(user=user)
        if created and user.is_staff:
            profile_obj.role = 'teacher'
            profile_obj.save()

        initial_data = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
        }
        profile_form = UserProfileForm(instance=profile_obj, initial=initial_data)
        password_form = ChangePasswordForm()

        context = {
            'profile_form': profile_form,
            'password_form': password_form,
            'profile': profile_obj,
            'user': user,
        }
        return render(request, 'components/_profile.html', context)

    def post(self, request):
        user = request.user
        profile_obj, created = UserProfile.objects.get_or_create(user=user)
        if created and user.is_staff:
            profile_obj.role = 'teacher'
            profile_obj.save()

        form_type = request.POST.get('form_type')

        if form_type == 'password':
            password_form = ChangePasswordForm(request.POST)
            if password_form.is_valid():
                old_password = password_form.cleaned_data.get('old_password')
                new_password = password_form.cleaned_data.get('new_password')
                if user.check_password(old_password):
                    user.set_password(new_password)
                    user.save()
                    update_session_auth_hash(request, user)
                    messages.success(request, 'Đổi mật khẩu thành công!')
                else:
                    messages.error(request, 'Mật khẩu hiện tại không chính xác!')
            else:
                messages.error(request, 'Mật khẩu mới không hợp lệ!')
            return redirect('profile')

        profile_form = UserProfileForm(request.POST, instance=profile_obj)
        if profile_form.is_valid():
            user.first_name = profile_form.cleaned_data.get('first_name', '')
            user.last_name = profile_form.cleaned_data.get('last_name', '')
            user.email = profile_form.cleaned_data.get('email', '')
            user.save()
            profile_form.save()
            messages.success(request, 'Cập nhật thông tin thành công!')
            return redirect('profile')
        else:
            messages.error(request, 'Thông tin không hợp lệ. Vui lòng kiểm tra lại.')

        password_form = ChangePasswordForm()

        context = {
            'profile_form': profile_form,
            'password_form': password_form,
            'profile': profile_obj,
            'user': user,
        }
        return render(request, 'components/_profile.html', context)
