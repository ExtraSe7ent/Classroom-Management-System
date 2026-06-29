from datetime import time, timedelta
import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from core.models import UserProfile, Class, Student, Schedule, Assignment, Submission, Attendance, DailyComment

SUBJECT_CONTENT = {
    'toan': {
        'questions': [
            (
                "Giải phương trình bậc hai",
                "Giải phương trình: 2x² – 5x + 3 = 0. Tính tổng và tích hai nghiệm rồi kiểm tra lại bằng định lý Viète.",
            ),
            (
                "Bài tập hình học – đường cao",
                "Cho tam giác ABC có AB = 6 cm, AC = 8 cm, BC = 10 cm. Chứng minh tam giác vuông tại A và tính độ dài đường cao AH.",
            ),
            (
                "Tìm giá trị nguyên của biểu thức",
                "Tìm tất cả x nguyên để biểu thức M = (2x + 1) / (x – 3) nhận giá trị nguyên.",
            ),
            (
                "Vẽ và phân tích đồ thị hàm số",
                "Vẽ đồ thị hàm số y = x² – 2x – 3. Xác định đỉnh, trục đối xứng và toàn bộ giao điểm với hai trục toạ độ.",
            ),
            (
                "Giải hệ phương trình bậc nhất",
                "Giải hệ phương trình: { 3x + 2y = 12 ; 2x – y = 1 }. Kiểm tra nghiệm bằng cách thế lại vào từng phương trình.",
            ),
            (
                "Chứng minh tứ giác nội tiếp",
                "Cho tứ giác ABCD có ∠A + ∠C = 180°. Chứng minh ABCD nội tiếp đường tròn và tính bán kính ngoại tiếp nếu AC = 10 cm.",
            ),
            (
                "Bài tập lượng giác cơ bản",
                "Cho sin α = 3/5 với 0° < α < 90°. Tính cos α, tan α, cot α và giá trị biểu thức P = sin²α + 2cos²α – 1.",
            ),
            (
                "Giải bất phương trình hữu tỉ",
                "Giải bất phương trình (x² – 4x + 3) / (x – 2) ≥ 0 và biểu diễn tập nghiệm trên trục số.",
            ),
        ],
        'notes': [
            "Em làm được hết, nhưng câu hình học em còn chưa chắc lắm ạ.",
            "Em giải theo cách khác thầy dạy trên lớp, mong thầy xem và góp ý ạ.",
            "Câu cuối em để trống vì chưa hiểu phần đường tròn ngoại tiếp ạ.",
            "Em làm lại câu 3 hai lần vì sai lần đầu, mong cô đọc phần sau ạ.",
            "Em nộp muộn vì máy bị lỗi khi vẽ đồ thị, xin cô thông cảm ạ.",
            "Thưa cô, em không chắc kết quả câu bất phương trình, mong cô chữa kỹ giúp em ạ.",
            "Em làm bài tay rồi chụp lại thành file, mong cô đọc được ạ.",
        ],
        'file_prefix': 'de_toan',
        'sub_ext': 'pdf',
        'sub_mime': 'application/pdf',
        'sub_prefix': 'bai_lam_toan',
    },
    'van': {
        'questions': [
            (
                "Phân tích đoạn thơ Trao duyên",
                "Phân tích 8 câu đầu đoạn trích 'Trao duyên' (Truyện Kiều – Nguyễn Du). Làm nổi bật tâm trạng đau đớn, bế tắc của Kiều khi trao mối tình đầu cho em.",
            ),
            (
                "Nghị luận xã hội – lòng biết ơn",
                "Viết đoạn văn nghị luận xã hội khoảng 200 chữ về lòng biết ơn đối với thầy cô giáo. Cần có luận điểm rõ ràng, dẫn chứng thực tế.",
            ),
            (
                "Hình tượng người lính trong Đồng chí",
                "Cảm nhận hình tượng người lính trong bài thơ 'Đồng chí' của Chính Hữu. Phân tích ít nhất 2 hình ảnh thơ đặc sắc và nêu ý nghĩa biểu tượng.",
            ),
            (
                "Phân tích nhân vật Lão Hạc",
                "Phân tích nhân vật Lão Hạc trong truyện ngắn cùng tên của Nam Cao. Làm rõ bi kịch người nông dân Việt Nam trước Cách mạng qua sự kiện bán con chó Vàng.",
            ),
            (
                "Phân tích khổ 1 bài Đây thôn Vĩ Dạ",
                "Phân tích vẻ đẹp ngôn ngữ và hình ảnh thơ trong khổ thơ đầu bài 'Đây thôn Vĩ Dạ' (Hàn Mặc Tử). Chú ý bút pháp lãng mạn và nỗi niềm của thi nhân.",
            ),
            (
                "Nghị luận về hiện tượng nghiện điện thoại",
                "Viết bài nghị luận xã hội (300–400 chữ) về hiện tượng học sinh sử dụng điện thoại quá nhiều. Nêu nguyên nhân, hậu quả và giải pháp.",
            ),
            (
                "Cảm nhận bài thơ Viếng lăng Bác",
                "Cảm nhận tình cảm của nhà thơ Viễn Phương đối với Bác Hồ qua hai khổ thơ đầu bài 'Viếng lăng Bác'. Liên hệ với cảm xúc của bản thân.",
            ),
        ],
        'notes': [
            "Em viết dài hơn yêu cầu một chút vì không cắt được ý, mong cô thông cảm ạ.",
            "Đoạn văn của em chưa có nhiều dẫn chứng, em sẽ bổ sung nếu cô cho phép ạ.",
            "Em tham khảo thêm tài liệu nhưng tự viết lại hoàn toàn bằng lời của mình ạ.",
            "Em không chắc phần phân tích nghệ thuật, mong cô góp ý thêm ạ.",
            "Em viết tay rồi chụp ảnh đính kèm ạ, mong cô đọc được ạ.",
            "Thưa cô, em chưa được học tác phẩm này trên lớp chính nên bài còn yếu ạ.",
            "Em không nhớ chính xác câu thơ nên trích không nguyên văn, xin cô thông cảm ạ.",
        ],
        'file_prefix': 'de_van',
        'sub_ext': 'docx',
        'sub_mime': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'sub_prefix': 'bai_van',
    },
    'anh': {
        'questions': [
            (
                "IELTS Writing Task 2 – Social Media",
                "Write an IELTS-style essay (minimum 250 words): 'Social media has more negative effects on society than positive ones.' Discuss both views and give your own opinion with supporting arguments.",
            ),
            (
                "Conditional Sentences – Unit 5",
                "Complete exercises 3–7 on page 48 (Unit 5). Focus on conditional type 1 and type 2. Additionally, write 5 original example sentences using each type.",
            ),
            (
                "Reading Comprehension – Climate Change",
                "Read the passage 'Climate Change and Its Effects' (handout). Answer all comprehension questions (True/False + Short Answer). Justify each answer with a quoted sentence from the text.",
            ),
            (
                "IELTS Speaking Part 2 – A Memorable Trip",
                "Describe a memorable trip you have taken. Prepare a full script of 200–250 words covering: where you went, who you went with, what you did, and why it was memorable.",
            ),
            (
                "Passive Voice – Rewriting Sentences",
                "Rewrite the 10 given sentences using the passive voice. For each sentence, identify the original tense and explain in one line why the passive voice is preferred here.",
            ),
            (
                "IELTS Writing Task 1 – Bar Chart",
                "Describe the bar chart showing internet usage by age group in 2010 versus 2023. Write at least 150 words, include a clear overview and highlight the most significant comparisons.",
            ),
            (
                "Vocabulary in Context – Unit 6",
                "From Unit 6, find 10 unfamiliar words. For each word write: the word, its part of speech, Vietnamese meaning, and one original English sentence that shows its meaning clearly.",
            ),
        ],
        'notes': [
            "I used some grammar structures from Unit 5 but I'm not sure they're all correct. Please correct me, ma'am.",
            "Em chưa hiểu conditional type 2 rõ lắm, phần đó em còn đoán ạ. Xin cô giảng lại.",
            "I wrote a bit more than 250 words for the essay. Hope that's still okay, ma'am!",
            "Em dùng từ điển để tra từ vựng nên một số từ có thể không đúng văn phong học thuật ạ.",
            "Em nộp bản script thay vì ghi âm vì micro bị hỏng ạ. Xin cô thông cảm.",
            "I'm not confident about sentences 7 and 8 in the passive voice exercise. Could you explain more?",
            "Thưa cô, em chưa đọc hết passage vì không có tài liệu, em làm theo trí nhớ từ lúc học trên lớp ạ.",
        ],
        'file_prefix': 'de_anh',
        'sub_ext': 'docx',
        'sub_mime': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'sub_prefix': 'answers_english',
    },
}


