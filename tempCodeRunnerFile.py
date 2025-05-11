# app.py
from flask import Flask, render_template, redirect, url_for, request, session, flash
import datetime
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- Dữ liệu Người dùng Mẫu CỐ ĐỊNH ---
STUDENT_ACCOUNTS = {
    "khang.2302700102@st.umt.edu.vn": {"password": "123", "full_name": "Nguyễn Văn Khang", "major": "Công nghệ thông tin"},
    "minh.2301122334@st.umt.edu.vn": {"password": "123", "full_name": "Trần Thị Minh", "major": "Quản trị Kinh doanh"},
    "lan.2305566778@st.umt.edu.vn": {"password": "123", "full_name": "Lê Thị Lan", "major": "Ngôn ngữ Anh"}
}
FACULTY_ACCOUNTS = {
    "gv_khang.2302700102": {"password": "123", "full_name": "Nguyễn Văn Khang (GV)", "department": "Khoa Công nghệ Thông tin"},
    "gv_thanh.1234": {"password": "123", "full_name": "Phạm Văn Thành (GV)", "department": "Khoa Kinh tế"},
}

# --- Dữ liệu Mẫu khác ---
student_courses_sample = [
    {"id": "CS101", "name": "Nhập môn Lập trình", "schedule": "Thứ 2, Tiết 1-3"},
    {"id": "MA101", "name": "Toán cao cấp A1", "schedule": "Thứ 3, Tiết 4-6"},
    {"id": "EN101", "name": "Tiếng Anh học thuật 1", "schedule": "Thứ 4, Tiết 1-3"},
]
faculty_courses_sample = [ 
    {"id": "CS101", "name": "Nhập môn Lập trình", "credits": 3, "student_count": 100},
]
teaching_schedule_sample = [ 
    {"course_name": "Nhập môn Lập trình", "date": "Thứ 2, 13/05/2025", "time": "07:30 - 09:30", "room": "B201"},
]

