# app.py
from flask import Flask, render_template, redirect, url_for
import datetime

app = Flask(__name__)

# --- Dữ liệu mẫu ---
# Thông tin người dùng sinh viên (Student user info)
student_user_info = {
    "name": "Văn A", # Student Name
    "major": "Công nghệ thông tin" # Information Technology
}

# Thông tin người dùng giảng viên (Faculty user info)
faculty_user_info = {
    "name": "Thị B", # Faculty Name
    "department": "Khoa Công nghệ Thông tin" # IT Department
}

# Danh sách môn học của sinh viên (Student's courses)
student_courses_sample = [
    {"id": "CS101", "name": "Nhập môn Lập trình", "schedule": "Thứ 2, Tiết 1-3"},
    {"id": "MA101", "name": "Toán cao cấp A1", "schedule": "Thứ 3, Tiết 4-6"},
    {"id": "EN101", "name": "Tiếng Anh học thuật 1", "schedule": "Thứ 4, Tiết 1-3"},
]

# Danh sách môn học giảng viên phụ trách (Faculty's courses)
faculty_courses_sample = [
    {"id": "CS101", "name": "Nhập môn Lập trình", "credits": 3, "student_count": 120},
    {"id": "CS305", "name": "Phát triển Web Nâng cao", "credits": 3, "student_count": 45},
    {"id": "AI202", "name": "Nhập môn Trí tuệ Nhân tạo", "credits": 4, "student_count": 70},
]

# Lịch dạy mẫu của giảng viên (Faculty's sample teaching schedule)
teaching_schedule_sample = [
    {"course_name": "Nhập môn Lập trình", "date": "Thứ 2, 13/05/2025", "time": "07:30 - 09:30", "room": "B201"},
    {"course_name": "Phát triển Web Nâng cao", "date": "Thứ 3, 14/05/2025", "time": "13:30 - 15:30", "room": "C105"},
]


# Sự kiện lịch của sinh viên (Student's calendar events)
today = datetime.date.today()
student_calendar_events_sample = [
    {
        "id": "event1", "course_id": "CS101", "title": "Nhập môn Lập trình",
        "date": today.strftime("%Y-%m-%d"), "start_time": "07:30", "end_time": "09:30",
        "lecturer_materials_url": "#", "notes_link": url_for('student_notes', course_id='CS101', _external=True) if 'student_notes' in app.url_map._rules_by_endpoint else '#'
    },
    {
        "id": "event2", "course_id": "MA101", "title": "Toán cao cấp A1",
        "date": (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d"), "start_time": "09:45", "end_time": "11:45",
        "lecturer_materials_url": "#", "notes_link": url_for('student_notes', course_id='MA101', _external=True) if 'student_notes' in app.url_map._rules_by_endpoint else '#'
    },
]

# --- Routes ---

@app.route('/')
def show_login_page():
    """
    Hiển thị trang đăng nhập chính.
    Displays the main login page.
    """
    current_year = datetime.datetime.now().year
    return render_template('login.html', current_year=current_year)

@app.route('/student/dashboard')
def student_dashboard():
    """
    Hiển thị trang tổng quan của sinh viên.
    Displays the student dashboard.
    """
    upcoming_reviews = [
        {"subject": "Nhập môn Lập trình", "topic": "Biến và kiểu dữ liệu", "due_date": "Ngày mai"},
        {"subject": "Toán cao cấp A1", "topic": "Giới hạn hàm số", "due_date": "Trong 2 ngày"},
    ]
    upcoming_events = sorted(
        [event for event in student_calendar_events_sample if datetime.datetime.strptime(event['date'], '%Y-%m-%d').date() >= today],
        key=lambda x: x['date']
    )[:3]

    return render_template(
        'index.html', # This is the student's dashboard
        user=student_user_info,
        courses=student_courses_sample,
        reviews=upcoming_reviews,
        calendar_events=student_calendar_events_sample,
        upcoming_events_dashboard=upcoming_events
    )

@app.route('/student/notes/<course_id>')
def student_notes(course_id):
    """
    Hiển thị trang ghi chú cho một môn học cụ thể của sinh viên.
    Displays the notes page for a specific student course.
    """
    course = next((c for c in student_courses_sample if c["id"] == course_id), None)
    if not course:
        return "Không tìm thấy môn học", 404
    return render_template('notes_template.html', course=course, user=student_user_info)

@app.route('/student/materials/<course_id>/<event_date>')
def get_student_materials(course_id, event_date):
    """
    Giả lập việc lấy tài liệu cho một buổi học cụ thể của sinh viên.
    Simulates fetching materials for a specific student class session.
    """
    course = next((c for c in student_courses_sample if c["id"] == course_id), None)
    if not course:
        return {"error": "Course not found"}, 404
    
    materials = [
        f"Slide bài giảng {course['name']} - Buổi {event_date}.pdf",
        f"Bài tập về nhà {event_date}.docx",
    ]
    return {"course_name": course['name'], "event_date": event_date, "materials": materials}


@app.route('/faculty/dashboard')
def faculty_dashboard():
    """
    Hiển thị trang tổng quan của giảng viên.
    Displays the faculty dashboard.
    """
    return render_template(
        'faculty_dashboard.html',
        faculty_user=faculty_user_info,
        faculty_courses=faculty_courses_sample,
        teaching_schedule=teaching_schedule_sample
        )

# --- Chạy ứng dụng ---
if __name__ == '__main__':
    app.run(debug=True)