def _subject_key(cls):
    username = cls.teacher.username.lower()
    if 'toan' in username:
        return 'toan'
    if 'van' in username:
        return 'van'
    if 'anh' in username:
        return 'anh'
    return 'toan'


class Command(BaseCommand):
    help = 'Seed diverse demo data for EduManager'

    def _make_user(self, username, last_name, first_name, email, phone, password, is_staff=False, role='student'):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'last_name': last_name, 'first_name': first_name, 'email': email, 'is_staff': is_staff, 'is_superuser': False}
        )
        if created:
            user.set_password(password)
            user.save()
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.phone = phone
        profile.role = role
        profile.save()
        return user

    def handle(self, *args, **options):
        teacher_toan = self._make_user('TeacherToan', 'Giáo viên', 'Toán', 'toan@edumanager.local', '0900000001', 'TeacherToan@123', True, 'teacher')
        teacher_van  = self._make_user('TeacherVan',  'Giáo viên', 'Văn',  'van@edumanager.local',  '0911223344', 'TeacherVan@123',  True, 'teacher')
        teacher_anh  = self._make_user('TeacherAnh',  'Giáo viên', 'Anh',  'anh@edumanager.local',  '0922334455', 'TeacherAnh@123',  True, 'teacher')

        students = []
        first_names = ['Anh', 'Bình', 'Châu', 'Dũng', 'Em', 'Phong', 'Giang', 'Hải', 'Linh', 'Khánh', 'Minh', 'Ngọc', 'Oanh', 'Phương', 'Quân', 'Sơn', 'Trang', 'Uyên', 'Vinh', 'Yến']
        last_names  = ['Nguyễn', 'Trần', 'Lê', 'Phạm', 'Hoàng', 'Huỳnh', 'Phan', 'Vũ', 'Võ', 'Đặng', 'Bùi', 'Đỗ', 'Hồ', 'Ngô', 'Dương', 'Lý', 'Đinh', 'Đoàn', 'Lâm', 'Mai']

        for i in range(1, 21):
            uname = f'Student{i:02d}'
            user = self._make_user(
                uname,
                random.choice(last_names),
                random.choice(first_names),
                f'student{i:02d}@gmail.com',
                f'09{random.randint(10000000, 99999999)}',
                f'{uname}@123',
                role='student',
            )
            student, _ = Student.objects.get_or_create(user=user, defaults={'student_id': f'HS{i:03d}'})
            students.append(student)

        classes_data = [
            ('Lớp Toán 9A',               'Toán đại số và hình học cơ bản.',         'Cô Toán',  teacher_toan, 'Phòng A101'),
            ('Lớp Toán 9B (Nâng cao)',     'Toán học nâng cao ôn thi chuyên.',        'Cô Toán',  teacher_toan, 'Phòng A102'),
            ('Lớp Toán 10 (Chuyên)',       'Luyện đề đại học sớm.',                   'Cô Toán',  teacher_toan, 'Phòng A103'),
            ('Lớp Ngữ Văn 9',             'Luyện đề thi Ngữ Văn.',                   'Thầy Văn', teacher_van,  'Phòng B202'),
            ('Lớp Ngữ Văn 10',            'Phân tích tác phẩm văn học.',             'Thầy Văn', teacher_van,  'Phòng B203'),
            ('Lớp Tiếng Anh IELTS',       'Luyện thi IELTS mục tiêu 6.5.',           'Cô Anh',   teacher_anh,  'Phòng Lab 3'),
            ('Lớp Tiếng Anh Giao Tiếp',   'Tiếng Anh giao tiếp cơ bản.',             'Cô Anh',   teacher_anh,  'Phòng Lab 4'),
        ]

        classes = []
        for name, desc, tname, tuser, room in classes_data:
            cls, _ = Class.objects.get_or_create(
                name=name,
                defaults={'description': desc, 'teacher_name': tname, 'teacher': tuser, 'room': room},
            )
            classes.append(cls)

        for student in students:
            for cls in random.sample(classes, k=random.randint(2, 4)):
                cls.students.add(student)

        schedules = [
            (classes[0], 'Monday',    time(18, 0),  time(19, 30)),
            (classes[1], 'Wednesday', time(18, 0),  time(19, 30)),
            (classes[2], 'Friday',    time(18, 0),  time(19, 30)),
            (classes[3], 'Tuesday',   time(19, 30), time(21, 0)),
            (classes[4], 'Thursday',  time(19, 30), time(21, 0)),
            (classes[5], 'Saturday',  time(8, 0),   time(10, 0)),
            (classes[6], 'Sunday',    time(9, 0),   time(11, 0)),
        ]
        for cls, day, start, end in schedules:
            Schedule.objects.get_or_create(
                class_obj=cls, day_of_week=day, start_time=start,
                defaults={'end_time': end, 'room': cls.room},
            )

        now = timezone.now()

        assignments = []
        for cls in classes:
            sk = _subject_key(cls)
            content = SUBJECT_CONTENT[sk]
            chosen = random.sample(content['questions'], k=3)
            for i, (title, description) in enumerate(chosen, 1):
                dummy_file = SimpleUploadedFile(
                    f"{content['file_prefix']}_{i}.pdf",
                    b"file_content",
                    content_type="application/pdf",
                )
                due = now + timedelta(days=random.randint(-10, 10))
                a, _ = Assignment.objects.get_or_create(
                    title=title, class_obj=cls,
                    defaults={'description': description, 'due_date': due, 'created_by': cls.teacher, 'file': dummy_file},
                )
                assignments.append(a)

        feedbacks = [
            'Bài làm tốt, trình bày rõ ràng.',
            'Cần cố gắng thêm ở phần lý thuyết.',
            'Sai một số lỗi nhỏ, xem lại đáp án nhé.',
            'Xuất sắc! Tiếp tục phát huy.',
            'Bài làm còn sơ sài, cần bổ sung luận điểm.',
            'Ý tưởng tốt nhưng trình bày chưa mạch lạc.',
            'Kết quả đúng nhưng thiếu bước giải trung gian.',
        ]

        for assignment in assignments:
            sk = _subject_key(assignment.class_obj)
            content = SUBJECT_CONTENT[sk]
            enrolled_students = assignment.class_obj.students.all()

            for student in enrolled_students:
                if random.random() > 0.3:
                    if assignment.due_date < now:
                        grade    = round(random.uniform(5.0, 10.0), 1)
                        feedback = random.choice(feedbacks)
                        status   = 'graded'
                        submit_time = assignment.due_date - timedelta(days=random.randint(1, 3))
                    else:
                        grade    = None
                        feedback = ''
                        status   = 'pending'
                        submit_time = now - timedelta(hours=random.randint(1, 10))

                    sub_file = SimpleUploadedFile(
                        f"{content['sub_prefix']}_{student.student_id}.{content['sub_ext']}",
                        b"submission_content",
                        content_type=content['sub_mime'],
                    )
                    Submission.objects.get_or_create(
                        assignment=assignment, student=student,
                        defaults={
                            'status': status,
                            'file': sub_file,
                            'note': random.choice(content['notes']),
                            'submitted_at': submit_time,
                            'grade': grade,
                            'feedback': feedback,
                        },
                    )

        att_statuses = ['present', 'present', 'present', 'present', 'excused', 'absent']
        att_comments = ['Học sinh ngoan.', 'Hay nói chuyện riêng.', 'Làm bài nhanh.', 'Hơi trầm.', 'Tiến bộ nhiều.', '']

        for cls in classes:
            for day_offset in range(10):
                att_date = (now - timedelta(days=day_offset)).date()
                if att_date.weekday() in [0, 2, 4]:
                    for student in cls.students.all():
                        status = random.choice(att_statuses)
                        Attendance.objects.get_or_create(
                            student=student, class_obj=cls, date=att_date,
                            defaults={'status': status},
                        )
                        if random.random() > 0.7:
                            DailyComment.objects.get_or_create(
                                student=student, class_obj=cls, comment_date=att_date,
                                defaults={'comment_text': random.choice(att_comments), 'created_by': cls.teacher},
                            )

        self.stdout.write(self.style.SUCCESS('Successfully seeded diverse demo data.'))
