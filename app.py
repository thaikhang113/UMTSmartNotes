from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash # Added for password hashing
import os
import datetime
import mysql.connector # Import MySQL connector
from mysql.connector import Error # Import Error for exception handling
from functools import wraps # Make sure to import wraps
import json # For handling JSON data with quizzes

app = Flask(__name__)
app.secret_key = 'your_very_secret_key_here_CHANGE_ME' # Rất quan trọng: Thay đổi key này!
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Giới hạn tải lên 16 MB

# Đảm bảo thư mục upload tồn tại
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- Cấu hình Cơ sở dữ liệu ---
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "Khag12344@" # Mật khẩu của bạn
DB_NAME = "umtsmartnotes"

# --- Hàm trợ giúp Cơ sở dữ liệu ---
def get_db_connection():
    """Thiết lập kết nối đến cơ sở dữ liệu MySQL."""
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return conn
    except Error as e:
        app.logger.error(f"Lỗi kết nối đến MySQL: {e}")
        flash(f"Lỗi kết nối cơ sở dữ liệu. Vui lòng thử lại sau.", "danger")
        return None

# --- Lớp User và các hàm quản lý session ---
class User:
    """Đại diện cho một người dùng."""
    def __init__(self, id, username, role, full_name=None):
        self.id = id
        self.username = username
        self.role = role
        self.full_name = full_name
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
    """Lưu thông tin người dùng vào session."""
    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role
    session['full_name'] = user.full_name

def logout_user_session():
    """Xóa thông tin người dùng khỏi session."""
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('role', None)
    session.pop('full_name', None)

@app.context_processor
def inject_user():
    """
    Cung cấp biến current_user cho tất cả các template.
    QUAN TRỌNG: Trong các template HTML, hãy sử dụng {{ current_user }} thay vì {{ user }}.
    """
    if 'user_id' in session and 'username' in session and 'role' in session:
        return {'current_user': User(session['user_id'], session['username'], session['role'], session.get('full_name'))}
    return {'current_user': None}


def get_current_user_object():
    """Lấy đối tượng User hiện tại từ session nếu đã đăng nhập."""
    if 'user_id' in session and 'username' in session and 'role' in session:
        return User(session['user_id'], session['username'], session['role'], session.get('full_name'))
    return None


def login_required(role=None):
    """Decorator để bảo vệ các route yêu cầu đăng nhập."""
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
                    return redirect(url_for('login')) # Fallback
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Custom Template Filter ---
@app.template_filter('format_date_display')
def format_date_display_filter(value, format_str='%d/%m/%Y'):
    """Định dạng chuỗi ngày tháng để hiển thị."""
    if not value:
        return ""
    try:
        # Assuming value might be a date object or string 'YYYY-MM-DD'
        if isinstance(value, (datetime.date, datetime.datetime)):
            return value.strftime(format_str)
        date_obj = datetime.datetime.strptime(str(value), '%Y-%m-%d').date()
        return date_obj.strftime(format_str)
    except (ValueError, TypeError) as e:
        app.logger.warning(f"Không thể định dạng ngày: {value}, Lỗi: {e}")
        return str(value) # Return original value if formatting fails


