# app.py
from flask import Flask, render_template, redirect, url_for, request, session, flash, send_from_directory
import datetime
import os
from werkzeug.utils import secure_filename # Để xử lý tên file an toàn

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Cấu hình thư mục upload
UPLOAD_FOLDER = 'uploads' # Tạo thư mục này trong cùng cấp với app.py
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Hàm kiểm tra đuôi file cho phép
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Dữ liệu Người dùng Mẫu CỐ ĐỊNH ---
STUDENT_ACCOUNTS = {
    "khang.2302700102@st.umt.edu.vn": {"password": "123", "full_name": "Nguyễn Văn Khang", "major": "Công nghệ thông tin"},
    "minh.2301122334@st.umt.edu.vn": {"password": "123", "full_name": "Trần Thị Minh", "major": "Quản trị Kinh doanh"},
}
FACULTY_ACCOUNTS = {
    "gv_phutrung.hl": {"password": "123", "full_name": "Huỳnh Lê Phú Trung", "department": "Khoa CNTT", "courses_taught": ["BIT104V1", "BIT115V1"]},
    "gv_nhon.dv": {"password": "123", "full_name": "Đỗ Văn Nhơn", "department": "Khoa CNTT", "courses_taught": ["BIT115V1"]},
    "gv_phuc.dv": {"password": "123", "full_name": "Đoàn Văn Phúc", "department": "Khoa KHXH", "courses_taught": ["BIT104V1"]},
    "gv_huy.ht": {"password": "123", "full_name": "Hà Triệu Huy", "department": "Khoa Lý luận Chính trị", "courses_taught": ["GED102V1"]},
    "gv_van.thq": {"password": "123", "full_name": "Trần Hữu Quốc Văn", "department": "Khoa CNTT", "courses_taught": ["BIT114V1"]},
    "gv_tien.dm": {"password": "123", "full_name": "Đỗ Minh Tiến", "department": "Khoa CNTT", "courses_taught": ["BIT110V1"]},
    "gv_van.vtt": {"password": "123", "full_name": "Võ Thị Thanh Vân", "department": "Khoa CNTT", "courses_taught": ["BIT114V1"]},
    "gv_hang.vtm": {"password": "123", "full_name": "Vũ Thị Mỹ Hằng", "department": "Khoa CNTT", "courses_taught": ["BIT110V1"]},
    "gv_khang.2302700102": {"password": "123", "full_name": "Nguyễn Văn Khang (GV Demo)", "department": "Khoa CNTT", "courses_taught": ["CS101", "MA101"]}
}

# --- Dữ liệu Môn học ---
student_courses_sample = [
    {"id": "BIT104V1", "name": "Introduction To Mathematical Analysis", "code": "BIT104V1", "schedule": "Thứ 2 & Thứ 6", "credits": 3},
    {"id": "BIT115V1", "name": "Introduction to Artificial Intelligence", "code": "BIT115V1", "schedule": "Thứ 2 & Thứ 5", "credits": 3},
    {"id": "BIT114V1", "name": "Introduction to Software engineering", "code": "BIT114V1", "schedule": "Thứ 2 & Thứ 5", "credits": 3},
    {"id": "BIT110V1", "name": "Introduction to Operating systems", "code": "BIT110V1", "schedule": "Thứ 5 & Thứ 6", "credits": 3},
    {"id": "GED102V1", "name": "Scientific Socialism", "code": "GED102V1", "schedule": "Thứ 7", "credits": 2},
    {"id": "CS101", "name": "Nhập môn Lập trình (cũ)", "code": "CS101", "schedule": "N/A", "credits": 3},
    {"id": "MA101", "name": "Toán cao cấp A1 (cũ)", "code": "MA101", "schedule": "N/A", "credits": 3},
]

