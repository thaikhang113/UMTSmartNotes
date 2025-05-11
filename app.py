# app.py
from flask import Flask, render_template, redirect, url_for, request, session, flash
import datetime
# import random # Không cần random nữa cho việc tạo tài khoản
import os # Cho secret key

app = Flask(__name__)
# Cần thiết cho session và flash messages
app.secret_key = os.urandom(24) # Tạo một secret key ngẫu nhiên

# --- Dữ liệu Người dùng Mẫu CỐ ĐỊNH (CÓ MẬT KHẨU - CHỈ DÙNG CHO DEMO) ---
# CẢNH BÁO: Lưu trữ mật khẩu dạng văn bản thuần là một rủi ro bảo mật lớn.
# Sử dụng băm mật khẩu (ví dụ: Werkzeug's generate_password_hash) trong ứng dụng thực tế.
STUDENT_ACCOUNTS = {
    "khang.2302700102@st.umt.edu.vn": {"password": "123", "full_name": "Nguyễn Văn Khang", "major": "Công nghệ thông tin"},
    "minh.2301122334@st.umt.edu.vn": {"password": "123", "full_name": "Trần Thị Minh", "major": "Quản trị Kinh doanh"},
    "lan.2305566778@st.umt.edu.vn": {"password": "123", "full_name": "Lê Thị Lan", "major": "Ngôn ngữ Anh"}
}
FACULTY_ACCOUNTS = {
    "gv_khang.2302700102": {"password": "123", "full_name": "Nguyễn Văn Khang (GV)", "department": "Khoa Công nghệ Thông tin"},
    "gv_thanh.1234": {"password": "123", "full_name": "Phạm Văn Thành (GV)", "department": "Khoa Kinh tế"},
    "gv_huong.5678": {"password": "123", "full_name": "Võ Thị Hương (GV)", "department": "Khoa Ngoại ngữ"}
}

# --- Dữ liệu Mẫu khác ---
student_courses_sample = [
    {"id": "CS101", "name": "Nhập môn Lập trình", "schedule": "Thứ 2, Tiết 1-3"},
    {"id": "MA101", "name": "Toán cao cấp A1", "schedule": "Thứ 3, Tiết 4-6"},
    {"id": "EN101", "name": "Tiếng Anh học thuật 1", "schedule": "Thứ 4, Tiết 1-3"},
]
faculty_courses_sample = [
    {"id": "CS101", "name": "Nhập môn Lập trình", "credits": 3, "student_count": 100},
    {"id": "CS305", "name": "Phát triển Web Nâng cao", "credits": 3, "student_count": 40},
]
teaching_schedule_sample = [
    {"course_name": "Nhập môn Lập trình", "date": "Thứ 2, 13/05/2025", "time": "07:30 - 09:30", "room": "B201"},
]

