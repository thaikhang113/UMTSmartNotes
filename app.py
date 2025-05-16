from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.utils import secure_filename
# Bỏ qua werkzeug.security nếu không dùng hash ngay bây giờ, nhưng nên giữ lại để sau này nâng cấp
# from werkzeug.security import generate_password_hash, check_password_hash
import os
import datetime
import mysql.connector
from mysql.connector import Error
from functools import wraps
import json

app = Flask(__name__)
app.secret_key = 'your_very_secret_key_here_CHANGE_ME_AND_KEEP_IT_SECRET' # THAY ĐỔI KEY NÀY!
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "Khag12344@" # Mật khẩu MySQL của bạn
DB_NAME = "umtsmartnotes"

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset='utf8mb4'
        )
        if conn.is_connected():
            app.logger.info("Successfully connected to the database.")
            return conn
        else:
            app.logger.error("Failed to connect to the database (is_connected is False).")
            flash("Không thể kết nối đến cơ sở dữ liệu.", "danger")
            return None
    except Error as e:
        app.logger.error(f"Lỗi kết nối đến MySQL: {e}")
        flash(f"Lỗi kết nối cơ sở dữ liệu. Vui lòng thử lại sau hoặc liên hệ quản trị viên.", "danger")
        return None

class User:
    def __init__(self, id, username, role, full_name=None, major=None, department=None):
        self.id = id
        self.username = username
        self.role = role
        self.full_name = full_name
        self.major = major
        self.department = department
        self.is_active = True

    def get_id(self):
        return str(self.id)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

def login_user_session(user):
    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role
    session['full_name'] = user.full_name
    session['major'] = user.major
    session['department'] = user.department

def logout_user_session():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('role', None)
    session.pop('full_name', None)
    session.pop('major', None)
    session.pop('department', None)

@app.context_processor
def inject_user():
    if 'user_id' in session and 'username' in session and 'role' in session:
        return {'current_user': User(
            session['user_id'],
            session['username'],
            session['role'],
            session.get('full_name'),
            session.get('major'),
            session.get('department')
        )}
    return {'current_user': None}

def get_current_user_object():
    if 'user_id' in session and 'username' in session and 'role' in session:
        return User(
            session['user_id'],
            session['username'],
            session['role'],
            session.get('full_name'),
            session.get('major'),
            session.get('department')
        )
    return None

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_user = get_current_user_object()
            if not current_user:
                flash("Vui lòng đăng nhập để truy cập trang này.", "warning")
                return redirect(url_for('login', next=request.url))
            if role and current_user.role != role:
                flash(f"Bạn không có quyền truy cập vào trang này. Cần vai trò: {role}.", "danger")
                if current_user.role == 'student':
                    return redirect(url_for('student_dashboard'))
                elif current_user.role == 'faculty':
                    return redirect(url_for('faculty_dashboard'))
                else:
                    return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.template_filter('format_date_display')
def format_date_display_filter(value, format_str='%d/%m/%Y'):
    if not value:
        return ""
    try:
        if isinstance(value, (datetime.date, datetime.datetime)):
            return value.strftime(format_str)
        for fmt in ('%Y-%m-%d', '%Y-%m-%d %H:%M:%S'):
            try:
                date_obj = datetime.datetime.strptime(str(value), fmt)
                return date_obj.strftime(format_str)
            except ValueError:
                continue
        app.logger.warning(f"Không thể định dạng ngày: {value} với các định dạng đã biết.")
        return str(value)
    except Exception as e:
        app.logger.warning(f"Lỗi không xác định khi định dạng ngày: {value}, Lỗi: {e}")
        return str(value)

