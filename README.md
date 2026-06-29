# EduManager — Ứng dụng Quản lý Lớp Học Thêm

Đồ án cuối kỳ · CSE3045 — Học theo dự án khoa học và kỹ thuật  
Khoa Công nghệ và Kỹ thuật tiên tiến · Trường Đại học Việt Nhật, ĐHQGHN

---

## 1. Hướng dẫn cài đặt & chạy dự án

### Yêu cầu

- Python 3.10+
- Docker Desktop

### Các bước

```bash
# 1. Clone repository
git clone <url-repository>
cd EduManager

# 2. Khởi động PostgreSQL
docker compose up -d

# 3. Tạo môi trường ảo và cài thư viện
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 4. Tạo bảng dữ liệu
python manage.py migrate

# 5. Tạo dữ liệu mẫu
python manage.py seed_demo

# 6. Chạy server
python manage.py runserver
```

Truy cập: **http://127.0.0.1:8000/**

### Tài khoản demo

#### Giáo viên

| Tên đăng nhập | Mật khẩu          | Lớp phụ trách                        |
|---------------|-------------------|--------------------------------------|
| `TeacherToan` | `TeacherToan@123` | Toán 9A, Toán 9B (Nâng cao), Toán 10 |
| `TeacherVan`  | `TeacherVan@123`  | Ngữ Văn 9, Ngữ Văn 10                |
| `TeacherAnh`  | `TeacherAnh@123`  | Tiếng Anh IELTS, Tiếng Anh Giao Tiếp |

#### Học sinh

| Tên đăng nhập | Mật khẩu        |
|---------------|-----------------|
| `Student01`   | `Student01@123` |
| `Student02`   | `Student02@123` |
| …             | …               |
| `Student20`   | `Student20@123` |

---

## 2. Tài liệu Django Models

Hệ thống gồm **9 model** ánh xạ thành 9 bảng trong PostgreSQL.

### `UserProfile`
Mở rộng `User` Django — lưu thông tin bổ sung của người dùng.

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `user` | OneToOneField → User | Tài khoản Django |
| `role` | CharField | `teacher` hoặc `student` |
| `phone` | CharField | Số điện thoại (10 số, bắt đầu bằng 0) |
| `date_of_birth` | DateField | Ngày sinh |
| `address` | TextField | Địa chỉ |

### `Student`
Hồ sơ học sinh, liên kết nhiều-nhiều với lớp học.

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `user` | OneToOneField → User | Tài khoản học sinh |
| `student_id` | CharField | Mã học sinh (VD: HS001) |
| `classes` | ManyToManyField → Class | Danh sách lớp đang học |

### `Class`
Lớp học do giáo viên phụ trách.

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `name` | CharField | Tên lớp |
| `teacher` | ForeignKey → User | Giáo viên (SET_NULL khi xóa) |
| `teacher_name` | CharField | Tên hiển thị của giáo viên |
| `room` | CharField | Phòng học mặc định |
| `description` | TextField | Mô tả lớp |

### `Schedule`
Lịch học cố định theo thứ trong tuần.

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `class_obj` | ForeignKey → Class | Lớp học |
| `day_of_week` | CharField | Thứ (Monday → Sunday) |
| `start_time` | TimeField | Giờ bắt đầu |
| `end_time` | TimeField | Giờ kết thúc |
| `room` | CharField | Phòng học ca này |

> Ràng buộc: `unique_together (class_obj, day_of_week, start_time)` — không trùng lịch; view kiểm tra thêm xung đột phòng.

### `Assignment`
Bài tập do giáo viên giao cho lớp.

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `class_obj` | ForeignKey → Class | Lớp nhận bài |
| `title` | CharField | Tiêu đề (5–255 ký tự) |
| `description` | TextField | Nội dung đề bài |
| `due_date` | DateTimeField | Hạn nộp (phải > thời điểm tạo) |
| `file` | FileField | File đính kèm (PDF/Word/ảnh, tối đa 10MB) |
| `created_by` | ForeignKey → User | Giáo viên tạo bài |

### `Submission`
Bài nộp của học sinh.

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `assignment` | ForeignKey → Assignment | Bài tập |
| `student` | ForeignKey → Student | Học sinh nộp |
| `file` | FileField | File bài làm |
| `note` | TextField | Ghi chú kèm bài (tối đa 500 ký tự) |
| `status` | CharField | `pending` / `graded` / `missing` |
| `grade` | DecimalField | Điểm 0.0–10.0 |
| `feedback` | TextField | Nhận xét của giáo viên |

