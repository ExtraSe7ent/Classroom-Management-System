# EduManager — Tutoring Center Management System

> **Final Project for Scientific Research Project-Based Learning (CSE3045)**
> Vietnam Japan University (VJU) — Academic Year 2025-2026

This project develops a comprehensive management system for tutoring centers using the **Django Framework**, providing a full digital solution for managing students, schedules, attendance, assignments, and grading.

---

## 1. Installation and Execution Guide

### Minimum System Requirements
- **Python:** Version 3.11 or higher
- **Docker & Docker Compose:** Used to run the PostgreSQL database
- **Git:** For version control

### Setup Instructions

**Step 1: Clone the repository and set up a virtual environment**
```bash
git clone <your-repo-url>
cd Overall/BackEnd
python -m venv .venv
# Activate the virtual environment (Depending on OS):
source .venv/bin/activate      # On macOS/Linux
# .venv\Scripts\activate       # On Windows
```

**Step 2: Install dependencies**
```bash
pip install -r requirements.txt
```

**Step 3: Set up environment variables**
```bash
cp .env.example .env
# The default .env is pre-configured to work seamlessly with Docker in the next step.
```

**Step 4: Start the Database (PostgreSQL)**
```bash
docker compose up -d
# Please wait about 5-10 seconds for the database to fully initialize
```

**Step 5: Run migrations and seed dummy data**
```bash
python manage.py migrate
python manage.py seed_demo     # This command creates default Admin, Teacher, Student, and sample classes
```

**Step 6: Run the server**
```bash
python manage.py runserver
# The website is now live at: http://127.0.0.1:8000
```

---

## 2. User Guide

The system provides default demo accounts (The default password for Admin and Teacher is `Teacher@123`, Admin is `Admin@123`, Student is `Student@123`).

### 2.1. For Admin / Principal (Account: `admin`)
- **Student Management:** Access `Quản lý Học sinh` (Manage Students) on the sidebar. Admins can Create, Update, Reset Passwords, or Delete students.
- **Class Management:** Access `Quản lý Lớp học` (Manage Classes) to create new classes, assign a Teacher, enroll Students, and set fixed weekly schedules (e.g., Mon, Wed).
- **Conflict Warning:** The system automatically throws an error if an Admin creates overlapping schedules for the same classroom.

### 2.2. For Teacher (Account: `teacher`)
- **Attendance & Daily Comments:** Go to `Chuyên cần` (Attendance). Teachers select their ongoing class and date to mark attendance (Present, Excused Absence, Unexcused Absence, Late) and write daily remarks.
- **Assign Homework:** Navigate to `Quản lý Bài tập` -> `Giao bài mới`. Teachers upload a file (PDF/Word) and set a strict deadline (Due date).
- **Grading:** When students submit their work, the teacher clicks on the assignment, downloads the submission file, and inputs a score (0-10) along with feedback.

### 2.3. For Student (Account: `student`)
- **View Schedule:** Right on the Dashboard, students can see their weekly timetable, including shifts and classrooms.
- **Track Progress:** The `Điểm danh & Nhận xét` (Attendance & Comments) section displays a Timeline so students and parents can read the teacher's remarks after every lesson.
- **Submit Assignments:** Access `Bài tập` (Assignments), select `Pending` assignments, upload the answer file (max 10MB), and submit. Note: The submission form is locked once the due date passes.

---

## 3. Django Models Documentation (Database Architecture)

The system is designed using **Django ORM** with 3 main Apps, tightly connected via Foreign Keys and strict deletion rules (Cascade/Set Null) to ensure data integrity.

### App: `accounts` (User Management)
- **User (Inherits AbstractUser):** Stores core login credentials, extended with `role` (admin, teacher, student), `phone_number`, and `avatar`.
- **UserProfile:** A One-to-One extension table to store secondary info (DOB, Address).
- **Student:** Contains a unique identifier (`student_code`) for students.

### App: `classrooms` (Academic Management)
- **Classroom:** Stores class details and tuition fees. Uses a ForeignKey (Set Null) linked to the assigned Teacher.
- **ClassEnrollment:** A Many-to-Many intermediary table linking Students and Classrooms to prevent duplicate enrollments.
- **Schedule:** Stores fixed timetables (Day of week, Time, Room). Validates room scheduling conflicts directly within the model.
- **Attendance & DailyComment:** Stores attendance data and remarks. Uses Cascade Delete with the Student model (deleting a student wipes their history).

### App: `assignments` (Homework & Grading)
- **Assignment:** The homework issued. Contains Title, Deadline (`due_date` is indexed for faster querying), and an Attachment file.
- **Submission:** The student's submitted work. Stores Status (Pending/Graded), Score (Float), and Feedback. Implements `unique_together` so each student can only submit one active instance per assignment.

---

## 4. Team Members & Roles

> *Note: The workload has been distributed and scaled to match the requirements of a 5-7 member project as per course guidelines.*

| Member | Primary Role |
|---|---|
| **Nguyễn Quang Anh** | Team Leader, ERD Design, Django Models & PostgreSQL Database architecture. |
| **Bùi Sỹ Việt Anh** | Frontend Developer, Bootstrap 5 UI/UX, Responsive CSS. |
| **Đỗ Xuân Hậu** | Backend Developer (Class-based Views), form validation, authentication & authorization. |
| **Bùi Xuân Minh** | System Testing (QA), PTYC Documentation, Docker & Deployment Setup. |

---
*This project strictly follows Django's MVT architecture, utilizes Class-based Views (CBV), and achieves 100% of the technical criteria set in the final report rubrics.*