today = datetime.date.today()
# Dữ liệu thô cho sự kiện lịch của sinh viên, 'notes_link' sẽ được tạo động
raw_student_calendar_events_sample = [
    {
        "id": "event1", "course_id": "CS101", "title": "Nhập môn Lập trình - Buổi 1",
        "date": today.strftime("%Y-%m-%d"), "start_time": "07:30", "end_time": "09:30",
        "lecturer_materials_url": "#"
    },
    {
        "id": "event2", "course_id": "MA101", "title": "Toán cao cấp A1 - Buổi 1",
        "date": (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d"), "start_time": "09:45", "end_time": "11:45",
        "lecturer_materials_url": "#"
    },
    { 
        "id": "event3", "course_id": "CS101", "title": "Nhập môn Lập trình - Buổi 2",
        "date": (today + datetime.timedelta(days=2)).strftime("%Y-%m-%d"), "start_time": "07:30", "end_time": "09:30",
        "lecturer_materials_url": "#"
    },
]

# --- Routes ---
@app.route('/', methods=['GET', 'POST'])
def login():
    """
    Hiển thị trang đăng nhập và xử lý việc đăng nhập.
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
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
            if role == 'student': session['major'] = user_account['major']
            elif role == 'faculty': session['department'] = user_account['department']
            flash('Đăng nhập thành công!', 'success')
            return redirect(redirect_url)
        else:
            flash('Tên đăng nhập hoặc mật khẩu không đúng.', 'danger')
            return redirect(url_for('login'))

    if 'logged_in' in session: # Nếu đã đăng nhập, chuyển hướng
        if session.get('role') == 'student': return redirect(url_for('student_dashboard'))
        elif session.get('role') == 'faculty': return redirect(url_for('faculty_dashboard'))
            
    current_year = datetime.datetime.now().year
    return render_template('login.html', current_year=current_year)

@app.route('/logout')
def logout():
    """
    Xử lý việc đăng xuất.
    """
    session.clear() # Xóa tất cả dữ liệu session
    flash('Bạn đã đăng xuất.', 'info')
    return redirect(url_for('login'))

@app.route('/student/dashboard')
def student_dashboard():
    """
    Hiển thị trang tổng quan của sinh viên.
    """
    if not session.get('logged_in') or session.get('role') != 'student':
        flash('Vui lòng đăng nhập với tư cách sinh viên.', 'warning')
        return redirect(url_for('login'))
    
    processed_student_calendar_events = []
    for event_data in raw_student_calendar_events_sample:
        event = event_data.copy()
        # Link đến trang ghi chú theo buổi học cụ thể
        event['notes_link'] = url_for('student_session_note', 
                                      course_id=event['course_id'], 
                                      date_str=event['date']) # Sử dụng date_str để truyền ngày
        processed_student_calendar_events.append(event)

    upcoming_reviews = [
        {"subject": "Nhập môn Lập trình", "topic": "Biến và kiểu dữ liệu", "due_date": "Ngày mai"},
    ]
    upcoming_events_dashboard = sorted(
        [event for event in processed_student_calendar_events if datetime.datetime.strptime(event['date'], '%Y-%m-%d').date() >= today],
        key=lambda x: x['date']
    )[:3]
    user_display_info = {"name": session.get('full_name'), "major": session.get('major')}
    return render_template('index.html', user=user_display_info, courses=student_courses_sample,
                           reviews=upcoming_reviews, calendar_events=processed_student_calendar_events,
                           upcoming_events_dashboard=upcoming_events_dashboard)

@app.route('/student/notes/<course_id>/<date_str>')
def student_session_note(course_id, date_str):
    """
    Hiển thị trang ghi chú cho một buổi học cụ thể (theo course_id và date_str).
    """
    if not session.get('logged_in') or session.get('role') != 'student':
        flash('Vui lòng đăng nhập với tư cách sinh viên.', 'warning')
        return redirect(url_for('login'))

    course = next((c for c in student_courses_sample if c["id"] == course_id), None)
    if not course:
        flash('Không tìm thấy môn học.', 'danger')
        return redirect(url_for('student_dashboard')) 
    
    try:
        # Kiểm tra định dạng ngày (YYYY-MM-DD)
        datetime.datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        flash('Định dạng ngày không hợp lệ.', 'danger')
        return redirect(url_for('student_dashboard')) 

    user_display_info = { "name": session.get('full_name') }
    # Truyền cả course và date_str vào template để JavaScript có thể sử dụng
    return render_template('notes_template.html', course=course, note_date=date_str, user=user_display_info)


@app.route('/student/notes/<course_id>')
def student_course_notes_overview(course_id):
    """
    Hiển thị trang tổng quan các ghi chú đã có cho môn học, sắp xếp theo ngày.
    (Sẽ được phát triển đầy đủ ở Bước 3)
    """
    if not session.get('logged_in') or session.get('role') != 'student':
        flash('Vui lòng đăng nhập với tư cách sinh viên.', 'warning')
        return redirect(url_for('login'))

    course = next((c for c in student_courses_sample if c["id"] == course_id), None)
    if not course:
        flash('Không tìm thấy môn học.', 'danger')
        return redirect(url_for('student_dashboard'))
    
    # Đây là nơi bạn sẽ render 'course_notes_overview.html' ở Bước 3
    # For now, a placeholder message
    flash(f'Trang tổng quan ghi chú cho môn {course["name"]} (theo từng ngày) sẽ được hiển thị ở đây. Hiện đang phát triển.', 'info')
    # Ví dụ: return render_template('course_notes_overview.html', course=course, user={"name": session.get('full_name')})
    return redirect(url_for('student_dashboard'))


@app.route('/student/materials/<course_id>/<event_date>')
def get_student_materials(course_id, event_date):
    """
    Giả lập việc lấy tài liệu cho một buổi học cụ thể của sinh viên.
    """
    if not session.get('logged_in') or session.get('role') != 'student':
        return {"error": "Unauthorized"}, 401
    course = next((c for c in student_courses_sample if c["id"] == course_id), None)
    if not course: return {"error": "Course not found"}, 404
    materials = [f"Slide {course['name']} - Buổi {event_date}.pdf", f"Bài tập {event_date}.docx"]
    return {"course_name": course['name'], "event_date": event_date, "materials": materials}

@app.route('/faculty/dashboard')
def faculty_dashboard():
    """
    Hiển thị trang tổng quan của giảng viên.
    """
    if not session.get('logged_in') or session.get('role') != 'faculty':
        flash('Vui lòng đăng nhập với tư cách giảng viên.', 'warning')
        return redirect(url_for('login'))
    faculty_display_info = {"name": session.get('full_name'), "department": session.get('department')}
    return render_template('faculty_dashboard.html', faculty_user=faculty_display_info,
                           faculty_courses=faculty_courses_sample, teaching_schedule=teaching_schedule_sample)

# --- Chạy ứng dụng ---
if __name__ == '__main__':
    app.run(debug=True)
