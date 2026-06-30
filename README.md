# EduManager — Ứng dụng Quản lý Lớp Học Thêm

> [!IMPORTANT]
> **🌐 WEBSITE DEMO:** [https://classroom-management-system-qlwq.onrender.com]

## 1. Công nghệ sử dụng

- **Front-end:** HTML5, CSS3 thuần (áp dụng Responsive Design cho web/mobile), JavaScript cơ bản. Giao diện UI/UX được tinh chỉnh theo tiêu chuẩn hiện đại, đảm bảo tính nhất quán.
- **Back-end:** Python Django (Sử dụng Class-based Views & Django Forms). Có hệ thống Authentication & Authorization phân quyền rõ ràng (Admin/Teacher vs Student).
- **Cơ sở dữ liệu:** PostgreSQL (Lưu trữ an toàn, sử dụng Django ORM hiệu quả với các quy tắc Cascade Delete và Set Null).
- **Triển khai (Deployment):** Render (Web Server) và Supabase (Database).

---

## 2. Hướng dẫn cài đặt & chạy dự án

Dự án hỗ trợ môi trường chạy cục bộ với Docker để dễ dàng khởi tạo Database.

### Yêu cầu hệ thống

- Python 3.10+
- Docker Desktop (Để chạy DB PostgreSQL)
- Git

### Các bước cài đặt

```bash
# 1. Clone repository về máy
git clone <url-repository>
cd Classroom-Management-System

# 2. Thiết lập file môi trường (.env) từ file mẫu
cp .env.example .env            # Windows (Cmd): copy .env.example .env

# 3. Khởi động PostgreSQL qua Docker
docker compose up -d

# 4. Tạo môi trường ảo và cài đặt thư viện
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 5. Khởi tạo cơ sở dữ liệu
python manage.py migrate

# 6. Khởi tạo dữ liệu mẫu (Tạo sẵn Giáo viên, Học sinh, Lớp học)
python manage.py seed_demo

# 7. Tạo tài khoản Superuser (Để đăng nhập trang quản trị - Tùy chọn)
python manage.py createsuperuser

# 8. Chạy server phát triển
python manage.py runserver

```

### Tài khoản Demo có sẵn

**Giáo viên (Admin):**
| Tên đăng nhập | Mật khẩu | Lớp phụ trách |
| ------------- | ----------------- | ------------------------------------ |
| `TeacherToan` | `TeacherToan@123` | Toán 9A, Toán 9B (Nâng cao), Toán 10 |
| `TeacherVan` | `TeacherVan@123` | Ngữ Văn 9, Ngữ Văn 10 |
| `TeacherAnh` | `TeacherAnh@123` | Tiếng Anh IELTS, Tiếng Anh Giao Tiếp |

**Học sinh (User):**
Tên đăng nhập từ `Student01` đến `Student20`. Mật khẩu tương ứng: `Student01@123`, `Student02@123`...

---

## 3. Tài liệu Django Models (Database Schema)

Hệ thống được thiết kế với **9 Models** chặt chẽ, tối ưu cho nghiệp vụ giáo dục bổ trợ:

1. **`UserProfile`**: Mở rộng thông tin từ bảng `User` mặc định của Django. Chứa `role` (teacher/student), `phone`, `contact_phone` (số điện thoại liên hệ khẩn cấp), `date_of_birth`, `address`.
2. **`Student`**: Hồ sơ học sinh định danh bằng `student_id` (VD: HS001). Liên kết N-N với lớp học thông qua bảng trung gian (Django tự tạo).
3. **`Class`**: Quản lý lớp học (`name`, `room`). Chứa ForeignKey `teacher` trỏ tới User (Quy tắc `on_delete=models.SET_NULL` để bảo toàn lớp học khi giáo viên nghỉ việc).
4. **`Schedule`**: Lưu trữ thời khóa biểu cố định. Bắt buộc có cơ chế kiểm tra **không trùng giờ/phòng/giáo viên/học sinh**.
5. **`Assignment`**: Bài tập về nhà (`title`, `description`, `due_date`, `file` đính kèm hỗ trợ pdf, doc, docx, png, jpg < 10MB).
6. **`Submission`**: Lưu bài làm của học sinh (`file` đính kèm hỗ trợ pdf, doc, docx, png, jpg < 10MB). Xóa học sinh sẽ xóa luôn bài nộp (`on_delete=models.CASCADE`). Chứa điểm `grade` (float 0.0-10.0) và lời phê `feedback`.
7. **`Attendance`**: Bảng dữ liệu điểm danh chuyên cần (`status`: present/absent/excused) theo từng ngày.

8. **`DailyComment`**: Nhận xét thái độ, kết quả học tập hàng ngày của giáo viên dành riêng cho mỗi học sinh.
9. **`PasswordResetOTP`**: Quản lý vòng đời mã OTP 6 số để lấy lại mật khẩu an toàn (Hết hạn sau 5 phút).

---

## 4. Hướng dẫn sử dụng Website

### Phân hệ Giáo viên (Admin)

- **Quản lý lớp học & Lịch học:** Tạo lớp học mới. Xếp học sinh từ danh sách trung tâm vào lớp bằng tính năng **Tìm kiếm nâng cao**. Đặt thời khóa biểu cố định cho lớp.
- **Quản lý học sinh:** Quản trị danh sách học sinh. Giáo viên có thể **Thêm học sinh mới** (Hệ thống tự cấp mã HS và mật khẩu mặc định). _Lưu ý: Để đảm bảo bảo mật và minh bạch, tính năng Sửa/Xóa học sinh toàn cục bị khóa, giáo viên chỉ được phép "Xóa học sinh khỏi lớp học" của mình._
- **Điểm danh & Nhận xét:** Truy cập mục Điểm danh, chọn ngày hiện tại để đánh dấu chuyên cần (Đi học / Vắng). Kết hợp gửi luôn lời nhận xét ngắn gọn về thái độ buổi học đó.
- **Giao bài & Chấm bài:** Đăng bài tập kèm tài liệu (giới hạn thời gian nộp). Mở bài nộp của học sinh để chấm điểm hệ số thập phân và ghi phản hồi.

### Phân hệ Học sinh (User)

- **Đăng ký & Đăng nhập:** Học sinh có thể tự đăng ký tài khoản qua form `Register`. Nếu quên mật khẩu, có thể yêu cầu gửi mã OTP về Email để khôi phục.
- **Trang chủ (Dashboard):** Tra cứu ngay lập tức các bài tập về nhà sắp đến hạn và các thống kê chuyên cần.
- **Xem Lịch học:** Theo dõi thời khóa biểu cố định hàng tuần (Thứ, Ca học, Phòng học).
- **Kiểm tra Điểm danh:** Tra cứu lại tỷ lệ đi học và timeline nhận xét chi tiết của thầy cô.
- **Nộp bài tập:** Tải đề bài về. Nộp bài làm dưới dạng văn bản hoặc ảnh trước khi hết thời gian `due_date`. Hệ thống tự động khóa tính năng nộp bài nếu quá hạn.
- **Xem Điểm số:** Theo dõi điểm số và đọc lời phê chi tiết sau khi giáo viên hoàn tất việc chấm bài.