@app.route('/login', methods=['GET', 'POST'])
def login():
    current_user = get_current_user_object()
    if current_user:
        if current_user.role == 'student':
            return redirect(url_for('student_dashboard'))
        elif current_user.role == 'faculty':
            return redirect(url_for('faculty_dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password_input = request.form['password'] # Mật khẩu người dùng nhập
        role = request.form['role']

        conn = get_db_connection()
        if not conn:
            return render_template('login.html')

        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            # Lấy cột 'password' (văn bản thô) từ CSDL
            query = "SELECT id, username, password, role, full_name, major, department FROM users WHERE username = %s AND role = %s"
            cursor.execute(query, (username, role))
            user_data = cursor.fetchone()

            app.logger.debug(f"Login attempt for user: {username}, role: {role}")
            app.logger.debug(f"User data from DB: {user_data}")


            # So sánh trực tiếp mật khẩu (KHÔNG AN TOÀN)
            if user_data and user_data.get('password') == password_input:
                app.logger.info(f"Password match for user: {username}")
                user_obj = User(
                    user_data['id'],
                    user_data['username'],
                    user_data['role'],
                    user_data.get('full_name'),
                    user_data.get('major'),
                    user_data.get('department')
                )
                login_user_session(user_obj)
                flash('Đăng nhập thành công!', 'success')
                if role == 'student':
                    return redirect(url_for('student_dashboard'))
                elif role == 'faculty':
                    return redirect(url_for('faculty_dashboard'))
            else:
                app.logger.warning(f"Password mismatch or user not found for: {username}")
                flash('Tên đăng nhập, mật khẩu hoặc vai trò không đúng.', 'danger')
        except Error as e:
            app.logger.error(f"Lỗi truy vấn CSDL khi đăng nhập cho người dùng {username}: {e}")
            flash("Lỗi truy vấn cơ sở dữ liệu khi đăng nhập. Vui lòng thử lại.", "danger")
        except Exception as e:
            app.logger.error(f"Lỗi không xác định khi đăng nhập: {e}")
            flash("Đã xảy ra lỗi không mong muốn trong quá trình đăng nhập. Vui lòng thử lại.", "danger")
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
                app.logger.info("Database connection closed after login attempt.")

    return render_template('login.html')

@app.route('/logout')
@login_required()
def logout():
    logout_user_session()
    flash('Bạn đã đăng xuất.', 'info')
    return redirect(url_for('login'))

# --- Student Routes ---
@app.route('/student/dashboard')
@login_required(role='student')
def student_dashboard():
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('login'))

    student_courses = []
    calendar_events_data = []
    quizzes_data_js = {}
    available_quizzes_list = []
    upcoming_events_dashboard = []
    reviews_data = []

    current_user_obj = get_current_user_object()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        query_courses = """
            SELECT c.id, c.course_code, c.course_name, c.credits
            FROM courses c
            JOIN enrollments e ON c.id = e.course_id
            WHERE e.student_id = %s
        """
        cursor.execute(query_courses, (current_user_obj.id,))
        student_courses = cursor.fetchall()

        calendar_query = """
            SELECT
                cs.id, cs.session_title as title, cs.session_date as date,
                cs.start_time, cs.end_time,
                cs.course_id, c.course_name, c.course_code,
                cs.lecturer_name, cs.location, cs.event_type,
                cs.quiz_id, q.title as quiz_title
            FROM course_sessions cs
            JOIN courses c ON cs.course_id = c.id
            JOIN enrollments e ON c.id = e.course_id
            LEFT JOIN quizzes q ON cs.quiz_id = q.id AND q.course_id = cs.course_id AND q.session_id = cs.id
            WHERE e.student_id = %s
            ORDER BY cs.session_date, cs.start_time
        """
        cursor.execute(calendar_query, (current_user_obj.id,))
        calendar_events_data = cursor.fetchall()

        for event in calendar_events_data:
            if event.get('quiz_id'):
                if event['quiz_id'] not in quizzes_data_js:
                    quizzes_data_js[event['quiz_id']] = {
                        'id': event['quiz_id'],
                        'title': event.get('quiz_title', f"Quiz cho {event['title']}"),
                        'course_id': event['course_id'],
                        'session_id': event['id']
                    }

        if student_courses:
            enrolled_course_ids = [c['id'] for c in student_courses]
            if enrolled_course_ids: # Kiểm tra nếu list không rỗng
                format_strings = ','.join(['%s'] * len(enrolled_course_ids))
                quiz_available_query = f"""
                    SELECT q.id as quiz_id, q.title, c.course_name, cs.session_date as session_date_str
                    FROM quizzes q
                    JOIN courses c ON q.course_id = c.id
                    LEFT JOIN course_sessions cs ON q.session_id = cs.id
                    WHERE q.course_id IN ({format_strings})
                    ORDER BY c.course_name, cs.session_date, q.title
                """
                cursor.execute(quiz_available_query, tuple(enrolled_course_ids))
                available_quizzes_list = cursor.fetchall()

        today_str = str(datetime.date.today())
        upcoming_events_dashboard = [
            ev for ev in calendar_events_data if str(ev['date']) >= today_str
        ][:2]

    except Error as e:
        app.logger.error(f"Lỗi lấy dữ liệu dashboard cho sinh viên {current_user_obj.id}: {e}")
        flash("Không thể tải dữ liệu bảng điều khiển.", "danger")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template(
        'index.html',
        courses=student_courses,
        calendar_events=calendar_events_data,
        quizzes_data_for_js=quizzes_data_js,
        upcoming_events_dashboard=upcoming_events_dashboard,
        reviews=reviews_data,
        available_quizzes=available_quizzes_list
    )

@app.route('/student/select_session/<int:course_id>')
@login_required(role='student')
def student_select_session(course_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('student_dashboard'))

    course_data = None
    sessions_list = []
    action_type_from_query = request.args.get('action_type', 'notes')
    quizzes_info_for_sessions = {} # Để lưu thông tin quiz cho từng buổi học

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, course_code, course_name FROM courses WHERE id = %s", (course_id,))
        course_data = cursor.fetchone()

        if not course_data:
            flash("Khóa học không tồn tại.", "danger")
            return redirect(url_for('student_dashboard'))

        cursor.execute("SELECT student_id FROM enrollments WHERE student_id = %s AND course_id = %s", (current_user_obj.id, course_id))
        if not cursor.fetchone():
            flash("Bạn chưa ghi danh vào khóa học này.", "warning")
            return redirect(url_for('student_dashboard'))

        query_sessions = """
            SELECT
                cs.id, cs.session_title, cs.session_date,
                cs.start_time, cs.end_time, cs.lecturer_name, cs.location, cs.event_type,
                cs.material_url, cs.quiz_id, q.title as quiz_title,
                (SELECT COUNT(*) FROM questions WHERE quiz_id = q.id) as questions_in_quiz_count
            FROM course_sessions cs
            LEFT JOIN quizzes q ON cs.quiz_id = q.id AND q.course_id = cs.course_id AND q.session_id = cs.id
            WHERE cs.course_id = %s
            ORDER BY cs.session_date DESC, cs.start_time DESC, cs.id DESC
        """
        cursor.execute(query_sessions, (course_id,))
        sessions_list = cursor.fetchall()

        for sess in sessions_list:
            if sess.get('quiz_id'):
                quizzes_info_for_sessions[sess['quiz_id']] = {
                    'title': sess.get('quiz_title'),
                    'questions': sess.get('questions_in_quiz_count', 0)
                }


    except Error as e:
        app.logger.error(f"Lỗi lấy danh sách buổi học cho khóa {course_id} (SV): {e}")
        flash("Không thể tải danh sách buổi học.", "danger")
        return redirect(url_for('student_dashboard'))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('student_select_session.html',
                           course=course_data,
                           sessions=sessions_list,
                           action_type=action_type_from_query,
                           quizzes_data=quizzes_info_for_sessions) # Truyền dữ liệu quiz


@app.route('/student/note/course/<int:course_id>/session_date/<string:date_str>')
@login_required(role='student')
def student_session_note(course_id, date_str):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn: return redirect(url_for('student_dashboard'))

    session_event_info = None
    material_url_for_session = None
    cursor = None

    try:
        # Chuyển đổi date_str sang đối tượng date để query an toàn hơn
        try:
            valid_date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Định dạng ngày không hợp lệ.", "danger")
            return redirect(url_for('student_select_session', course_id=course_id))

        cursor = conn.cursor(dictionary=True)
        query_session = """
            SELECT cs.id, cs.session_title, cs.session_date, cs.material_url,
                   c.course_name, c.id as course_db_id
            FROM course_sessions cs
            JOIN courses c ON cs.course_id = c.id
            WHERE cs.course_id = %s AND DATE(cs.session_date) = %s
            LIMIT 1
        """
        cursor.execute(query_session, (course_id, valid_date_obj))
        session_event_info = cursor.fetchone()

        if not session_event_info:
            flash(f"Không tìm thấy buổi học cho ngày {date_str} của khóa học này.", "warning")
            return redirect(url_for('student_select_session', course_id=course_id))

        cursor.execute("SELECT student_id FROM enrollments WHERE student_id = %s AND course_id = %s",
                       (current_user_obj.id, course_id))
        if not cursor.fetchone():
            flash("Bạn chưa ghi danh vào khóa học này.", "warning")
            return redirect(url_for('student_dashboard'))

        material_url_for_session = session_event_info.get('material_url')

    except Error as e:
        app.logger.error(f"Lỗi CSDL khi lấy thông tin buổi học cho ghi chú: {e}")
        flash("Lỗi tải thông tin buổi học.", "danger")
        return redirect(url_for('student_select_session', course_id=course_id))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    course_context = {'id': course_id, 'name': session_event_info.get('course_name')}
    note_date_context = session_event_info.get('session_date')

    return render_template('notes_template.html',
                           course=course_context,
                           note_date=note_date_context, # Đây là datetime.date object
                           material_url=material_url_for_session,
                           session_event=session_event_info
                           )

# --- Faculty Routes ---
@app.route('/faculty/dashboard')
@login_required(role='faculty')
def faculty_dashboard():
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('login'))

    faculty_courses_data = []
    teaching_schedule_data = []

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        query_main_courses = "SELECT id, course_code, course_name, credits FROM courses WHERE faculty_id = %s"
        cursor.execute(query_main_courses, (current_user_obj.id,))
        faculty_courses_data = cursor.fetchall()

        query_teaching_schedule = """
            SELECT cs.id, cs.session_title, cs.session_date, cs.start_time, cs.end_time,
                   c.course_name, cs.location
            FROM course_sessions cs
            JOIN courses c ON cs.course_id = c.id
            WHERE (c.faculty_id = %s OR cs.lecturer_name = %s) AND cs.session_date >= CURDATE()
            ORDER BY cs.session_date, cs.start_time
            LIMIT 2
        """
        cursor.execute(query_teaching_schedule, (current_user_obj.id, current_user_obj.full_name))
        teaching_schedule_data = cursor.fetchall()

    except Error as e:
        app.logger.error(f"Lỗi lấy danh sách khóa học của giảng viên {current_user_obj.id}: {e}")
        flash("Không thể tải danh sách khóa học.", "danger")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('faculty_dashboard.html',
                           faculty_user=current_user_obj,
                           faculty_courses=faculty_courses_data,
                           teaching_schedule=teaching_schedule_data)


