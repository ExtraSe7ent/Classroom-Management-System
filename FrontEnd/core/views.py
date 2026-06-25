import json
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import UserProfile, Class, Student, Schedule, Assignment, Submission, Attendance
from .forms import (
    UserProfileForm, ChangePasswordForm, ClassForm, StudentForm, StudentEditForm,
    ScheduleForm, AssignmentForm, GradeSubmissionForm, SubmissionForm
)


def _get_csrf_token(request):
    from django.middleware.csrf import get_token
    return get_token(request)


def viet_name(user):
    """Returns full name in Vietnamese order: last_name (Last name) + first_name (First name)."""
    parts = [user.last_name, user.first_name]
    return ' '.join(p for p in parts if p).strip() or user.username


# ===== AUTH =====

def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        return redirect('user_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            if user.is_staff:
                return redirect('admin_dashboard')
            return redirect('user_dashboard')
        else:
            messages.error(request, 'Username or password is incorrect!')

    return render(request, 'auth/login.html')


def logout_view(request):
    if request.method == 'POST':
        logout(request)
    return redirect('login')


# ===== ADMIN =====

@login_required
def admin_dashboard(request):
    total_classes = Class.objects.count()
    total_students = Student.objects.count()
    context = {
        'total_classes': total_classes,
        'total_students': total_students,
    }
    return render(request, 'admin/dashboard.html', context)


@login_required
def class_list(request):
    if request.method == 'POST':
        form = ClassForm(request.POST)
        if form.is_valid():
            cls = form.save()
            return JsonResponse({
                'status': 'ok',
                'id': cls.id,
                'name': cls.name,
                'description': cls.description or '',
                'teacher_name': cls.teacher_name,
                'room': cls.room or 'Freedom',
                'student_count': 0,
                'created_at': cls.created_at.strftime('%d/%m/%Y'),
                'schedule': 'Not scheduled yet',
            })
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    classes = Class.objects.annotate(student_count=Count('students')).order_by('-created_at')

    # Normalize the data so the template renders correctly
    class_list_data = []
    for c in classes:
        class_list_data.append({
            'id': c.id,
            'name': c.name,
            'description': c.description or '',
            'teacher_name': c.teacher_name,
            'schedule': c.get_schedule_display(),
            'room': c.room or 'Freedom',
            'student_count': c.student_count,
            'created_at': c.created_at.strftime('%d/%m/%Y'),
        })

    return render(request, 'admin/class_list.html', {'classes': class_list_data})


@login_required
def class_detail(request, pk):
    class_obj = get_object_or_404(Class, pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action')

        # Place students in class
        if action == 'enroll':
            student_ids = request.POST.getlist('student_ids[]')
            enrolled = []
            for sid in student_ids:
                try:
                    student = Student.objects.get(id=sid)
                    class_obj.students.add(student)
                    enrolled.append({
                        'id': student.id,
                        'student_id': student.student_id,
                        'name': viet_name(student.user),
                        'phone': student.user.profile.phone or '',
                        'email': student.user.email,
                    })
                except Student.DoesNotExist:
                    pass
            return JsonResponse({'status': 'ok', 'enrolled': enrolled})

        # Remove students from class
        if action == 'drop':
            student_id = request.POST.get('student_id')
            try:
                student = Student.objects.get(id=student_id)
                class_obj.students.remove(student)
                return JsonResponse({'status': 'ok'})
            except Student.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Student does not exist.'}, status=404)

    students_in_class = class_obj.students.select_related('user', 'user__profile').all()
    all_center_students = Student.objects.select_related('user', 'user__profile').all()

    students_in_class_data = [{
        'id': s.id,
        'student_id': s.student_id,
        'name': viet_name(s.user),
        'phone': s.user.profile.phone or '' if hasattr(s.user, 'profile') else '',
        'email': s.user.email,
    } for s in students_in_class]

    all_students_data = [{
        'id': s.id,
        'student_id': s.student_id,
        'name': viet_name(s.user),
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
            'room': class_obj.room or 'Freedom',
            'created_at': class_obj.created_at.strftime('%d/%m/%Y'),
        },
        'students_in_class': students_in_class_data,
        'all_center_students': all_students_data,
    }
    return render(request, 'admin/class_detail.html', context)


@login_required
def schedule(request, pk):
    class_obj = get_object_or_404(Class, pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action', 'add')

        if action == 'delete':
            sched_id = request.POST.get('schedule_id')
            Schedule.objects.filter(id=sched_id, class_obj=class_obj).delete()
            return JsonResponse({'status': 'ok'})

        # Add new class schedule
        form = ScheduleForm(request.POST)
        if form.is_valid():
            day = form.cleaned_data['day_of_week']
            start = form.cleaned_data['start_time']
            end = form.cleaned_data['end_time']
            room = form.cleaned_data.get('room', '')

            # Check for duplicate classroom schedules
            if room:
                conflict = Schedule.objects.filter(
                    day_of_week=day, room__iexact=room
                ).exclude(class_obj=class_obj)
                for s in conflict:
                    if max(start, s.start_time) < min(end, s.end_time):
                        return JsonResponse({
                            'status': 'error',
                            'message': f'Error in classroom schedule. The classroom has [{s.class_obj.name}] registered at this time.'
                        }, status=400)

            sched = form.save(commit=False)
            sched.class_obj = class_obj
            sched.save()

            day_names = dict([
                ('Monday','Monday'), ('Tuesday','Tuesday'), ('Wednesday','Wednesday'),
                ('Thursday','Thursday'), ('Friday','Friday'), ('Saturday','Saturday'), ('Sunday','Sunday')
            ])

            return JsonResponse({
                'status': 'ok',
                'id': sched.id,
                'day_name': day_names.get(day, day),
                'start_time': start.strftime('%H:%M'),
                'end_time': end.strftime('%H:%M'),
                'room': room or 'Online',
            })
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    existing_schedules = Schedule.objects.filter(class_obj=class_obj)
    all_schedules = Schedule.objects.select_related('class_obj').all()

    day_names = {
        'Monday':'Monday', 'Tuesday':'Tuesday', 'Wednesday':'Wednesday',
        'Thursday':'Thursday', 'Friday':'Friday', 'Saturday':'Saturday', 'Sunday':'Sunday'
    }

    existing_data = [{
        'id': s.id,
        'class_name': s.class_obj.name,
        'day_of_week': s.day_of_week,
        'day_name': day_names.get(s.day_of_week, s.day_of_week),
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
    return render(request, 'admin/schedule.html', context)


@login_required
def student_list(request):
    if request.method == 'POST':
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
                    'classes': student.get_classes_display(),
                    'date_of_birth': str(user.profile.date_of_birth or ''),
                    'address': user.profile.address or '',
                    'default_password': 'Student@123',
                })
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

        if action == 'edit':
            student_id = request.POST.get('student_db_id')
            student = get_object_or_404(Student, id=student_id)
            user = student.user
            form = StudentEditForm(request.POST)
            if form.is_valid():
                d = form.cleaned_data
                user.first_name = d['first_name']
                user.last_name = d['last_name']
                user.email = d.get('email', '')
                user.save()
                profile, _ = UserProfile.objects.get_or_create(user=user)
                profile.phone = d.get('phone', '')
                profile.date_of_birth = d.get('date_of_birth')
                profile.address = d.get('address', '')
                profile.save()
                # Admin updates classes
                classes_str = request.POST.get('classes', '')
                return JsonResponse({
                    'status': 'ok',
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'phone': profile.phone or '',
                    'email': user.email,
                    'classes': classes_str,
                })
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

        if action == 'delete':
            student_id = request.POST.get('student_db_id')
            student = get_object_or_404(Student, id=student_id)
            sid = student.student_id
            student.user.delete()  # Cascade deletes Student and UserProfile
            return JsonResponse({'status': 'ok', 'student_id': sid})

    students = Student.objects.select_related('user', 'user__profile').prefetch_related('classes').all()

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
        'classes': s.get_classes_display(),
    } for s in students]

    # Automatically generate the next HS Code
    count = Student.objects.count()
    next_student_id = f'HS{str(count + 1).zfill(3)}'

    context = {
        'students': students_data,
        'next_student_id': next_student_id,
    }
    return render(request, 'admin/student_list.html', context)


@login_required
def attendance(request):
    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        attendance_date = request.POST.get('date')
        class_obj = get_object_or_404(Class, id=class_id)

        students = class_obj.students.all()
        saved = 0
        for student in students:
            status = request.POST.get(f'status_{student.student_id}', 'present')
            remarks = request.POST.get(f'remarks_{student.student_id}', '')
            Attendance.objects.update_or_create(
                student=student,
                class_obj=class_obj,
                date=attendance_date,
                defaults={'status': status, 'remarks': remarks}
            )
            saved += 1

        return JsonResponse({'status': 'ok', 'saved': saved})

    classes = Class.objects.all()
    classes_data = [{'id': c.id, 'name': c.name} for c in classes]

    # List of students by class (key is string id)
    students_by_class = {}
    for c in classes:
        students_by_class[str(c.id)] = [{
            'student_id': s.student_id,
            'name': viet_name(s.user),
        } for s in c.students.select_related('user').all()]

    context = {
        'classes': classes_data,
        'students_by_class_json': json.dumps(students_by_class),
    }
    return render(request, 'admin/attendance.html', context)


@login_required
def assignment_list(request):
    if request.method == 'POST':
        form = AssignmentForm(request.POST, request.FILES)
        if form.is_valid():
            assignment = form.save(commit=False)
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
                'submission_count': 0,
                'total_students': assignment.class_obj.students.count(),
                'description': assignment.description or '',
            })
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    assignments = Assignment.objects.select_related('class_obj').prefetch_related('submissions').order_by('-created_at')
    classes = Class.objects.all()

    assignments_data = [{
        'id': a.id,
        'title': a.title,
        'class_name': a.class_obj.name,
        'due_date': a.due_date.strftime('%Y-%m-%dT%H:%M'),
        'created_at': a.created_at.strftime('%d/%m/%Y'),
        'file_name': a.file.name.split('/')[-1] if a.file else '',
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
    return render(request, 'admin/assignment_list.html', context)


@login_required
def grading(request, pk):
    assignment = get_object_or_404(Assignment.objects.select_related('class_obj'), pk=pk)

    if request.method == 'POST':
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

    # Get all students in the class and merge with submissions
    students_in_class = assignment.class_obj.students.select_related('user').all()
    existing_subs = {s.student_id: s for s in Submission.objects.filter(assignment=assignment).select_related('student')}

    submissions_data = []
    for student in students_in_class:
        sub = existing_subs.get(student.id)
        submissions_data.append({
            'student_id': student.student_id,
            'name': viet_name(student.user),
            'submitted_at': sub.submitted_at.strftime('%d/%m/%Y %H:%M') if sub and sub.status != 'missing' else '-',
            'student_note': sub.note if sub else '',
            'file_name': sub.file.name.split('/')[-1] if sub and sub.file else '',
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
    return render(request, 'admin/grading.html', context)


# ===== USER =====

def _get_student_or_none(request):
    try:
        return Student.objects.select_related('user').prefetch_related('classes').get(user=request.user)
    except Student.DoesNotExist:
        return None


@login_required
def user_dashboard(request):
    student = _get_student_or_none(request)

    if student:
        classes = student.classes.all()
        submissions = Submission.objects.filter(student=student).select_related('assignment')
        waiting_graded = submissions.filter(status='pending').count()  # Submitted, awaiting grading
        graded = submissions.filter(status='graded').count()           # Got points

        # Count unsubmitted papers: assignments in class but no valid submission
        all_assignments = Assignment.objects.filter(class_obj__in=classes)
        submitted_ids = submissions.exclude(status='missing').values_list('assignment_id', flat=True)
        not_submitted_count = all_assignments.exclude(id__in=submitted_ids).count()

        # Calculate attendance rate
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
            'name': viet_name(request.user),
            'student_id': student.student_id,
            'username': request.user.username,
            'email': request.user.email,
            'classes': [c.name for c in classes],
        }
        stats = {
            'active_classes_count': classes.count(),
            'attendance_rate': att_rate,
            'not_submitted_count': not_submitted_count,   # Not yet submitted
            'waiting_graded_count': waiting_graded,        # Submitted awaiting grading
            'graded_assignments_count': graded,            # Got points
        }
    else:
        student_info = {'name': viet_name(request.user), 'student_id': '', 'username': request.user.username, 'email': request.user.email, 'classes': []}
        stats = {'active_classes_count': 0, 'attendance_rate': 0, 'not_submitted_count': 0, 'waiting_graded_count': 0, 'graded_assignments_count': 0}
        urgent_assignments = []

    context = {
        'student': student_info,
        'urgent_assignments': urgent_assignments,
        'stats': stats,
    }
    return render(request, 'user/dashboard.html', context)


@login_required
def user_schedule(request):
    student = _get_student_or_none(request)

    day_names = {
        'Monday':'Monday', 'Tuesday':'Tuesday', 'Wednesday':'Wednesday',
        'Thursday':'Thursday', 'Friday':'Friday', 'Saturday':'Saturday', 'Sunday':'Sunday'
    }
    colors = ['indigo', 'emerald', 'violet', 'amber', 'rose', 'cyan']

    student_schedule = []
    if student:
        schedules = Schedule.objects.filter(class_obj__in=student.classes.all()).select_related('class_obj')
        for i, s in enumerate(schedules):
            student_schedule.append({
                'class_name': s.class_obj.name,
                'day_of_week': s.day_of_week,
                'day_name': day_names.get(s.day_of_week, s.day_of_week),
                'start_time': s.start_time.strftime('%H:%M'),
                'end_time': s.end_time.strftime('%H:%M'),
                'room': s.room or 'Online',
                'teacher': s.class_obj.teacher_name,
                'color': colors[i % len(colors)],
            })

    context = {
        'schedule': student_schedule,
        'student': {'name': viet_name(request.user), 'student_id': student.student_id if student else ''},
    }
    return render(request, 'user/schedule.html', context)


@login_required
def user_attendance(request):
    student = _get_student_or_none(request)

    logs = []
    stats = {'total_sessions': 0, 'present_sessions': 0, 'excused_sessions': 0, 'absent_sessions': 0, 'attendance_percentage': 0}

    if student:
        attendances = Attendance.objects.filter(student=student).select_related('class_obj').order_by('-date')

        status_names = {'present': 'Go to school', 'excused': 'Absence of leave', 'absent': 'Absence without permission'}
        for att in attendances:
            logs.append({
                'date': att.date.strftime('%d/%m/%Y'),
                'class_name': att.class_obj.name,
                'status': att.status,
                'status_name': status_names.get(att.status, att.status),
                'feedback': att.remarks,
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
    return render(request, 'user/attendance_view.html', context)


@login_required
def user_assignment_list(request):
    student = _get_student_or_none(request)
    assignments_data = []

    if student:
        classes = student.classes.all()
        status_names = {'pending': 'Waiting for scoring', 'graded': 'Got points', 'missing': 'Overdue / Missing items', 'not_submitted': 'Haven't done it yet'}

        for cls in classes:
            for a in Assignment.objects.filter(class_obj=cls).order_by('-created_at'):
                try:
                    sub = Submission.objects.get(assignment=a, student=student)
                    status = sub.status
                    grade = sub.grade
                    feedback = sub.feedback
                    submitted_at = sub.submitted_at.strftime('%d/%m/%Y %H:%M')
                    file_name = sub.file.name.split('/')[-1] if sub.file else ''
                except Submission.DoesNotExist:
                    status = 'not_submitted'
                    grade = None
                    feedback = ''
                    submitted_at = ''
                    file_name = ''

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
                })

    context = {'assignments': assignments_data}
    return render(request, 'user/assignment_list.html', context)


@login_required
def user_assignment_detail(request, pk):
    assignment = get_object_or_404(Assignment.objects.select_related('class_obj', 'created_by'), pk=pk)
    student = _get_student_or_none(request)

    if request.method == 'POST' and student:
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
            })
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    # Get the current submission if any
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
        'teacher': assignment.class_obj.teacher_name,
        'file_name': assignment.file.name.split('/')[-1] if assignment.file else '',
        'file_size': '',
        'description': assignment.description or '',
        'status': 'not_submitted',
        'grade': None,
        'feedback': '',
        'submitted_at': '',
        'submitted_file': '',
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
            'student_note': submission.note,
        })

    context = {'assignment': assignment_data}
    return render(request, 'user/assignment_detail.html', context)


# ===== CHUNG =====

@login_required
def profile(request):
    user = request.user
    profile_obj, created = UserProfile.objects.get_or_create(user=user)
    if created and user.is_staff:
        profile_obj.role = 'teacher'
        profile_obj.save()

    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, instance=profile_obj)
        password_form = ChangePasswordForm(request.POST)

        new_password = request.POST.get('new_password', '').strip()

        if profile_form.is_valid():
            user.first_name = profile_form.cleaned_data.get('first_name', '')
            user.last_name = profile_form.cleaned_data.get('last_name', '')
            user.email = profile_form.cleaned_data.get('email', '')
            user.save()
            profile_form.save()

            if new_password:
                if password_form.is_valid():
                    old_password = password_form.cleaned_data.get('old_password')
                    if user.check_password(old_password):
                        user.set_password(new_password)
                        user.save()
                        messages.success(request, 'Updated successfully!')
                        return redirect('profile')
                    else:
                        messages.error(request, 'Old password is incorrect!')
                else:
                    messages.error(request, 'New password is not valid!')
            else:
                messages.success(request, 'Updated information successfully!')
                return redirect('profile')
        else:
            messages.error(request, 'Invalid information. Please check again.')

    else:
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
