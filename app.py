from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.utils import secure_filename
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
    # Hàm này được sử dụng nội bộ trong Python, template sẽ dùng current_user từ context_processor
    if 'user_id' in session and 'username' in session and 'role' in session:
        return User(session['user_id'], session['username'], session['role'], session.get('full_name'))
    return None


def login_required(role=None):
    """Decorator để bảo vệ các route yêu cầu đăng nhập."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_user = get_current_user_object() # Sử dụng hàm mới để lấy object User
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
        date_obj = datetime.datetime.strptime(str(value), '%Y-%m-%d')
        return date_obj.strftime(format_str)
    except (ValueError, TypeError):
        app.logger.warning(f"Không thể định dạng ngày: {value}")
        try: # Thử định dạng nếu value đã là đối tượng date/datetime
            return value.strftime(format_str)
        except AttributeError:
             return str(value)


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
            # QUAN TRỌNG: Trong ứng dụng thực tế, hãy lưu trữ và kiểm tra mật khẩu đã HASH!
            query = "SELECT id, username, password, role, full_name FROM users WHERE username = %s AND role = %s"
            cursor.execute(query, (username, role))
            user_data = cursor.fetchone()

            if user_data and user_data['password'] == password: # Thay thế bằng kiểm tra hash mật khẩu
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
        finally:
            if cursor: cursor.close()
            if conn and conn.is_connected(): conn.close()
        
    return render_template('login.html')

@app.route('/logout')
@login_required() # Đảm bảo chỉ người đã đăng nhập mới logout được
def logout():
    """Xử lý đăng xuất người dùng."""
    logout_user_session()
    flash('Bạn đã đăng xuất.', 'info')
    return redirect(url_for('login'))

# --- Student Routes ---
@app.route('/student/dashboard')
@login_required(role='student')
def student_dashboard():
    """Hiển thị dashboard của sinh viên."""
    # current_user đã có sẵn trong template nhờ context_processor
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('login')) 

    student_courses = []
    current_user_obj = get_current_user_object() # Lấy object User để dùng ID
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
            
    return render_template('index.html', courses=student_courses) # current_user đã có sẵn


# @app.route('/student/select_session/<int:course_id>')
# @login_required(role='student')
# def student_select_session(course_id):
#     """Cho phép sinh viên chọn một buổi học của khóa học."""
#     current_user_obj = get_current_user_object()
#     conn = get_db_connection()
#     if not conn:
#         return redirect(url_for('student_dashboard'))

#     course = None
#     sessions = []
#     cursor = None
#     try:
#         cursor = conn.cursor(dictionary=True)
#         cursor.execute("SELECT id, course_code, course_name FROM courses WHERE id = %s", (course_id,))
#         course = cursor.fetchone()

#         if not course:
#             flash("Khóa học không tồn tại.", "danger")
#             return redirect(url_for('student_dashboard'))

#         cursor.execute("SELECT * FROM enrollments WHERE student_id = %s AND course_id = %s", (current_user_obj.id, course_id))
#         if not cursor.fetchone():
#             flash("Bạn chưa ghi danh vào khóa học này.", "warning")
#             return redirect(url_for('student_dashboard'))

#         cursor.execute("""
#             SELECT id, session_title, session_date, start_time, end_time, lecturer_name, location, event_type 
#             FROM course_sessions 
#             WHERE course_id = %s 
#             ORDER BY session_date DESC, start_time DESC, id DESC
#         """, (course_id,))
#         sessions = cursor.fetchall()

#     except Error as e:
#         app.logger.error(f"Lỗi lấy danh sách buổi học cho khóa {course_id}: {e}")
#         flash("Không thể tải danh sách buổi học.", "danger")
#     finally:
#         if cursor: cursor.close()
#         if conn and conn.is_connected(): conn.close()