@app.route('/faculty/course_sessions/<int:course_id>', methods=['GET', 'POST'])
@login_required(role='faculty')
def faculty_course_sessions(course_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('faculty_dashboard'))

    course_info_data = None
    sessions_list_data = []
    quizzes_data_for_template = {}
    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, course_code, course_name, faculty_id FROM courses WHERE id = %s", (course_id,))
        course_info_data = cursor.fetchone()

        if not course_info_data:
            flash("Khóa học không tồn tại.", "danger")
            return redirect(url_for('faculty_dashboard'))

        is_main_faculty = (course_info_data['faculty_id'] == current_user_obj.id)
        cursor.execute("SELECT lecturer_name FROM course_sessions WHERE course_id = %s AND lecturer_name = %s LIMIT 1",
                       (course_id, current_user_obj.full_name))
        is_session_lecturer = cursor.fetchone() is not None

        if not (is_main_faculty or is_session_lecturer):
            flash("Bạn không có quyền quản lý buổi học cho khóa này.", "danger")
            return redirect(url_for('faculty_dashboard'))

        if request.method == 'POST':
            session_title = request.form.get('session_title')
            session_date_str = request.form.get('session_date')
            start_time_str = request.form.get('start_time')
            end_time_str = request.form.get('end_time')
            lecturer_name = request.form.get('lecturer_name', current_user_obj.full_name)
            location = request.form.get('location')
            event_type = request.form.get('event_type')
            material_url_form = request.form.get('material_url') # material_url từ form
            quiz_id_form = request.form.get('quiz_id') # quiz_id từ form

            if not all([session_title, session_date_str, start_time_str, end_time_str, lecturer_name, location, event_type]):
                flash("Vui lòng điền đầy đủ thông tin bắt buộc cho buổi học.", "warning")
            else:
                try:
                    session_date = datetime.datetime.strptime(session_date_str, '%Y-%m-%d').date()
                    start_time = datetime.datetime.strptime(start_time_str, '%H:%M').time()
                    end_time = datetime.datetime.strptime(end_time_str, '%H:%M').time()

                    insert_query = """INSERT INTO course_sessions
                                      (course_id, session_title, session_date, start_time, end_time,
                                       lecturer_name, location, event_type, material_url, quiz_id)
                                      VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                    cursor.execute(insert_query, (course_id, session_title, session_date, start_time, end_time,
                                                  lecturer_name, location, event_type,
                                                  material_url_form if material_url_form else None,
                                                  quiz_id_form if quiz_id_form else None))
                    conn.commit()
                    flash("Buổi học đã được tạo thành công!", "success")
                except ValueError:
                    flash("Định dạng ngày hoặc giờ không hợp lệ. Vui lòng sử dụng YYYY-MM-DD cho ngày và HH:MM cho giờ.", "danger")
                except Error as e:
                    app.logger.error(f"Lỗi tạo buổi học cho khóa {course_id}: {e}")
                    flash(f"Lỗi khi tạo buổi học: {e}", "danger")
                    if conn.is_connected(): conn.rollback()
            return redirect(url_for('faculty_course_sessions', course_id=course_id))

        query_sessions = """
            SELECT cs.id, cs.session_title, cs.session_date, cs.start_time, cs.end_time,
                   cs.lecturer_name, cs.location, cs.event_type, cs.material_url,
                   cs.quiz_id, q.title as quiz_title, (SELECT COUNT(*) FROM questions WHERE quiz_id = cs.quiz_id) as question_count
            FROM course_sessions cs
            LEFT JOIN quizzes q ON cs.quiz_id = q.id WHERE cs.course_id = %s
            ORDER BY cs.session_date DESC, cs.start_time DESC, cs.id DESC
        """
        cursor.execute(query_sessions, (course_id,))
        sessions_list_data = cursor.fetchall()

        for session_item in sessions_list_data:
            if session_item.get('quiz_id'): # Kiểm tra xem có quiz_id không
                quizzes_data_for_template[session_item['quiz_id']] = {
                    'title': session_item.get('quiz_title'),
                    'questions_count': session_item.get('question_count', 0)
                }
    except Error as e:
        app.logger.error(f"Lỗi CSDL trong faculty_course_sessions cho khóa {course_id}: {e}")
        flash(f"Lỗi cơ sở dữ liệu: {e}", "danger")
        return redirect(url_for('faculty_dashboard'))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('faculty_course_sessions.html',
                           course=course_info_data,
                           sessions=sessions_list_data,
                           quizzes_data=quizzes_data_for_template)


@app.route('/faculty/upload_material/course/<int:course_id>/session_date/<string:date_str>', methods=['GET', 'POST'])
@login_required(role='faculty')
def faculty_upload_material(course_id, date_str):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('faculty_dashboard'))

    course_info_data = None
    session_event_info_data = None
    cursor = None

    try:
        # Chuyển đổi date_str sang đối tượng date để query an toàn hơn
        try:
            valid_date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Định dạng ngày không hợp lệ.", "danger")
            return redirect(url_for('faculty_course_sessions', course_id=course_id))


        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, course_code, course_name, faculty_id FROM courses WHERE id = %s", (course_id,))
        course_info_data = cursor.fetchone()
        if not course_info_data:
            flash("Khóa học không tồn tại.", "danger")
            return redirect(url_for('faculty_dashboard'))

        cursor.execute("""
            SELECT id, session_title, session_date, lecturer_name, material_url
            FROM course_sessions
            WHERE course_id = %s AND DATE(session_date) = %s
            LIMIT 1
        """, (course_id, valid_date_obj))
        session_event_info_data = cursor.fetchone()

        if not session_event_info_data:
            flash(f"Không tìm thấy buổi học cho ngày {date_str} của khóa {course_info_data['course_name']}.", "warning")
            return redirect(url_for('faculty_course_sessions', course_id=course_id))

        is_main_faculty = (course_info_data['faculty_id'] == current_user_obj.id)
        is_session_lecturer = (session_event_info_data['lecturer_name'] == current_user_obj.full_name)
        if not (is_main_faculty or is_session_lecturer):
            flash("Bạn không có quyền tải lên tài liệu cho buổi học này.", "danger")
            return redirect(url_for('faculty_course_sessions', course_id=course_id))

        if request.method == 'POST':
            if 'material_file' not in request.files:
                flash('Không có tệp nào được chọn.', 'warning')
                return redirect(request.url)
            file = request.files['material_file']
            if file.filename == '':
                flash('Không có tệp nào được chọn.', 'warning')
                return redirect(request.url)

            if file:
                filename = secure_filename(file.filename)
                session_upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'course_materials', str(course_id), date_str)
                if not os.path.exists(session_upload_folder):
                    os.makedirs(session_upload_folder, exist_ok=True)

                file_path_on_server = os.path.join(session_upload_folder, filename)
                db_file_path = os.path.join('course_materials', str(course_id), date_str, filename).replace("\\", "/")

                try:
                    file.save(file_path_on_server)
                    update_session_query = "UPDATE course_sessions SET material_url = %s WHERE id = %s"
                    cursor.execute(update_session_query, (db_file_path, session_event_info_data['id']))
                    conn.commit()
                    flash(f"Tệp '{filename}' đã được tải lên và liên kết với buổi học.", 'success')
                    session_event_info_data['material_url'] = db_file_path
                except Error as e:
                    app.logger.error(f"Lỗi CSDL khi lưu tài liệu: {e}")
                    flash("Lỗi khi lưu thông tin tệp vào cơ sở dữ liệu.", "danger")
                    if conn.is_connected(): conn.rollback()
                except Exception as e:
                    app.logger.error(f"Lỗi lưu file: {e}")
                    flash(f"Lỗi khi lưu tệp: {e}", "danger")
                return redirect(url_for('faculty_upload_material', course_id=course_id, date_str=date_str))

    except Error as e:
        app.logger.error(f"Lỗi CSDL trong faculty_upload_material: {e}")
        flash(f"Lỗi cơ sở dữ liệu: {e}", "danger")
        return redirect(url_for('faculty_course_sessions', course_id=course_id))
    except Exception as e:
        app.logger.error(f"Lỗi không xác định trong faculty_upload_material: {e}")
        flash("Đã có lỗi không xác định xảy ra.", "danger")
        return redirect(url_for('faculty_dashboard'))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('faculty_upload_material.html',
                           course=course_info_data,
                           session_event=session_event_info_data)


@app.route('/download_material_path/<path:file_path_in_db>')
@login_required()
def download_material_by_path(file_path_in_db):
    current_user = get_current_user_object() # Lấy user hiện tại
    # Kiểm tra sơ bộ quyền (cần logic chi tiết hơn dựa trên vai trò và ghi danh/phụ trách)
    # Ví dụ: Sinh viên chỉ được tải tài liệu của môn mình học, giảng viên chỉ của môn mình dạy.
    # Hiện tại, chỉ kiểm tra đăng nhập.
    if not current_user:
        flash("Vui lòng đăng nhập để tải tài liệu.", "warning")
        return redirect(url_for('login'))

    # Bảo vệ chống path traversal cơ bản
    if ".." in file_path_in_db or file_path_in_db.startswith("/"):
        flash("Đường dẫn tài liệu không hợp lệ.", "danger")
        return redirect(url_for('index')) # Hoặc một trang lỗi chung

    # Giả định file_path_in_db là đường dẫn tương đối từ thư mục UPLOAD_FOLDER
    # Ví dụ: 'course_materials/1/2025-05-12/dummy.pdf'
    full_path_to_file = os.path.join(app.config['UPLOAD_FOLDER'], file_path_in_db)
    app.logger.info(f"Attempting to download file from: {full_path_to_file}")


    if not os.path.exists(full_path_to_file) or not os.path.isfile(full_path_to_file):
        app.logger.error(f"Tệp tài liệu không tìm thấy tại: {full_path_to_file}")
        flash("Tệp tài liệu không tìm thấy trên máy chủ.", "danger")
        default_redirect = url_for('student_dashboard') if current_user.role == 'student' else url_for('faculty_dashboard')
        return redirect(request.referrer or default_redirect)

    try:
        # Tách thư mục và tên file cho send_from_directory
        directory_for_send = os.path.dirname(full_path_to_file)
        filename_for_send = os.path.basename(full_path_to_file)
        return send_from_directory(directory=directory_for_send, path=filename_for_send, as_attachment=True)
    except Exception as e:
        app.logger.error(f"Lỗi khi gửi tệp {file_path_in_db}: {e}")
        flash("Lỗi khi tải tài liệu.", "danger")
        default_redirect = url_for('student_dashboard') if current_user.role == 'student' else url_for('faculty_dashboard')
        return redirect(request.referrer or default_redirect)

# --- Quiz Routes ---
@app.route('/faculty/manage_quiz/course/<int:course_id>/session_date/<string:date_str>', methods=['GET', 'POST'])
@login_required(role='faculty')
def faculty_manage_quiz(course_id, date_str):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn: return redirect(url_for('faculty_dashboard'))

    course_info_data = None
    session_event_info_data = None
    quiz_data_for_form = None
    cursor = None

    try:
        # Chuyển đổi date_str sang đối tượng date để query an toàn hơn
        try:
            valid_date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Định dạng ngày không hợp lệ.", "danger")
            return redirect(url_for('faculty_course_sessions', course_id=course_id))

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, course_code, course_name, faculty_id FROM courses WHERE id = %s", (course_id,))
        course_info_data = cursor.fetchone()
        if not course_info_data:
            flash("Khóa học không tồn tại.", "danger")
            return redirect(url_for('faculty_dashboard'))

        cursor.execute("""
            SELECT id, session_title, session_date, lecturer_name, quiz_id
            FROM course_sessions
            WHERE course_id = %s AND DATE(session_date) = %s
            LIMIT 1
        """, (course_id, valid_date_obj))
        session_event_info_data = cursor.fetchone()
        if not session_event_info_data:
            flash(f"Không tìm thấy buổi học ngày {date_str} cho khóa {course_info_data['course_name']}.", "warning")
            return redirect(url_for('faculty_course_sessions', course_id=course_id))

        is_main_faculty = (course_info_data['faculty_id'] == current_user_obj.id)
        is_session_lecturer = (session_event_info_data['lecturer_name'] == current_user_obj.full_name)
        if not (is_main_faculty or is_session_lecturer):
            flash("Bạn không có quyền quản lý quiz cho buổi học này.", "danger")
            return redirect(url_for('faculty_course_sessions', course_id=course_id))

        current_quiz_id = session_event_info_data.get('quiz_id')
        if current_quiz_id:
            cursor.execute("SELECT id, title FROM quizzes WHERE id = %s", (current_quiz_id,))
            quiz_header = cursor.fetchone()
            if quiz_header:
                quiz_data_for_form = {'id': quiz_header['id'], 'title': quiz_header['title'], 'questions': []}
                cursor.execute("SELECT id, question_text, question_type, options, correct_answer FROM questions WHERE quiz_id = %s ORDER BY id", (current_quiz_id,))
                questions_db = cursor.fetchall()
                for q_db in questions_db:
                    options_list = []
                    if q_db['options']:
                        try:
                            options_list = json.loads(q_db['options'])
                        except json.JSONDecodeError: app.logger.warning(f"Lỗi decode JSON options cho câu hỏi {q_db['id']}")
                    quiz_data_for_form['questions'].append({
                        'id': q_db['id'],
                        'text': q_db['question_text'],
                        'type': q_db['question_type'],
                        'options': options_list,
                        'correct_answer': q_db['correct_answer']
                    })

        if request.method == 'POST':
            quiz_title_form = request.form.get('quiz_title', f"Quiz: {session_event_info_data['session_title']}")
            quiz_id_to_use = current_quiz_id

            conn.start_transaction()
            if not quiz_id_to_use:
                insert_quiz_q = "INSERT INTO quizzes (course_id, session_id, title, created_by) VALUES (%s, %s, %s, %s)"
                cursor.execute(insert_quiz_q, (course_id, session_event_info_data['id'], quiz_title_form, current_user_obj.id))
                quiz_id_to_use = cursor.lastrowid
                cursor.execute("UPDATE course_sessions SET quiz_id = %s WHERE id = %s", (quiz_id_to_use, session_event_info_data['id']))
            else:
                update_quiz_q = "UPDATE quizzes SET title = %s WHERE id = %s"
                cursor.execute(update_quiz_q, (quiz_title_form, quiz_id_to_use))

            if quiz_id_to_use:
                 cursor.execute("DELETE FROM questions WHERE quiz_id = %s", (quiz_id_to_use,))

            question_texts = request.form.getlist('question_text[]')
            num_questions_added = 0
            for i, q_text_strip in enumerate(map(str.strip, question_texts)):
                if not q_text_strip: continue
                options_for_this_q_raw = [
                    request.form.get(f'option_{i}_0', ''), request.form.get(f'option_{i}_1', ''),
                    request.form.get(f'option_{i}_2', ''), request.form.get(f'option_{i}_3', '') ]
                options_for_this_q_filtered = [opt.strip() for opt in options_for_this_q_raw if opt.strip()]
                correct_answer_index_str = request.form.get(f'correct_answer_{i}')
                correct_answer_text = None

                if not options_for_this_q_filtered or len(options_for_this_q_filtered) < 2:
                    flash(f"Câu hỏi '{q_text_strip[:30]}...' cần ít nhất 2 lựa chọn. Bỏ qua.", "warning"); continue
                if correct_answer_index_str is not None:
                    try:
                        correct_idx = int(correct_answer_index_str)
                        if 0 <= correct_idx < len(options_for_this_q_filtered):
                            correct_answer_text = options_for_this_q_filtered[correct_idx]
                        else: flash(f"Lựa chọn đáp án đúng không hợp lệ cho '{q_text_strip[:30]}...'. Bỏ qua.", "warning"); continue
                    except ValueError: flash(f"Định dạng đáp án đúng không hợp lệ cho '{q_text_strip[:30]}...'. Bỏ qua.", "warning"); continue
                else: flash(f"Chưa chọn đáp án đúng cho '{q_text_strip[:30]}...'. Bỏ qua.", "warning"); continue

                if q_text_strip and correct_answer_text:
                    q_insert = "INSERT INTO questions (quiz_id, question_text, question_type, options, correct_answer) VALUES (%s, %s, %s, %s, %s)"
                    cursor.execute(q_insert, (quiz_id_to_use, q_text_strip, 'multiple_choice', json.dumps(options_for_this_q_filtered), correct_answer_text))
                    num_questions_added += 1
            conn.commit()
            if num_questions_added > 0: flash(f"Quiz đã được lưu với {num_questions_added} câu hỏi!", "success")
            elif quiz_id_to_use: flash(f"Tiêu đề quiz '{quiz_title_form}' đã được lưu. Chưa có câu hỏi nào.", "info")
            else: flash("Không có thay đổi nào được lưu.", "warning")
            return redirect(url_for('faculty_manage_quiz', course_id=course_id, date_str=date_str))
    except Error as e:
        app.logger.error(f"Lỗi CSDL quản lý quiz: {e}")
        flash("Lỗi tải hoặc lưu trang quản lý quiz.", "danger")
        if conn and conn.is_connected(): conn.rollback()
        return redirect(url_for('faculty_course_sessions', course_id=course_id))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    return render_template('faculty_manage_quiz.html',
                           course=course_info_data,
                           session_event=session_event_info_data,
                           quiz=quiz_data_for_form)

@app.route('/student/take_quiz/<int:quiz_id>')
@login_required(role='student')
def student_take_quiz(quiz_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn: return redirect(url_for('student_dashboard'))
    quiz_info_data = None; questions_list_data = []; session_title_for_display = None; cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT q.id, q.title, q.course_id, q.session_id, c.course_name, cs.session_title
            FROM quizzes q JOIN courses c ON q.course_id = c.id
            LEFT JOIN course_sessions cs ON q.session_id = cs.id AND q.course_id = cs.course_id
            WHERE q.id = %s """, (quiz_id,))
        quiz_info_data = cursor.fetchone()
        if not quiz_info_data: flash("Quiz không tồn tại.", "danger"); return redirect(url_for('student_dashboard'))
        session_title_for_display = quiz_info_data.get('session_title')
        cursor.execute("SELECT student_id FROM enrollments WHERE student_id = %s AND course_id = %s",
                       (current_user_obj.id, quiz_info_data['course_id']))
        if not cursor.fetchone(): flash("Bạn chưa ghi danh vào khóa học của quiz này.", "warning"); return redirect(url_for('student_dashboard'))
        cursor.execute("SELECT id, question_text, question_type, options FROM questions WHERE quiz_id = %s ORDER BY id", (quiz_id,))
        questions_raw = cursor.fetchall()
        for q_item in questions_raw:
            q_item['options_list'] = []
            if q_item['question_type'] == 'multiple_choice' and q_item['options']:
                try:
                    loaded_options = json.loads(q_item['options'])
                    if isinstance(loaded_options, list): q_item['options_list'] = loaded_options
                except (json.JSONDecodeError, TypeError): app.logger.warning(f"Quiz {quiz_id}, Q {q_item['id']}: JSON options error.")
            questions_list_data.append(q_item)
    except Error as e: app.logger.error(f"Lỗi CSDL lấy quiz {quiz_id} cho SV {current_user_obj.id}: {e}"); flash("Lỗi tải quiz.", "danger"); return redirect(url_for('student_dashboard'))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    return render_template('student_take_quiz.html', quiz=quiz_info_data, questions=questions_list_data,
                           course_name=quiz_info_data.get('course_name'), session_title=session_title_for_display, quiz_id=quiz_id)

