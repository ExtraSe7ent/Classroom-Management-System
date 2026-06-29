# EduManager — Ứng dụng Quản lý Lớp Học Thêm

<div align="center">

**Dự án cuối kỳ · CSE3045 — Học theo dự án khoa học và kỹ thuật**  
Khoa Công nghệ và Kỹ thuật tiên tiến · Trường Đại học Việt Nhật, ĐHQGHN

| Thành viên       | Vai trò                             |
| ---------------- | ----------------------------------- |
| Nguyễn Quang Anh | Backend (Views, Forms, Auth, OTP)   |
| Bùi Sỹ Việt Anh  | Frontend (Templates, CSS, JS)       |
| Bùi Xuân Vinh    | Database (Models, Migrations, Seed) |
| Đỗ Xuân Hậu      | BA / Tester (Use Cases, Tài liệu)   |

</div>

---

## Mục lục

1. [Tổng quan hệ thống](#1-tổng-quan-hệ-thống)
2. [Công nghệ sử dụng](#2-công-nghệ-sử-dụng)
3. [Cài đặt & chạy dự án](#3-cài-đặt--chạy-dự-án)
4. [Tài khoản demo](#4-tài-khoản-demo)
5. [Cấu trúc thư mục](#5-cấu-trúc-thư-mục)
6. [Thiết kế cơ sở dữ liệu](#6-thiết-kế-cơ-sở-dữ-liệu)
7. [Bản đồ Use Case (UC01–UC12)](#7-bản-đồ-use-case-uc01uc12)
8. [Yêu cầu kỹ thuật & cách đáp ứng](#8-yêu-cầu-kỹ-thuật--cách-đáp-ứng)
9. [Chức năng nổi bật](#9-chức-năng-nổi-bật)
10. [Lệnh hữu ích](#10-lệnh-hữu-ích)

---

## 1. Tổng quan hệ thống

EduManager là hệ thống web quản lý trung tâm học thêm, phục vụ hai nhóm người dùng:

- **Giáo viên (Teacher):** quản lý lớp, học sinh, lịch học, điểm danh, nhận xét, giao và chấm bài tập.
- **Học sinh (Student):** xem lịch học, theo dõi điểm danh, nộp bài tập, xem điểm số và nhận xét.

```
Học sinh tự đăng ký → Đăng nhập → Xem lịch / Nộp bài / Theo dõi điểm
Giáo viên đăng nhập → Quản lý lớp & học sinh → Điểm danh / Giao bài / Chấm điểm
```

---

## 2. Công nghệ sử dụng

| Tầng          | Công nghệ               | Chi tiết                                                             |
| ------------- | ----------------------- | -------------------------------------------------------------------- |
| **Frontend**  | HTML5, CSS3, JavaScript | Thuần — không dùng Bootstrap/Tailwind                                |
|               | Django Template Engine  | `{% extends %}`, `{% include %}`, `{% block %}`                      |
|               | Responsive Design       | CSS Flexbox + Grid, media query tại 768px                            |
| **Backend**   | Python 3.10+            | —                                                                    |
|               | Django 6                | Class-based Views, Auth, Forms, ORM, Sessions                        |
|               | Xác thực & phân quyền   | `is_staff` flag, `LoginRequiredMixin`                                |
|               | OTP Email               | `django.core.mail` + `PasswordResetOTP` model                        |
| **Database**  | PostgreSQL 16           | Chạy trong Docker Compose                                            |
|               | Django ORM              | `select_related`, `prefetch_related`, `annotate`, `update_or_create` |
| **Dev tools** | Docker Compose          | Khởi động DB bằng 1 lệnh                                             |
|               | python-dotenv           | Tách cấu hình nhạy cảm ra file `.env`                                |

---

## 3. Cài đặt & chạy dự án

### Yêu cầu

- Python 3.10 trở lên
- Docker Desktop (để chạy PostgreSQL)

### Các bước

```bash
# 1. Clone repository về máy
git clone <url-repository>
cd EduManager

# 2. Khởi động PostgreSQL bằng Docker
docker compose up -d

# 3. Tạo môi trường ảo Python và cài thư viện
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 4. Áp dụng migration (tạo bảng trong DB)
python manage.py migrate

# 5. Tạo dữ liệu mẫu và tài khoản demo
python manage.py seed_demo

# 6. Khởi động server
python manage.py runserver
```

Mở trình duyệt: **http://127.0.0.1:8000/**

### Cấu hình tùy chọn (file `.env`)

Tạo file `.env` trong thư mục `EduManager/` nếu muốn tùy chỉnh:

```env
# Database (mặc định khớp với docker-compose.yml)
DB_NAME=edumanager_db
DB_USER=edumanager
DB_PASSWORD=edumanager_pass
DB_HOST=localhost
DB_PORT=5432

# Email — để trống để dùng console backend (OTP in ra terminal)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=your_gmail@gmail.com
EMAIL_HOST_PASSWORD=your_app_password   # Google App Password
```

> **Mặc định khi không có `.env`:** OTP được in thẳng ra terminal — demo được ngay, không cần cấu hình email.

---

## 4. Tài khoản demo

Sau khi chạy `python manage.py seed_demo`, hệ thống tạo sẵn:

### Giáo viên (3 tài khoản)

| Tên đăng nhập | Mật khẩu          | Lớp phụ trách                        |
| ------------- | ----------------- | ------------------------------------ |
| `TeacherToan` | `TeacherToan@123` | Toán 9A, 9B (Nâng cao), 10 (Chuyên)  |
| `TeacherVan`  | `TeacherVan@123`  | Ngữ Văn 9, Ngữ Văn 10                |
| `TeacherAnh`  | `TeacherAnh@123`  | Tiếng Anh IELTS, Tiếng Anh Giao Tiếp |

### Học sinh (20 tài khoản)

| Tên đăng nhập | Mật khẩu        |
| ------------- | --------------- |
| `Student01`   | `Student01@123` |
| `Student02`   | `Student02@123` |
| …             | …               |
| `Student20`   | `Student20@123` |

> Ngoài ra, học sinh có thể **tự tạo tài khoản** tại trang `/register/`.

---

## 5. Cấu trúc thư mục

```
EduManager/
│
├── manage.py
├── docker-compose.yml          # [DB] PostgreSQL container
├── requirements.txt
├── .env                        # Cấu hình môi trường — KHÔNG commit
│
├── config/                     # Cấu hình Django project
│   ├── settings.py             # [BE] Cài đặt toàn cục (DB, email, session, OTP)
│   ├── urls.py                 # [BE] URL gốc — nối vào core.urls
│   ├── wsgi.py                 # Entry point production
│   └── asgi.py
│
├── core/                       # App chính — toàn bộ logic nghiệp vụ
│   ├── models.py               # [DB] 9 model → 9 bảng PostgreSQL
│   ├── views.py                # [BE] 19 Class-based Views
│   ├── forms.py                # [BE] 10 Form + 3 hàm validator
│   ├── urls.py                 # [BE] 19 URL patterns
│   ├── admin.py                # [BE] Đăng ký model vào Django Admin
│   ├── apps.py
│   ├── migrations/             # [DB] Lịch sử thay đổi schema
│   └── management/
│       └── commands/
│           └── seed_demo.py    # Tạo 3 giáo viên, 20 học sinh, 7 lớp, bài tập mẫu
│
├── templates/                  # [FE] Giao diện HTML
│   ├── base.html               # Layout chung (sidebar, topbar, toast, modal)
│   ├── auth/
│   │   ├── login.html          # Đăng nhập + Quên mật khẩu OTP
│   │   └── register.html       # Tạo tài khoản học sinh mới
│   ├── teacher/                # 8 trang dành cho Giáo viên
│   │   ├── dashboard.html
│   │   ├── class_list.html
│   │   ├── class_detail.html
│   │   ├── schedule.html
│   │   ├── student_list.html
│   │   ├── attendance.html
│   │   ├── assignment_list.html
│   │   └── grading.html
│   ├── student/                # 5 trang dành cho Học sinh
│   │   ├── dashboard.html
│   │   ├── schedule.html
│   │   ├── attendance.html
│   │   ├── assignment_list.html
│   │   └── assignment_detail.html
│   └── components/             # Partial templates dùng chung
│       ├── _sidebar.html
│       ├── _profile.html
│       ├── _toast.html
│       └── _modal_confirm.html
│
└── static/                     # [FE] CSS và JavaScript
    ├── css/
    │   ├── base.css            # CSS variables, reset, typography, utilities
    │   ├── layout.css          # App shell: sidebar, topbar, responsive
    │   └── components.css      # Button, card, table, form, modal, toast, badge
    └── js/
        └── utils.js            # showToast, openModal, togglePassword, validateFile, getCookie
```

**Phân tách FE / BE / DB:**

| Tầng         | Thư mục / File                                                               |
| ------------ | ---------------------------------------------------------------------------- |
| **Frontend** | `templates/` + `static/`                                                     |
| **Backend**  | `core/views.py`, `core/forms.py`, `core/urls.py`, `core/admin.py`, `config/` |
| **Database** | `core/models.py`, `core/migrations/`, `docker-compose.yml`                   |

---

## 6. Thiết kế cơ sở dữ liệu

Hệ thống gồm **9 model Django** ánh xạ thành 9 bảng PostgreSQL:

| Model              | Bảng DB                 | Mô tả                                                 | Ràng buộc nghiệp vụ                                          |
| ------------------ | ----------------------- | ----------------------------------------------------- | ------------------------------------------------------------ |
| `UserProfile`      | `core_userprofile`      | Mở rộng User Django: SĐT, địa chỉ, ngày sinh, vai trò | `role` ∈ {teacher, student}                                  |
| `Student`          | `core_student`          | Hồ sơ học sinh, mã HS, danh sách lớp (M2M)            | Xóa Student → cascade xóa dữ liệu liên đới                   |
| `Class`            | `core_class`            | Lớp học, giáo viên phụ trách, phòng mặc định          | Teacher xóa → `teacher = NULL` (SET_NULL)                    |
| `Schedule`         | `core_schedule`         | Lịch học cố định theo thứ                             | `unique_together`: lớp + thứ + giờ bắt đầu; chặn trùng phòng |
| `Assignment`       | `core_assignment`       | Bài tập: tiêu đề, mô tả, file đính kèm, hạn nộp       | `due_date` phải > thời điểm tạo                              |
| `Submission`       | `core_submission`       | Bài nộp của học sinh                                  | `unique_together`: bài tập + học sinh; điểm 0.0–10.0         |
| `Attendance`       | `core_attendance`       | Điểm danh: present / excused / absent                 | DB index trên `(student, date)`                              |
| `DailyComment`     | `core_dailycomment`     | Nhận xét hàng ngày từ giáo viên                       | `upsert` — ghi đè nếu đã có nhận xét cùng ngày               |
| `PasswordResetOTP` | `core_passwordresetotp` | Mã OTP khôi phục mật khẩu                             | Hết hạn 5 phút; dùng 1 lần (`is_used`)                       |

### Quan hệ giữa các bảng

```
User (Django built-in)
 ├── UserProfile  (OneToOne)
 ├── Student      (OneToOne)  ←── M2M ──→  Class
 ├── Class        (FK: teacher)
 ├── Assignment   (FK: created_by)
 └── DailyComment (FK: created_by)

Class
 ├── Schedule     (FK: class_obj)
 ├── Assignment   (FK: class_obj)
 ├── Attendance   (FK: class_obj)
 └── DailyComment (FK: class_obj)

Student
 ├── Submission   (FK: student)
 ├── Attendance   (FK: student)
 └── DailyComment (FK: student)
```

---

## 7. Bản đồ Use Case (UC01–UC12)

| UC    | Tên chức năng            | Actor     | View (Class)                                               | URL                                                        |
| ----- | ------------------------ | --------- | ---------------------------------------------------------- | ---------------------------------------------------------- |
| UC01  | Đăng nhập / Đăng xuất    | Chung     | `LoginView`, `LogoutView`                                  | `/` · `/logout/`                                           |
| UC01C | Quên mật khẩu qua OTP    | Chung     | `SendOTPView`, `ResetPasswordView`                         | `/forgot-password/send-otp/` · `/forgot-password/reset/`   |
| —     | Tạo tài khoản học sinh   | Học sinh  | `RegisterView`                                             | `/register/`                                               |
| UC02  | Xem / Cập nhật hồ sơ     | Chung     | `ProfileView`                                              | `/profile/`                                                |
| UC03  | Quản lý học sinh         | Giáo viên | `StudentListView`                                          | `/students/`                                               |
| UC04  | Quản lý lớp học          | Giáo viên | `ClassListView`, `ClassDetailView`, `ScheduleView`         | `/classes/` · `/classes/<pk>/` · `/classes/<pk>/schedule/` |
| UC05  | Điểm danh học viên       | Giáo viên | `AttendanceView`                                           | `/attendance/`                                             |
| UC06  | Nhập nhận xét hàng ngày  | Giáo viên | `AttendanceView` → `DailyComment`                          | `/attendance/`                                             |
| UC07  | Giao bài tập về nhà      | Giáo viên | `AssignmentListView`                                       | `/assignments/`                                            |
| UC08  | Chấm điểm bài tập        | Giáo viên | `GradingView`                                              | `/assignments/<pk>/grading/`                               |
| UC09  | Xem lịch học             | Học sinh  | `StudentScheduleView`                                      | `/my-schedule/`                                            |
| UC10  | Xem điểm danh & nhận xét | Học sinh  | `StudentAttendanceView`                                    | `/my-attendance/`                                          |
| UC11  | Xem và nộp bài tập       | Học sinh  | `StudentAssignmentListView`, `StudentAssignmentDetailView` | `/my-assignments/` · `/my-assignments/<pk>/`               |
| UC12  | Xem điểm số              | Học sinh  | `StudentAssignmentListView` (tab Đã có điểm)               | `/my-assignments/`                                         |

---

## 8. Yêu cầu kỹ thuật & cách đáp ứng

### Frontend

| Yêu cầu                | Cách thực hiện                                                                    |
| ---------------------- | --------------------------------------------------------------------------------- |
| HTML5                  | Toàn bộ template dùng HTML5 semantic (`<header>`, `<main>`, `<nav>`)              |
| CSS3                   | CSS Variables (`:root`), Flexbox, Grid, `@keyframes` (toast animation)            |
| JavaScript             | Vanilla JS — AJAX `fetch()`, DOM manipulation, form validation client-side        |
| Django Template Engine | `{% extends %}`, `{% block %}`, `{% include %}`, `{% url %}`, `{% load static %}` |
| Responsive design      | `@media (max-width: 768px)` — sidebar ẩn, layout 1 cột trên mobile                |

### Backend

| Yêu cầu                | Cách thực hiện                                                                                                                |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Xác thực & phân quyền  | `LoginRequiredMixin`, `is_staff` flag phân biệt Giáo viên / Học sinh, `update_session_auth_hash` giữ session sau đổi mật khẩu |
| Class-based Views      | 19 CBV trong `core/views.py` — tất cả kế thừa `View` hoặc `LoginRequiredMixin + View`                                         |
| Django Forms           | 10 Form (7 `ModelForm` + 3 `Form`) với `clean()` và `clean_<field>()` validation                                              |
| Xử lý lỗi & validation | Server-side trong Forms, client-side trong JS; HTTP 400/404 cho AJAX errors                                                   |
| OTP Email              | `PasswordResetOTP` model + `send_mail()`; mã 6 số, hết hạn 5 phút, dùng 1 lần                                                 |

### Database

| Yêu cầu                | Cách thực hiện                                                                                    |
| ---------------------- | ------------------------------------------------------------------------------------------------- |
| PostgreSQL             | `django.db.backends.postgresql` + psycopg3 binary                                                 |
| Thiết kế models hợp lý | 9 model, quan hệ FK/M2M rõ ràng, `on_delete` phù hợp, `unique_together` chặn dữ liệu trùng        |
| Django ORM             | `select_related`, `prefetch_related`, `annotate(Count(...))`, `update_or_create`, `get_or_create` |

---

## 9. Chức năng nổi bật

### Đăng nhập & phân quyền

- Sau đăng nhập, hệ thống tự động chuyển hướng: Giáo viên → `/teacher-dashboard/`, Học sinh → `/student-dashboard/`.
- Session tồn tại 24 giờ (`SESSION_COOKIE_AGE = 86400`).
- Đổi mật khẩu không làm mất session (dùng `update_session_auth_hash`).

### Quên mật khẩu qua OTP

1. Nhập số điện thoại đã đăng ký → hệ thống gửi mã OTP 6 số tới **email** gắn với SĐT.
2. Nhập OTP + mật khẩu mới → cập nhật ngay lập tức.
3. **Môi trường dev:** OTP in ra terminal (không cần cấu hình SMTP).
4. **Môi trường production:** điền thông tin SMTP Gmail vào `.env`.

### Kiểm tra lịch phòng học

- `ScheduleView` kiểm tra xung đột phòng trước khi lưu: cùng phòng + cùng thứ + trùng khung giờ → báo lỗi cụ thể.

### Upload & chấm bài tập

- Giáo viên giao bài kèm file đề (PDF/Word/ảnh, tối đa 10MB).
- Học sinh nộp file bài làm; hệ thống khóa nút nộp khi quá hạn.
- Giáo viên chấm điểm (0.0–10.0) + ghi nhận xét → học sinh xem kết quả ngay.

### Điểm danh & nhận xét

- Điểm danh 3 trạng thái: **Có mặt / Vắng phép / Vắng không phép**.
- Nhận xét hàng ngày được lưu riêng và hiển thị theo timeline trên trang học sinh.

---

</div>
