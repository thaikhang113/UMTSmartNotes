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
}
FACULTY_ACCOUNTS = {
    "gv_khang.2302700102": {"password": "123", "full_name": "Nguyễn Văn Khang (GV)", "department": "Khoa Công nghệ Thông tin"},
}

# --- Dữ liệu Môn học ---
student_courses_sample = [
    {"id": "BIT104V1", "name": "Introduction To Mathematical Analysis", "code": "BIT104V1", "schedule": "Lịch học cụ thể trong tuần"},
    {"id": "BIT115V1", "name": "Introduction to Artificial Intelligence", "code": "BIT115V1", "schedule": "Lịch học cụ thể trong tuần"},
    {"id": "BIT114V1", "name": "Introduction to Software engineering", "code": "BIT114V1", "schedule": "Lịch học cụ thể trong tuần"},
    {"id": "BIT110V1", "name": "Introduction to Operating systems", "code": "BIT110V1", "schedule": "Lịch học cụ thể trong tuần"},
    {"id": "GED102V1", "name": "Scientific Socialism", "code": "GED102V1", "schedule": "Lịch học cụ thể trong tuần"},
]
faculty_courses_sample = [ 
    {"id": "CS101", "name": "Nhập môn Lập trình", "credits": 3, "student_count": 100},
]
teaching_schedule_sample = [ 
    {"course_name": "Nhập môn Lập trình", "date": "Thứ 2, 13/05/2025", "time": "07:30 - 09:30", "room": "B201"},
]

# --- Dữ liệu Lịch học Chi tiết (10 buổi cho mỗi môn) ---
# ĐIỀU CHỈNH: Tuần bắt đầu từ Thứ Hai, 05/05/2025 để dễ kiểm tra với ngày hiện tại
# ADJUSTMENT: Week starts from Monday, May 5, 2025, for easier testing with current date
start_date_week1 = datetime.date(2025, 5, 5) # THAY ĐỔI NGÀY BẮT ĐẦU (CHANGED START DATE)

raw_student_calendar_events_sample = []
event_id_counter = 1

def create_recurring_sessions(base_event, num_sessions=10):
    global event_id_counter
    sessions = []
    base_date = datetime.datetime.strptime(base_event["date"], "%Y-%m-%d").date()
    for i in range(num_sessions):
        event_date = base_date + datetime.timedelta(weeks=i)
        session_event = base_event.copy()
        session_event["id"] = f"event{event_id_counter}"
        session_event["title"] = f"{base_event['title_root']} - Buổi {i+1}" # Sử dụng title_root
        session_event["date"] = event_date.strftime("%Y-%m-%d")
        if (i % 3 == 0): session_event["material_url"] = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
        elif (i % 3 == 1): session_event["material_url"] = "https://www.clickdimensions.com/links/TestPDFfile.pdf"
        else: session_event["material_url"] = None
        sessions.append(session_event)
        event_id_counter += 1
    return sessions

# 1. Môn: Introduction To Mathematical Analysis (BIT104V1)
base_event_math_lab = {
    "course_id": "BIT104V1", "title_root": "Intro To Mathematical Analysis", "course_code": "BIT104V1",
    "date": start_date_week1.strftime("%Y-%m-%d"), # Thứ Hai
    "start_time": "07:00", "end_time": "09:30", "lecturer_materials_url": "#",
    "lecturer": "Huỳnh Lê Phú Trung", "location": "P.512, Tòa nhà Sáng tạo", "eventType": "LAB-1", "credits": 3
}
raw_student_calendar_events_sample.extend(create_recurring_sessions(base_event_math_lab))
base_event_math_lec = {
    "course_id": "BIT104V1", "title_root": "Intro To Mathematical Analysis", "course_code": "BIT104V1",
    "date": (start_date_week1 + datetime.timedelta(days=4)).strftime("%Y-%m-%d"), # Thứ Sáu
    "start_time": "07:00", "end_time": "09:30", "lecturer_materials_url": "#",
    "lecturer": "Đoàn Văn Phúc", "location": "P.404, Tòa nhà Sáng tạo", "eventType": "LEC", "credits": 3
}
raw_student_calendar_events_sample.extend(create_recurring_sessions(base_event_math_lec))

# 2. Môn: Introduction to Artificial Intelligence (BIT115V1)
base_event_ai_lab = {
    "course_id": "BIT115V1", "title_root": "Intro to Artificial Intelligence", "course_code": "BIT115V1",
    "date": start_date_week1.strftime("%Y-%m-%d"), # Thứ Hai
    "start_time": "09:50", "end_time": "12:20", "lecturer_materials_url": "#",
    "lecturer": "Huỳnh Lê Phú Trung", "location": "P.501, Tòa nhà Sáng tạo", "eventType": "LAB-1", "credits": 3
}
raw_student_calendar_events_sample.extend(create_recurring_sessions(base_event_ai_lab))
base_event_ai_lec = {
    "course_id": "BIT115V1", "title_root": "Intro to Artificial Intelligence", "course_code": "BIT115V1",
    "date": (start_date_week1 + datetime.timedelta(days=3)).strftime("%Y-%m-%d"), # Thứ Năm
    "start_time": "07:00", "end_time": "09:30", "lecturer_materials_url": "#",
    "lecturer": "Đỗ Văn Nhơn", "location": "P.801, Tòa nhà Sáng tạo", "eventType": "LEC", "credits": 3
}
raw_student_calendar_events_sample.extend(create_recurring_sessions(base_event_ai_lec))

