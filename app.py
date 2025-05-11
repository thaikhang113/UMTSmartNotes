# app.py
<<<<<<< HEAD
from flask import Flask, render_template
import datetime # Thêm thư viện datetime

app = Flask(__name__)

# Dữ liệu mẫu (sau này sẽ được thay thế bằng cơ sở dữ liệu và logic thực tế)
user_info = {
    "name": "Sinh viên UMT",
    "major": "Công nghệ thông tin"
}

courses_sample = [
=======
from flask import Flask, render_template, redirect, url_for, request, session, flash
import datetime
import random # Để tạo dữ liệu mẫu (For generating sample data)
import os # Cho secret key (For secret key)

app = Flask(__name__)
# Cần thiết cho session và flash messages
# Necessary for session and flash messages
app.secret_key = os.urandom(24) # Tạo một secret key ngẫu nhiên (Generate a random secret key)

# --- Dữ liệu Người dùng Mẫu CỐ ĐỊNH (CÓ MẬT KHẨU - CHỈ DÙNG CHO DEMO) ---
# --- FIXED Sample User Data (WITH PASSWORDS - FOR DEMO ONLY) ---
# CẢNH BÁO: Lưu trữ mật khẩu dạng văn bản thuần là một rủi ro bảo mật lớn.
# Sử dụng băm mật khẩu (ví dụ: Werkzeug's generate_password_hash) trong ứng dụng thực tế.
# WARNING: Storing plain text passwords is a major security risk.
# Use password hashing (e.g., Werkzeug's generate_password_hash) in a real application.

STUDENT_ACCOUNTS = {
    "khang.2302700102@st.umt.edu.vn": {
        "password": "123",
        "full_name": "Nguyễn Văn Khang",
        "major": "Công nghệ thông tin",
        "id_suffix": "2302700102"
    },
    "minh.2301122334@st.umt.edu.vn": {
        "password": "123",
        "full_name": "Trần Thị Minh",
        "major": "Quản trị Kinh doanh",
        "id_suffix": "2301122334"
    },
    "lan.2305566778@st.umt.edu.vn": {
        "password": "123",
        "full_name": "Lê Thị Lan",
        "major": "Ngôn ngữ Anh",
        "id_suffix": "2305566778"
    }
    # Bạn có thể thêm nhiều tài khoản sinh viên khác ở đây
    # You can add more student accounts here
}

FACULTY_ACCOUNTS = {
    "gv_khang.2302700102@st.umt.edu.vn": {
        "password": "123",
        "full_name": "Nguyễn Văn Khang (GV)",
        "department": "Khoa Công nghệ Thông tin",
        "id_suffix": "2302700102"
    },
    "gv_thanh.1234@st.umt.edu.vn": {
        "password": "123",
        "full_name": "Phạm Văn Thành (GV)",
        "department": "Khoa Kinh tế",
        "id_suffix": "1234"
    },
    "gv_huong.5678@st.umt.edu.vn": {
        "password": "123",
        "full_name": "Võ Thị Hương (GV)",
        "department": "Khoa Ngoại ngữ",
        "id_suffix": "5678"
    }
    # Bạn có thể thêm nhiều tài khoản giảng viên khác ở đây
    # You can add more faculty accounts here
}

# --- Dữ liệu Mẫu khác (Môn học, Lịch, v.v.) ---
# --- Other Sample Data (Courses, Schedule, etc.) ---
student_courses_sample = [
>>>>>>> test1
    {"id": "CS101", "name": "Nhập môn Lập trình", "schedule": "Thứ 2, Tiết 1-3"},
    {"id": "MA101", "name": "Toán cao cấp A1", "schedule": "Thứ 3, Tiết 4-6"},
    {"id": "EN101", "name": "Tiếng Anh học thuật 1", "schedule": "Thứ 4, Tiết 1-3"},
    {"id": "BM202", "name": "Quản trị Marketing", "schedule": "Thứ 5, Tiết 7-9"},
    {"id": "ECO101", "name": "Kinh tế vi mô", "schedule": "Thứ 6, Tiết 1-3"},
]

<<<<<<< HEAD
# Dữ liệu mẫu cho các sự kiện lịch
# Trong thực tế, ngày tháng cần được xử lý động
today = datetime.date.today()
calendar_events_sample = [
    {
        "id": "event1",
        "course_id": "CS101",
        "title": "Nhập môn Lập trình",
        "date": today.strftime("%Y-%m-%d"),
        "start_time": "07:30",
        "end_time": "09:30",
        "lecturer_materials_url": "#", # Placeholder
        "notes_link": "/notes/CS101" # Liên kết đến trang ghi chú chung của môn học
    },
    {
        "id": "event2",
        "course_id": "MA101",
        "title": "Toán cao cấp A1",
        "date": (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
        "start_time": "09:45",
        "end_time": "11:45",
        "lecturer_materials_url": "#",
        "notes_link": "/notes/MA101"
    },
    {
        "id": "event3",
        "course_id": "EN101",
        "title": "Tiếng Anh học thuật 1",
        "date": (today + datetime.timedelta(days=2)).strftime("%Y-%m-%d"),
        "start_time": "07:30",
        "end_time": "09:30",
        "lecturer_materials_url": "#",
        "notes_link": "/notes/EN101"
    },
     {
        "id": "event4",
        "course_id": "CS101", # Một buổi học khác của CS101
        "title": "Nhập môn Lập trình - Lab",
        "date": (today + datetime.timedelta(days=5)).strftime("%Y-%m-%d"),
        "start_time": "13:30",
        "end_time": "15:30",
        "lecturer_materials_url": "#",
        "notes_link": "/notes/CS101"
    }
]

# Route cho trang chính (Dashboard)
@app.route('/')
def dashboard():
    """
    Hiển thị trang tổng quan chính của ứng dụng.
    """
=======
faculty_courses_sample = [
    {"id": "CS101", "name": "Nhập môn Lập trình", "credits": 3, "student_count": 100},
    {"id": "CS305", "name": "Phát triển Web Nâng cao", "credits": 3, "student_count": 40},
    {"id": "AI202", "name": "Nhập môn Trí tuệ Nhân tạo", "credits": 4, "student_count": 60},
    {"id": "MA205", "name": "Xác suất Thống kê", "credits": 3, "student_count": 80},
]

teaching_schedule_sample = [
    {"course_name": "Nhập môn Lập trình", "date": "Thứ 2, 13/05/2025", "time": "07:30 - 09:30", "room": "B201"},
    {"course_name": "Phát triển Web Nâng cao", "date": "Thứ 3, 14/05/2025", "time": "13:30 - 15:30", "room": "C105"},
    {"course_name": "Xác suất Thống kê", "date": "Thứ 5, 16/05/2025", "time": "09:45 - 11:45", "room": "A303"},
]

today = datetime.date.today()
# Dữ liệu thô cho sự kiện lịch của sinh viên, 'notes_link' sẽ được tạo động
# Raw data for student calendar events, 'notes_link' will be generated dynamically
raw_student_calendar_events_sample = [
    {
        "id": "event1", "course_id": "CS101", "title": "Nhập môn Lập trình",
        "date": today.strftime("%Y-%m-%d"), "start_time": "07:30", "end_time": "09:30",
        "lecturer_materials_url": "#"
    },
    {
        "id": "event2", "course_id": "MA101", "title": "Toán cao cấp A1",
        "date": (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d"), "start_time": "09:45", "end_time": "11:45",
        "lecturer_materials_url": "#"
    },
    {
        "id": "event3", "course_id": "EN101", "title": "Tiếng Anh học thuật 1",
        "date": (today + datetime.timedelta(days=2)).strftime("%Y-%m-%d"), "start_time": "07:30", "end_time": "09:30",
        "lecturer_materials_url": "#"
    },
]

# --- Routes ---

@app.route('/', methods=['GET', 'POST'])
def login():
    """
    Hiển thị trang đăng nhập và xử lý việc đăng nhập.
    Displays the login page and handles login attempts.
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role') # 'student' or 'faculty'

        user_account = None
        redirect_url = None

        if role == 'student':
            if username in STUDENT_ACCOUNTS and STUDENT_ACCOUNTS[username]['password'] == password:
                user_account = STUDENT_ACCOUNTS[username]
                redirect_url = url_for('student_dashboard')
        elif role == 'faculty':
            if username in FACULTY_ACCOUNTS and FACULTY_ACCOUNTS[username]['password'] == password:
                user_account = FACULTY_ACCOUNTS[username]
                redirect_url = url_for('faculty_dashboard')
        
        if user_account:
            session['logged_in'] = True
            session['username'] = username
            session['role'] = role
            session['full_name'] = user_account['full_name']
            if role == 'student':
                session['major'] = user_account['major']
            elif role == 'faculty':
                session['department'] = user_account['department']
            flash('Đăng nhập thành công!', 'success') # Login successful!
            return redirect(redirect_url)
        else:
            flash('Tên đăng nhập hoặc mật khẩu không đúng.', 'danger') # Incorrect username or password.
            return redirect(url_for('login'))

    # GET request: show login page
    # Nếu đã đăng nhập, chuyển hướng đến dashboard phù hợp
    # If already logged in, redirect to appropriate dashboard
    if 'logged_in' in session:
        if session.get('role') == 'student':
            return redirect(url_for('student_dashboard'))
        elif session.get('role') == 'faculty':
            return redirect(url_for('faculty_dashboard'))
            
    current_year = datetime.datetime.now().year
    return render_template('login.html', current_year=current_year)

@app.route('/logout')
def logout():
    """
    Xử lý việc đăng xuất.
    Handles logout.
    """
    session.clear() # Xóa tất cả dữ liệu session (Clear all session data)
    flash('Bạn đã đăng xuất.', 'info') # You have been logged out.
    return redirect(url_for('login'))

@app.route('/student/dashboard')
def student_dashboard():
    """
    Hiển thị trang tổng quan của sinh viên.
    Displays the student dashboard.
    """
    if not session.get('logged_in') or session.get('role') != 'student':
        flash('Vui lòng đăng nhập với tư cách sinh viên.', 'warning') # Please log in as a student.
        return redirect(url_for('login'))

    # Tạo notes_link động cho các sự kiện lịch của sinh viên
    # Dynamically create notes_link for student calendar events
    processed_student_calendar_events = []
    for event_data in raw_student_calendar_events_sample:
        # Sao chép dữ liệu sự kiện để không thay đổi bản gốc raw_student_calendar_events_sample
        # Copy event data to avoid modifying the original raw_student_calendar_events_sample
        event = event_data.copy()
        event['notes_link'] = url_for('student_notes', course_id=event['course_id'])
        processed_student_calendar_events.append(event)

>>>>>>> test1
    upcoming_reviews = [
        {"subject": "Nhập môn Lập trình", "topic": "Biến và kiểu dữ liệu", "due_date": "Ngày mai"},
        {"subject": "Toán cao cấp A1", "topic": "Giới hạn hàm số", "due_date": "Trong 2 ngày"},
    ]
<<<<<<< HEAD
    # Lấy 3 sự kiện lịch gần nhất cho dashboard
    upcoming_events = sorted([event for event in calendar_events_sample if datetime.datetime.strptime(event['date'], '%Y-%m-%d').date() >= today], key=lambda x: x['date'])[:3]

    return render_template(
        'index.html',
        user=user_info,
        courses=courses_sample,
        reviews=upcoming_reviews,
        calendar_events=calendar_events_sample, # Truyền dữ liệu lịch
        upcoming_events_dashboard = upcoming_events # Truyền dữ liệu lịch cho dashboard
    )

# Route cho trang ghi chú (ví dụ)
@app.route('/notes/<course_id>')
def notes(course_id):
    """
    Hiển thị trang ghi chú cho một môn học cụ thể.
    """
    course = next((c for c in courses_sample if c["id"] == course_id), None)
    if not course:
        return "Không tìm thấy môn học", 404
    return render_template('notes_template.html', course=course, user=user_info)

# (Thêm) Route giả lập để lấy tài liệu (ví dụ)
@app.route('/materials/<course_id>/<event_date>')
def get_materials(course_id, event_date):
    """
    Giả lập việc lấy tài liệu cho một buổi học cụ thể.
    Trong thực tế, bạn sẽ truy vấn CSDL hoặc API Canvas/SIS.
    """
    course = next((c for c in courses_sample if c["id"] == course_id), None)
    if not course:
        return {"error": "Course not found"}, 404
    
    # Giả sử tài liệu là một danh sách các link hoặc tên file
    materials = [
        f"Slide bài giảng {course['name']} - Buổi {event_date}.pdf",
        f"Bài tập về nhà {event_date}.docx",
        "Link tham khảo thêm: example.com/resource"
=======
    
    # Lọc các sự kiện sắp tới từ danh sách đã xử lý
    # Filter upcoming events from the processed list
    upcoming_events_dashboard = sorted(
        [event for event in processed_student_calendar_events if datetime.datetime.strptime(event['date'], '%Y-%m-%d').date() >= today],
        key=lambda x: x['date']
    )[:3]
    
    # Lấy thông tin người dùng từ session
    # Get user info from session
    user_display_info = {
        "name": session.get('full_name'),
        "major": session.get('major')
    }

    return render_template(
        'index.html', 
        user=user_display_info, # Truyền thông tin người dùng từ session (Pass session user info)
        courses=student_courses_sample,
        reviews=upcoming_reviews,
        calendar_events=processed_student_calendar_events, # Sử dụng danh sách đã xử lý (Use the processed list)
        upcoming_events_dashboard=upcoming_events_dashboard
    )

@app.route('/student/notes/<course_id>')
def student_notes(course_id):
    """
    Hiển thị trang ghi chú cho một môn học cụ thể của sinh viên.
    Displays the notes page for a specific student course.
    """
    if not session.get('logged_in') or session.get('role') != 'student':
        flash('Vui lòng đăng nhập với tư cách sinh viên.', 'warning') # Please log in as a student.
        return redirect(url_for('login'))

    course = next((c for c in student_courses_sample if c["id"] == course_id), None)
    if not course:
        flash('Không tìm thấy môn học.', 'danger') # Course not found.
        return redirect(url_for('student_dashboard'))
    
    user_display_info = { "name": session.get('full_name') }
    return render_template('notes_template.html', course=course, user=user_display_info)

@app.route('/student/materials/<course_id>/<event_date>')
def get_student_materials(course_id, event_date):
    """
    Giả lập việc lấy tài liệu cho một buổi học cụ thể của sinh viên.
    Simulates fetching materials for a specific student class session.
    """
    if not session.get('logged_in') or session.get('role') != 'student':
        return {"error": "Unauthorized"}, 401 # Trả về lỗi JSON cho route dạng API (Return JSON error for API-like route)

    course = next((c for c in student_courses_sample if c["id"] == course_id), None)
    if not course:
        return {"error": "Course not found"}, 404
    
    materials = [
        f"Slide bài giảng {course['name']} - Buổi {event_date}.pdf",
        f"Bài tập về nhà {event_date}.docx",
>>>>>>> test1
    ]
    return {"course_name": course['name'], "event_date": event_date, "materials": materials}


<<<<<<< HEAD
=======
@app.route('/faculty/dashboard')
def faculty_dashboard():
    """
    Hiển thị trang tổng quan của giảng viên.
    Displays the faculty dashboard.
    """
    if not session.get('logged_in') or session.get('role') != 'faculty':
        flash('Vui lòng đăng nhập với tư cách giảng viên.', 'warning') # Please log in as a faculty member.
        return redirect(url_for('login'))

    # Lấy thông tin người dùng từ session
    # Get user info from session
    faculty_display_info = {
        "name": session.get('full_name'),
        "department": session.get('department')
    }
    return render_template(
        'faculty_dashboard.html',
        faculty_user=faculty_display_info, # Truyền thông tin người dùng từ session (Pass session user info)
        faculty_courses=faculty_courses_sample,
        teaching_schedule=teaching_schedule_sample
        )

# --- Chạy ứng dụng ---
>>>>>>> test1
if __name__ == '__main__':
    app.run(debug=True)
