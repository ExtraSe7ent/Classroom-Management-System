"""
Management command tạo dữ liệu mẫu phong phú để demo.

Chạy:  python manage.py seed_demo
Lệnh sẽ XOÁ dữ liệu nghiệp vụ cũ + user không phải superuser, rồi tạo lại
bộ dữ liệu mới gồm: 3 tài khoản demo (admin/teacher/student), nhiều giáo viên,
học sinh, lớp học, lịch học, ghi danh, điểm danh, nhận xét, bài tập và bài nộp.
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

# (họ + đệm, tên) — đặt vào first_name/last_name sao cho get_full_name() đọc đúng thứ tự tiếng Việt
STUDENT_NAMES = [
    ("Nguyễn Văn", "An"), ("Trần Thị", "Bình"), ("Lê Minh", "Anh"),
    ("Phạm Hoàng", "Long"), ("Hoàng Thị", "Mai"), ("Vũ Đức", "Khang"),
    ("Đặng Thị", "Hương"), ("Bùi Văn", "Nam"), ("Đỗ Thị", "Lan"),
    ("Ngô Minh", "Quân"), ("Dương Thị", "Thảo"), ("Lý Văn", "Tuấn"),
    ("Phan Thị", "Ngọc"), ("Võ Hoàng", "Phúc"), ("Đinh Thị", "Trang"),
    ("Mai Văn", "Hải"), ("Trịnh Thị", "Yến"), ("Tạ Minh", "Đức"),
]

ATTENDANCE_WEIGHTS = (
    ['present'] * 7 + ['late'] * 1 + ['absent_excused'] * 1 + ['absent_unexcused'] * 1
)

COMMENTS = [
    "Em tiếp thu bài tốt, phát biểu sôi nổi.",
    "Cần chú ý hơn trong giờ học, hay nói chuyện riêng.",
    "Làm bài tập đầy đủ, có tiến bộ rõ rệt.",
    "Hôm nay em hơi mệt, chưa tập trung tốt.",
    "Kỹ năng nghe đã cải thiện, tiếp tục phát huy.",
    "Em cần luyện thêm phần phát âm ở nhà.",
    "Rất tích cực hỗ trợ các bạn trong nhóm.",
    "Hoàn thành xuất sắc bài kiểm tra nhỏ trên lớp.",
]


class Command(BaseCommand):
    help = "Tạo dữ liệu mẫu phong phú để demo hệ thống quản lý lớp học."

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(42)
        self.stdout.write("→ Xoá dữ liệu cũ...")
        Submission.objects.all().delete()
        Assignment.objects.all().delete()
        DailyComment.objects.all().delete()
        Attendance.objects.all().delete()
        ClassEnrollment.objects.all().delete()
        Schedule.objects.all().delete()
        Classroom.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

        # ============ TÀI KHOẢN ADMIN (superuser) ============
        admin, _ = User.objects.get_or_create(
            username='admin',
            defaults=dict(email='admin@edu.vn', first_name='Hiệu trưởng', last_name='Demo'),
        )
        admin.role = User.ROLE_ADMIN
        admin.is_staff = True
        admin.is_superuser = True
        admin.first_name = admin.first_name or 'Hiệu trưởng'
        admin.last_name = admin.last_name or 'Demo'
        admin.set_password('Admin@123')
        admin.save()
        UserProfile.objects.get_or_create(user=admin, defaults=dict(phone='0900000000', address='Hà Nội'))

        # ============ GIÁO VIÊN ============
        teachers_data = [
            ('teacher', 'Nguyễn Thị', 'Lan', '0901000001'),
            ('gv_hung', 'Trần Văn', 'Hùng', '0901000002'),
            ('gv_mai', 'Phạm Thị', 'Mai', '0901000003'),
        ]
        teachers = []
        for username, fn, ln, phone in teachers_data:
            t = User.objects.create(
                username=username, first_name=fn, last_name=ln,
                role=User.ROLE_TEACHER, phone_number=phone, email=f'{username}@edu.vn',
            )
            t.set_password('Teacher@123')
            t.save()
            UserProfile.objects.get_or_create(user=t, defaults=dict(phone=phone, address='Hà Nội'))
            teachers.append(t)
        self.stdout.write(f"  + {len(teachers)} giáo viên")

        # ============ HỌC SINH ============
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
                defaults=dict(phone=f'09120000{i:02d}', address=f'Số {i} phố Cầu Giấy, Hà Nội'),
            )
            students.append(u)
        self.stdout.write(f"  + {len(students)} học sinh")

        # ============ LỚP HỌC + LỊCH HỌC ============
        # (tên, giáo viên, học phí, phòng, [(thứ, giờ bắt đầu, giờ kết thúc)])
        classes_data = [
            ("Tiếng Anh Giao Tiếp A1", teachers[0], 1200000, "Phòng A1",
             [(0, time(18, 0), time(19, 30)), (2, time(18, 0), time(19, 30))]),
            ("Toán Nâng Cao Lớp 9", teachers[1], 1500000, "Phòng A2",
             [(1, time(19, 45), time(21, 15)), (3, time(19, 45), time(21, 15))]),
            ("Luyện Thi IELTS Foundation", teachers[2], 2500000, "Phòng B1",
             [(0, time(17, 30), time(19, 0)), (4, time(17, 30), time(19, 0))]),
            ("Lập Trình Scratch Cho Trẻ", teachers[0], 1000000, "Phòng B2",
             [(5, time(9, 0), time(10, 30)), (6, time(9, 0), time(10, 30))]),
        ]
        classrooms = []
        for name, teacher, tuition, room, slots in classes_data:
            c = Classroom.objects.create(
                name=name, teacher=teacher, tuition=tuition,
                description=f"Lớp {name} do thầy/cô {teacher.get_full_name()} phụ trách.",
                is_active=True,
            )
            for day, start, end in slots:
                Schedule.objects.create(
                    classroom=c, day_of_week=day, start_time=start, end_time=end, room_name=room,
                )
            classrooms.append(c)
        self.stdout.write(f"  + {len(classrooms)} lớp học (kèm lịch học)")

        # ============ GHI DANH ============
        for c in classrooms:
            members = random.sample(students, random.randint(8, 11))
            for s in members:
                ClassEnrollment.objects.get_or_create(classroom=c, student=s)
        # Đảm bảo tài khoản student demo có mặt ở 2 lớp đầu
        demo_student = next(s for s in students if s.username == 'student')
        for c in classrooms[:2]:
            ClassEnrollment.objects.get_or_create(classroom=c, student=demo_student)
        total_enroll = ClassEnrollment.objects.count()
        self.stdout.write(f"  + {total_enroll} lượt ghi danh")

        # ============ ĐIỂM DANH + NHẬN XÉT (4 tuần gần nhất) ============
        today = timezone.localdate()
        att_count = 0
        cmt_count = 0
        for c in classrooms:
            enrolled = list(c.enrollments.select_related('student'))
            for sch in c.schedules.all():
                # các ngày trong 28 ngày qua trùng thứ của buổi học
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
                        # ~30% buổi có nhận xét của giáo viên
                        if random.random() < 0.3:
                            DailyComment.objects.update_or_create(
                                classroom=c, student=enr.student, schedule=sch, date=d,
                                defaults={
                                    'content': random.choice(COMMENTS),
                                    'created_by': c.teacher,
                                },
                            )
                            cmt_count += 1
        self.stdout.write(f"  + {att_count} bản ghi điểm danh, {cmt_count} nhận xét")

        # ============ BÀI TẬP + BÀI NỘP ============
        now = timezone.now()
        assignment_titles = [
            ("Bài tập Unit 1: Greetings", -5),
            ("Ôn tập từ vựng chủ đề Gia đình", -2),
            ("Bài tập về nhà tuần này", 4),
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
                    description="Hoàn thành các yêu cầu trong đề bài và nộp đúng hạn.",
                    due_date=due,
                )
                asm_count += 1
                # Bài đã quá hạn: nhiều học sinh đã nộp, một phần đã chấm
                if day_offset < 0:
                    submitters = random.sample(
                        enrolled_students, k=max(1, int(len(enrolled_students) * 0.7))
                    )
                    for s in submitters:
                        is_graded = random.random() < 0.6
                        Submission.objects.create(
                            assignment=asm, student=s,
                            content="Em xin nộp bài làm ạ.",
                            status=Submission.STATUS_GRADED if is_graded else Submission.STATUS_PENDING,
                            grade=round(random.uniform(6.0, 10.0), 1) if is_graded else None,
                            teacher_comment="Bài làm tốt, cần trình bày gọn hơn." if is_graded else "",
                        )
                        sub_count += 1
                        if is_graded:
                            graded_count += 1
        self.stdout.write(f"  + {asm_count} bài tập, {sub_count} bài nộp ({graded_count} đã chấm)")

        # ============ TÓM TẮT ============
        self.stdout.write(self.style.SUCCESS("\n✓ Tạo dữ liệu mẫu thành công!\n"))
        self.stdout.write("TÀI KHOẢN DEMO (mỗi vai trò 1 tài khoản):")
        self.stdout.write("  • Admin/Hiệu trưởng : admin    / Admin@123")
        self.stdout.write("  • Giáo viên          : teacher  / Teacher@123")
        self.stdout.write("  • Học sinh/Phụ huynh : student  / Student@123")
        self.stdout.write("  (các học sinh khác: hs01..hs18 / Hocsinh@123 ; giáo viên khác: gv_hung, gv_mai / Teacher@123)")