#     return render_template('student_select_session.html', course=course, sessions=sessions) # current_user đã có sẵn
@app.route('/student/select_session/<int:course_id>')
@login_required(role='student')
def student_select_session(course_id):
    """Cho phép sinh viên chọn một buổi học của khóa học."""
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        # Nếu không có kết nối DB, flash message đã được set trong get_db_connection
        # và chúng ta nên chuyển hướng đến một trang an toàn hơn, ví dụ student_dashboard
        return redirect(url_for('student_dashboard')) # Đã sửa: Chuyển hướng khi không có conn

    course_data = None # Đổi tên từ 'course' để tránh nhầm lẫn với biến 'courses' trong các template khác
    sessions = []
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Lấy thông tin khóa học
        cursor.execute("SELECT id, course_code, course_name FROM courses WHERE id = %s", (course_id,))
        course_data = cursor.fetchone() # Gán dữ liệu vào course_data

        if not course_data:
            flash("Khóa học không tồn tại.", "danger")
            return redirect(url_for('student_dashboard'))

        # Kiểm tra sinh viên có ghi danh vào khóa học này không
        cursor.execute("SELECT * FROM enrollments WHERE student_id = %s AND course_id = %s", (current_user_obj.id, course_id))
        if not cursor.fetchone():
            flash("Bạn chưa ghi danh vào khóa học này.", "warning")
            return redirect(url_for('student_dashboard'))

        # Lấy các buổi học của khóa học
        cursor.execute("""
            SELECT id, session_title, session_date, start_time, end_time, lecturer_name, location, event_type 
            FROM course_sessions 
            WHERE course_id = %s 
            ORDER BY session_date DESC, start_time DESC, id DESC
        """, (course_id,))
        sessions = cursor.fetchall()

    except Error as e:
        app.logger.error(f"Lỗi lấy danh sách buổi học cho khóa {course_id}: {e}")
        flash("Không thể tải danh sách buổi học.", "danger")
        # Trong trường hợp lỗi, course_data có thể vẫn là None
        # Chúng ta vẫn nên cố gắng render template với những gì có thể, hoặc redirect
        return redirect(url_for('student_dashboard')) # Chuyển hướng khi có lỗi DB nghiêm trọng
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    # Đảm bảo course_data được truyền vào template với tên là 'course'
    return render_template('student_select_session.html', course=course_data, sessions=sessions)

# --- Faculty Routes ---
@app.route('/faculty/dashboard')
@login_required(role='faculty')
def faculty_dashboard():
    """Hiển thị dashboard của giảng viên."""
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('login'))

    faculty_courses = []
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Lấy các khóa học mà giảng viên này là người phụ trách chính
        query = "SELECT id, course_code, course_name, credits FROM courses WHERE faculty_id = %s" 
        cursor.execute(query, (current_user_obj.id,))
        faculty_courses = cursor.fetchall()
        
    except Error as e:
        app.logger.error(f"Lỗi lấy danh sách khóa học của giảng viên {current_user_obj.id}: {e}")
        flash("Không thể tải danh sách khóa học.", "danger")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
            
    return render_template('faculty_dashboard.html', courses=faculty_courses) # current_user đã có sẵn


@app.route('/faculty/course_sessions/<int:course_id>', methods=['GET', 'POST'])
@login_required(role='faculty')
def faculty_course_sessions(course_id):
    """Quản lý các buổi học của khóa học cho giảng viên."""
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('faculty_dashboard'))

    course = None
    sessions = []
    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)
        # Xác thực giảng viên có quyền quản lý khóa học này
        cursor.execute("SELECT id, course_code, course_name FROM courses WHERE id = %s AND faculty_id = %s", (course_id, current_user_obj.id))
        course = cursor.fetchone()

        if not course: # Nếu không phải GV chính, kiểm tra xem có phải GV dạy buổi nào trong khóa không
            cursor.execute("""
                SELECT DISTINCT c.id, c.course_code, c.course_name FROM courses c
                JOIN course_sessions cs ON c.id = cs.course_id
                WHERE c.id = %s AND cs.lecturer_name = %s LIMIT 1 
            """, (course_id, current_user_obj.full_name)) 
            course_as_lecturer = cursor.fetchone()
            if not course_as_lecturer:
                flash("Khóa học không hợp lệ hoặc bạn không có quyền quản lý buổi học cho khóa này.", "danger")
                return redirect(url_for('faculty_dashboard'))
            course = course_as_lecturer # Cho phép quản lý nếu là GV của ít nhất 1 buổi


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
        sessions = cursor.fetchall()

    except Error as e:
        app.logger.error(f"Lỗi CSDL trong faculty_course_sessions cho khóa {course_id}: {e}")
        flash(f"Lỗi cơ sở dữ liệu: {e}", "danger")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
            
    return render_template('faculty_course_sessions.html', course=course, sessions=sessions) # current_user đã có sẵn