@app.route('/student/submit_quiz/<int:quiz_id>', methods=['POST'])
@login_required(role='student')
def student_submit_quiz(quiz_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn: flash("Lỗi kết nối CSDL.", "danger"); return redirect(url_for('student_take_quiz', quiz_id=quiz_id))
    cursor = None; attempt_id = None; score_count = 0; total_questions = 0
    try:
        conn.start_transaction(); cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT course_id FROM quizzes WHERE id = %s", (quiz_id,))
        quiz_course = cursor.fetchone()
        if not quiz_course: flash("Quiz không tồn tại.", "danger"); conn.rollback(); return redirect(url_for('student_dashboard'))
        cursor.execute("SELECT student_id FROM enrollments WHERE student_id = %s AND course_id = %s", (current_user_obj.id, quiz_course['course_id']))
        if not cursor.fetchone(): flash("Bạn không được phép làm quiz này.", "warning"); conn.rollback(); return redirect(url_for('student_dashboard'))
        cursor.execute("SELECT id, correct_answer, question_type FROM questions WHERE quiz_id = %s", (quiz_id,))
        db_questions = {q['id']: {'correct': q['correct_answer'], 'type': q['question_type']} for q in cursor.fetchall()}
        total_questions = len(db_questions)
        if total_questions == 0: flash("Quiz này không có câu hỏi.", "warning"); conn.rollback(); return redirect(url_for('student_take_quiz', quiz_id=quiz_id))
        cursor.execute("INSERT INTO quiz_attempts (quiz_id, student_id, score) VALUES (%s, %s, %s)", (quiz_id, current_user_obj.id, 0.0))
        attempt_id = cursor.lastrowid
        form_answers = request.form
        for q_id, q_data in db_questions.items():
            student_answer_val = form_answers.get(f"question_{q_id}")
            is_correct = False
            if student_answer_val is not None:
                norm_stud_ans = student_answer_val.strip().lower()
                norm_corr_ans = q_data['correct'].strip().lower() if q_data.get('correct') else ""
                if norm_stud_ans == norm_corr_ans: is_correct = True; score_count += 1
            cursor.execute("INSERT INTO attempt_answers (attempt_id, question_id, student_answer, is_correct) VALUES (%s, %s, %s, %s)",
                           (attempt_id, q_id, student_answer_val, is_correct))
        final_score = (score_count / total_questions) * 100 if total_questions > 0 else 0.0
        cursor.execute("UPDATE quiz_attempts SET score = %s WHERE id = %s", (final_score, attempt_id))
        conn.commit()
        flash(f"Bài quiz đã nộp! Điểm: {score_count}/{total_questions} ({final_score:.2f}%)", "success")
        return redirect(url_for('student_quiz_results', attempt_id=attempt_id))
    except Error as e: app.logger.error(f"Lỗi CSDL nộp quiz {quiz_id} SV {current_user_obj.id}: {e}"); flash(f"Lỗi nộp bài: {e}", "danger"); conn.rollback()
    except Exception as e: app.logger.error(f"Lỗi không mong muốn nộp quiz {quiz_id} SV {current_user_obj.id}: {e}"); flash(f"Lỗi không mong muốn: {e}", "danger"); conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    return redirect(url_for('student_take_quiz', quiz_id=quiz_id))

@app.route('/student/quiz_results/<int:attempt_id>')
@login_required(role='student')
def student_quiz_results(attempt_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn: return redirect(url_for('student_dashboard'))
    attempt_data = None; answers_data = []; cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT qa.id, qa.quiz_id, qa.student_id, qa.score, qa.attempted_at, q.title as quiz_title, c.course_name,
                   DATE_FORMAT(qa.attempted_at, '%d/%m/%Y %H:%i:%S') as timestamp
            FROM quiz_attempts qa JOIN quizzes q ON qa.quiz_id = q.id JOIN courses c ON q.course_id = c.id
            WHERE qa.id = %s AND qa.student_id = %s """, (attempt_id, current_user_obj.id))
        attempt_data = cursor.fetchone()
        if not attempt_data: flash("Không tìm thấy kết quả.", "danger"); return redirect(url_for('student_dashboard'))
        cursor.execute("""
            SELECT aa.student_answer, aa.is_correct, q.id as question_id, q.question_text, q.correct_answer, q.options, q.question_type
            FROM attempt_answers aa JOIN questions q ON aa.question_id = q.id
            WHERE aa.attempt_id = %s ORDER BY q.id """, (attempt_id,))
        raw_answers = cursor.fetchall()
        for ans_item in raw_answers:
            ans_item['options_list'] = []
            if ans_item['question_type'] == 'multiple_choice' and ans_item['options']:
                try:
                    loaded_options = json.loads(ans_item['options'])
                    if isinstance(loaded_options, list): ans_item['options_list'] = loaded_options
                except (json.JSONDecodeError, TypeError): app.logger.warning(f"KQ Quiz: Lỗi decode JSON options cho Q ID {ans_item['question_id']}")
            answers_data.append(ans_item)
    except Error as e: app.logger.error(f"Lỗi CSDL lấy KQ quiz (attempt {attempt_id}) SV {current_user_obj.id}: {e}"); flash("Lỗi tải KQ quiz.", "danger"); return redirect(url_for('student_dashboard'))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    return render_template('student_quiz_results.html', attempt=attempt_data, details=answers_data,
                           quiz_title=attempt_data.get('quiz_title'), course_name=attempt_data.get('course_name'))

# --- Flashcard Routes (Sử dụng localStorage phía client) ---
@app.route('/student/flashcard_hub')
@login_required(role='student')
def student_flashcard_hub():
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn: return redirect(url_for('student_dashboard'))
    student_courses_for_fc = []; cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT c.id, c.course_code, c.course_name as name FROM courses c JOIN enrollments e ON c.id = e.course_id WHERE e.student_id = %s ORDER BY c.course_name", (current_user_obj.id,))
        student_courses_for_fc = cursor.fetchall()
    except Error as e: app.logger.error(f"Lỗi CSDL lấy KH cho FC Hub SV {current_user_obj.id}: {e}"); flash("Lỗi tải thông tin KH cho FC Hub.", "danger")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    return render_template('student_flashcard_hub.html', courses=student_courses_for_fc)

@app.route('/student/flashcards/create/general', methods=['GET'])
@login_required(role='student')
def student_create_flashcard_general():
    return render_template('student_create_flashcard.html', context_title="Tạo Flashcard Chung", course=None, session_event=None)

@app.route('/student/flashcards/view/general', methods=['GET'])
@login_required(role='student')
def student_view_flashcard_general():
    return render_template('student_view_flashcards.html', context_title="Xem Flashcard Chung", course=None, session_event=None, storage_key='flashcards_umt_general')

@app.route('/student/flashcards/select_session_for_flashcard/<int:course_id>/<string:action_type>')
@login_required(role='student')
def student_select_session_for_flashcard(course_id, action_type):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn: return redirect(url_for('student_flashcard_hub'))
    course_data_fc = None; sessions_list_fc = []; cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, course_code, course_name FROM courses WHERE id = %s", (course_id,))
        course_data_fc = cursor.fetchone()
        if not course_data_fc: flash("Khóa học không tồn tại.", "danger"); return redirect(url_for('student_flashcard_hub'))
        cursor.execute("SELECT student_id FROM enrollments WHERE student_id = %s AND course_id = %s", (current_user_obj.id, course_id))
        if not cursor.fetchone(): flash("Bạn chưa ghi danh vào khóa học này.", "warning"); return redirect(url_for('student_flashcard_hub'))
        cursor.execute("SELECT id, session_title, session_date FROM course_sessions WHERE course_id = %s ORDER BY session_date DESC, id DESC", (course_id,))
        sessions_list_fc = cursor.fetchall()
    except Error as e: app.logger.error(f"Lỗi lấy buổi học cho FC, KH {course_id}, action {action_type}: {e}"); flash("Lỗi tải danh sách buổi học.", "danger"); return redirect(url_for('student_flashcard_hub'))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    # Sửa: template_action_type để student_select_session.html có thể tạo link đúng
    template_action_type = f"student_create_flashcard_for_session" if action_type == 'create' else f"student_view_flashcards_for_session"
    return render_template('student_select_session.html', course=course_data_fc, sessions=sessions_list_fc, action_type=template_action_type)

@app.route('/student/flashcards/create/course/<int:course_id>/session/<string:date_str>', methods=['GET'])
@login_required(role='student')
def student_create_flashcard_for_session(course_id, date_str):
    conn = get_db_connection();
    if not conn: return redirect(url_for('student_flashcard_hub'))
    course_info_fc = None; session_event_fc = None; cursor = None
    try:
        valid_date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, course_name FROM courses WHERE id = %s", (course_id,))
        course_info_fc = cursor.fetchone()
        if not course_info_fc: flash("Khóa học không tồn tại.", "danger"); return redirect(url_for('student_flashcard_hub'))
        cursor.execute("SELECT id, session_title, session_date FROM course_sessions WHERE course_id = %s AND DATE(session_date) = %s LIMIT 1", (course_id, valid_date_obj))
        session_event_fc = cursor.fetchone()
        if not session_event_fc: flash(f"Buổi học ngày {date_str} không tồn tại.", "warning"); return redirect(url_for('student_select_session_for_flashcard', course_id=course_id, action_type='create'))
    except ValueError: flash("Định dạng ngày không hợp lệ.", "danger"); return redirect(url_for('student_select_session_for_flashcard', course_id=course_id, action_type='create'))
    except Error as e: app.logger.error(f"Lỗi lấy TT tạo FC cho buổi học: {e}"); flash("Lỗi tải thông tin.", "danger"); return redirect(url_for('student_flashcard_hub'))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    context_title = f"Tạo Flashcard: {course_info_fc['course_name']} - Buổi {session_event_fc['session_date']}"
    return render_template('student_create_flashcard.html', context_title=context_title, course=course_info_fc, session_event=session_event_fc)

@app.route('/student/flashcards/view/course/<int:course_id>/session/<string:date_str>', methods=['GET'])
@login_required(role='student')
def student_view_flashcards_for_session(course_id, date_str):
    conn = get_db_connection();
    if not conn: return redirect(url_for('student_flashcard_hub'))
    course_info_fc = None; session_event_fc = None; cursor = None
    try:
        valid_date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, course_name FROM courses WHERE id = %s", (course_id,))
        course_info_fc = cursor.fetchone()
        if not course_info_fc: flash("Khóa học không tồn tại.", "danger"); return redirect(url_for('student_flashcard_hub'))
        cursor.execute("SELECT id, session_title, session_date FROM course_sessions WHERE course_id = %s AND DATE(session_date) = %s LIMIT 1", (course_id, valid_date_obj))
        session_event_fc = cursor.fetchone()
        if not session_event_fc: flash(f"Buổi học ngày {date_str} không tồn tại.", "warning"); return redirect(url_for('student_select_session_for_flashcard', course_id=course_id, action_type='view'))
    except ValueError: flash("Định dạng ngày không hợp lệ.", "danger"); return redirect(url_for('student_select_session_for_flashcard', course_id=course_id, action_type='view'))
    except Error as e: app.logger.error(f"Lỗi lấy TT xem FC cho buổi học: {e}"); flash("Lỗi tải thông tin.", "danger"); return redirect(url_for('student_flashcard_hub'))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    context_title = f"Xem Flashcard: {course_info_fc['course_name']} - Buổi {session_event_fc['session_date']}"
    storage_key = f"flashcards_umt_{course_id}_{date_str}"
    return render_template('student_view_flashcards.html', context_title=context_title, course=course_info_fc, session_event=session_event_fc, storage_key=storage_key)

# --- General Routes ---
@app.route('/')
def index():
    current_user_obj = get_current_user_object()
    if current_user_obj:
        if current_user_obj.role == 'student':
            return redirect(url_for('student_dashboard'))
        elif current_user_obj.role == 'faculty':
            return redirect(url_for('faculty_dashboard'))
    return redirect(url_for('login'))

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.datetime.now().year}

if __name__ == '__main__':
    app.run(debug=True, port=5001)