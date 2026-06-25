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
    
    # Use annotation to count student numbers directly from SQL Server
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
            messages.success(request, f"Class {new_class.name} successfully created. Add students and schedules!")
            # Navigate straight to the details page to add students immediately
            return redirect('classroom_detail', pk=new_class.id)
    else:
        # By default, the teacher is selected as the person currently logged in
        form = ClassroomForm(initial={'teacher': request.user})
    return render(request, 'classrooms/classroom_form.html', {'form': form, 'title': 'Create a new class'})

@login_required
def classroom_update(request, pk):
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('user_dashboard')
    
    classroom = get_object_or_404(Classroom, pk=pk)
    if request.method == 'POST':
        form = ClassroomForm(request.POST, instance=classroom)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated class {classroom.name}")
            return redirect('classroom_list')
    else:
        form = ClassroomForm(instance=classroom)
    return render(request, 'classrooms/classroom_form.html', {'form': form, 'title': f'Edit class {classroom.name}'})

@login_required
def classroom_delete(request, pk):
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('user_dashboard')
    
    classroom = get_object_or_404(Classroom, pk=pk)
    if request.method == 'POST':
        name = classroom.name
        classroom.delete()
        messages.success(request, f"Class {name} successfully deleted.")
    return redirect('classroom_list')

@login_required
def schedule_create(request, classroom_id):
    """Handling class scheduling for a specific class with duplicate scheduling validation"""
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('user_dashboard')
    
    classroom = get_object_or_404(Classroom, id=classroom_id)
    form = ScheduleForm() # Initialize the default form for the GET method

    if request.method == 'POST':
        form = ScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.classroom = classroom
            try:
                schedule.save() # Trigger clean() and save()
                messages.success(request, "Successfully schedule your classes!")
                return redirect('classroom_detail', pk=classroom_id) # Navigate back to the layer details to see the results
            except ValidationError as e:
                # Get the first error from ValidationError to display to the user
                error_msg = e.messages[0] if hasattr(e, 'messages') else str(e)
                messages.error(request, error_msg)
            except Exception as e:
                messages.error(request, "An error occurred while saving data.")
    
    return render(request, 'classrooms/schedule_form.html', {'form': form, 'classroom': classroom})

@login_required
def schedule_delete(request, pk):
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('user_dashboard')
    schedule = get_object_or_404(Schedule, pk=pk)
    classroom_id = schedule.classroom.id
    schedule.delete()
    messages.success(request, "Lesson deleted successfully.")
    return redirect('classroom_detail', pk=classroom_id)

@login_required
def classroom_detail(request, pk):
    """Detailed administration page of a class: View calendar, list of students and Enroll"""
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('user_dashboard')
    
    classroom = get_object_or_404(Classroom, pk=pk)
    schedules = classroom.schedules.all().order_by('day_of_week', 'start_time')
    
    # Get the list of classes that have been attended today for this class
    today = timezone.now().date()
    attended_ids = set(Attendance.objects.filter(classroom=classroom, date=today).values_list('schedule_id', flat=True))

    # 1. Manage the list of students IN CLASS
    q_enrolled = request.GET.get('q_enrolled', '')
    enrollments = classroom.enrollments.all().select_related('student')
    if q_enrolled:
        enrollments = enrollments.filter(
            # Search by student's username, first_name, last_name
            Q(student__username__icontains=q_enrolled) | 
            Q(student__first_name__icontains=q_enrolled) | 
            Q(student__last_name__icontains=q_enrolled)
        )

    # 2. Handling SEARCH FOR STUDENTS TO ADD (Not yet in class)
    q_potential = request.GET.get('q_potential', '')
    already_enrolled = classroom.enrollments.values_list('student_id', flat=True)
    potential_students = User.objects.filter(role='student').exclude(id__in=already_enrolled).select_related('student_profile')
    
    if q_potential:
        # Search by username, first_name, last_name, student_code of potential students
        potential_students = potential_students.filter(
            Q(username__icontains=q_potential) | 
            Q(first_name__icontains=q_potential) | 
            Q(last_name__icontains=q_potential) |
            Q(student_profile__student_code__icontains=q_potential)
        )
    else:
        # By default, the 10 newest students who do not have a class are taken to display if there is no query
        potential_students = potential_students.order_by('-date_joined')[:10]

    enroll_form = EnrollmentForm()

    if request.method == 'POST':
        # Handle deletion of students from class
        if 'remove_student' in request.POST:
            enrollment_id = request.POST.get('enrollment_id')
            enroll_obj = get_object_or_404(ClassEnrollment, id=enrollment_id, classroom=classroom)
            enroll_obj.delete()
            messages.success(request, "Student removed from class.")
            return redirect('classroom_detail', pk=pk)
            
        # Handling MASS DELETION of students from class
        if 'bulk_remove' in request.POST:
            enrollment_ids = request.POST.getlist('enrollment_ids')
            if enrollment_ids:
                deleted_count, _ = ClassEnrollment.objects.filter(id__in=enrollment_ids, classroom=classroom).delete()
                messages.success(request, f"Deleted {deleted_count} students from class.")
            else:
                messages.warning(request, "Please select at least one student to delete.")
            return redirect('classroom_detail', pk=pk)

        # Handling ADD MORE STUDENTS TO CLASS (Mass Enrollment)
        if 'add_to_class' in request.POST:
            student_ids = request.POST.getlist('student') # Get list of IDs from checkbox
            base_url = reverse('classroom_detail', kwargs={'pk': pk})
            
            if not student_ids:
                messages.error(request, "Please select at least one student to add.")
                return redirect(f"{base_url}?open_modal=1")
            
            added_count = 0
            for s_id in student_ids:
                if not ClassEnrollment.objects.filter(classroom=classroom, student_id=s_id).exists():
                    ClassEnrollment.objects.create(classroom=classroom, student_id=int(s_id))
                    added_count += 1
            
            messages.success(request, f"Successfully enrolled {added_count} new students.")
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
    # Check if there is an open_modal parameter from the GET request, add it to the context so that JS opens the modal
    if request.GET.get('open_modal') == '1':
        context['open_enroll_modal'] = True
    return render(request, 'classrooms/classroom_detail.html', context)

