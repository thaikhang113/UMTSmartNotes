# app.py
from flask import Flask, render_template, redirect, url_for, request, session, flash
import datetime
import os
# Thêm werkzeug.utils để xử lý tên file an toàn (nếu thực sự upload)
# from werkzeug.utils import secure_filename 

app = Flask(__name__)
app.secret_key = os.urandom(24)
# Cấu hình thư mục upload (chỉ cần nếu thực sự lưu file)
# UPLOAD_FOLDER = 'uploads' 
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # Giới hạn 16MB

# --- Dữ liệu Người dùng Mẫu CỐ ĐỊNH ---
STUDENT_ACCOUNTS = {
    "khang.2302700102@st.umt.edu.vn": {"password": "123", "full_name": "Nguyễn Văn Khang", "major": "Công nghệ thông tin"},
    "minh.2301122334@st.umt.edu.vn": {"password": "123", "full_name": "Trần Thị Minh", "major": "Quản trị Kinh doanh"},
}
FACULTY_ACCOUNTS = {
    "gv_khang.2302700102": {"password": "123", "full_name": "Nguyễn Văn Khang (GV)", "department": "Khoa Công nghệ Thông tin", "courses_taught": ["CS101", "MA101"]},
    "gv_thanh.1234": {"password": "123", "full_name": "Phạm Văn Thành (GV)", "department": "Khoa Kinh tế", "courses_taught": ["EN101"]},
}

# --- Dữ liệu Mẫu khác ---
student_courses_sample = [
    {"id": "CS101", "name": "Nhập môn Lập trình", "code": "BIT101V1", "schedule": "Thứ 2 & Thứ 5", "credits": 3},
    {"id": "MA101", "name": "Toán cao cấp A1", "code": "MAT101V1", "schedule": "Thứ 3", "credits": 3},
    {"id": "EN101", "name": "Tiếng Anh học thuật 1", "code": "ENG101V1", "schedule": "Thứ 4", "credits": 2},
]

# ĐỊNH NGHĨA teaching_schedule_sample Ở ĐÂY (GLOBAL SCOPE)
teaching_schedule_sample = [
    {"course_name": "Nhập môn Lập trình", "date": "Thứ 2, 12/05/2025", "time": "07:30 - 09:30", "room": "B201"},
    {"course_name": "Toán cao cấp A1", "date": "Thứ 3, 13/05/2025", "time": "13:30 - 15:30", "room": "C105"},
    {"course_name": "Tiếng Anh học thuật 1", "date": "Thứ 4, 14/05/2025", "time": "09:45 - 11:45", "room": "A303"},
]


today_obj = datetime.date.today() 
start_date_week1 = today_obj - datetime.timedelta(days=today_obj.weekday()) 
if today_obj.weekday() == 6: 
    start_date_week1 -= datetime.timedelta(days=6)


raw_student_calendar_events_sample = []
event_id_counter = 1

def create_recurring_sessions(base_event, num_sessions=10):
    global event_id_counter
    sessions = []
    try:
        base_date = datetime.datetime.strptime(base_event["date"], "%Y-%m-%d").date()
    except ValueError:
        print(f"Lỗi định dạng ngày cho sự kiện gốc: {base_event}")
        return sessions 

    for i in range(num_sessions):
        event_date = base_date + datetime.timedelta(weeks=i)
        session_event = base_event.copy()
        session_event["id"] = f"event{event_id_counter}"
        session_event["title"] = f"{base_event.get('title_root', base_event.get('title', 'Buổi học'))} - Buổi {i+1}"
        session_event["date"] = event_date.strftime("%Y-%m-%d")
        
        if not session_event.get("material_url"): 
            if (i % 3 == 0): session_event["material_url"] = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
            elif (i % 3 == 1): session_event["material_url"] = "https://www.clickdimensions.com/links/TestPDFfile.pdf"
            else: session_event["material_url"] = None
        
        sessions.append(session_event)
        event_id_counter += 1
    return sessions

initial_events_data = [
    {"course_id": "CS101", "title_root": "Nhập môn Lập trình", "course_code": "BIT101V1", "date_offset_days": 0, "start_time": "07:30", "end_time": "09:30", "lecturer": "Huỳnh Lê Phú Trung", "location": "P.512", "eventType": "LAB-1", "credits": 3},
    {"course_id": "CS101", "title_root": "Nhập môn Lập trình", "course_code": "BIT101V1", "date_offset_days": 3, "start_time": "13:30", "end_time": "15:30", "lecturer": "Võ Thị Thanh Vân", "location": "P.506", "eventType": "LEC", "credits": 3},
    {"course_id": "MA101", "title_root": "Toán cao cấp A1", "course_code": "MAT101V1", "date_offset_days": 1, "start_time": "09:45", "end_time": "11:45", "lecturer": "Đỗ Văn Nhơn", "location": "P.801", "eventType": "LEC", "credits": 3},
    {"course_id": "EN101", "title_root": "Tiếng Anh học thuật 1", "course_code": "ENG101V1", "date_offset_days": 2, "start_time": "09:45", "end_time": "11:45", "lecturer": "Đoàn Văn Phúc", "location": "P.404", "eventType": "LEC", "credits": 2},
]

