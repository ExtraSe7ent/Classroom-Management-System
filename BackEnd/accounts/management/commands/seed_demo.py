"""
Management command to generate rich mock data for demo.

Run:  python manage.py seed_demo
The command will DELETE old transactional data + non-superuser users, then recreate
a new set of demo data including: 3 demo accounts (admin/teacher/student), multiple teachers,
students, classrooms, schedules, enrollments, attendances, comments, assignments, and submissions.
"""
import random
from datetime import timedelta, time

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User, Student, UserProfile
from assignments.models import Assignment, Submission
from classrooms.models import (
    Attendance, Classroom, ClassEnrollment, DailyComment, Schedule,
)

# Student names tuples (first_name, last_name)
STUDENT_NAMES = [
    ("John", "Smith"), ("Alice", "Johnson"), ("Bob", "Brown"),
    ("Charlie", "Davis"), ("Diana", "Miller"), ("Evan", "Garcia"),
    ("Fiona", "Rodriguez"), ("George", "Wilson"), ("Hannah", "Martinez"),
    ("Ian", "Anderson"), ("Julia", "Taylor"), ("Kevin", "Thomas"),
    ("Laura", "Hernandez"), ("Michael", "Moore"), ("Nina", "Martin"),
    ("Oliver", "Jackson"), ("Patricia", "Thompson"), ("Quincy", "White"),
]

ATTENDANCE_WEIGHTS = (
    ['present'] * 7 + ['late'] * 1 + ['absent_excused'] * 1 + ['absent_unexcused'] * 1
)

COMMENTS = [
    "Active participation and good understanding of the lesson.",
    "Needs to focus more, tends to talk in class.",
    "Completed all homework, showing clear progress.",
    "Seemed a bit tired today, focus could be improved.",
    "Listening skills have improved, keep up the good work.",
    "Should practice pronunciation more at home.",
    "Very helpful to classmates during group work.",
    "Excellent performance on today's pop quiz.",
]