# 3. Môn: Introduction to Software engineering (BIT114V1)
base_event_se_lec = {
    "course_id": "BIT114V1", "title_root": "Intro to Software engineering", "course_code": "BIT114V1",
    "date": start_date_week1.strftime("%Y-%m-%d"), # Thứ Hai
    "start_time": "13:50", "end_time": "16:40", "lecturer_materials_url": "#",
    "lecturer": "Võ Thị Thanh Vân", "location": "P.506, Tòa nhà Sáng tạo", "eventType": "LEC", "credits": 3
}
raw_student_calendar_events_sample.extend(create_recurring_sessions(base_event_se_lec))
base_event_se_lab = {
    "course_id": "BIT114V1", "title_root": "Intro to Software engineering", "course_code": "BIT114V1",
    "date": (start_date_week1 + datetime.timedelta(days=3)).strftime("%Y-%m-%d"), # Thứ Năm
    "start_time": "09:50", "end_time": "12:20", "lecturer_materials_url": "#",
    "lecturer": "Trần Hữu Quốc Văn", "location": "P.A03, Tòa nhà Sáng tạo", "eventType": "LAB-2", "credits": 3
}
raw_student_calendar_events_sample.extend(create_recurring_sessions(base_event_se_lab))

# 4. Môn: Introduction to Operating systems (BIT110V1)
base_event_os_lec = {
    "course_id": "BIT110V1", "title_root": "Intro to Operating systems", "course_code": "BIT110V1",
    "date": (start_date_week1 + datetime.timedelta(days=3)).strftime("%Y-%m-%d"), # Thứ Năm
    "start_time": "13:50", "end_time": "16:40", "lecturer_materials_url": "#",
    "lecturer": "Vũ Thị Mỹ Hằng", "location": "P.A02, Tòa nhà Sáng tạo", "eventType": "LEC", "credits": 3
}
raw_student_calendar_events_sample.extend(create_recurring_sessions(base_event_os_lec))
base_event_os_lab = {
    "course_id": "BIT110V1", "title_root": "Intro to Operating systems", "course_code": "BIT110V1",
    "date": (start_date_week1 + datetime.timedelta(days=4)).strftime("%Y-%m-%d"), # Thứ Sáu
    "start_time": "09:30", "end_time": "12:00", "lecturer_materials_url": "#",
    "lecturer": "Đỗ Minh Tiến", "location": "P.512, Tòa nhà Sáng tạo", "eventType": "LAB-1", "credits": 3
}
raw_student_calendar_events_sample.extend(create_recurring_sessions(base_event_os_lab))

# 5. Môn: Scientific Socialism (GED102V1)
base_event_socialism = {
    "course_id": "GED102V1", "title_root": "Scientific Socialism", "course_code": "GED102V1",
    "date": (start_date_week1 + datetime.timedelta(days=5)).strftime("%Y-%m-%d"), # Thứ Bảy
    "start_time": "07:00", "end_time": "09:30", "lecturer_materials_url": "#",
    "lecturer": "Hà Triệu Huy", "location": "P.801, Tòa nhà Sáng tạo", "eventType": "LEC", "credits": 2
}
raw_student_calendar_events_sample.extend(create_recurring_sessions(base_event_socialism))

# --- Custom Jinja Filter ---
@app.template_filter('format_date_display')
def format_date_display_filter(value, format_str='%d/%m/%Y'):
    try:
        date_obj = datetime.datetime.strptime(value, '%Y-%m-%d')
        return date_obj.strftime(format_str)
    except (ValueError, TypeError):
        return value

# --- Routes (phần còn lại giữ nguyên logic) ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        user_account = None
        redirect_url = None
        if role == 'student':
            if username == "khang.2302700102@st.umt.edu.vn" and STUDENT_ACCOUNTS.get(username, {}).get('password') == password:
                user_account = STUDENT_ACCOUNTS[username]
                redirect_url = url_for('student_dashboard')
            elif username in STUDENT_ACCOUNTS and STUDENT_ACCOUNTS[username]['password'] == password:
                user_account = STUDENT_ACCOUNTS[username]
                # Chuyển hướng sinh viên khác đến một dashboard chung hơn hoặc trang login nếu chưa có dashboard riêng
                # Redirect other students to a more generic dashboard or login if no specific dashboard exists
                flash('Lịch học chi tiết hiện chỉ dành cho tài khoản demo Nguyễn Văn Khang.', 'info')
                redirect_url = url_for('student_dashboard_generic') # Cần tạo route này nếu muốn
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
            return redirect(redirect_url if redirect_url else url_for('login'))
        else:
            flash('Tên đăng nhập hoặc mật khẩu không đúng.', 'danger')
            return redirect(url_for('login'))

    if 'logged_in' in session:
        if session.get('username') == "khang.2302700102@st.umt.edu.vn" and session.get('role') == 'student':
             return redirect(url_for('student_dashboard'))
        # Xử lý chuyển hướng cho các user khác nếu cần
    current_year = datetime.datetime.now().year
    return render_template('login.html', current_year=current_year)