# --- Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Xử lý đăng nhập người dùng."""
    current_user = get_current_user_object()
    if current_user:
        if current_user.role == 'student':
            return redirect(url_for('student_dashboard'))
        elif current_user.role == 'faculty':
            return redirect(url_for('faculty_dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        conn = get_db_connection()
        if not conn:
            return render_template('login.html')

        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT id, username, password, role, full_name FROM users WHERE username = %s AND role = %s"
            cursor.execute(query, (username, role))
            user_data = cursor.fetchone()

            if user_data and user_data['password'] == password:
                user_obj = User(user_data['id'], user_data['username'], user_data['role'], user_data.get('full_name'))
                login_user_session(user_obj)
                flash('Đăng nhập thành công!', 'success')
                if role == 'student':
                    return redirect(url_for('student_dashboard'))
                elif role == 'faculty':
                    return redirect(url_for('faculty_dashboard'))
            else:
                flash('Tên đăng nhập, mật khẩu hoặc vai trò không đúng.', 'danger')
        except Error as e:
            app.logger.error(f"Lỗi truy vấn CSDL khi đăng nhập: {e}")
            flash(f"Lỗi truy vấn cơ sở dữ liệu khi đăng nhập.", "danger")
        except Exception as e:
            app.logger.error(f"Lỗi không xác định khi đăng nhập: {e}")
            flash("Đã xảy ra lỗi không mong muốn. Vui lòng thử lại.", "danger")
        finally:
            if cursor: cursor.close()
            if conn and conn.is_connected(): conn.close()

    return render_template('login.html')

# Example route to add a user with a hashed password (for testing)
# You should have a proper user registration system
@app.route('/register_test_user', methods=['GET'])
def register_test_user():
    # conn = get_db_connection()
    # if not conn:
    #     return "DB connection error"
    # cursor = None
    # try:
    #     cursor = conn.cursor()
    #     hashed_password = generate_password_hash("studentpass")
    #     # Check if user exists before inserting
    #     cursor.execute("SELECT id FROM users WHERE username = %s AND role = %s", ("khang.id@st.umt.edu.vn", "student"))
    #     if not cursor.fetchone():
    #         sql = "INSERT INTO users (username, password_hash, role, full_name) VALUES (%s, %s, %s, %s)"
    #         val = ("khang.id@st.umt.edu.vn", hashed_password, "student", "Nguyễn Văn Khang")
    #         cursor.execute(sql, val)
    #         conn.commit()
    #         return "Student user created/updated with hashed password!"
    #     else:
    #         # Update existing user's password if needed for testing
    #         # sql_update = "UPDATE users SET password_hash = %s WHERE username = %s AND role = %s"
    #         # cursor.execute(sql_update, (hashed_password, "khang.id@st.umt.edu.vn", "student"))
    #         # conn.commit()
    #         return "Student user already exists."

    #     hashed_password_faculty = generate_password_hash("facultypass")
    #     cursor.execute("SELECT id FROM users WHERE username = %s AND role = %s", ("gv_khang.id", "faculty"))
    #     if not cursor.fetchone():
    #         sql_faculty = "INSERT INTO users (username, password_hash, role, full_name) VALUES (%s, %s, %s, %s)"
    #         val_faculty = ("gv_khang.id", hashed_password_faculty, "faculty", "Giảng viên Khang")
    #         cursor.execute(sql_faculty, val_faculty)
    #         conn.commit()
    #         return "Faculty user created/updated with hashed password!"
    #     else:
    #         return "Faculty user already exists."

    # except Error as e:
    #     if conn and conn.is_connected(): conn.rollback()
    #     app.logger.error(f"Error in register_test_user: {e}")
    #     return f"Error: {e}"
    # finally:
    #     if cursor: cursor.close()
    #     if conn and conn.is_connected(): conn.close()
    return "Registration route is commented out for safety. Uncomment in app.py to use."


@app.route('/logout')
@login_required()
def logout():
    """Xử lý đăng xuất người dùng."""
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
    current_user_obj = get_current_user_object()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT c.id, c.course_code, c.course_name, c.credits
            FROM courses c
            JOIN enrollments e ON c.id = e.course_id
            WHERE e.student_id = %s
        """
        cursor.execute(query, (current_user_obj.id,))
        student_courses = cursor.fetchall()
    except Error as e:
        app.logger.error(f"Lỗi lấy danh sách khóa học của sinh viên {current_user_obj.id}: {e}")
        flash("Không thể tải danh sách khóa học của bạn.", "danger")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('index.html', courses=student_courses)


@app.route('/student/select_session/<int:course_id>')
@login_required(role='student')
def student_select_session(course_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('student_dashboard'))

    course_data = None
    sessions_list = [] # Renamed to avoid conflict if 'sessions' is used in context
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, course_code, course_name FROM courses WHERE id = %s", (course_id,))
        course_data = cursor.fetchone()

        if not course_data:
            flash("Khóa học không tồn tại.", "danger")
            return redirect(url_for('student_dashboard'))

        cursor.execute("SELECT * FROM enrollments WHERE student_id = %s AND course_id = %s", (current_user_obj.id, course_id))
        if not cursor.fetchone():
            flash("Bạn chưa ghi danh vào khóa học này.", "warning")
            return redirect(url_for('student_dashboard'))

        cursor.execute("""
            SELECT id, session_title, session_date, start_time, end_time, lecturer_name, location, event_type
            FROM course_sessions
            WHERE course_id = %s
            ORDER BY session_date DESC, start_time DESC, id DESC
        """, (course_id,))
        sessions_list = cursor.fetchall()

    except Error as e:
        app.logger.error(f"Lỗi lấy danh sách buổi học cho khóa {course_id}: {e}")
        flash("Không thể tải danh sách buổi học.", "danger")
        return redirect(url_for('student_dashboard'))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('student_select_session.html', course=course_data, sessions=sessions_list)


# --- Faculty Routes ---
@app.route('/faculty/dashboard')
@login_required(role='faculty')
def faculty_dashboard():
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('login'))

    faculty_courses = []
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id, course_code, course_name, credits FROM courses WHERE faculty_id = %s"
        cursor.execute(query, (current_user_obj.id,))
        faculty_courses = cursor.fetchall()

    except Error as e:
        app.logger.error(f"Lỗi lấy danh sách khóa học của giảng viên {current_user_obj.id}: {e}")
        flash("Không thể tải danh sách khóa học.", "danger")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('faculty_dashboard.html', courses=faculty_courses)


@app.route('/faculty/course_sessions/<int:course_id>', methods=['GET', 'POST'])
@login_required(role='faculty')
def faculty_course_sessions(course_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('faculty_dashboard'))

    course_info = None # Renamed from course to avoid conflict
    sessions_list = [] # Renamed
    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, course_code, course_name FROM courses WHERE id = %s AND faculty_id = %s", (course_id, current_user_obj.id))
        course_info = cursor.fetchone()

        if not course_info:
            cursor.execute("""
                SELECT DISTINCT c.id, c.course_code, c.course_name FROM courses c
                JOIN course_sessions cs ON c.id = cs.course_id
                WHERE c.id = %s AND cs.lecturer_name = %s LIMIT 1
            """, (course_id, current_user_obj.full_name))
            course_as_lecturer = cursor.fetchone()
            if not course_as_lecturer:
                flash("Khóa học không hợp lệ hoặc bạn không có quyền quản lý buổi học cho khóa này.", "danger")
                return redirect(url_for('faculty_dashboard'))
            course_info = course_as_lecturer


        if request.method == 'POST':
            session_title = request.form.get('session_title')
            session_date_str = request.form.get('session_date')
            start_time_str = request.form.get('start_time')
            end_time_str = request.form.get('end_time')
            lecturer_name = request.form.get('lecturer_name', current_user_obj.full_name)
            location = request.form.get('location')
            event_type = request.form.get('event_type')

            if not all([session_title, session_date_str, start_time_str, end_time_str, lecturer_name, location, event_type]):
                flash("Vui lòng điền đầy đủ thông tin cho buổi học.", "warning")
            else:
                try:
                    session_date = datetime.datetime.strptime(session_date_str, '%Y-%m-%d').date()
                    start_time = datetime.datetime.strptime(start_time_str, '%H:%M').time()
                    end_time = datetime.datetime.strptime(end_time_str, '%H:%M').time()

                    insert_query = """INSERT INTO course_sessions
                                      (course_id, session_title, session_date, start_time, end_time, lecturer_name, location, event_type)
                                      VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                    cursor.execute(insert_query, (course_id, session_title, session_date, start_time, end_time, lecturer_name, location, event_type))
                    conn.commit()
                    flash("Buổi học đã được tạo thành công!", "success")
                except ValueError:
                    flash("Định dạng ngày hoặc giờ không hợp lệ. Vui lòng sử dụng YYYY-MM-DD cho ngày và HH:MM cho giờ.", "danger")
                except Error as e:
                    app.logger.error(f"Lỗi tạo buổi học cho khóa {course_id}: {e}")
                    flash(f"Lỗi khi tạo buổi học: {e}", "danger")
                    if conn.is_connected(): conn.rollback()
            return redirect(url_for('faculty_course_sessions', course_id=course_id))

        cursor.execute("""
            SELECT id, session_title, session_date, start_time, end_time, lecturer_name, location, event_type
            FROM course_sessions
            WHERE course_id = %s
            ORDER BY session_date DESC, start_time DESC, id DESC
        """, (course_id,))
        sessions_list = cursor.fetchall()

    except Error as e:
        app.logger.error(f"Lỗi CSDL trong faculty_course_sessions cho khóa {course_id}: {e}")
        flash(f"Lỗi cơ sở dữ liệu: {e}", "danger")
        return redirect(url_for('faculty_dashboard')) # Redirect on error
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('faculty_course_sessions.html', course=course_info, sessions=sessions_list)


@app.route('/faculty/upload_material/<int:session_id>', methods=['GET', 'POST'])
@login_required(role='faculty')
def faculty_upload_material(session_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        # Flash message already set in get_db_connection
        return redirect(url_for('faculty_dashboard'))

    session_details = None
    materials = []
    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)
        query_session = """
            SELECT cs.id, cs.session_title, cs.course_id, c.faculty_id, cs.lecturer_name, c.course_name
            FROM course_sessions cs
            JOIN courses c ON cs.course_id = c.id
            WHERE cs.id = %s
        """
        cursor.execute(query_session, (session_id,))
        session_details = cursor.fetchone()

        if not session_details:
            flash("Buổi học không tồn tại.", "danger")
            return redirect(url_for('faculty_dashboard'))

        is_main_faculty = (session_details['faculty_id'] == current_user_obj.id)
        is_session_lecturer = (session_details['lecturer_name'] == current_user_obj.full_name)

        if not (is_main_faculty or is_session_lecturer):
            flash("Bạn không có quyền tải lên tài liệu cho buổi học này.", "danger")
            return redirect(url_for('faculty_course_sessions', course_id=session_details['course_id']))

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
                # Create a more structured path: UPLOAD_FOLDER / course_id / session_id / filename
                course_session_upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], 
                                                            'course_materials', 
                                                            str(session_details['course_id']), 
                                                            str(session_id))
                if not os.path.exists(course_session_upload_folder):
                    os.makedirs(course_session_upload_folder, exist_ok=True)

                file_path_on_server = os.path.join(course_session_upload_folder, filename)
                
                # Check if material for this session with the same name already exists
                cursor.execute("SELECT id FROM session_materials WHERE session_id = %s AND file_name = %s", (session_id, filename))
                if cursor.fetchone():
                    flash(f"Tệp '{filename}' đã tồn tại cho buổi học này. Vui lòng đổi tên tệp hoặc xóa tệp cũ.", "warning")
                else:
                    try:
                        file.save(file_path_on_server)
                        # Store relative path from UPLOAD_FOLDER in DB
                        db_file_path = os.path.join('course_materials', str(session_details['course_id']), str(session_id), filename).replace("\\","/")
                        insert_query = """
                            INSERT INTO session_materials (session_id, file_name, file_path, uploaded_by)
                            VALUES (%s, %s, %s, %s)
                        """
                        cursor.execute(insert_query, (session_id, filename, db_file_path, current_user_obj.id))
                        conn.commit()
                        flash(f"Tệp '{filename}' đã được tải lên thành công.", 'success')
                    except Error as e:
                        app.logger.error(f"Lỗi CSDL khi lưu tài liệu cho buổi {session_id}: {e}")
                        flash(f"Lỗi khi lưu thông tin tệp vào cơ sở dữ liệu: {e}", "danger")
                        if conn.is_connected(): conn.rollback()
                    except Exception as e: # Catch generic file save errors
                        app.logger.error(f"Lỗi lưu file cho buổi {session_id}, file {filename}: {e}")
                        flash(f"Lỗi khi lưu tệp: {e}", "danger")
                return redirect(url_for('faculty_upload_material', session_id=session_id))

        # GET request: Fetch existing materials for this session
        cursor.execute("SELECT id, file_name, uploaded_at, file_path FROM session_materials WHERE session_id = %s ORDER BY uploaded_at DESC", (session_id,))
        materials = cursor.fetchall()

    except Error as e:
        app.logger.error(f"Lỗi CSDL trong faculty_upload_material cho buổi {session_id}: {e}")
        flash(f"Lỗi cơ sở dữ liệu: {e}", "danger")
        # Redirect to a safe page on DB error
        return redirect(url_for('faculty_course_sessions', course_id=session_details['course_id'] if session_details else faculty_dashboard()))
    except Exception as e: # Catch other potential errors
        app.logger.error(f"Lỗi không xác định trong faculty_upload_material: {e}")
        flash("Đã có lỗi không xác định xảy ra.", "danger")
        return redirect(url_for('faculty_dashboard'))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('faculty_upload_material.html', session=session_details, materials=materials, course={'id': session_details.get('course_id'), 'name': session_details.get('course_name')})