class Command(BaseCommand):
    help = "Seed mock data to demo the classroom management system."

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(42)
        self.stdout.write("→ Deleting old data...")
        Submission.objects.all().delete()
        Assignment.objects.all().delete()
        DailyComment.objects.all().delete()
        Attendance.objects.all().delete()
        ClassEnrollment.objects.all().delete()
        Schedule.objects.all().delete()
        Classroom.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

        # ============ ADMIN ACCOUNT (superuser) ============
        admin, _ = User.objects.get_or_create(
            username='admin',
            defaults=dict(email='admin@edu.vn', first_name='Principal', last_name='Demo', phone_number='0900000000'),
        )
        admin.role = User.ROLE_ADMIN
        admin.is_staff = True
        admin.is_superuser = True
        admin.first_name = admin.first_name or 'Principal'
        admin.last_name = admin.last_name or 'Demo'
        admin.set_password('Admin@123')
        admin.save()
        UserProfile.objects.get_or_create(user=admin, defaults=dict(address='Hanoi'))

        # ============ TEACHERS ============
        teachers_data = [
            ('teacher', 'Sarah', 'Connor', '0901000001'),
            ('gv_hung', 'John', 'Watson', '0901000002'),
            ('gv_mai', 'Mary', 'Jane', '0901000003'),
        ]
        teachers = []
        for username, fn, ln, phone in teachers_data:
            t = User.objects.create(
                username=username, first_name=fn, last_name=ln,
                role=User.ROLE_TEACHER, phone_number=phone, email=f'{username}@edu.vn',
            )
            t.set_password('Teacher@123')
            t.save()
            UserProfile.objects.get_or_create(user=t, defaults=dict(address='Hanoi'))
            teachers.append(t)
        self.stdout.write(f"  + {len(teachers)} teachers")

        # ============ STUDENTS ============
        students = []
        for i, (fn, ln) in enumerate(STUDENT_NAMES, start=1):
            username = 'student' if i == 3 else f'hs{i:02d}'
            password = 'Student@123' if i == 3 else 'Hocsinh@123'
            u = User.objects.create(
                username=username, first_name=fn, last_name=ln,
                role=User.ROLE_STUDENT, phone_number=f'09120000{i:02d}',
                email=f'{username}@edu.vn',
            )
            u.set_password(password)
            u.save()
            Student.objects.create(user=u, student_code=f'HS2026-{i:03d}')
            UserProfile.objects.get_or_create(
                user=u,
                defaults=dict(address=f'No. {i} Cau Giay St, Hanoi'),
            )
            students.append(u)
        self.stdout.write(f"  + {len(students)} students")

        # ============ CLASSROOMS & SCHEDULES ============
        # (name, teacher, tuition, room, [(day_of_week, start_time, end_time)])
        classes_data = [
            ("English Communication A1", teachers[0], 1200000, "Room A1",
             [(0, time(18, 0), time(19, 30)), (2, time(18, 0), time(19, 30))]),
            ("Advanced Math Class 9", teachers[1], 1500000, "Room A2",
             [(1, time(19, 45), time(21, 15)), (3, time(19, 45), time(21, 15))]),
            ("IELTS Preparation Foundation", teachers[2], 2500000, "Room B1",
             [(0, time(17, 30), time(19, 0)), (4, time(17, 30), time(19, 0))]),
            ("Scratch Coding for Kids", teachers[0], 1000000, "Room B2",
             [(5, time(9, 0), time(10, 30)), (6, time(9, 0), time(10, 30))]),
        ]
        classrooms = []
        for name, teacher, tuition, room, slots in classes_data:
            c = Classroom.objects.create(
                name=name, teacher=teacher, tuition=tuition,
                description=f"Class {name} managed by {teacher.get_full_name()}.",
                is_active=True,
            )
            for day, start, end in slots:
                Schedule.objects.create(
                    classroom=c, day_of_week=day, start_time=start, end_time=end, room_name=room,
                )
            classrooms.append(c)
        self.stdout.write(f"  + {len(classrooms)} classrooms (with schedules)")

        # ============ GHI DANH ============
        for c in classrooms:
            members = random.sample(students, random.randint(8, 11))
            for s in members:
                ClassEnrollment.objects.get_or_create(classroom=c, student=s)
        # Ensure the demo student account is enrolled in the first two classrooms
        demo_student = next(s for s in students if s.username == 'student')
        for c in classrooms[:2]:
            ClassEnrollment.objects.get_or_create(classroom=c, student=demo_student)
        total_enroll = ClassEnrollment.objects.count()
        self.stdout.write(f"  + {total_enroll} enrollments")

        # ============ ATTENDANCE & COMMENTS (Last 4 weeks) ============
        today = timezone.localdate()
        att_count = 0
        cmt_count = 0
        for c in classrooms:
            enrolled = list(c.enrollments.select_related('student'))
            for sch in c.schedules.all():
                # find dates in the past 28 days that match the day of the week of this schedule slot
                for delta in range(28, -1, -1):
                    d = today - timedelta(days=delta)
                    if d.weekday() != sch.day_of_week:
                        continue
                    for enr in enrolled:
                        status = random.choice(ATTENDANCE_WEIGHTS)
                        Attendance.objects.update_or_create(
                            classroom=c, student=enr.student, schedule=sch, date=d,
                            defaults={'status': status, 'remark': ''},
                        )
                        att_count += 1
                        # ~30% chance that teacher left a comment for the student on that day
                        if random.random() < 0.3:
                            DailyComment.objects.update_or_create(
                                classroom=c, student=enr.student, schedule=sch, date=d,
                                defaults={
                                    'content': random.choice(COMMENTS),
                                    'created_by': c.teacher,
                                },
                            )
                            cmt_count += 1
        self.stdout.write(f"  + {att_count} attendance records, {cmt_count} comments")

        # ============ ASSIGNMENTS & SUBMISSIONS ============
        now = timezone.now()
        assignment_titles = [
            ("Homework Unit 1: Greetings", -5),
            ("Vocabulary Review: Family", -2),
            ("Weekly Homework Assignment", 4),
        ]
        asm_count = 0
        sub_count = 0
        graded_count = 0
        for c in classrooms:
            enrolled_students = [e.student for e in c.enrollments.all()]
            for title, day_offset in assignment_titles:
                due = now + timedelta(days=day_offset)
                asm = Assignment.objects.create(
                    classroom=c,
                    title=f"{title} - {c.name}",
                    description="Please complete all required tasks and submit on time.",
                    due_date=due,
                )
                asm_count += 1
                # Overdue assignments: many students submitted, some graded
                if day_offset < 0:
                    submitters = random.sample(
                        enrolled_students, k=max(1, int(len(enrolled_students) * 0.7))
                    )
                    for s in submitters:
                        is_graded = random.random() < 0.6
                        Submission.objects.create(
                            assignment=asm, student=s,
                            content="I would like to submit my homework.",
                            status=Submission.STATUS_GRADED if is_graded else Submission.STATUS_PENDING,
                            grade=round(random.uniform(6.0, 10.0), 1) if is_graded else None,
                            teacher_comment="Good job, but try to structure your work better." if is_graded else "",
                        )
                        sub_count += 1
                        if is_graded:
                            graded_count += 1
        self.stdout.write(f"  + {asm_count} assignments, {sub_count} submissions ({graded_count} graded)")

        # ============ SUMMARY ============
        self.stdout.write(self.style.SUCCESS("\n✓ Demo data seeded successfully!\n"))
        self.stdout.write("DEMO ACCOUNTS (one account for each role):")
        self.stdout.write("  • Admin/Principal   : admin    / Admin@123")
        self.stdout.write("  • Teacher           : teacher  / Teacher@123")
        self.stdout.write("  • Student/Parent    : student  / Student@123")
        self.stdout.write("  (other students: hs01..hs18 / Hocsinh@123 ; other teachers: gv_hung, gv_mai / Teacher@123)")