today = datetime.date.today()
# Cập nhật raw_student_calendar_events_sample để có material_url
# Update raw_student_calendar_events_sample to include material_url
raw_student_calendar_events_sample = [
    {
        "id": "event1", "course_id": "CS101", "title": "Nhập môn Lập trình - Buổi 1", 
        "date": today.strftime("%Y-%m-%d"), "start_time": "07:30", "end_time": "09:30", 
        "lecturer_materials_url": "#", # Giữ lại cho modal
        "material_url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf" # URL PDF mẫu
    },
    {
        "id": "event2", "course_id": "MA101", "title": "Toán cao cấp A1 - Buổi 1", 
        "date": (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d"), "start_time": "09:45", "end_time": "11:45", 
        "lecturer_materials_url": "#",
        "material_url": None # Ví dụ buổi này không có tài liệu
    },
    { 
        "id": "event3", "course_id": "CS101", "title": "Nhập môn Lập trình - Buổi 2", 
        "date": (today + datetime.timedelta(days=7)).strftime("%Y-%m-%d"), "start_time": "07:30", "end_time": "09:30", 
        "lecturer_materials_url": "#",
        "material_url": "https://www.clickdimensions.com/links/TestPDFfile.pdf" # URL PDF mẫu khác
    },
    { 
        "id": "event4", "course_id": "CS101", "title": "Nhập môn Lập trình - Buổi 3 (Lab)", 
        "date": (today + datetime.timedelta(days=9)).strftime("%Y-%m-%d"), "start_time": "13:30", "end_time": "15:30",
        "lecturer_materials_url": "#",
        "material_url": None # Lab không có slide
    },
    {
        "id": "event5", "course_id": "EN101", "title": "Tiếng Anh học thuật 1 - Buổi 1", 
        "date": (today + datetime.timedelta(days=3)).strftime("%Y-%m-%d"), "start_time": "09:45", "end_time": "11:45", 
        "lecturer_materials_url": "#",
        "material_url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    },
]

# --- Custom Jinja Filter ---
@app.template_filter('format_date_display')
def format_date_display_filter(value):
    try:
        date_obj = datetime.datetime.strptime(value, '%Y-%m-%d')
        return date_obj.strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        return value

# --- Routes ---
@app.route('/', methods=['GET', 'POST'])
def login():
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
    if 'logged_in' in session:
        if session.get('role') == 'student': return redirect(url_for('student_dashboard'))
        elif session.get('role') == 'faculty': return redirect(url_for('faculty_dashboard'))
    current_year = datetime.datetime.now().year
    return render_template('login.html', current_year=current_year)

@app.route('/logout')
def logout():
    session.clear()
    flash('Bạn đã đăng xuất.', 'info')
    return redirect(url_for('login'))

@app.route('/student/dashboard')
def student_dashboard():
    if not session.get('logged_in') or session.get('role') != 'student':
        flash('Vui lòng đăng nhập với tư cách sinh viên.', 'warning')
        return redirect(url_for('login'))
    
    processed_student_calendar_events = []
    for event_data in raw_student_calendar_events_sample:
        event = event_data.copy()
        event['notes_link'] = url_for('student_session_note', course_id=event['course_id'], date_str=event['date'])
        processed_student_calendar_events.append(event)

    upcoming_reviews = [{"subject": "Nhập môn Lập trình", "topic": "Biến và kiểu dữ liệu", "due_date": "Ngày mai"}]
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
    if not session.get('logged_in') or session.get('role') != 'student':
        flash('Vui lòng đăng nhập với tư cách sinh viên.', 'warning')
        return redirect(url_for('login'))
    
    course = next((c for c in student_courses_sample if c["id"] == course_id), None)
    if not course:
        flash('Không tìm thấy môn học.', 'danger')
        return redirect(url_for('student_dashboard')) 
    
    try:
        datetime.datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        flash('Định dạng ngày không hợp lệ.', 'danger')
        return redirect(url_for('student_course_notes_overview', course_id=course_id))

    # Tìm buổi học (event) tương ứng để lấy material_url
    # Find the corresponding session (event) to get material_url
    session_event_data = next((evt for evt in raw_student_calendar_events_sample if evt['course_id'] == course_id and evt['date'] == date_str), None)
    material_url_for_session = session_event_data.get('material_url') if session_event_data else None

    user_display_info = { "name": session.get('full_name') }
    return render_template('notes_template.html', 
                           course=course, 
                           note_date=date_str, 
                           user=user_display_info,
                           material_url=material_url_for_session) # Truyền URL tài liệu vào template

@app.route('/student/notes/<course_id>')
def student_course_notes_overview(course_id):
    if not session.get('logged_in') or session.get('role') != 'student':
        flash('Vui lòng đăng nhập với tư cách sinh viên.', 'warning')
        return redirect(url_for('login'))
    course = next((c for c in student_courses_sample if c["id"] == course_id), None)
    if not course:
        flash('Không tìm thấy môn học.', 'danger')
        return redirect(url_for('student_dashboard'))
    course_sessions = [
        session_event for session_event in raw_student_calendar_events_sample 
        if session_event['course_id'] == course_id
    ]
    course_sessions.sort(key=lambda x: datetime.datetime.strptime(x['date'], '%Y-%m-%d'))
    user_display_info = { "name": session.get('full_name') }
    return render_template('course_notes_overview.html', 
                           course=course, 
                           sessions=course_sessions, 
                           user=user_display_info)

@app.route('/student/materials/<course_id>/<event_date>')
def get_student_materials(course_id, event_date):
    if not session.get('logged_in') or session.get('role') != 'student':
        return {"error": "Unauthorized"}, 401
    
    # Tìm thông tin buổi học để lấy danh sách tài liệu (nếu có nhiều)
    # For this demo, we'll just return a generic list based on the old logic
    # In a real app, you'd fetch specific materials for this event_date
    course = next((c for c in student_courses_sample if c["id"] == course_id), None)
    if not course: return {"error": "Course not found"}, 404
    
    # Tìm event cụ thể để lấy lecturer_materials_url nếu cần
    # This route is mainly for the modal, which might show a general link or specific files
    # For now, let's return a generic list.
    materials = [f"Slide {course['name']} - Buổi {event_date}.pdf", f"Bài tập {event_date}.docx", "Link tham khảo: example.com"]
    return {"course_name": course['name'], "event_date": event_date, "materials": materials}

@app.route('/faculty/dashboard')
def faculty_dashboard():
    if not session.get('logged_in') or session.get('role') != 'faculty':
        flash('Vui lòng đăng nhập với tư cách giảng viên.', 'warning')
        return redirect(url_for('login'))
    faculty_display_info = {"name": session.get('full_name'), "department": session.get('department')}
    return render_template('faculty_dashboard.html', faculty_user=faculty_display_info,
                           faculty_courses=faculty_courses_sample, teaching_schedule=teaching_schedule_sample)

if __name__ == '__main__':
    app.run(debug=True)