> Ràng buộc: `unique_together (assignment, student)` — mỗi học sinh chỉ nộp một lần.

### `Attendance`
Điểm danh chuyên cần.

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `student` | ForeignKey → Student | Học sinh |
| `class_obj` | ForeignKey → Class | Lớp học |
| `date` | DateField | Ngày điểm danh |
| `status` | CharField | `present` / `excused` / `absent` |

> Có DB index trên `(student, date)` để tăng tốc truy vấn lịch sử.

### `DailyComment`
Nhận xét hàng ngày của giáo viên dành cho từng học sinh.

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `student` | ForeignKey → Student | Học sinh được nhận xét |
| `class_obj` | ForeignKey → Class | Lớp học |
| `comment_date` | DateField | Ngày nhận xét |
| `comment_text` | TextField | Nội dung nhận xét |
| `created_by` | ForeignKey → User | Giáo viên nhận xét |

### `PasswordResetOTP`
Mã OTP dùng để khôi phục mật khẩu.

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `user` | ForeignKey → User | Tài khoản cần reset |
| `otp_code` | CharField | Mã 6 chữ số |
| `expires_at` | DateTimeField | Thời điểm hết hạn (5 phút) |
| `is_used` | BooleanField | Đã dùng chưa |

---

## 3. Hướng dẫn sử dụng

### Dành cho Giáo viên

**Đăng nhập:** Truy cập `http://127.0.0.1:8000/` → nhập tài khoản → vào trang Tổng quan.

**Quản lý lớp học** (`/classes/`)
- Tạo lớp mới: điền tên lớp, phòng, mô tả.
- Xem chi tiết lớp: thêm hoặc xóa học sinh khỏi lớp.
- Xếp lịch học: chọn thứ, giờ bắt đầu/kết thúc, phòng — hệ thống tự kiểm tra trùng phòng.

**Quản lý học sinh** (`/students/`)
- Thêm học sinh: nhập họ tên, SĐT, email → hệ thống tạo tài khoản với mật khẩu mặc định `Student@123`.
- Sửa thông tin hoặc xóa học sinh (xóa cascade toàn bộ dữ liệu liên quan).

**Điểm danh & nhận xét** (`/attendance/`)
- Chọn lớp và ngày → điểm danh từng học sinh (Có mặt / Vắng phép / Vắng không phép) → nhập nhận xét → Lưu.

**Giao bài tập** (`/assignments/`)
- Tạo bài tập: chọn lớp, tiêu đề, mô tả, hạn nộp, file đề bài.

**Chấm điểm** (`/assignments/<pk>/grading/`)
- Xem danh sách bài đã nộp → nhập điểm (0.0–10.0) và nhận xét → Lưu điểm.

---

### Dành cho Học sinh

**Đăng ký tài khoản:** Truy cập `/register/` → điền thông tin → đăng nhập tự động.

**Đăng nhập:** Truy cập `http://127.0.0.1:8000/` → nhập tài khoản → vào Trang chủ học sinh.

**Xem lịch học** (`/my-schedule/`): lịch học theo tuần của tất cả lớp đang tham gia.

**Xem điểm danh & nhận xét** (`/my-attendance/`): tỷ lệ chuyên cần và timeline nhận xét của giáo viên.

**Bài tập** (`/my-assignments/`): xem theo trạng thái Chưa nộp / Đã nộp / Đã có điểm / Quá hạn; click vào để xem đề và nộp bài trước hạn; xem điểm và nhận xét sau khi được chấm.

---

### Quên mật khẩu

1. Màn hình đăng nhập → **Quên mật khẩu**.
2. Nhập số điện thoại đã đăng ký → **Gửi mã** → nhận OTP qua email.
3. Nhập mật khẩu mới + mã OTP → **Lưu thay đổi**.

---

## 4. Lệnh hữu ích

```bash
docker compose up -d              # Bật PostgreSQL
docker compose down               # Tắt (giữ dữ liệu)
docker compose down -v            # Tắt + xóa sạch dữ liệu

python manage.py migrate          # Áp dụng migration
python manage.py seed_demo        # Tạo lại dữ liệu mẫu
python manage.py createsuperuser  # Tạo tài khoản Django Admin
python manage.py runserver        # Chạy server tại :8000
```

> Trang Django Admin: **http://127.0.0.1:8000/django-admin/**