@app.route('/faculty/upload_material/<int:session_id>', methods=['GET', 'POST'])
@login_required(role='faculty')
def faculty_upload_material(session_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('faculty_dashboard'))

    session_details = None
    materials = []
    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)
        query_session = """
            SELECT cs.id, cs.session_title, cs.course_id, c.faculty_id, cs.lecturer_name
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
                session_upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'session_materials', str(session_id))
                if not os.path.exists(session_upload_folder):
                    os.makedirs(session_upload_folder)
                
                file_path_on_server = os.path.join(session_upload_folder, filename)
                
                cursor.execute("SELECT id FROM session_materials WHERE session_id = %s AND file_name = %s", (session_id, filename))
                if cursor.fetchone():
                    flash(f"Tệp '{filename}' đã tồn tại cho buổi học này. Vui lòng đổi tên tệp hoặc xóa tệp cũ.", "warning")
                else:
                    try:
                        file.save(file_path_on_server)
                        db_file_path = os.path.join('session_materials', str(session_id), filename).replace("\\","/") 
                        insert_query = """
                            INSERT INTO session_materials (session_id, file_name, file_path, uploaded_by)
                            VALUES (%s, %s, %s, %s)
                        """
                        cursor.execute(insert_query, (session_id, filename, db_file_path, current_user_obj.id))
                        conn.commit()
                        flash(f"Tệp '{filename}' đã được tải lên thành công.", 'success')
                    except Error as e:
                        app.logger.error(f"Lỗi CSDL khi lưu tài liệu cho buổi {session_id}: {e}")
                        flash(f"Lỗi khi lưu thông tin tệp vào cơ sở dữ liệu.", "danger")
                        if conn.is_connected(): conn.rollback()
                    except Exception as e:
                        app.logger.error(f"Lỗi lưu file cho buổi {session_id}, file {filename}: {e}")
                        flash(f"Lỗi khi lưu tệp: {e}", "danger")
                return redirect(url_for('faculty_upload_material', session_id=session_id))

        cursor.execute("SELECT id, file_name, uploaded_at FROM session_materials WHERE session_id = %s ORDER BY uploaded_at DESC", (session_id,))
        materials = cursor.fetchall()

    except Error as e:
        app.logger.error(f"Lỗi CSDL trong faculty_upload_material cho buổi {session_id}: {e}")
        flash(f"Lỗi cơ sở dữ liệu: {e}", "danger")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
            
    return render_template('faculty_upload_material.html', session=session_details, materials=materials) # current_user đã có sẵn


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
        
        full_path_to_file = os.path.join(app.config['UPLOAD_FOLDER'], material['file_path'])
        directory_for_send = os.path.dirname(full_path_to_file)
        filename_for_send = os.path.basename(full_path_to_file)

        if not os.path.exists(full_path_to_file):
            app.logger.error(f"Tệp tài liệu không tìm thấy tại: {full_path_to_file} cho material_id: {material_id}")
            flash("Tệp tài liệu không tìm thấy trên máy chủ.", "danger")
            return redirect(request.referrer or url_for('student_dashboard' if current_user_obj.role == 'student' else 'faculty_dashboard'))

        return send_from_directory(directory=directory_for_send, path=filename_for_send, as_attachment=True)

    except Error as e:
        app.logger.error(f"Lỗi CSDL khi tải tài liệu {material_id}: {e}")
        flash(f"Lỗi cơ sở dữ liệu khi tải tài liệu.", "danger")
    except Exception as e:
        app.logger.error(f"Lỗi chung khi tải tài liệu {material_id}: {e}")
        flash(f"Lỗi không xác định khi tải tài liệu.", "danger")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    return redirect(request.referrer or url_for('student_dashboard' if current_user_obj.role == 'student' else 'faculty_dashboard'))

# --- Notes Routes ---
@app.route('/notes/session/<int:session_id>')
@login_required()
def course_notes_overview(session_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('login'))

    session_info = None
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
        session_info = cursor.fetchone()

        if not session_info:
            flash("Buổi học không tồn tại.", "danger")
            return redirect(url_for('student_dashboard') if current_user_obj.role == 'student' else url_for('faculty_dashboard'))
        
        can_view_session = False
        if current_user_obj.role == 'student':
            cursor.execute("SELECT * FROM enrollments WHERE student_id = %s AND course_id = %s", (current_user_obj.id, session_info['course_id']))
            if cursor.fetchone():
                can_view_session = True
        elif current_user_obj.role == 'faculty':
            if session_info['course_faculty_id'] == current_user_obj.id or session_info['session_lecturer_name'] == current_user_obj.full_name:
                can_view_session = True
        
        if not can_view_session:
            flash("Bạn không có quyền xem ghi chú cho buổi học này.", "danger")
            return redirect(url_for('student_dashboard') if current_user_obj.role == 'student' else url_for('faculty_dashboard'))

        notes_query = "SELECT id, title, LEFT(content, 100) as preview, updated_at FROM notes WHERE session_id = %s AND user_id = %s ORDER BY updated_at DESC"
        cursor.execute(notes_query, (session_id, current_user_obj.id))
        notes_list = cursor.fetchall()

    except Error as e:
        app.logger.error(f"Lỗi lấy ghi chú cho buổi {session_id}, người dùng {current_user_obj.id}: {e}")
        flash("Không thể tải ghi chú.", "danger")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
            
    return render_template('course_notes_overview.html', session_info=session_info, notes=notes_list) # current_user đã có sẵn


@app.route('/notes/create/<int:session_id>', methods=['GET', 'POST'])
@login_required()
def create_note(session_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('course_notes_overview', session_id=session_id)) 

    session_info = None
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
        session_info = cursor.fetchone()
        if not session_info:
            flash("Buổi học không hợp lệ.", "danger")
            return redirect(url_for('student_dashboard') if current_user_obj.role == 'student' else url_for('faculty_dashboard'))

        can_create_note = False
        if current_user_obj.role == 'student':
            cursor.execute("SELECT * FROM enrollments WHERE student_id = %s AND course_id = %s", (current_user_obj.id, session_info['course_id']))
            if cursor.fetchone():
                can_create_note = True
        elif current_user_obj.role == 'faculty':
             if session_info['course_faculty_id'] == current_user_obj.id or session_info['session_lecturer_name'] == current_user_obj.full_name:
                can_create_note = True
        
        if not can_create_note:
            flash("Bạn không có quyền tạo ghi chú cho buổi học này.", "danger")
            return redirect(url_for('course_notes_overview', session_id=session_id))


        if request.method == 'POST':
            title = request.form.get('title', 'Ghi chú không tiêu đề')
            content = request.form.get('content', '')

            insert_query = "INSERT INTO notes (session_id, user_id, title, content) VALUES (%s, %s, %s, %s)"
            cursor.execute(insert_query, (session_id, current_user_obj.id, title, content))
            conn.commit()
            new_note_id = cursor.lastrowid 
            flash('Ghi chú đã được tạo thành công!', 'success')
            return redirect(url_for('edit_note', note_id=new_note_id))
            
    except Error as e:
        app.logger.error(f"Lỗi tạo ghi chú cho buổi {session_id}, người dùng {current_user_obj.id}: {e}")
        flash(f"Lỗi khi tạo ghi chú: {e}", "danger")
        if conn and conn.is_connected(): conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('notes_template.html', session_info=session_info, note=None, is_new=True, session_id=session_id) # current_user đã có sẵn


@app.route('/notes/edit/<int:note_id>', methods=['GET', 'POST'])
@login_required()
def edit_note(note_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('login')) 

    note_data = None
    session_info_for_template = None 
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        query_note = """
            SELECT n.id, n.title, n.content, n.session_id, n.user_id,
                   cs.session_title, crs.course_name
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

        if note_data['session_id']:
             session_info_for_template = { # Đổi tên biến để tránh nhầm lẫn
                'id': note_data['session_id'],
                'session_title': note_data['session_title'],
                'course_name': note_data['course_name']
            }

        if request.method == 'POST':
            title = request.form.get('title', note_data['title'])
            content = request.form.get('content', note_data['content'])
            
            update_query = "UPDATE notes SET title = %s, content = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s AND user_id = %s"
            cursor.execute(update_query, (title, content, note_id, current_user_obj.id))
            conn.commit()
            flash('Ghi chú đã được cập nhật!', 'success')
            cursor.execute(query_note, (note_id, current_user_obj.id)) 
            note_data = cursor.fetchone() # Tải lại dữ liệu mới nhất
            if note_data and note_data['session_id']: # Cập nhật lại session_info_for_template
                 session_info_for_template = {
                    'id': note_data['session_id'],
                    'session_title': note_data['session_title'],
                    'course_name': note_data['course_name']
                }

    except Error as e:
        app.logger.error(f"Lỗi sửa ghi chú {note_id} cho người dùng {current_user_obj.id}: {e}")
        flash(f"Lỗi khi cập nhật ghi chú: {e}", "danger")
        if conn and conn.is_connected(): conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    if not note_data: 
        flash("Không thể tải ghi chú để chỉnh sửa.", "danger")
        return redirect(url_for('student_dashboard') if current_user_obj.role == 'student' else url_for('faculty_dashboard'))
        
    return render_template('notes_template.html', note=note_data, session_info=session_info_for_template, is_new=False, session_id=note_data.get('session_id')) # current_user đã có sẵn