for base_data in initial_events_data:
    base_event = base_data.copy()
    base_event["date"] = (start_date_week1 + datetime.timedelta(days=base_data["date_offset_days"])).strftime("%Y-%m-%d")
    base_event.pop("date_offset_days") 
    base_event["lecturer_materials_url"] = "#" 
    raw_student_calendar_events_sample.extend(create_recurring_sessions(base_event))


# --- Custom Jinja Filter ---
@app.template_filter('format_date_display')
def format_date_display_filter(value, format_str='%d/%m/%Y'):
    try:
        date_obj = datetime.datetime.strptime(value, '%Y-%m-%d')
        return date_obj.strftime(format_str)
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
            elif role == 'faculty': 
                session['department'] = user_account['department']
                session['courses_taught'] = user_account.get('courses_taught', []) 
            flash('Đăng nhập thành công!', 'success')
            return redirect(redirect_url if redirect_url else url_for('login'))
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
    current_student_username = session.get('username')
    
    # Chỉ tạo lịch chi tiết cho Khang, các SV khác có thể có logic khác
    if current_student_username == "khang.2302700102@st.umt.edu.vn":
        for event_data in raw_student_calendar_events_sample:
            event = event_data.copy()
            event['notes_link'] = url_for('student_session_note', course_id=event['course_id'], date_str=event['date'])
            processed_student_calendar_events.append(event)
    # else:
        # Xử lý lịch cho các sinh viên khác nếu cần, ví dụ:
        # processed_student_calendar_events = get_calendar_for_student(current_student_username)
        # Hoặc để trống nếu họ không có lịch đặc biệt

    upcoming_reviews = [{"subject": "Nhập môn Lập trình", "topic": "Biến và kiểu dữ liệu", "due_date": "Ngày mai"}]
    current_display_date = datetime.date.today() 
    upcoming_events_dashboard = sorted(
        [event for event in processed_student_calendar_events if datetime.datetime.strptime(event['date'], '%Y-%m-%d').date() >= current_display_date],
        key=lambda x: x['date']
    )[:3]
    user_display_info = {"name": session.get('full_name'), "major": session.get('major')}
    
    display_courses = []
    if current_student_username == "khang.2302700102@st.umt.edu.vn":
        student_courses_ids = set(evt['course_id'] for evt in raw_student_calendar_events_sample)
        display_courses = [course for course in student_courses_sample if course['id'] in student_courses_ids]
    else:
        # Sinh viên khác có thể thấy tất cả môn học mẫu hoặc không thấy môn nào nếu không có logic riêng
        display_courses = student_courses_sample 


    return render_template('index.html', user=user_display_info, courses=display_courses,
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
    session_event_data = next((evt for evt in raw_student_calendar_events_sample if evt['course_id'] == course_id and evt['date'] == date_str), None)
    material_url_for_session = session_event_data.get('material_url') if session_event_data else None
    user_display_info = { "name": session.get('full_name') }
    return render_template('notes_template.html', course=course, note_date=date_str, 
                           user=user_display_info, material_url=material_url_for_session)


@app.route('/student/notes/<course_id>') 
def student_course_notes_overview(course_id):
    if not session.get('logged_in') or session.get('role') != 'student':
        flash('Vui lòng đăng nhập với tư cách sinh viên.', 'warning')
        return redirect(url_for('login'))
    course = next((c for c in student_courses_sample if c["id"] == course_id), None)
    if not course:
        flash('Không tìm thấy môn học.', 'danger')
        return redirect(url_for('student_dashboard'))
    
    # Chỉ lấy các buổi học của sinh viên hiện tại (nếu là Khang) cho môn này
    current_student_username = session.get('username')
    course_sessions_for_display = []
    if current_student_username == "khang.2302700102@st.umt.edu.vn":
        course_sessions_for_display = [
            session_event for session_event in raw_student_calendar_events_sample 
            if session_event['course_id'] == course_id
        ]
        course_sessions_for_display.sort(key=lambda x: datetime.datetime.strptime(x['date'], '%Y-%m-%d'))
    # else:
        # Xử lý cho các sinh viên khác nếu họ có cách xem ghi chú khác

    user_display_info = { "name": session.get('full_name') }
    return render_template('course_notes_overview.html', course=course, 
                           sessions=course_sessions_for_display, user=user_display_info)


@app.route('/student/materials/<course_id>/<event_date>') 
def get_student_materials(course_id, event_date):
    if not session.get('logged_in') or session.get('role') != 'student':
        return {"error": "Unauthorized"}, 401
    
    session_event_data = next((evt for evt in raw_student_calendar_events_sample 
                               if evt['course_id'] == course_id and evt['date'] == event_date), None)
    
    course = next((c for c in student_courses_sample if c["id"] == course_id), None)
    if not course: return {"error": "Course not found"}, 404

    materials = []
    if session_event_data and session_event_data.get('material_url'):
        material_name = session_event_data.get('material_url').split('/')[-1] if session_event_data.get('material_url') else "Tài liệu buổi học"
        materials.append(f"Tài liệu chính: {material_name}")
    else:
        materials.append(f"Slide {course['name']} - Buổi {event_date}.pdf (Chưa có)")
    materials.append(f"Bài tập {event_date}.docx (Mẫu)")
    
    return {"course_name": course['name'], "event_date": event_date, "materials": materials}


@app.route('/faculty/dashboard')
def faculty_dashboard():
    if not session.get('logged_in') or session.get('role') != 'faculty':
        flash('Vui lòng đăng nhập với tư cách giảng viên.', 'warning')
        return redirect(url_for('login'))
    
    faculty_username = session.get('username')
    faculty_data = FACULTY_ACCOUNTS.get(faculty_username)
    
    taught_course_ids = faculty_data.get('courses_taught', []) if faculty_data else []
    
    faculty_display_courses = [
        course for course in student_courses_sample if course['id'] in taught_course_ids
    ]

    faculty_display_info = {"name": session.get('full_name'), "department": session.get('department')}
    return render_template('faculty_dashboard.html', faculty_user=faculty_display_info,
                           faculty_courses=faculty_display_courses, 
                           teaching_schedule=teaching_schedule_sample) # Đảm bảo biến này được truyền


@app.route('/faculty/course_sessions/<course_id>')
def faculty_course_sessions(course_id):
    if not session.get('logged_in') or session.get('role') != 'faculty':
        flash('Vui lòng đăng nhập.', 'warning')
        return redirect(url_for('login'))

    faculty_username = session.get('username')
    faculty_data = FACULTY_ACCOUNTS.get(faculty_username)
    if not faculty_data or course_id not in faculty_data.get('courses_taught', []):
        flash('Bạn không có quyền truy cập môn học này.', 'danger')
        return redirect(url_for('faculty_dashboard'))

    course = next((c for c in student_courses_sample if c["id"] == course_id), None)
    if not course:
        flash('Không tìm thấy môn học.', 'danger')
        return redirect(url_for('faculty_dashboard'))
    
    course_sessions = [
        evt for evt in raw_student_calendar_events_sample if evt['course_id'] == course_id
    ]
    course_sessions.sort(key=lambda x: datetime.datetime.strptime(x['date'], '%Y-%m-%d'))

    return render_template('faculty_course_sessions.html', 
                           course=course, 
                           sessions=course_sessions,
                           faculty_user={"name": session.get('full_name')})


@app.route('/faculty/upload_material/<course_id>/<date_str>', methods=['GET', 'POST'])
def faculty_upload_material(course_id, date_str):
    if not session.get('logged_in') or session.get('role') != 'faculty':
        flash('Vui lòng đăng nhập.', 'warning')
        return redirect(url_for('login'))

    faculty_username = session.get('username')
    faculty_data = FACULTY_ACCOUNTS.get(faculty_username)
    if not faculty_data or course_id not in faculty_data.get('courses_taught', []):
        flash('Bạn không có quyền truy cập môn học này.', 'danger')
        return redirect(url_for('faculty_dashboard'))

    course = next((c for c in student_courses_sample if c["id"] == course_id), None)
    session_event_to_update = None
    # Tìm đúng sự kiện trong raw_student_calendar_events_sample để cập nhật
    for i, evt in enumerate(raw_student_calendar_events_sample):
        if evt['course_id'] == course_id and evt['date'] == date_str:
            session_event_to_update = raw_student_calendar_events_sample[i] # Lấy tham chiếu để cập nhật
            break

    if not course or not session_event_to_update:
        flash('Không tìm thấy môn học hoặc buổi học.', 'danger')
        return redirect(url_for('faculty_dashboard'))

    if request.method == 'POST':
        uploaded_file = request.files.get('material_file') 
        if uploaded_file and uploaded_file.filename != '':
            simulated_filename = uploaded_file.filename 
            
            # Cập nhật trực tiếp vào list (vì session_event_to_update là tham chiếu)
            session_event_to_update['material_url'] = f"/uploads/simulated/{simulated_filename}" 
            
            flash(f'Đã "tải lên" tài liệu "{simulated_filename}" cho buổi học ngày {date_str}.', 'success')
            return redirect(url_for('faculty_course_sessions', course_id=course_id))
        else:
            flash('Vui lòng chọn một file để tải lên.', 'warning')

    return render_template('faculty_upload_material.html', 
                           course=course, 
                           session_event=session_event_to_update, # Truyền sự kiện đã tìm thấy
                           faculty_user={"name": session.get('full_name')})


if __name__ == '__main__':
    app.run(debug=True)