@app.route('/student/dashboard_generic') # Route ví dụ cho sinh viên khác
def student_dashboard_generic():
    if not session.get('logged_in') or session.get('role') != 'student':
        return redirect(url_for('login'))
    # Hiển thị một dashboard đơn giản hơn, không có lịch chi tiết
    user_display_info = {"name": session.get('full_name'), "major": session.get('major')}
    return render_template('index.html', user=user_display_info, courses=student_courses_sample,
                           reviews=[], calendar_events=[], upcoming_events_dashboard=[])


@app.route('/logout')
def logout():
    session.clear()
    flash('Bạn đã đăng xuất.', 'info')
    return redirect(url_for('login'))

@app.route('/student/dashboard') # Dashboard cho Khang
def student_dashboard():
    if not session.get('logged_in') or session.get('role') != 'student' or session.get('username') != "khang.2302700102@st.umt.edu.vn":
        flash('Truy cập không hợp lệ.', 'warning')
        return redirect(url_for('login'))
    
    processed_student_calendar_events = []
    for event_data in raw_student_calendar_events_sample:
        event = event_data.copy()
        event['notes_link'] = url_for('student_session_note', course_id=event['course_id'], date_str=event['date'])
        processed_student_calendar_events.append(event)

    upcoming_reviews = [{"subject": "Nhập môn Lập trình", "topic": "Biến và kiểu dữ liệu", "due_date": "Ngày mai"}]
    # Lấy ngày hiện tại thực tế khi render dashboard
    # Get the actual current date when rendering the dashboard
    current_display_date = datetime.date.today() 
    upcoming_events_dashboard = sorted(
        [event for event in processed_student_calendar_events if datetime.datetime.strptime(event['date'], '%Y-%m-%d').date() >= current_display_date],
        key=lambda x: x['date']
    )[:3]
    user_display_info = {"name": session.get('full_name'), "major": session.get('major')}
    
    khang_courses_ids = set(evt['course_id'] for evt in raw_student_calendar_events_sample)
    khang_courses_details = [course for course in student_courses_sample if course['id'] in khang_courses_ids]

    return render_template('index.html', user=user_display_info, courses=khang_courses_details,
                           reviews=upcoming_reviews, calendar_events=processed_student_calendar_events,
                           upcoming_events_dashboard=upcoming_events_dashboard)

@app.route('/student/notes/<course_id>/<date_str>')
def student_session_note(course_id, date_str):
    # ... (giữ nguyên logic) ...
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
    session_event_data = next((evt for evt in raw_student_calendar_events_sample if evt['course_id'] == course_id and evt['date'] == date_str), None)
    material_url_for_session = session_event_data.get('material_url') if session_event_data else None
    user_display_info = { "name": session.get('full_name') }
    return render_template('notes_template.html', course=course, note_date=date_str, 
                           user=user_display_info, material_url=material_url_for_session)

@app.route('/student/notes/<course_id>')
def student_course_notes_overview(course_id):
    # ... (giữ nguyên logic) ...
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
    return render_template('course_notes_overview.html', course=course, 
                           sessions=course_sessions, user=user_display_info)

@app.route('/student/materials/<course_id>/<event_date>')
def get_student_materials(course_id, event_date):
    # ... (giữ nguyên logic) ...
    if not session.get('logged_in') or session.get('role') != 'student':
        return {"error": "Unauthorized"}, 401
    session_event_data = next((evt for evt in raw_student_calendar_events_sample 
                               if evt['course_id'] == course_id and evt['date'] == event_date), None)
    course = next((c for c in student_courses_sample if c["id"] == course_id), None)
    if not course: return {"error": "Course not found"}, 404
    materials = []
    if session_event_data and session_event_data.get('material_url'):
        materials.append(f"Tài liệu chính: {session_event_data.get('material_url').split('/')[-1]}")
    else:
        materials.append(f"Slide {course['name']} - Buổi {event_date}.pdf (Mẫu)")
    materials.append(f"Bài tập {event_date}.docx (Mẫu)")
    return {"course_name": course['name'], "event_date": event_date, "materials": materials}

@app.route('/faculty/dashboard')
def faculty_dashboard():
    # ... (giữ nguyên logic) ...
    if not session.get('logged_in') or session.get('role') != 'faculty':
        flash('Vui lòng đăng nhập với tư cách giảng viên.', 'warning')
        return redirect(url_for('login'))
    faculty_display_info = {"name": session.get('full_name'), "department": session.get('department')}
    return render_template('faculty_dashboard.html', faculty_user=faculty_display_info,
                           faculty_courses=faculty_courses_sample, teaching_schedule=teaching_schedule_sample)

if __name__ == '__main__':
    app.run(debug=True)