teaching_schedule_sample = [
    {"course_name": "Introduction To Mathematical Analysis", "date": "Thứ 2, 12/05/2025", "time": "07:00 - 09:30", "room": "P.512"},
    {"course_name": "Introduction to Artificial Intelligence", "date": "Thứ 5, 15/05/2025", "time": "07:00 - 09:30", "room": "P.801"},
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
            # Để trống material_url ban đầu, giảng viên sẽ upload
            session_event["material_url"] = None
        sessions.append(session_event)
        event_id_counter += 1
    return sessions

initial_events_data = [
    {"course_id": "BIT104V1", "title_root": "Intro To Mathematical Analysis", "course_code": "BIT104V1", "date_offset_days": 0, "start_time": "07:00", "end_time": "09:30", "lecturer": "Huỳnh Lê Phú Trung", "location": "P.512, Tòa nhà Sáng tạo", "eventType": "LAB-1", "credits": 3},
    {"course_id": "BIT115V1", "title_root": "Intro to Artificial Intelligence", "course_code": "BIT115V1", "date_offset_days": 0, "start_time": "09:50", "end_time": "12:20", "lecturer": "Huỳnh Lê Phú Trung", "location": "P.501, Tòa nhà Sáng tạo", "eventType": "LAB-1", "credits": 3},
    {"course_id": "BIT114V1", "title_root": "Intro to Software engineering", "course_code": "BIT114V1", "date_offset_days": 0, "start_time": "13:50", "end_time": "16:40", "lecturer": "Võ Thị Thanh Vân", "location": "P.506, Tòa nhà Sáng tạo", "eventType": "LEC", "credits": 3},
    {"course_id": "BIT115V1", "title_root": "Intro to Artificial Intelligence", "course_code": "BIT115V1", "date_offset_days": 3, "start_time": "07:00", "end_time": "09:30", "lecturer": "Đỗ Văn Nhơn", "location": "P.801, Tòa nhà Sáng tạo", "eventType": "LEC", "credits": 3},
    {"course_id": "BIT114V1", "title_root": "Intro to Software engineering", "course_code": "BIT114V1", "date_offset_days": 3, "start_time": "09:50", "end_time": "12:20", "lecturer": "Trần Hữu Quốc Văn", "location": "P.A03, Tòa nhà Sáng tạo", "eventType": "LAB-2", "credits": 3},
    {"course_id": "BIT110V1", "title_root": "Intro to Operating systems", "course_code": "BIT110V1", "date_offset_days": 3, "start_time": "13:50", "end_time": "16:40", "lecturer": "Vũ Thị Mỹ Hằng", "location": "P.A02, Tòa nhà Sáng tạo", "eventType": "LEC", "credits": 3},
    {"course_id": "BIT104V1", "title_root": "Intro To Mathematical Analysis", "course_code": "BIT104V1", "date_offset_days": 4, "start_time": "07:00", "end_time": "09:30", "lecturer": "Đoàn Văn Phúc", "location": "P.404, Tòa nhà Sáng tạo", "eventType": "LEC", "credits": 3},
    {"course_id": "BIT110V1", "title_root": "Intro to Operating systems", "course_code": "BIT110V1", "date_offset_days": 4, "start_time": "09:30", "end_time": "12:00", "lecturer": "Đỗ Minh Tiến", "location": "P.512, Tòa nhà Sáng tạo", "eventType": "LAB-1", "credits": 3},
    {"course_id": "GED102V1", "title_root": "Scientific Socialism", "course_code": "GED102V1", "date_offset_days": 5, "start_time": "07:00", "end_time": "09:30", "lecturer": "Hà Triệu Huy", "location": "P.801, Tòa nhà Sáng tạo", "eventType": "LEC", "credits": 2},
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
    # ... (logic đăng nhập giữ nguyên) ...
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
    # ... (logic giữ nguyên) ...
    if not session.get('logged_in') or session.get('role') != 'student':
        flash('Vui lòng đăng nhập với tư cách sinh viên.', 'warning')
        return redirect(url_for('login'))
    
    processed_student_calendar_events = []
    current_student_username = session.get('username')
    
    if current_student_username == "khang.2302700102@st.umt.edu.vn":
        for event_data in raw_student_calendar_events_sample:
            event = event_data.copy()
            event['notes_link'] = url_for('student_session_note', course_id=event['course_id'], date_str=event['date'])
            processed_student_calendar_events.append(event)

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
        display_courses = [course for course in student_courses_sample if course['id'] not in ["CS101", "MA101", "EN101"]] 


    return render_template('index.html', user=user_display_info, courses=display_courses,
                           reviews=upcoming_reviews, calendar_events=processed_student_calendar_events,
                           upcoming_events_dashboard=upcoming_events_dashboard)

@app.route('/student/notes/<course_id>/<date_str>')
def student_session_note(course_id, date_str):
    # ... (logic giữ nguyên) ...
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
    # ... (logic giữ nguyên) ...
    if not session.get('logged_in') or session.get('role') != 'student':
        flash('Vui lòng đăng nhập với tư cách sinh viên.', 'warning')
        return redirect(url_for('login'))
    course = next((c for c in student_courses_sample if c["id"] == course_id), None)
    if not course:
        flash('Không tìm thấy môn học.', 'danger')
        return redirect(url_for('student_dashboard'))
    
    current_student_username = session.get('username')
    course_sessions_for_display = []
    if current_student_username == "khang.2302700102@st.umt.edu.vn":
        course_sessions_for_display = [
            session_event for session_event in raw_student_calendar_events_sample 
            if session_event['course_id'] == course_id
        ]
        course_sessions_for_display.sort(key=lambda x: datetime.datetime.strptime(x['date'], '%Y-%m-%d'))

    user_display_info = { "name": session.get('full_name') }
    return render_template('course_notes_overview.html', course=course, 
                           sessions=course_sessions_for_display, user=user_display_info)

@app.route('/student/materials/<course_id>/<event_date>')
def get_student_materials(course_id, event_date):
    # ... (logic giữ nguyên) ...
    if not session.get('logged_in') or session.get('role') != 'student':
        return {"error": "Unauthorized"}, 401
    session_event_data = next((evt for evt in raw_student_calendar_events_sample 
                               if evt['course_id'] == course_id and evt['date'] == event_date), None)
    course = next((c for c in student_courses_sample if c["id"] == course_id), None)
    if not course: return {"error": "Course not found"}, 404
    materials = []
    if session_event_data and session_event_data.get('material_url'):
        # Nếu là URL giả lập đã upload, trỏ đến route /uploads
        if session_event_data['material_url'].startswith('/uploads/simulated/'):
             material_name = session_event_data['material_url'].split('/')[-1]
             materials.append(f"Tài liệu: {material_name} (Nhấp vào để xem/tải)") # Sinh viên sẽ nhấp vào link trong iframe
        elif session_event_data['material_url'].startswith('http'): # Link ngoài
             materials.append(f"Link tài liệu: {session_event_data['material_url']}")
        else: # Trường hợp khác (có thể là tên file cũ hoặc placeholder)
             materials.append(f"Tài liệu: {session_event_data['material_url']}")
    else:
        materials.append(f"Slide {course['name']} - Buổi {event_date}.pdf (Chưa có)")
    return {"course_name": course['name'], "event_date": event_date, "materials": materials}

@app.route('/faculty/dashboard')
def faculty_dashboard():
    # ... (logic giữ nguyên) ...
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
                           teaching_schedule=teaching_schedule_sample) 

@app.route('/faculty/course_sessions/<course_id>')
def faculty_course_sessions(course_id):
    # ... (logic giữ nguyên) ...
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
    session_event_to_update_index = -1
    for i, evt in enumerate(raw_student_calendar_events_sample):
        if evt['course_id'] == course_id and evt['date'] == date_str:
            session_event_to_update_index = i
            break
    
    if not course or session_event_to_update_index == -1:
        flash('Không tìm thấy môn học hoặc buổi học.', 'danger')
        return redirect(url_for('faculty_dashboard'))

    session_event_to_update = raw_student_calendar_events_sample[session_event_to_update_index]

    if request.method == 'POST':
        if 'material_file' not in request.files:
            flash('Không có phần file trong request.', 'warning')
            return redirect(request.url)
        file = request.files['material_file']
        if file.filename == '':
            flash('Chưa chọn file nào.', 'warning')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            # Tạo tên file mới để tránh trùng lặp và dễ quản lý
            # Create a new filename to avoid conflicts and for easier management
            # Ví dụ: CS101_2025-05-12_original_filename.pdf
            new_filename = f"{course_id}_{date_str}_{original_filename}"
            
            # Tạo đường dẫn đầy đủ để lưu file
            # Create the full path to save the file
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
            
            try:
                # Tạo thư mục uploads nếu chưa có
                # Create the uploads directory if it doesn't exist
                if not os.path.exists(app.config['UPLOAD_FOLDER']):
                    os.makedirs(app.config['UPLOAD_FOLDER'])
                file.save(file_path)
                
                # Cập nhật material_url trong raw_student_calendar_events_sample
                # Update material_url in raw_student_calendar_events_sample
                # URL sẽ là đường dẫn để route /uploads/ phục vụ
                # The URL will be the path for the /uploads/ route to serve
                raw_student_calendar_events_sample[session_event_to_update_index]['material_url'] = url_for('serve_uploaded_file', filename=new_filename)
                
                flash(f'Đã tải lên tài liệu "{original_filename}" thành công!', 'success')
                return redirect(url_for('faculty_course_sessions', course_id=course_id))
            except Exception as e:
                flash(f'Lỗi khi lưu file: {e}', 'danger')
                return redirect(request.url)
        else:
            flash('Loại file không được phép.', 'warning')
            return redirect(request.url)

    return render_template('faculty_upload_material.html', 
                           course=course, 
                           session_event=session_event_to_update, 
                           faculty_user={"name": session.get('full_name')})

# ROUTE MỚI ĐỂ PHỤC VỤ FILE TỪ THƯ MỤC UPLOADS
# NEW ROUTE TO SERVE FILES FROM THE UPLOADS DIRECTORY
@app.route('/uploads/<path:filename>')
def serve_uploaded_file(filename):
    """
    Phục vụ file từ thư mục UPLOAD_FOLDER.
    Serves files from the UPLOAD_FOLDER directory.
    """
    if not session.get('logged_in'): # Kiểm tra đăng nhập cơ bản
        flash('Vui lòng đăng nhập để xem tài liệu.', 'warning')
        return redirect(url_for('login'))
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        flash('Không tìm thấy tài liệu.', 'danger')
        # Có thể chuyển hướng về trang trước đó hoặc trang lỗi thân thiện hơn
        # Could redirect to the previous page or a more user-friendly error page
        return "File not found", 404


if __name__ == '__main__':
    # Tạo thư mục uploads nếu chưa có
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