@app.route('/download_material/<int:material_id>')
@login_required()
def download_material(material_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return redirect(request.referrer or url_for('login'))

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        query = """SELECT sm.file_name, sm.file_path, sm.session_id,
                          cs.course_id, c.faculty_id as course_faculty_id,
                          cs.lecturer_name as session_lecturer_name, sm.uploaded_by
                   FROM session_materials sm
                   JOIN course_sessions cs ON sm.session_id = cs.id
                   JOIN courses c ON cs.course_id = c.id
                   WHERE sm.id = %s"""
        cursor.execute(query, (material_id,))
        material = cursor.fetchone()

        if not material:
            flash("Tài liệu không tồn tại.", "danger")
            return redirect(request.referrer or url_for('student_dashboard' if current_user_obj.role == 'student' else 'faculty_dashboard'))

        can_download = False
        if current_user_obj.role == 'faculty':
            if material['course_faculty_id'] == current_user_obj.id or \
               material['session_lecturer_name'] == current_user_obj.full_name or \
               material['uploaded_by'] == current_user_obj.id:
                 can_download = True
        elif current_user_obj.role == 'student':
            cursor.execute("SELECT student_id FROM enrollments WHERE student_id = %s AND course_id = %s", (current_user_obj.id, material['course_id']))
            if cursor.fetchone():
                can_download = True

        if not can_download:
            flash("Bạn không có quyền tải xuống tài liệu này.", "danger")
            return redirect(request.referrer or url_for('student_dashboard' if current_user_obj.role == 'student' else 'faculty_dashboard'))

        # file_path in DB is relative to UPLOAD_FOLDER
        full_path_to_file = os.path.join(app.config['UPLOAD_FOLDER'], material['file_path'])
        directory_for_send = os.path.dirname(full_path_to_file)
        filename_for_send = os.path.basename(full_path_to_file)

        if not os.path.exists(full_path_to_file) or not os.path.isfile(full_path_to_file):
            app.logger.error(f"Tệp tài liệu không tìm thấy tại: {full_path_to_file} cho material_id: {material_id}")
            flash("Tệp tài liệu không tìm thấy trên máy chủ.", "danger")
            return redirect(request.referrer or url_for('student_dashboard' if current_user_obj.role == 'student' else 'faculty_dashboard'))

        return send_from_directory(directory=directory_for_send, path=filename_for_send, as_attachment=True)

    except Error as e:
        app.logger.error(f"Lỗi CSDL khi tải tài liệu {material_id}: {e}")
        flash(f"Lỗi cơ sở dữ liệu khi tải tài liệu.", "danger")
    except Exception as e:
        app.logger.error(f"Lỗi chung khi tải tài liệu {material_id}: {e} (Path: {full_path_to_file if 'full_path_to_file' in locals() else 'N/A'})")
        flash(f"Lỗi không xác định khi tải tài liệu.", "danger")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    
    default_redirect = url_for('student_dashboard' if current_user_obj.role == 'student' else 'faculty_dashboard')
    return redirect(request.referrer or default_redirect)


# --- Notes Routes ---
@app.route('/notes/session/<int:session_id>')
@login_required()
def course_notes_overview(session_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('login'))

    session_info_data = None # Renamed
    notes_list = []
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        query_session = """
            SELECT cs.id, cs.session_title, cs.course_id, c.course_name, c.course_code, c.faculty_id as course_faculty_id, cs.lecturer_name as session_lecturer_name
            FROM course_sessions cs
            JOIN courses c ON cs.course_id = c.id
            WHERE cs.id = %s
        """
        cursor.execute(query_session, (session_id,))
        session_info_data = cursor.fetchone()

        if not session_info_data:
            flash("Buổi học không tồn tại.", "danger")
            return redirect(url_for('student_dashboard') if current_user_obj.role == 'student' else url_for('faculty_dashboard'))

        can_view_session = False
        if current_user_obj.role == 'student':
            cursor.execute("SELECT * FROM enrollments WHERE student_id = %s AND course_id = %s", (current_user_obj.id, session_info_data['course_id']))
            if cursor.fetchone():
                can_view_session = True
        elif current_user_obj.role == 'faculty': # Faculty can view notes if they teach the course or the session
            if session_info_data['course_faculty_id'] == current_user_obj.id or session_info_data['session_lecturer_name'] == current_user_obj.full_name:
                can_view_session = True

        if not can_view_session:
            flash("Bạn không có quyền xem ghi chú cho buổi học này.", "danger")
            return redirect(url_for('student_dashboard') if current_user_obj.role == 'student' else url_for('faculty_dashboard'))

        # Fetch notes for the current user for this session
        notes_query = "SELECT id, title, LEFT(content, 100) as preview, updated_at FROM notes WHERE session_id = %s AND user_id = %s ORDER BY updated_at DESC"
        cursor.execute(notes_query, (session_id, current_user_obj.id))
        notes_list = cursor.fetchall()

    except Error as e:
        app.logger.error(f"Lỗi lấy ghi chú cho buổi {session_id}, người dùng {current_user_obj.id}: {e}")
        flash("Không thể tải ghi chú.", "danger")
        # Redirect to a safe page on error
        return redirect(url_for('student_dashboard') if current_user_obj.role == 'student' else url_for('faculty_dashboard'))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('course_notes_overview.html', session_info=session_info_data, notes=notes_list, course={'id': session_info_data.get('course_id'), 'name': session_info_data.get('course_name')})


@app.route('/notes/create/<int:session_id>', methods=['GET', 'POST'])
@login_required()
def create_note(session_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('course_notes_overview', session_id=session_id))

    session_info_data = None # Renamed
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        query_session = """
            SELECT cs.id, cs.session_title, c.course_name, c.id as course_id, c.faculty_id as course_faculty_id, cs.lecturer_name as session_lecturer_name
            FROM course_sessions cs
            JOIN courses c ON cs.course_id = c.id
            WHERE cs.id = %s
        """
        cursor.execute(query_session, (session_id,))
        session_info_data = cursor.fetchone()
        if not session_info_data:
            flash("Buổi học không hợp lệ.", "danger")
            return redirect(url_for('student_dashboard') if current_user_obj.role == 'student' else url_for('faculty_dashboard'))

        # Authorization check
        can_create_note_flag = False # Renamed
        if current_user_obj.role == 'student':
            cursor.execute("SELECT * FROM enrollments WHERE student_id = %s AND course_id = %s", (current_user_obj.id, session_info_data['course_id']))
            if cursor.fetchone():
                can_create_note_flag = True
        elif current_user_obj.role == 'faculty':
             if session_info_data['course_faculty_id'] == current_user_obj.id or session_info_data['session_lecturer_name'] == current_user_obj.full_name:
                can_create_note_flag = True

        if not can_create_note_flag:
            flash("Bạn không có quyền tạo ghi chú cho buổi học này.", "danger")
            return redirect(url_for('course_notes_overview', session_id=session_id))


        if request.method == 'POST':
            title = request.form.get('title', f'Ghi chú ngày {datetime.date.today().strftime("%d-%m-%Y")}') # Default title
            content = request.form.get('content', '')

            insert_query = "INSERT INTO notes (session_id, user_id, title, content) VALUES (%s, %s, %s, %s)"
            cursor.execute(insert_query, (session_id, current_user_obj.id, title, content))
            conn.commit()
            new_note_id = cursor.lastrowid
            flash('Ghi chú đã được tạo thành công!', 'success')
            return redirect(url_for('edit_note', note_id=new_note_id)) # Redirect to edit page for the new note

    except Error as e:
        app.logger.error(f"Lỗi tạo ghi chú cho buổi {session_id}, người dùng {current_user_obj.id}: {e}")
        flash(f"Lỗi khi tạo ghi chú: {e}", "danger")
        if conn and conn.is_connected(): conn.rollback()
        # On error, redirect back to overview or dashboard
        return redirect(url_for('course_notes_overview', session_id=session_id))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    
    # For GET request, show the note creation form
    # Pass course and session info to the template
    course_context = {'id': session_info_data.get('course_id'), 'name': session_info_data.get('course_name')}
    note_date_context = session_info_data.get('session_date') if session_info_data else datetime.date.today()

    return render_template('notes_template.html', 
                           session_info=session_info_data, 
                           note=None, 
                           is_new=True, 
                           session_id=session_id,
                           course=course_context,
                           note_date=note_date_context)


@app.route('/notes/edit/<int:note_id>', methods=['GET', 'POST'])
@login_required()
def edit_note(note_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        # Appropriate redirect if DB fails
        return redirect(url_for('student_dashboard') if current_user_obj.role == 'student' else url_for('faculty_dashboard'))

    note_data = None
    session_info_for_template = None
    course_context = None
    note_date_context = None
    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)
        query_note = """
            SELECT n.id, n.title, n.content, n.session_id, n.user_id, n.created_at, n.updated_at,
                   cs.session_title, cs.session_date, cs.course_id,
                   crs.course_name, crs.course_code
            FROM notes n
            LEFT JOIN course_sessions cs ON n.session_id = cs.id
            LEFT JOIN courses crs ON cs.course_id = crs.id
            WHERE n.id = %s AND n.user_id = %s
        """
        cursor.execute(query_note, (note_id, current_user_obj.id))
        note_data = cursor.fetchone()

        if not note_data:
            flash("Ghi chú không tồn tại hoặc bạn không có quyền chỉnh sửa.", "danger")
            return redirect(url_for('student_dashboard') if current_user_obj.role == 'student' else url_for('faculty_dashboard'))

        # Prepare context for template
        if note_data.get('session_id'):
             session_info_for_template = {
                'id': note_data['session_id'],
                'session_title': note_data['session_title'],
                'course_name': note_data['course_name'] # This comes from join
            }
             course_context = {'id': note_data.get('course_id'), 'name': note_data.get('course_name')}
             note_date_context = note_data.get('session_date')
        else: # Handle notes not linked to a specific session (future feature?)
            course_context = {'id': 'general', 'name': 'Ghi chú chung'}
            note_date_context = note_data.get('created_at').date() if note_data.get('created_at') else datetime.date.today()


        if request.method == 'POST':
            title = request.form.get('title', note_data['title'])
            content = request.form.get('content', note_data['content'])

            update_query = "UPDATE notes SET title = %s, content = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s AND user_id = %s"
            cursor.execute(update_query, (title, content, note_id, current_user_obj.id))
            conn.commit()
            flash('Ghi chú đã được cập nhật!', 'success')
            
            # Fetch the updated note data again to pass to template
            cursor.execute(query_note, (note_id, current_user_obj.id))
            note_data = cursor.fetchone()
            # Re-populate context if data changed (though title/content are main changes)
            if note_data.get('session_id'):
                 session_info_for_template = {
                    'id': note_data['session_id'],
                    'session_title': note_data['session_title'],
                    'course_name': note_data['course_name']
                }
                 course_context = {'id': note_data.get('course_id'), 'name': note_data.get('course_name')}
                 note_date_context = note_data.get('session_date')


    except Error as e:
        app.logger.error(f"Lỗi sửa ghi chú {note_id} cho người dùng {current_user_obj.id}: {e}")
        flash(f"Lỗi khi cập nhật ghi chú: {e}", "danger")
        if conn and conn.is_connected(): conn.rollback()
        # On error, do not lose the edit page if possible, or redirect safely
        # return redirect(request.url) # Could cause loop if error persists
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    if not note_data: # Should have been caught earlier, but as a safeguard
        flash("Không thể tải ghi chú để chỉnh sửa.", "danger")
        return redirect(url_for('student_dashboard') if current_user_obj.role == 'student' else url_for('faculty_dashboard'))

    return render_template('notes_template.html',
                           note=note_data,
                           session_info=session_info_for_template,
                           is_new=False,
                           session_id=note_data.get('session_id'),
                           course=course_context,
                           note_date=note_date_context)


@app.route('/notes/delete/<int:note_id>', methods=['POST']) # Should be POST for deletion
@login_required()
def delete_note(note_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        # For AJAX, return JSON. For form post, flash and redirect.
        # Assuming this might be called via JS later, so jsonify is reasonable.
        return jsonify({'success': False, 'message': 'Lỗi kết nối cơ sở dữ liệu.'}), 500


    cursor = None
    original_session_id_for_redirect = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Get session_id for redirect before deleting
        cursor.execute("SELECT session_id FROM notes WHERE id = %s AND user_id = %s", (note_id, current_user_obj.id))
        note_to_delete = cursor.fetchone()

        if not note_to_delete:
            flash("Ghi chú không tồn tại hoặc bạn không có quyền xóa.", "warning")
            # Determine a safe redirect if called via non-JS POST
            default_redirect = url_for('student_dashboard' if current_user_obj.role == 'student' else 'faculty_dashboard')
            return jsonify({'success': False, 'message': 'Không tìm thấy ghi chú hoặc không có quyền xóa.' , 'redirect_url': default_redirect }), 404

        original_session_id_for_redirect = note_to_delete['session_id']

        delete_query = "DELETE FROM notes WHERE id = %s AND user_id = %s"
        cursor.execute(delete_query, (note_id, current_user_obj.id))
        conn.commit()

        if cursor.rowcount > 0:
            flash('Ghi chú đã được xóa.', 'success')
            if original_session_id_for_redirect:
                redirect_url = url_for('course_notes_overview', session_id=original_session_id_for_redirect)
            elif current_user_obj.role == 'student':
                redirect_url = url_for('student_dashboard') # Or a general notes page if exists
            else:
                redirect_url = url_for('faculty_dashboard')
            return jsonify({'success': True, 'message': 'Ghi chú đã được xóa.', 'redirect_url': redirect_url})
        else:
            # This case means the note wasn't found or didn't belong to the user during delete itself,
            # though the earlier check should have caught it.
            flash("Không thể xóa ghi chú. Có thể nó đã được xóa hoặc bạn không có quyền.", "warning")
            default_redirect = url_for('student_dashboard' if current_user_obj.role == 'student' else 'faculty_dashboard')
            return jsonify({'success': False, 'message': 'Không thể xóa ghi chú.', 'redirect_url': default_redirect }), 403


    except Error as e:
        app.logger.error(f"Lỗi xóa ghi chú {note_id} cho người dùng {current_user_obj.id}: {e}")
        if conn and conn.is_connected(): conn.rollback()
        # For AJAX
        return jsonify({'success': False, 'message': f'Lỗi cơ sở dữ liệu: {e}'}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    # Fallback if not returned earlier (should ideally not be reached if logic is sound)
    # Flash message might not be seen if this is an AJAX call expecting JSON.
    flash("Lỗi không xác định khi xóa ghi chú.", "danger")
    default_redirect = url_for('student_dashboard' if current_user_obj.role == 'student' else 'faculty_dashboard')
    return jsonify({'success': False, 'message': 'Lỗi không xác định khi xóa.', 'redirect_url': default_redirect }), 500


# --- Flashcard Routes ---
@app.route('/student/flashcard_hub/course/<int:course_id>')
@login_required(role='student')
def student_flashcard_hub_course(course_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn: return redirect(url_for('student_dashboard'))

    course_info_data = None # Renamed
    hubs_list = [] # Renamed
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, course_code, course_name FROM courses WHERE id = %s", (course_id,))
        course_info_data = cursor.fetchone()
        if not course_info_data:
            flash("Khóa học không tồn tại.", "danger")
            return redirect(url_for('student_dashboard'))

        cursor.execute("SELECT * FROM enrollments WHERE student_id = %s AND course_id = %s", (current_user_obj.id, course_id))
        if not cursor.fetchone():
            flash("Bạn chưa ghi danh vào khóa học này để xem flashcards.", "warning")
            return redirect(url_for('student_dashboard'))

        hub_query = "SELECT id, name, created_at FROM flashcard_hubs WHERE user_id = %s AND course_id = %s ORDER BY name"
        cursor.execute(hub_query, (current_user_obj.id, course_id))
        hubs_list = cursor.fetchall()
    except Error as e:
        app.logger.error(f"Lỗi CSDL lấy flashcard hubs cho khóa {course_id}, người dùng {current_user_obj.id}: {e}")
        flash("Lỗi tải bộ flashcard.", "danger")
        return redirect(url_for('student_dashboard')) # Redirect on DB error
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('student_flashcard_hub.html', course=course_info_data, hubs=hubs_list)

@app.route('/student/flashcard_hub/create/<int:course_id>', methods=['POST'])
@login_required(role='student')
def create_flashcard_hub(course_id):
    current_user_obj = get_current_user_object()
    hub_name = request.form.get('hub_name')
    if not hub_name:
        flash("Tên bộ flashcard là bắt buộc.", "warning")
        return redirect(url_for('student_flashcard_hub_course', course_id=course_id))

    conn = get_db_connection()
    if not conn: return redirect(url_for('student_flashcard_hub_course', course_id=course_id))

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True) # Using dictionary=True is fine for SELECT
        cursor.execute("SELECT * FROM enrollments WHERE student_id = %s AND course_id = %s", (current_user_obj.id, course_id))
        if not cursor.fetchone():
            flash("Bạn cần ghi danh vào khóa học để tạo bộ flashcard.", "warning")
            return redirect(url_for('student_dashboard')) # More general redirect

        insert_query = "INSERT INTO flashcard_hubs (user_id, course_id, name) VALUES (%s, %s, %s)"
        # For INSERT, dictionary=True on cursor is not strictly needed but doesn't hurt
        cursor.execute(insert_query, (current_user_obj.id, course_id, hub_name))
        conn.commit()
        flash(f"Bộ flashcard '{hub_name}' đã được tạo.", "success")
    except Error as e:
        app.logger.error(f"Lỗi CSDL tạo flashcard hub cho khóa {course_id}, người dùng {current_user_obj.id}: {e}")
        flash(f"Lỗi tạo bộ flashcard: {e}", "danger")
        if conn and conn.is_connected(): conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return redirect(url_for('student_flashcard_hub_course', course_id=course_id))


@app.route('/student/flashcards/view/<int:hub_id>')
@login_required(role='student')
def student_view_flashcards(hub_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn: return redirect(url_for('student_dashboard'))

    hub_info_data = None # Renamed
    flashcards_list_data = [] # Renamed
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        hub_query = """
            SELECT fh.id, fh.name, fh.course_id, c.course_name, c.course_code
            FROM flashcard_hubs fh
            JOIN courses c ON fh.course_id = c.id
            WHERE fh.id = %s AND fh.user_id = %s
        """
        cursor.execute(hub_query, (hub_id, current_user_obj.id))
        hub_info_data = cursor.fetchone()

        if not hub_info_data:
            flash("Bộ flashcard không tồn tại hoặc bạn không có quyền truy cập.", "danger")
            # Redirect to a more general page if hub not found or not authorized
            return redirect(url_for('student_dashboard')) # Consider a specific flashcard hub listing page if you have one

        fc_query = "SELECT id, question, answer FROM flashcards WHERE hub_id = %s ORDER BY id" # Assuming order by creation
        cursor.execute(fc_query, (hub_id,))
        flashcards_list_data = cursor.fetchall()
    except Error as e:
        app.logger.error(f"Lỗi CSDL lấy flashcards cho hub {hub_id}, người dùng {current_user_obj.id}: {e}")
        flash("Lỗi tải flashcards.", "danger")
        # On error, redirect safely
        return redirect(url_for('student_flashcard_hub_course', course_id=hub_info_data['course_id']) if hub_info_data else url_for('student_dashboard'))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('student_view_flashcards.html', hub=hub_info_data, flashcards=flashcards_list_data, course=hub_info_data) # Pass course object as well


@app.route('/student/flashcards/add_to_hub/<int:hub_id>', methods=['POST'])
@login_required(role='student')
def add_flashcard_to_hub(hub_id):
    current_user_obj = get_current_user_object()
    question = request.form.get('question')
    answer = request.form.get('answer')

    if not question or not answer:
        flash("Câu hỏi và câu trả lời không được để trống.", "warning")
        return redirect(url_for('student_view_flashcards', hub_id=hub_id))

    conn = get_db_connection()
    if not conn: return redirect(url_for('student_view_flashcards', hub_id=hub_id))

    cursor = None
    try:
        # No need for dictionary=True for a simple existence check if you only use the fact it found something
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM flashcard_hubs WHERE id = %s AND user_id = %s", (hub_id, current_user_obj.id))
        if not cursor.fetchone():
            flash("Bạn không có quyền thêm flashcard vào bộ này.", "danger")
            # Redirect to a general student page if unauthorized
            return redirect(url_for('student_dashboard'))

        insert_query = "INSERT INTO flashcards (hub_id, question, answer) VALUES (%s, %s, %s)"
        cursor.execute(insert_query, (hub_id, question, answer))
        conn.commit()
        flash("Flashcard đã được thêm.", "success")
    except Error as e:
        app.logger.error(f"Lỗi CSDL thêm flashcard vào hub {hub_id}, người dùng {current_user_obj.id}: {e}")
        flash(f"Lỗi thêm flashcard: {e}", "danger")
        if conn and conn.is_connected(): conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return redirect(url_for('student_view_flashcards', hub_id=hub_id))


# --- Quiz Routes ---
@app.route('/faculty/manage_quiz/<int:course_id>', methods=['GET'])
@login_required(role='faculty')
def faculty_manage_quiz(course_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn: return redirect(url_for('faculty_dashboard'))

    course_info_data = None # Renamed
    quizzes_list_data = [] # Renamed
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Ensure faculty is authorized for this course
        cursor.execute("SELECT id, course_code, course_name FROM courses WHERE id = %s AND faculty_id = %s", (course_id, current_user_obj.id))
        course_info_data = cursor.fetchone()
        if not course_info_data:
            flash("Khóa học không hợp lệ hoặc bạn không có quyền quản lý quiz cho khóa học này.", "danger")
            return redirect(url_for('faculty_dashboard'))

        # Fetch quizzes created by this faculty for this course
        quiz_query = "SELECT id, title, created_at FROM quizzes WHERE course_id = %s AND created_by = %s ORDER BY created_at DESC"
        cursor.execute(quiz_query, (course_id, current_user_obj.id))
        quizzes_list_data = cursor.fetchall()
    except Error as e:
        app.logger.error(f"Lỗi CSDL lấy quizzes cho khóa {course_id}, giảng viên {current_user_obj.id}: {e}")
        flash("Lỗi tải danh sách quiz.", "danger")
        return redirect(url_for('faculty_dashboard')) # Safe redirect on error
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('faculty_manage_quiz.html', course=course_info_data, quizzes=quizzes_list_data)


@app.route('/faculty/quiz/create/<int:course_id>', methods=['GET', 'POST'])
@login_required(role='faculty')
def faculty_create_quiz(course_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('faculty_manage_quiz', course_id=course_id))

    course_info_data = None # Renamed
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, course_code, course_name FROM courses WHERE id = %s AND faculty_id = %s", (course_id, current_user_obj.id))
        course_info_data = cursor.fetchone()
        if not course_info_data:
            flash("Khóa học không hợp lệ hoặc bạn không có quyền tạo quiz cho khóa học này.", "danger")
            return redirect(url_for('faculty_dashboard'))

        if request.method == 'POST':
            quiz_title = request.form.get('quiz_title')
            if not quiz_title:
                flash("Tiêu đề quiz là bắt buộc.", "warning")
                # Repopulate form with submitted data if title is missing
                questions_data_repop = []
                q_idx = 0
                while True:
                    q_text_key = f'questions[{q_idx}][question_text]'
                    if q_text_key not in request.form and q_idx > 0: break # Stop if no more questions
                    if q_text_key not in request.form and q_idx == 0 : # Handle empty initial form
                        questions_data_repop.append({}) # Add one empty question for template
                        break

                    questions_data_repop.append({
                        'question_text': request.form.get(q_text_key, ""),
                        'question_type': request.form.get(f'questions[{q_idx}][question_type]'),
                        'options': [request.form.get(f'questions[{q_idx}][options][{opt_idx}]') for opt_idx in range(4) if request.form.get(f'questions[{q_idx}][options][{opt_idx}]')],
                        'correct_answer': request.form.get(f'questions[{q_idx}][correct_answer]')
                    })
                    q_idx += 1
                return render_template('faculty_create_quiz_form.html', course=course_info_data, quiz_title=quiz_title, questions=questions_data_repop)

            quiz_id_created = None # Renamed
            try:
                # Consider explicit transaction start here if your DB engine supports it well with the connector
                # conn.start_transaction()

                quiz_insert_query = "INSERT INTO quizzes (course_id, title, created_by) VALUES (%s, %s, %s)"
                cursor.execute(quiz_insert_query, (course_id, quiz_title, current_user_obj.id))
                quiz_id_created = cursor.lastrowid
                
                any_valid_question_added = False # Renamed
                q_idx = 0
                while True:
                    question_text = request.form.get(f'questions[{q_idx}][question_text]')
                    # Better logic to stop: if question_text is empty AND it's not the first potential question slot
                    # or if the key itself doesn't exist for non-first questions
                    if not request.form.get(f'questions[{q_idx}][question_text]') and \
                       not request.form.get(f'questions[{q_idx}][question_type]') and \
                       q_idx > 0: # Check if any field for this question index exists
                        break
                    if q_idx > 20: break # Safety break for too many questions

                    if not question_text: # Skip if question text is empty
                        q_idx += 1
                        continue

                    question_type = request.form.get(f'questions[{q_idx}][question_type]')
                    correct_answer_input = request.form.get(f'questions[{q_idx}][correct_answer]') # This is likely the index or value of correct option
                    
                    options_list = []
                    if question_type == 'multiple_choice':
                        for opt_inner_idx in range(4): # Assuming max 4 options based on common forms
                            option_val = request.form.get(f'questions[{q_idx}][options][{opt_inner_idx}]')
                            if option_val and option_val.strip():
                                options_list.append(option_val.strip())
                    
                    options_json_db = json.dumps(options_list) if options_list else None

                    # Validation for question data
                    if question_text and question_type and correct_answer_input and (question_type != 'multiple_choice' or (options_list and len(options_list) >= 2)):
                        q_insert_sql = """INSERT INTO questions (quiz_id, question_text, question_type, options, correct_answer)
                                      VALUES (%s, %s, %s, %s, %s)"""
                        # For MC, correct_answer should be the text of the correct option
                        actual_correct_answer_text = ""
                        if question_type == 'multiple_choice' and options_list:
                            try:
                                correct_option_index = int(correct_answer_input) # Assuming form sends index
                                if 0 <= correct_option_index < len(options_list):
                                    actual_correct_answer_text = options_list[correct_option_index]
                                else: # Invalid index
                                    flash(f"Lựa chọn đáp án đúng không hợp lệ cho câu hỏi {q_idx+1}.", "warning")
                                    q_idx += 1
                                    continue 
                            except ValueError: # correct_answer_input was not an int
                                flash(f"Định dạng đáp án đúng không hợp lệ cho câu hỏi {q_idx+1}.", "warning")
                                q_idx += 1
                                continue
                        else: # For other types like 'short_answer'
                             actual_correct_answer_text = correct_answer_input


                        if not actual_correct_answer_text and question_type == 'multiple_choice':
                             flash(f"Đáp án đúng không được chọn hoặc không hợp lệ cho câu hỏi trắc nghiệm {q_idx+1}.", "warning")
                             q_idx +=1
                             continue


                        cursor.execute(q_insert_sql, (quiz_id_created, question_text, question_type, options_json_db, actual_correct_answer_text))
                        any_valid_question_added = True
                    elif question_text: # Question text exists but other parts are missing
                        flash(f"Câu hỏi {q_idx+1} ('{question_text[:20]}...') thiếu thông tin (loại, lựa chọn hoặc đáp án đúng). Nó sẽ không được thêm.", "warning")
                    
                    q_idx += 1
                    if q_idx > 0 and not request.form.get(f'questions[{q_idx}][question_text]') and not request.form.get(f'questions[{q_idx}][question_type]'):
                        break # Break if next set of fields is completely empty

                if not any_valid_question_added and quiz_id_created:
                    # Decide if a quiz without questions is allowed. If not, rollback and flash.
                    # For now, let's assume it's allowed but warn.
                    flash("Quiz đã được tạo nhưng không có câu hỏi hợp lệ nào được thêm. Vui lòng chỉnh sửa quiz để thêm câu hỏi.", "info")
                
                conn.commit()
                flash(f"Quiz '{quiz_title}' đã được tạo/cập nhật thành công!", "success")
                return redirect(url_for('faculty_manage_quiz', course_id=course_id))

            except Error as e:
                app.logger.error(f"Lỗi CSDL tạo quiz/câu hỏi cho khóa {course_id}: {e}")
                flash(f"Lỗi khi tạo quiz: {e}", "danger")
                if conn and conn.is_connected(): conn.rollback()
            except Exception as e: # Catch other errors like JSON issues or form processing
                app.logger.error(f"Lỗi chung khi tạo quiz: {e}")
                flash(f"Lỗi không xác định khi xử lý form tạo quiz: {e}", "danger")
                if conn and conn.is_connected(): conn.rollback()
        
        # GET request - render form for new quiz
        return render_template('faculty_create_quiz_form.html', course=course_info_data, quiz=None, questions=[{}]) # Pass one empty question for the form

    except Error as e: # Error during GET request processing
        app.logger.error(f"Lỗi CSDL trong faculty_create_quiz GET cho khóa {course_id}: {e}")
        flash(f"Lỗi tải trang tạo quiz: {e}", "danger")
        return redirect(url_for('faculty_manage_quiz', course_id=course_id))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()


@app.route('/student/take_quiz/<int:quiz_id>')
@login_required(role='student')
def student_take_quiz(quiz_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn: return redirect(url_for('student_dashboard'))

    quiz_info_data = None # Renamed
    questions_list = [] # Renamed
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT q.id, q.title, q.course_id, c.course_name 
            FROM quizzes q JOIN courses c ON q.course_id = c.id 
            WHERE q.id = %s
        """, (quiz_id,))
        quiz_info_data = cursor.fetchone()

        if not quiz_info_data:
            flash("Quiz không tồn tại.", "danger")
            return redirect(url_for('student_dashboard'))
        
        # Check enrollment
        cursor.execute("SELECT * FROM enrollments WHERE student_id = %s AND course_id = %s", (current_user_obj.id, quiz_info_data['course_id']))
        if not cursor.fetchone():
            flash("Bạn chưa ghi danh vào khóa học của quiz này.", "warning")
            return redirect(url_for('student_dashboard'))

        # Fetch questions
        q_query = "SELECT id, question_text, question_type, options FROM questions WHERE quiz_id = %s ORDER BY id" # Assuming default order
        cursor.execute(q_query, (quiz_id,))
        questions_raw = cursor.fetchall()
        
        for q_item in questions_raw: # Renamed loop var
            if q_item['question_type'] == 'multiple_choice' and q_item['options']:
                try:
                    q_item['options_list'] = json.loads(q_item['options']) # This should be a list of strings
                    if not isinstance(q_item['options_list'], list): q_item['options_list'] = [] # Ensure it's a list
                except (json.JSONDecodeError, TypeError):
                    q_item['options_list'] = []
                    app.logger.warning(f"Quiz {quiz_id}, Question {q_item['id']}: JSON options decode error or not a list. Options: {q_item['options']}")
            else:
                q_item['options_list'] = [] # For non-MCQ or if options are null/empty
            questions_list.append(q_item)

    except Error as e:
        app.logger.error(f"Lỗi CSDL lấy quiz {quiz_id} cho sinh viên {current_user_obj.id}: {e}")
        flash("Lỗi tải quiz.", "danger")
        return redirect(url_for('student_dashboard')) # Safe redirect
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
        
    return render_template('student_take_quiz.html', quiz=quiz_info_data, questions=questions_list, course_name=quiz_info_data.get('course_name'))


@app.route('/student/submit_quiz/<int:quiz_id>', methods=['POST'])
@login_required(role='student')
def student_submit_quiz(quiz_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        flash("Lỗi kết nối CSDL, không thể nộp bài.", "danger")
        return redirect(url_for('student_take_quiz', quiz_id=quiz_id))

    cursor = None
    attempt_id_created = None # Renamed
    score_achieved_count = 0 # Renamed
    total_questions_in_quiz = 0 # Renamed

    try:
        cursor = conn.cursor(dictionary=True)
        
        # Verify quiz exists and student is enrolled in the course
        cursor.execute("SELECT course_id FROM quizzes WHERE id = %s", (quiz_id,))
        quiz_course_data = cursor.fetchone()
        if not quiz_course_data:
            flash("Quiz không tồn tại.", "danger")
            return redirect(url_for('student_dashboard'))
        
        cursor.execute("SELECT * FROM enrollments WHERE student_id = %s AND course_id = %s", (current_user_obj.id, quiz_course_data['course_id']))
        if not cursor.fetchone():
            flash("Bạn không được phép làm quiz này.", "warning")
            return redirect(url_for('student_dashboard'))

        # Get all questions for this quiz to compare answers
        cursor.execute("SELECT id, correct_answer, question_type FROM questions WHERE quiz_id = %s", (quiz_id,))
        quiz_questions_from_db = cursor.fetchall() # Renamed
        # Map questions by ID for easy lookup
        questions_map_db = {q['id']: {'correct': q['correct_answer'], 'type': q['question_type']} for q in quiz_questions_from_db}
        total_questions_in_quiz = len(questions_map_db)

        if total_questions_in_quiz == 0:
            flash("Quiz này hiện không có câu hỏi nào. Không thể nộp bài.", "warning")
            return redirect(url_for('student_take_quiz', quiz_id=quiz_id))


        # Create an attempt record first (score will be updated later)
        attempt_insert_query = "INSERT INTO quiz_attempts (quiz_id, student_id, score) VALUES (%s, %s, %s)"
        cursor.execute(attempt_insert_query, (quiz_id, current_user_obj.id, 0.0)) # Initial score 0
        attempt_id_created = cursor.lastrowid

        submitted_answers_from_form = request.form # Renamed

        for q_db_id, q_data_db in questions_map_db.items():
            student_answer_key_form = f"answers[{q_db_id}]" # Key from the form
            # The form names in student_take_quiz.html are like "question_{{ question.id }}"
            # This needs to be consistent. Let's assume student_take_quiz.html uses `answers[{{question.id}}]`
            # If it's `question_{{question.id}}`, then key should be `question_${q_db_id}`
            
            # Corrected key based on common template structure
            student_answer_key_form_corrected = f"question_{q_db_id}"
            student_answer_value_submitted = submitted_answers_from_form.get(student_answer_key_form_corrected)
            
            is_answer_correct = False
            correct_db_answer_normalized = q_data_db['correct'].strip().lower() if q_data_db['correct'] else ""
            student_submitted_answer_normalized = student_answer_value_submitted.strip().lower() if student_answer_value_submitted else ""

            if student_answer_value_submitted is not None and student_submitted_answer_normalized == correct_db_answer_normalized:
                is_answer_correct = True
                score_achieved_count += 1
            
            ans_insert_sql = """
                INSERT INTO attempt_answers (attempt_id, question_id, student_answer, is_correct)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(ans_insert_sql, (attempt_id_created, q_db_id, student_answer_value_submitted, is_answer_correct))

        final_score_percentage = (score_achieved_count / total_questions_in_quiz) * 100 if total_questions_in_quiz > 0 else 0.0
        cursor.execute("UPDATE quiz_attempts SET score = %s WHERE id = %s", (final_score_percentage, attempt_id_created))
        
        conn.commit()
        flash(f"Bài quiz đã được nộp! Điểm của bạn: {score_achieved_count}/{total_questions_in_quiz} ({final_score_percentage:.2f}%)", "success")
        return redirect(url_for('student_quiz_results', attempt_id=attempt_id_created))

    except Error as e:
        app.logger.error(f"Lỗi CSDL khi nộp quiz {quiz_id} cho sinh viên {current_user_obj.id}: {e}")
        flash(f"Lỗi khi nộp bài quiz: {e}", "danger")
        if conn and conn.is_connected(): conn.rollback()
    except Exception as e: # Catch other unexpected errors during processing
        app.logger.error(f"Lỗi không mong muốn khi nộp quiz {quiz_id} cho sinh viên {current_user_obj.id}: {e}")
        flash(f"Lỗi không mong muốn khi nộp quiz: {e}", "danger")
        if conn and conn.is_connected(): conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    
    # Fallback redirect if error occurs before successful submission
    return redirect(url_for('student_take_quiz', quiz_id=quiz_id))


@app.route('/student/quiz_results/<int:attempt_id>')
@login_required(role='student')
def student_quiz_results(attempt_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn: return redirect(url_for('student_dashboard'))

    attempt_details_data = None # Renamed
    answers_details_list = [] # Renamed
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Fetch attempt details, ensuring it belongs to the current user
        attempt_query = """
            SELECT qa.id, qa.quiz_id, qa.student_id, qa.score, qa.attempted_at, 
                   q.title as quiz_title, q.course_id, c.course_name
            FROM quiz_attempts qa
            JOIN quizzes q ON qa.quiz_id = q.id
            JOIN courses c ON q.course_id = c.id
            WHERE qa.id = %s AND qa.student_id = %s 
        """ # Added course_id and course_name for context
        cursor.execute(attempt_query, (attempt_id, current_user_obj.id))
        attempt_details_data = cursor.fetchone()

        if not attempt_details_data:
            flash("Không tìm thấy kết quả bài làm hoặc bạn không có quyền xem.", "danger")
            return redirect(url_for('student_dashboard'))
        
        # Fetch answers for this attempt, along with question details
        answers_query = """
            SELECT aa.student_answer, aa.is_correct, 
                   q.id as question_id, q.question_text, q.correct_answer, q.options, q.question_type
            FROM attempt_answers aa
            JOIN questions q ON aa.question_id = q.id
            WHERE aa.attempt_id = %s
            ORDER BY q.id 
        """ # Assuming default order by question ID
        cursor.execute(answers_query, (attempt_id,))
        answers_raw_data = cursor.fetchall() # Renamed

        for ans_item in answers_raw_data: # Renamed loop var
            if ans_item['question_type'] == 'multiple_choice' and ans_item['options']:
                try:
                    ans_item['options_list'] = json.loads(ans_item['options'])
                    if not isinstance(ans_item['options_list'], list): ans_item['options_list'] = []
                except (json.JSONDecodeError, TypeError):
                    ans_item['options_list'] = []
                    app.logger.warning(f"Quiz Result Attempt {attempt_id}, Question {ans_item['question_id']}: JSON options decode error. Options: {ans_item['options']}")
            else:
                ans_item['options_list'] = []
            answers_details_list.append(ans_item)

    except Error as e:
        app.logger.error(f"Lỗi CSDL lấy kết quả quiz cho lần làm {attempt_id}, sinh viên {current_user_obj.id}: {e}")
        flash("Lỗi tải kết quả quiz.", "danger")
        return redirect(url_for('student_dashboard')) # Safe redirect
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
        
    return render_template('student_quiz_results.html', 
                           attempt=attempt_details_data, 
                           answers=answers_details_list,
                           quiz_title=attempt_details_data.get('quiz_title'), # Pass separately for clarity in template
                           course_name=attempt_details_data.get('course_name'))


# --- General Routes ---
@app.route('/')
def index():
    current_user_obj = get_current_user_object()
    if current_user_obj:
        if current_user_obj.role == 'student':
            return redirect(url_for('student_dashboard'))
        elif current_user_obj.role == 'faculty':
            return redirect(url_for('faculty_dashboard'))
    return redirect(url_for('login')) # Default to login if no user or unknown role

@app.context_processor
def inject_current_year():
    """Cung cấp biến current_year cho tất cả các template."""
    return {'current_year': datetime.datetime.now().year}


if __name__ == '__main__':
    # For production, use a WSGI server like Gunicorn or Waitress
    # app.run(debug=False) # debug=True is for development only
    app.run(debug=True, port=5001) # Changed port for potential conflicts