@app.route('/notes/delete/<int:note_id>', methods=['POST'])
@login_required()
def delete_note(note_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Lỗi kết nối cơ sở dữ liệu.'})

    cursor = None
    original_session_id = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT session_id FROM notes WHERE id = %s AND user_id = %s", (note_id, current_user_obj.id))
        note_info = cursor.fetchone()
        if note_info:
            original_session_id = note_info['session_id']
        else: 
            return jsonify({'success': False, 'message': 'Không tìm thấy ghi chú hoặc không có quyền xóa.'}) # flash() không hoạt động tốt với jsonify


        delete_query = "DELETE FROM notes WHERE id = %s AND user_id = %s"
        cursor.execute(delete_query, (note_id, current_user_obj.id))
        conn.commit()

        if cursor.rowcount > 0:
            flash('Ghi chú đã được xóa.', 'success') # flash sẽ hiển thị ở trang redirect tiếp theo
            redirect_url = url_for('course_notes_overview', session_id=original_session_id) if original_session_id else \
                           (url_for('student_dashboard') if current_user_obj.role == 'student' else url_for('faculty_dashboard'))
            return jsonify({'success': True, 'redirect_url': redirect_url})
        else:
            return jsonify({'success': False, 'message': 'Không thể xóa ghi chú.'})

    except Error as e:
        app.logger.error(f"Lỗi xóa ghi chú {note_id} cho người dùng {current_user_obj.id}: {e}")
        if conn and conn.is_connected(): conn.rollback()
        return jsonify({'success': False, 'message': f'Lỗi cơ sở dữ liệu: {e}'})
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    
    fallback_redirect = url_for('student_dashboard') if current_user_obj.role == 'student' else url_for('faculty_dashboard')
    return jsonify({'success': False, 'message': 'Lỗi không xác định khi xóa.', 'redirect_url': fallback_redirect })


# --- Flashcard Routes ---
@app.route('/student/flashcard_hub/course/<int:course_id>')
@login_required(role='student')
def student_flashcard_hub_course(course_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn: return redirect(url_for('student_dashboard')) 

    course_info = None
    hubs = []
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, course_code, course_name FROM courses WHERE id = %s", (course_id,))
        course_info = cursor.fetchone()
        if not course_info:
            flash("Khóa học không tồn tại.", "danger")
            return redirect(url_for('student_dashboard'))
        
        cursor.execute("SELECT * FROM enrollments WHERE student_id = %s AND course_id = %s", (current_user_obj.id, course_id))
        if not cursor.fetchone():
            flash("Bạn chưa ghi danh vào khóa học này để xem flashcards.", "warning")
            return redirect(url_for('student_dashboard'))

        hub_query = "SELECT id, name, created_at FROM flashcard_hubs WHERE user_id = %s AND course_id = %s ORDER BY name"
        cursor.execute(hub_query, (current_user_obj.id, course_id))
        hubs = cursor.fetchall()
    except Error as e:
        app.logger.error(f"Lỗi CSDL lấy flashcard hubs cho khóa {course_id}, người dùng {current_user_obj.id}: {e}")
        flash("Lỗi tải bộ flashcard.", "danger")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('student_flashcard_hub.html', course=course_info, hubs=hubs) # current_user đã có sẵn

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
        cursor = conn.cursor(dictionary=True) 
        cursor.execute("SELECT * FROM enrollments WHERE student_id = %s AND course_id = %s", (current_user_obj.id, course_id))
        if not cursor.fetchone():
            flash("Bạn cần ghi danh vào khóa học để tạo bộ flashcard.", "warning")
            return redirect(url_for('student_dashboard'))

        insert_query = "INSERT INTO flashcard_hubs (user_id, course_id, name) VALUES (%s, %s, %s)"
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

    hub_info = None
    flashcards_list = []
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
        hub_info = cursor.fetchone()

        if not hub_info:
            flash("Bộ flashcard không tồn tại hoặc bạn không có quyền truy cập.", "danger")
            return redirect(url_for('student_dashboard')) 

        fc_query = "SELECT id, question, answer FROM flashcards WHERE hub_id = %s ORDER BY id"
        cursor.execute(fc_query, (hub_id,))
        flashcards_list = cursor.fetchall()
    except Error as e:
        app.logger.error(f"Lỗi CSDL lấy flashcards cho hub {hub_id}, người dùng {current_user_obj.id}: {e}")
        flash("Lỗi tải flashcards.", "danger")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
        
    return render_template('student_view_flashcards.html', hub=hub_info, flashcards=flashcards_list) # current_user đã có sẵn


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
        cursor = conn.cursor() # Không cần dictionary=True cho SELECT đơn giản này
        cursor.execute("SELECT id FROM flashcard_hubs WHERE id = %s AND user_id = %s", (hub_id, current_user_obj.id))
        if not cursor.fetchone():
            flash("Bạn không có quyền thêm flashcard vào bộ này.", "danger")
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

    course_info = None
    quizzes_list = []
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, course_code, course_name FROM courses WHERE id = %s AND faculty_id = %s", (course_id, current_user_obj.id))
        course_info = cursor.fetchone()
        if not course_info:
            flash("Khóa học không hợp lệ hoặc bạn không có quyền quản lý quiz cho khóa học này.", "danger")
            return redirect(url_for('faculty_dashboard'))

        quiz_query = "SELECT id, title, created_at FROM quizzes WHERE course_id = %s AND created_by = %s ORDER BY created_at DESC"
        cursor.execute(quiz_query, (course_id, current_user_obj.id))
        quizzes_list = cursor.fetchall()
    except Error as e:
        app.logger.error(f"Lỗi CSDL lấy quizzes cho khóa {course_id}, giảng viên {current_user_obj.id}: {e}")
        flash("Lỗi tải danh sách quiz.", "danger")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('faculty_manage_quiz.html', course=course_info, quizzes=quizzes_list) # current_user đã có sẵn


@app.route('/faculty/quiz/create/<int:course_id>', methods=['GET', 'POST'])
@login_required(role='faculty')
def faculty_create_quiz(course_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('faculty_manage_quiz', course_id=course_id))

    course_info = None
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, course_code, course_name FROM courses WHERE id = %s AND faculty_id = %s", (course_id, current_user_obj.id))
        course_info = cursor.fetchone()
        if not course_info:
            flash("Khóa học không hợp lệ hoặc bạn không có quyền tạo quiz cho khóa học này.", "danger")
            return redirect(url_for('faculty_dashboard'))

        if request.method == 'POST':
            quiz_title = request.form.get('quiz_title')
            if not quiz_title:
                flash("Tiêu đề quiz là bắt buộc.", "warning")
                questions_data = [] # Để giữ lại dữ liệu câu hỏi nếu form submit lỗi
                q_idx = 0
                while True:
                    q_text = request.form.get(f'questions[{q_idx}][question_text]')
                    if q_text is None and q_idx > 0 : break # Dừng nếu không còn câu hỏi (và đã có ít nhất 1 câu)
                    if q_text is None and q_idx == 0 : # Xử lý trường hợp không có câu hỏi nào được nhập ban đầu
                        questions_data.append({}) # Thêm một câu hỏi trống để template render
                        break
                    questions_data.append({
                        'question_text': q_text or "",
                        'question_type': request.form.get(f'questions[{q_idx}][question_type]'),
                        'options': [opt for opt_idx in range(4) if (opt := request.form.get(f'questions[{q_idx}][options][{opt_idx}]'))], # Max 4 options assumed
                        'correct_answer': request.form.get(f'questions[{q_idx}][correct_answer]')
                    })
                    q_idx += 1
                return render_template('faculty_create_quiz_form.html', course=course_info, quiz_title=quiz_title, questions=questions_data)


            quiz_id = None
            try:
                # Bắt đầu transaction (nếu MySQL engine hỗ trợ và connector cho phép)
                # conn.start_transaction() 
                
                quiz_insert_query = "INSERT INTO quizzes (course_id, title, created_by) VALUES (%s, %s, %s)"
                cursor.execute(quiz_insert_query, (course_id, quiz_title, current_user_obj.id))
                quiz_id = cursor.lastrowid
                
                q_idx = 0
                any_question_added = False
                while True:
                    question_text = request.form.get(f'questions[{q_idx}][question_text]')
                    # Dừng nếu không có text câu hỏi VÀ đây không phải là câu hỏi đầu tiên (để cho phép quiz không có câu hỏi ban đầu)
                    if not question_text and q_idx > 0 and not any_question_added : 
                        break 
                    if not question_text and any_question_added: # Nếu đã có câu hỏi được thêm, câu hỏi trống tiếp theo nghĩa là hết
                        break
                    if not question_text and q_idx == 0 and not request.form.get(f'questions[{q_idx+1}][question_text]'): # Nếu câu đầu trống và không có câu sau
                        break


                    question_type = request.form.get(f'questions[{q_idx}][question_type]')
                    correct_answer = request.form.get(f'questions[{q_idx}][correct_answer]')
                    
                    options_list = []
                    if question_type == 'multiple_choice':
                        opt_inner_idx = 0
                        while True: # Lấy tối đa 4-5 options hoặc cho đến khi không còn
                            option_val = request.form.get(f'questions[{q_idx}][options][{opt_inner_idx}]')
                            if option_val is None or opt_inner_idx >= 5: break 
                            if option_val.strip(): options_list.append(option_val.strip())
                            opt_inner_idx +=1
                    
                    options_json = json.dumps(options_list) if options_list else None

                    if question_text and question_type and correct_answer:
                        q_insert = """INSERT INTO questions (quiz_id, question_text, question_type, options, correct_answer)
                                      VALUES (%s, %s, %s, %s, %s)"""
                        cursor.execute(q_insert, (quiz_id, question_text, question_type, options_json, correct_answer))
                        any_question_added = True
                    elif question_text and not (question_type and correct_answer): # Nếu có text câu hỏi nhưng thiếu thông tin khác
                        flash(f"Câu hỏi {q_idx+1} thiếu loại câu hỏi hoặc đáp án đúng.", "warning")
                        # Không commit và reload form ở đây, để người dùng sửa
                    q_idx += 1
                
                if not any_question_added and quiz_id: # Nếu quiz được tạo nhưng không có câu hỏi nào hợp lệ
                    flash("Quiz đã được tạo nhưng chưa có câu hỏi nào được thêm. Vui lòng thêm câu hỏi.", "info")
                    # Không commit nếu muốn quiz phải có câu hỏi, hoặc commit và cho phép sửa sau
                    # conn.commit() # Bỏ commit nếu muốn quiz phải có câu hỏi
                    # return redirect(url_for('faculty_edit_quiz', quiz_id=quiz_id)) # Chuyển đến trang sửa quiz
                
                conn.commit() # Commit sau khi tất cả câu hỏi đã được xử lý
                flash(f"Quiz '{quiz_title}' đã được tạo thành công!", "success")
                return redirect(url_for('faculty_manage_quiz', course_id=course_id))

            except Error as e:
                app.logger.error(f"Lỗi CSDL tạo quiz/câu hỏi cho khóa {course_id}: {e}")
                flash(f"Lỗi khi tạo quiz: {e}", "danger")
                if conn and conn.is_connected(): conn.rollback()
            except Exception as e:
                app.logger.error(f"Lỗi chung khi tạo quiz: {e}")
                flash(f"Lỗi không xác định khi tạo quiz: {e}", "danger")
                if conn and conn.is_connected(): conn.rollback()
        
        # GET request
        return render_template('faculty_create_quiz_form.html', course=course_info, quiz=None, questions=[{}]) # current_user đã có sẵn

    except Error as e:
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

    quiz_info = None
    questions = []
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT q.id, q.title, q.course_id, c.course_name FROM quizzes q JOIN courses c ON q.course_id = c.id WHERE q.id = %s", (quiz_id,))
        quiz_info = cursor.fetchone()
        if not quiz_info:
            flash("Quiz không tồn tại.", "danger")
            return redirect(url_for('student_dashboard'))
        
        cursor.execute("SELECT * FROM enrollments WHERE student_id = %s AND course_id = %s", (current_user_obj.id, quiz_info['course_id']))
        if not cursor.fetchone():
            flash("Bạn chưa ghi danh vào khóa học của quiz này.", "warning")
            return redirect(url_for('student_dashboard'))

        q_query = "SELECT id, question_text, question_type, options FROM questions WHERE quiz_id = %s ORDER BY id"
        cursor.execute(q_query, (quiz_id,))
        questions_raw = cursor.fetchall()
        
        for q in questions_raw:
            if q['question_type'] == 'multiple_choice' and q['options']:
                try:
                    q['options_list'] = json.loads(q['options'])
                except (json.JSONDecodeError, TypeError):
                    q['options_list'] = [] 
            else:
                q['options_list'] = []
            questions.append(q)

    except Error as e:
        app.logger.error(f"Lỗi CSDL lấy quiz {quiz_id} cho sinh viên {current_user_obj.id}: {e}")
        flash("Lỗi tải quiz.", "danger")
        return redirect(url_for('student_dashboard')) 
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
        
    return render_template('student_take_quiz.html', quiz=quiz_info, questions=questions) # current_user đã có sẵn


@app.route('/student/submit_quiz/<int:quiz_id>', methods=['POST'])
@login_required(role='student')
def student_submit_quiz(quiz_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('student_take_quiz', quiz_id=quiz_id))

    cursor = None
    attempt_id = None
    total_score_count = 0 
    num_questions = 0

    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT course_id FROM quizzes WHERE id = %s", (quiz_id,))
        quiz_course_data = cursor.fetchone()
        if not quiz_course_data:
            flash("Quiz không tồn tại.", "danger")
            return redirect(url_for('student_dashboard'))
        
        cursor.execute("SELECT * FROM enrollments WHERE student_id = %s AND course_id = %s", (current_user_obj.id, quiz_course_data['course_id']))
        if not cursor.fetchone():
            flash("Bạn không được phép làm quiz này.", "warning")
            return redirect(url_for('student_dashboard'))


        cursor.execute("SELECT id, correct_answer, question_type FROM questions WHERE quiz_id = %s", (quiz_id,))
        quiz_questions_db = cursor.fetchall()
        quiz_questions_map = {q['id']: {'correct': q['correct_answer'], 'type': q['question_type']} for q in quiz_questions_db}
        num_questions = len(quiz_questions_map)

        if not num_questions: # Mặc dù quiz có thể được tạo mà không có câu hỏi, nhưng không nên cho phép submit
            flash("Quiz này hiện không có câu hỏi nào để làm.", "warning")
            return redirect(url_for('student_select_session', course_id=quiz_course_data['course_id']) if quiz_course_data.get('course_id') else url_for('student_dashboard'))


        attempt_insert_query = "INSERT INTO quiz_attempts (quiz_id, student_id, score) VALUES (%s, %s, %s)"
        cursor.execute(attempt_insert_query, (quiz_id, current_user_obj.id, 0.0)) 
        attempt_id = cursor.lastrowid

        submitted_answers_form = request.form 

        for q_db_id, q_data in quiz_questions_map.items():
            student_ans_key = f"answers[{q_db_id}]" 
            student_answer_val = submitted_answers_form.get(student_ans_key)
            
            is_correct = False
            correct_db_answer_norm = q_data['correct'].strip().lower() if q_data['correct'] else ""
            student_submitted_answer_norm = student_answer_val.strip().lower() if student_answer_val else ""

            if student_answer_val is not None and student_submitted_answer_norm == correct_db_answer_norm:
                is_correct = True
                total_score_count += 1
            
            ans_insert_query = """
                INSERT INTO attempt_answers (attempt_id, question_id, student_answer, is_correct)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(ans_insert_query, (attempt_id, q_db_id, student_answer_val, is_correct))

        final_percentage_score = (total_score_count / num_questions) * 100 if num_questions > 0 else 0
        cursor.execute("UPDATE quiz_attempts SET score = %s WHERE id = %s", (final_percentage_score, attempt_id))
        
        conn.commit()
        flash(f"Bài quiz đã được nộp! Điểm của bạn: {total_score_count}/{num_questions} ({final_percentage_score:.2f}%)", "success")
        return redirect(url_for('student_quiz_results', attempt_id=attempt_id))

    except Error as e:
        app.logger.error(f"Lỗi CSDL khi nộp quiz {quiz_id} cho sinh viên {current_user_obj.id}: {e}")
        flash(f"Lỗi khi nộp bài quiz: {e}", "danger")
        if conn and conn.is_connected(): conn.rollback()
    except Exception as e:
        app.logger.error(f"Lỗi không mong muốn khi nộp quiz {quiz_id}: {e}")
        flash(f"Lỗi không mong muốn khi nộp quiz: {e}", "danger")
        if conn and conn.is_connected(): conn.rollback()
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

    attempt_details = None
    answers_details = []
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        attempt_query = """
            SELECT qa.id, qa.quiz_id, qa.student_id, qa.score, qa.attempted_at, q.title as quiz_title, c.course_name
            FROM quiz_attempts qa
            JOIN quizzes q ON qa.quiz_id = q.id
            JOIN courses c ON q.course_id = c.id
            WHERE qa.id = %s AND qa.student_id = %s
        """
        cursor.execute(attempt_query, (attempt_id, current_user_obj.id))
        attempt_details = cursor.fetchone()

        if not attempt_details:
            flash("Không tìm thấy kết quả bài làm hoặc bạn không có quyền xem.", "danger")
            return redirect(url_for('student_dashboard'))
        
        answers_query = """
            SELECT aa.student_answer, aa.is_correct, q.question_text, q.correct_answer, q.options, q.question_type
            FROM attempt_answers aa
            JOIN questions q ON aa.question_id = q.id
            WHERE aa.attempt_id = %s
            ORDER BY q.id
        """
        cursor.execute(answers_query, (attempt_id,))
        answers_raw = cursor.fetchall()

        for ans in answers_raw:
            if ans['question_type'] == 'multiple_choice' and ans['options']:
                try:
                    ans['options_list'] = json.loads(ans['options'])
                except (json.JSONDecodeError, TypeError): 
                    ans['options_list'] = []
            else:
                ans['options_list'] = []
            answers_details.append(ans)

    except Error as e:
        app.logger.error(f"Lỗi CSDL lấy kết quả quiz cho lần làm {attempt_id}, sinh viên {current_user_obj.id}: {e}")
        flash("Lỗi tải kết quả quiz.", "danger")
        return redirect(url_for('student_dashboard'))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
        
    return render_template('student_quiz_results.html', attempt=attempt_details, answers=answers_details) # current_user đã có sẵn

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
    """Cung cấp biến current_year cho tất cả các template."""
    return {'current_year': datetime.datetime.now().year}


if __name__ == '__main__':
    app.run(debug=True)