@login_required
def attendance_class_list(request):
    """Class selection page for attendance - Priority is given to classes scheduled today"""
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('user_dashboard')

    # Gets the date from the GET parameter (if any), default is today's date
    date_str = request.GET.get('date')
    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            target_date = timezone.localdate()
    else:
        target_date = timezone.localdate()

    weekday = target_date.weekday() # Python: 0 (T2) -> 6 (CN)

    # 1. Get the sessions taking place on the selected date
    schedules_target_day = list(Schedule.objects.filter(day_of_week=weekday).select_related('classroom'))
    
    # Get a list of class IDs that were attended that day
    attended_ids = set(Attendance.objects.filter(date=target_date).values_list('schedule_id', flat=True).distinct())

    for s in schedules_target_day:
        s.is_attended = s.id in attended_ids

    # 2. Take all other layers to review the history if needed
    all_classrooms = Classroom.objects.all().order_by('name')

    return render(request, 'classrooms/attendance_class_list.html', {
        'schedules_today': schedules_target_day,
        'all_classrooms': all_classrooms,
        'today': target_date,
        'is_real_today': target_date == timezone.localdate()
    })

@login_required
def attendance_manage(request, classroom_id, schedule_id, date_str):
    """Process student attendance for a specific class session UC05"""
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('user_dashboard')

    classroom = get_object_or_404(Classroom, pk=classroom_id)
    schedule = get_object_or_404(Schedule, pk=schedule_id, classroom=classroom)
    
    # Convert date_str to date object
    try:
        if date_str == 'today':
            target_date = timezone.localdate()
        else:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, "Invalid date format.")
        return redirect('classroom_detail', pk=classroom_id)

    # EX_FUTURE_DATE: Block attendance for future dates based on localdate
    if target_date > timezone.localdate():
        messages.error(request, "Attendance cannot be taken for classes that have not yet taken place!")
        return redirect('classroom_detail', pk=classroom_id)

    # Get the list of students enrolled in the class
    enrollments = ClassEnrollment.objects.filter(classroom=classroom).select_related('student')
    
    # EX_EMPTY_CLASS: Check for empty class
    if not enrollments.exists():
        messages.warning(request, "There are currently no students in the class to take attendance.")
        return redirect('classroom_detail', pk=classroom_id)

    # Get existing attendance data (if any) - EX_ALREADY_ATTENDED
    existing_attendance = Attendance.objects.filter(
        classroom=classroom, schedule=schedule, date=target_date
    ).values('student_id', 'status', 'remark')
    
    # Convert into dictionary for quick lookup in template
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
                
                messages.success(request, f"The attendance table on {target_date} has been updated successfully.")
                return redirect('classroom_detail', pk=classroom_id)
        except Exception as e:
            messages.error(request, f"Error when saving data: {str(e)}")

    # Define context inside the function and before rendering
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
    """Study Timeline for Students (UC10)"""
    if not request.user.role == 'student':
        return redirect('admin_dashboard')
    
    # Get this student's attendance history
    attendances = Attendance.objects.filter(student=request.user).select_related('classroom', 'schedule').order_by('-date', '-schedule__start_time')
    
    # Can be combined with DailyComments later here
    
    context = {'attendances': attendances}
    return render(request, 'classrooms/student_timeline.html', context)

@login_required
def daily_review_manage(request, classroom_id, schedule_id, date_str):
    """Process import of daily comments in bulk UC06"""
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return redirect('user_dashboard')

    classroom = get_object_or_404(Classroom, pk=classroom_id)
    schedule = get_object_or_404(Schedule, pk=schedule_id, classroom=classroom)
    
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return redirect('classroom_detail', pk=classroom_id)

    # EX_FUTURE_DATE: Block comments for future dates
    if target_date > timezone.localdate():
        messages.error(request, "Comments cannot be entered for a class that has not yet taken place!")
        return redirect('classroom_detail', pk=classroom_id)

    enrollments = ClassEnrollment.objects.filter(classroom=classroom).select_related('student')
    
    # Get attendance information to display (UX helps teachers remember the class situation)
    attendance_records = Attendance.objects.filter(classroom=classroom, schedule=schedule, date=target_date)
    attendance_map = {att.student_id: att for att in attendance_records}

    # Get old comments (if any) to display on the form
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
                    messages.warning(request, "Please enter at least one comment before saving!")
                else:
                    messages.success(request, f"{target_date} date comment successfully saved.")
                    return redirect('classroom_detail', pk=classroom_id)
        except Exception as e:
            messages.error(request, f"System error: {str(e)}")

    context = {
        'classroom': classroom,
        'schedule': schedule,
        'target_date': target_date,
        'enrollments': enrollments,
        'attendance_map': attendance_map,
        'comment_map': comment_map,
    }
    return render(request, 'classrooms/daily_review_form.html', context)
