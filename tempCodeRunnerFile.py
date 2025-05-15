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
DB_PASSWORD = "Khag12344@" # Mật khẩu của bạn - HÃY KIỂM TRA LẠI!
DB_NAME = "umtsmartnotes"   # Tên cơ sở dữ liệu của bạn - HÃY KIỂM TRA LẠI!

# --- Hàm trợ giúp Cơ sở dữ liệu ---
def get_db_connection():
    """Thiết lập kết nối đến cơ sở dữ liệu MySQL."""
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            # Thêm các tùy chọn khác nếu cần, ví dụ: charset='utf8mb4'
        )
        if conn.is_connected():
            app.logger.info("Successfully connected to the database.") # Ghi log khi kết nối thành công
            return conn
        else:
            app.logger.error("Failed to connect to the database (is_connected is False).")
            flash("Không thể kết nối đến cơ sở dữ liệu.", "danger")
            return None
    except Error as e:
        app.logger.error(f"Lỗi kết nối đến MySQL: {e}")
        flash(f"Lỗi kết nối cơ sở dữ liệu. Vui lòng thử lại sau hoặc liên hệ quản trị viên.", "danger")
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
    if 'user_id' in session and 'username' in session and 'role' in session:
        return {'current_user': User(session['user_id'], session['username'], session['role'], session.get('full_name'))}
    return {'current_user': None}


def get_current_user_object():
    if 'user_id' in session and 'username' in session and 'role' in session:
        return User(session['user_id'], session['username'], session['role'], session.get('full_name'))
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
        date_obj = datetime.datetime.strptime(str(value), '%Y-%m-%d').date()
        return date_obj.strftime(format_str)
    except (ValueError, TypeError) as e:
        app.logger.warning(f"Không thể định dạng ngày: {value}, Lỗi: {e}")
        return str(value) 


# --- Routes ---
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
        password = request.form['password']
        role = request.form['role']

        conn = get_db_connection()
        if not conn:
            # get_db_connection đã flash lỗi, chỉ cần render lại trang login
            return render_template('login.html') 

        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            # Đảm bảo bảng 'users' có cột 'password_hash'
            query = "SELECT id, username, password_hash, role, full_name FROM users WHERE username = %s AND role = %s"
            cursor.execute(query, (username, role))
            user_data = cursor.fetchone()

            if user_data and user_data.get('password_hash') and check_password_hash(user_data['password_hash'], password):
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
            app.logger.error(f"Lỗi truy vấn CSDL khi đăng nhập cho người dùng {username}: {e}")
            # Flash thông báo lỗi cụ thể hơn nếu có thể, hoặc giữ thông báo chung
            flash(f"Lỗi truy vấn cơ sở dữ liệu khi đăng nhập. Vui lòng kiểm tra lại thông tin hoặc liên hệ quản trị viên.", "danger")
        except Exception as e: # Bắt các lỗi không mong muốn khác
            app.logger.error(f"Lỗi không xác định khi đăng nhập: {e}")
            flash("Đã xảy ra lỗi không mong muốn trong quá trình đăng nhập. Vui lòng thử lại.", "danger")
        finally:
            if cursor: 
                cursor.close()
            if conn and conn.is_connected(): 
                conn.close()
                app.logger.info("Database connection closed.")

    return render_template('login.html')


@app.route('/register_test_user_once', methods=['GET'])
def register_test_user_once():
    # Hàm này chỉ nên chạy MỘT LẦN để tạo người dùng thử nghiệm với mật khẩu đã băm
    # Sau khi chạy thành công, bạn nên XÓA hoặc COMMENT OUT route này để tránh tạo lại.
    
    # conn = get_db_connection()
    # if not conn:
    #     return "Lỗi kết nối CSDL."
    # cursor = None
    # results = []
    # try:
    #     cursor = conn.cursor()
        
    #     # Kiểm tra và tạo người dùng sinh viên
    #     student_username = "khang.id@st.umt.edu.vn"
    #     student_password = "studentpass" # Mật khẩu gốc
    #     hashed_student_password = generate_password_hash(student_password)
        
    #     cursor.execute("SELECT id FROM users WHERE username = %s AND role = %s", (student_username, "student"))
    #     if not cursor.fetchone():
    #         sql_student = "INSERT INTO users (username, password_hash, role, full_name) VALUES (%s, %s, %s, %s)"
    #         val_student = (student_username, hashed_student_password, "student", "Nguyễn Văn Khang")
    #         cursor.execute(sql_student, val_student)
    #         conn.commit()
    #         results.append(f"Người dùng sinh viên '{student_username}' đã được tạo với mật khẩu đã băm.")
    #     else:
    #         results.append(f"Người dùng sinh viên '{student_username}' đã tồn tại.")

    #     # Kiểm tra và tạo người dùng giảng viên
    #     faculty_username = "gv_khang.id"
    #     faculty_password = "facultypass" # Mật khẩu gốc
    #     hashed_faculty_password = generate_password_hash(faculty_password)

    #     cursor.execute("SELECT id FROM users WHERE username = %s AND role = %s", (faculty_username, "faculty"))
    #     if not cursor.fetchone():
    #         sql_faculty = "INSERT INTO users (username, password_hash, role, full_name) VALUES (%s, %s, %s, %s)"
    #         val_faculty = (faculty_username, hashed_faculty_password, "faculty", "Giảng viên Khang")
    #         cursor.execute(sql_faculty, val_faculty)
    #         conn.commit()
    #         results.append(f"Người dùng giảng viên '{faculty_username}' đã được tạo với mật khẩu đã băm.")
    #     else:
    #         results.append(f"Người dùng giảng viên '{faculty_username}' đã tồn tại.")
        
    #     return "<br>".join(results)

    # except Error as e:
    #     if conn and conn.is_connected(): conn.rollback()
    #     app.logger.error(f"Lỗi trong register_test_user_once: {e}")
    #     return f"Lỗi: {e}"
    # finally:
    #     if cursor: cursor.close()
    #     if conn and conn.is_connected(): conn.close()
    return "Route đăng ký người dùng thử nghiệm đã được comment. Bỏ comment trong app.py để sử dụng (CHỈ CHẠY MỘT LẦN)."


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
    sessions_list = [] 
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
    # Truyền action_type nếu cần, ví dụ để phân biệt mục đích mở trang này
    # (ví dụ: 'notes' hoặc 'flashcards')
    action_type = request.args.get('action', 'notes') # Mặc định là 'notes'
    return render_template('student_select_session.html', course=course_data, sessions=sessions_list, action_type=action_type)


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

    return render_template('faculty_dashboard.html', faculty_courses=faculty_courses) # Đổi tên biến cho rõ ràng


@app.route('/faculty/course_sessions/<int:course_id>', methods=['GET', 'POST'])
@login_required(role='faculty')
def faculty_course_sessions(course_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('faculty_dashboard'))

    course_info = None 
    sessions_list = [] 
    quizzes_data_for_template = {} # Để truyền thông tin quiz cho template
    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, course_code, course_name, faculty_id FROM courses WHERE id = %s", (course_id,))
        course_info = cursor.fetchone()

        if not course_info:
            flash("Khóa học không tồn tại.", "danger")
            return redirect(url_for('faculty_dashboard'))
        
        # Kiểm tra quyền: Giảng viên chính hoặc giảng viên được phân công dạy buổi học
        is_main_faculty = (course_info['faculty_id'] == current_user_obj.id)
        
        cursor.execute("SELECT lecturer_name FROM course_sessions WHERE course_id = %s AND lecturer_name = %s LIMIT 1", (course_id, current_user_obj.full_name))
        is_session_lecturer = cursor.fetchone() is not None

        if not (is_main_faculty or is_session_lecturer):
            flash("Bạn không có quyền quản lý buổi học cho khóa này.", "danger")
            return redirect(url_for('faculty_dashboard'))


        if request.method == 'POST': # Xử lý thêm buổi học mới (nếu có form)
            # ... (logic thêm buổi học của bạn ở đây nếu cần) ...
            # Ví dụ:
            # session_title = request.form.get('session_title')
            # ... (các trường khác) ...
            # if all([...]):
            #    # insert into course_sessions
            #    conn.commit()
            #    flash("Buổi học đã được tạo!", "success")
            # else:
            #    flash("Vui lòng điền đủ thông tin.", "warning")
            # return redirect(url_for('faculty_course_sessions', course_id=course_id))
            pass # Bỏ qua phần này nếu không có form thêm buổi học trực tiếp ở đây


        cursor.execute("""
            SELECT cs.id, cs.session_title, cs.session_date, cs.start_time, cs.end_time, 
                   cs.lecturer_name, cs.location, cs.event_type,
                   GROUP_CONCAT(sm.file_name SEPARATOR ', ') as material_files, 
                   q.id as quiz_id, q.title as quiz_title, 
                   (SELECT COUNT(*) FROM questions WHERE quiz_id = q.id) as question_count
            FROM course_sessions cs
            LEFT JOIN session_materials sm ON cs.id = sm.session_id
            LEFT JOIN quizzes q ON cs.id = q.session_id AND q.course_id = cs.course_id 
            WHERE cs.course_id = %s
            GROUP BY cs.id
            ORDER BY cs.session_date DESC, cs.start_time DESC, cs.id DESC
        """, (course_id,))
        sessions_list = cursor.fetchall()
        
        # Lấy thông tin chi tiết hơn về quiz nếu cần cho template
        for session_item in sessions_list:
            if session_item['quiz_id']:
                quizzes_data_for_template[session_item['quiz_id']] = {
                    'title': session_item['quiz_title'],
                    'questions_count': session_item['question_count']
                    # Thêm các thông tin khác về quiz nếu cần
                }


    except Error as e:
        app.logger.error(f"Lỗi CSDL trong faculty_course_sessions cho khóa {course_id}: {e}")
        flash(f"Lỗi cơ sở dữ liệu: {e}", "danger")
        return redirect(url_for('faculty_dashboard')) 
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('faculty_course_sessions.html', course=course_info, sessions=sessions_list, quizzes_data=quizzes_data_for_template)


@app.route('/faculty/upload_material/<int:course_id>/<string:date_str>', methods=['GET', 'POST'])
@login_required(role='faculty')
def faculty_upload_material(course_id, date_str):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('faculty_dashboard'))

    course_info = None
    session_event_info = None # Thông tin buổi học cụ thể
    materials = [] # Danh sách tài liệu đã upload cho buổi học này
    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)
        
        # 1. Lấy thông tin khóa học
        cursor.execute("SELECT id, course_code, course_name, faculty_id FROM courses WHERE id = %s", (course_id,))
        course_info = cursor.fetchone()
        if not course_info:
            flash("Khóa học không tồn tại.", "danger")
            return redirect(url_for('faculty_dashboard'))

        # 2. Lấy thông tin buổi học dựa trên course_id và date_str
        # Giả sử date_str là duy nhất cho một buổi học trong một khóa
        # Nếu không, bạn cần một định danh buổi học rõ ràng hơn (ví dụ: session_id)
        cursor.execute("""
            SELECT id, session_title, session_date, lecturer_name, material_url 
            FROM course_sessions 
            WHERE course_id = %s AND DATE_FORMAT(session_date, %s) = %s 
            LIMIT 1 
        """, (course_id, '%Y-%m-%d', date_str)) # Đảm bảo date_str có định dạng YYYY-MM-DD
        session_event_info = cursor.fetchone()

        if not session_event_info:
            flash(f"Không tìm thấy buổi học cho ngày {date_str} của khóa {course_info['course_name']}.", "warning")
            # Có thể tạo buổi học nếu chưa có, hoặc yêu cầu người dùng chọn/tạo trước
            # Tạm thời chuyển hướng về trang quản lý buổi học
            return redirect(url_for('faculty_course_sessions', course_id=course_id))

        # 3. Kiểm tra quyền tải lên
        is_main_faculty = (course_info['faculty_id'] == current_user_obj.id)
        is_session_lecturer = (session_event_info['lecturer_name'] == current_user_obj.full_name)

        if not (is_main_faculty or is_session_lecturer):
            flash("Bạn không có quyền tải lên tài liệu cho buổi học này.", "danger")
            return redirect(url_for('faculty_course_sessions', course_id=course_id))

        # 4. Xử lý tải lên tệp nếu là POST request
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
                # Tạo đường dẫn lưu trữ: uploads/course_id/date_str/filename
                session_upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(course_id), date_str)
                if not os.path.exists(session_upload_folder):
                    os.makedirs(session_upload_folder, exist_ok=True)
                
                file_path_on_server = os.path.join(session_upload_folder, filename)
                
                # Kiểm tra tệp đã tồn tại chưa (có thể ghi đè hoặc báo lỗi)
                # Hiện tại, sẽ ghi đè nếu tên tệp giống nhau
                try:
                    file.save(file_path_on_server)
                    # Đường dẫn lưu trong DB sẽ là tương đối với UPLOAD_FOLDER
                    db_file_path = os.path.join(str(course_id), date_str, filename).replace("\\","/")
                    
                    # Cập nhật material_url trong bảng course_sessions
                    update_session_query = "UPDATE course_sessions SET material_url = %s WHERE id = %s"
                    cursor.execute(update_session_query, (db_file_path, session_event_info['id']))
                    
                    # (Tùy chọn) Lưu vào bảng session_materials nếu bạn muốn theo dõi lịch sử tải lên
                    # insert_material_query = """
                    #     INSERT INTO session_materials (session_id, file_name, file_path, uploaded_by)
                    #     VALUES (%s, %s, %s, %s)
                    # """
                    # cursor.execute(insert_material_query, (session_event_info['id'], filename, db_file_path, current_user_obj.id))
                    
                    conn.commit()
                    flash(f"Tệp '{filename}' đã được tải lên và liên kết với buổi học.", 'success')
                    # Cập nhật lại session_event_info để hiển thị URL mới
                    session_event_info['material_url'] = db_file_path
                except Error as e:
                    app.logger.error(f"Lỗi CSDL khi lưu tài liệu cho buổi học {session_event_info['id']}: {e}")
                    flash(f"Lỗi khi lưu thông tin tệp vào cơ sở dữ liệu.", "danger")
                    if conn.is_connected(): conn.rollback()
                except Exception as e:
                    app.logger.error(f"Lỗi lưu file {filename}: {e}")
                    flash(f"Lỗi khi lưu tệp: {e}", "danger")
                return redirect(url_for('faculty_upload_material', course_id=course_id, date_str=date_str))

        # 5. (GET request) Lấy danh sách tài liệu đã tải lên cho buổi học này (nếu dùng bảng session_materials)
        # Nếu chỉ dùng material_url trong course_sessions, thì không cần query này
        # cursor.execute("SELECT id, file_name, uploaded_at, file_path FROM session_materials WHERE session_id = %s ORDER BY uploaded_at DESC", (session_event_info['id'],))
        # materials = cursor.fetchall()


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
                           course=course_info, 
                           session_event=session_event_info, 
                           materials=materials) # materials có thể rỗng nếu bạn không dùng bảng riêng


@app.route('/download_material/<path:file_path_in_db>') # Sử dụng path converter
@login_required() 
def download_material(file_path_in_db):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return redirect(request.referrer or url_for('login'))

    cursor = None
    try:
        # Không cần truy vấn CSDL nếu file_path_in_db đã là đường dẫn tương đối chính xác
        # Tuy nhiên, cần kiểm tra quyền truy cập dựa trên logic của bạn
        # Ví dụ: Kiểm tra xem người dùng có ghi danh vào khóa học chứa tài liệu này không
        # Hoặc nếu là giảng viên, có quyền xem/tải tài liệu của khóa đó không.
        # Điều này phức tạp hơn nếu chỉ dựa vào file_path.
        # Tạm thời, giả sử file_path_in_db là an toàn và người dùng có quyền.
        # TRONG THỰC TẾ, BẠN CẦN CÓ LOGIC KIỂM TRA QUYỀN NGHIÊM NGẶT HƠN Ở ĐÂY.
        # Ví dụ: material_id sẽ tốt hơn là file_path trực tiếp trong URL.

        # Đường dẫn tuyệt đối đến tệp trên máy chủ
        # file_path_in_db bây giờ là phần sau 'uploads/', ví dụ: 'course_id/date_str/filename.pdf'
        full_path_to_file = os.path.join(app.config['UPLOAD_FOLDER'], file_path_in_db)
        
        if not os.path.exists(full_path_to_file) or not os.path.isfile(full_path_to_file):
            app.logger.error(f"Tệp tài liệu không tìm thấy tại: {full_path_to_file}")
            flash("Tệp tài liệu không tìm thấy trên máy chủ.", "danger")
            return redirect(request.referrer or url_for('student_dashboard' if current_user_obj.role == 'student' else 'faculty_dashboard'))

        # Tách thư mục và tên tệp để sử dụng send_from_directory
        directory_for_send = os.path.dirname(full_path_to_file)
        filename_for_send = os.path.basename(full_path_to_file)
        
        return send_from_directory(directory=directory_for_send, path=filename_for_send, as_attachment=True)

    except Exception as e:
        app.logger.error(f"Lỗi chung khi tải tài liệu {file_path_in_db}: {e}")
        flash(f"Lỗi không xác định khi tải tài liệu.", "danger")
    finally:
        if cursor: cursor.close() # cursor có thể không được dùng nếu không có truy vấn DB
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

    session_info_data = None 
    notes_list = []
    material_url_for_session = None # Để hiển thị tài liệu của buổi học
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        query_session = """
            SELECT cs.id, cs.session_title, cs.session_date, cs.material_url, 
                   c.id as course_id, c.course_name, c.course_code, c.faculty_id as course_faculty_id, 
                   cs.lecturer_name as session_lecturer_name
            FROM course_sessions cs
            JOIN courses c ON cs.course_id = c.id
            WHERE cs.id = %s
        """
        cursor.execute(query_session, (session_id,))
        session_info_data = cursor.fetchone()

        if not session_info_data:
            flash("Buổi học không tồn tại.", "danger")
            return redirect(url_for('student_dashboard') if current_user_obj.role == 'student' else url_for('faculty_dashboard'))
        
        material_url_for_session = session_info_data.get('material_url')

        can_view_session = False
        if current_user_obj.role == 'student':
            cursor.execute("SELECT * FROM enrollments WHERE student_id = %s AND course_id = %s", (current_user_obj.id, session_info_data['course_id']))
            if cursor.fetchone():
                can_view_session = True
        elif current_user_obj.role == 'faculty': 
            if session_info_data['course_faculty_id'] == current_user_obj.id or session_info_data['session_lecturer_name'] == current_user_obj.full_name:
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
        return redirect(url_for('student_dashboard') if current_user_obj.role == 'student' else url_for('faculty_dashboard'))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    # Truyền course và note_date cho notes_template.html
    course_context = {'id': session_info_data.get('course_id'), 'name': session_info_data.get('course_name')}
    note_date_context = session_info_data.get('session_date') if session_info_data else datetime.date.today()


    return render_template('notes_template.html', 
                           session_info=session_info_data, 
                           notes=notes_list, # Đây là danh sách ghi chú, không phải một ghi chú cụ thể
                           note=None, # Không có ghi chú cụ thể nào đang được chỉnh sửa ở đây
                           is_new=True, # Giả sử đây là để tạo ghi chú mới nếu chưa có
                           session_id=session_id,
                           course=course_context,
                           note_date=note_date_context,
                           material_url=material_url_for_session) # Truyền URL tài liệu


@app.route('/notes/create/<int:session_id>', methods=['GET', 'POST'])
@login_required()
def create_note(session_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('course_notes_overview', session_id=session_id))

    session_info_data = None 
    material_url_for_session = None
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        query_session = """
            SELECT cs.id, cs.session_title, cs.session_date, cs.material_url,
                   c.course_name, c.id as course_id, c.faculty_id as course_faculty_id, 
                   cs.lecturer_name as session_lecturer_name
            FROM course_sessions cs
            JOIN courses c ON cs.course_id = c.id
            WHERE cs.id = %s
        """
        cursor.execute(query_session, (session_id,))
        session_info_data = cursor.fetchone()
        if not session_info_data:
            flash("Buổi học không hợp lệ.", "danger")
            return redirect(url_for('student_dashboard') if current_user_obj.role == 'student' else url_for('faculty_dashboard'))
        
        material_url_for_session = session_info_data.get('material_url')

        can_create_note_flag = False 
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
            title = request.form.get('title', f'Ghi chú ngày {datetime.date.today().strftime("%d-%m-%Y")}') 
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
        return redirect(url_for('course_notes_overview', session_id=session_id))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    
    course_context = {'id': session_info_data.get('course_id'), 'name': session_info_data.get('course_name')}
    note_date_context = session_info_data.get('session_date') if session_info_data else datetime.date.today()

    return render_template('notes_template.html', 
                           session_info=session_info_data, 
                           note=None, # Đây là form tạo mới, chưa có note data cụ thể
                           is_new=True, 
                           session_id=session_id,
                           course=course_context,
                           note_date=note_date_context,
                           material_url=material_url_for_session)


@app.route('/notes/edit/<int:note_id>', methods=['GET', 'POST'])
@login_required()
def edit_note(note_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('student_dashboard') if current_user_obj.role == 'student' else url_for('faculty_dashboard'))

    note_data_to_edit = None # Đổi tên biến
    session_info_for_template = None
    course_context = None
    note_date_context = None
    material_url_for_session = None
    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)
        query_note = """
            SELECT n.id, n.title, n.content, n.session_id, n.user_id, n.created_at, n.updated_at,
                   cs.session_title, cs.session_date, cs.material_url, cs.course_id,
                   crs.course_name, crs.course_code
            FROM notes n
            LEFT JOIN course_sessions cs ON n.session_id = cs.id
            LEFT JOIN courses crs ON cs.course_id = crs.id
            WHERE n.id = %s AND n.user_id = %s
        """
        cursor.execute(query_note, (note_id, current_user_obj.id))
        note_data_to_edit = cursor.fetchone()

        if not note_data_to_edit:
            flash("Ghi chú không tồn tại hoặc bạn không có quyền chỉnh sửa.", "danger")
            return redirect(url_for('student_dashboard') if current_user_obj.role == 'student' else url_for('faculty_dashboard'))

        material_url_for_session = note_data_to_edit.get('material_url')

        if note_data_to_edit.get('session_id'):
             session_info_for_template = {
                'id': note_data_to_edit['session_id'],
                'session_title': note_data_to_edit['session_title'],
                'course_name': note_data_to_edit['course_name'] 
            }
             course_context = {'id': note_data_to_edit.get('course_id'), 'name': note_data_to_edit.get('course_name')}
             note_date_context = note_data_to_edit.get('session_date')
        else: 
            course_context = {'id': 'general', 'name': 'Ghi chú chung'}
            note_date_context = note_data_to_edit.get('created_at').date() if note_data_to_edit.get('created_at') else datetime.date.today()


        if request.method == 'POST':
            title = request.form.get('title', note_data_to_edit['title'])
            content = request.form.get('content', note_data_to_edit['content'])

            update_query = "UPDATE notes SET title = %s, content = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s AND user_id = %s"
            cursor.execute(update_query, (title, content, note_id, current_user_obj.id))
            conn.commit()
            flash('Ghi chú đã được cập nhật!', 'success')
            
            cursor.execute(query_note, (note_id, current_user_obj.id))
            note_data_to_edit = cursor.fetchone() # Tải lại dữ liệu mới nhất
            material_url_for_session = note_data_to_edit.get('material_url') # Cập nhật lại URL tài liệu
            if note_data_to_edit.get('session_id'):
                 session_info_for_template = {
                    'id': note_data_to_edit['session_id'],
                    'session_title': note_data_to_edit['session_title'],
                    'course_name': note_data_to_edit['course_name']
                }
                 course_context = {'id': note_data_to_edit.get('course_id'), 'name': note_data_to_edit.get('course_name')}
                 note_date_context = note_data_to_edit.get('session_date')


    except Error as e:
        app.logger.error(f"Lỗi sửa ghi chú {note_id} cho người dùng {current_user_obj.id}: {e}")
        flash(f"Lỗi khi cập nhật ghi chú: {e}", "danger")
        if conn and conn.is_connected(): conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    if not note_data_to_edit: 
        flash("Không thể tải ghi chú để chỉnh sửa.", "danger")
        return redirect(url_for('student_dashboard') if current_user_obj.role == 'student' else url_for('faculty_dashboard'))

    return render_template('notes_template.html',
                           note=note_data_to_edit,
                           session_info=session_info_for_template,
                           is_new=False,
                           session_id=note_data_to_edit.get('session_id'),
                           course=course_context,
                           note_date=note_date_context,
                           material_url=material_url_for_session)


@app.route('/notes/delete/<int:note_id>', methods=['POST']) 
@login_required()
def delete_note(note_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Lỗi kết nối cơ sở dữ liệu.'}), 500

    cursor = None
    original_session_id_for_redirect = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT session_id FROM notes WHERE id = %s AND user_id = %s", (note_id, current_user_obj.id))
        note_to_delete = cursor.fetchone()

        if not note_to_delete:
            flash("Ghi chú không tồn tại hoặc bạn không có quyền xóa.", "warning")
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
                redirect_url = url_for('student_dashboard') 
            else:
                redirect_url = url_for('faculty_dashboard')
            return jsonify({'success': True, 'message': 'Ghi chú đã được xóa.', 'redirect_url': redirect_url})
        else:
            flash("Không thể xóa ghi chú. Có thể nó đã được xóa hoặc bạn không có quyền.", "warning")
            default_redirect = url_for('student_dashboard' if current_user_obj.role == 'student' else 'faculty_dashboard')
            return jsonify({'success': False, 'message': 'Không thể xóa ghi chú.', 'redirect_url': default_redirect }), 403

    except Error as e:
        app.logger.error(f"Lỗi xóa ghi chú {note_id} cho người dùng {current_user_obj.id}: {e}")
        if conn and conn.is_connected(): conn.rollback()
        return jsonify({'success': False, 'message': f'Lỗi cơ sở dữ liệu: {e}'}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    flash("Lỗi không xác định khi xóa ghi chú.", "danger")
    default_redirect = url_for('student_dashboard' if current_user_obj.role == 'student' else 'faculty_dashboard')
    return jsonify({'success': False, 'message': 'Lỗi không xác định khi xóa.', 'redirect_url': default_redirect }), 500


# --- Flashcard Routes ---
# Các route cho flashcard (student_flashcard_hub_course, create_flashcard_hub, v.v.)
# cần được xem xét lại để phù hợp với cấu trúc CSDL mới (nếu có)
# và logic điều hướng (ví dụ: flashcard chung, flashcard theo môn, flashcard theo buổi học)

@app.route('/student/flashcard_hub') # Route chung cho Flashcard Hub
@login_required(role='student')
def student_flashcard_hub():
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn: return redirect(url_for('student_dashboard'))

    student_courses_for_flashcards = []
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Lấy danh sách các môn học sinh viên đã đăng ký để tạo/xem flashcard theo môn
        query_courses = """
            SELECT c.id, c.course_code, c.course_name
            FROM courses c
            JOIN enrollments e ON c.id = e.course_id
            WHERE e.student_id = %s
            ORDER BY c.course_name
        """
        cursor.execute(query_courses, (current_user_obj.id,))
        student_courses_for_flashcards = cursor.fetchall()
        
    except Error as e:
        app.logger.error(f"Lỗi CSDL lấy danh sách khóa học cho Flashcard Hub của SV {current_user_obj.id}: {e}")
        flash("Không thể tải thông tin môn học cho Flashcard Hub.", "danger")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('student_flashcard_hub.html', courses=student_courses_for_flashcards)


@app.route('/student/flashcards/create/general', methods=['GET'])
@login_required(role='student')
def student_create_flashcard_general():
    # Hiển thị form tạo flashcard chung (không theo môn/buổi)
    return render_template('student_create_flashcard.html', 
                           context_title="Tạo Flashcard Chung", 
                           course=None, 
                           session_event=None)

@app.route('/student/flashcards/view/general', methods=['GET'])
@login_required(role='student')
def student_view_flashcard_general():
    # Hiển thị flashcard chung
    # storage_key sẽ là 'flashcards_umt_general' trong JS
    return render_template('student_view_flashcards.html', 
                           context_title="Xem Flashcard Chung", 
                           course=None, 
                           session_event=None,
                           storage_key='flashcards_umt_general')


@app.route('/student/flashcards/select_session_for_action/<int:course_id>/<string:action_type>')
@login_required(role='student')
def student_select_session_for_flashcard(course_id, action_type):
    # action_type có thể là 'create' hoặc 'view'
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn: return redirect(url_for('student_flashcard_hub'))

    course_data = None
    sessions_list = []
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, course_code, course_name FROM courses WHERE id = %s", (course_id,))
        course_data = cursor.fetchone()
        if not course_data:
            flash("Khóa học không tồn tại.", "danger")
            return redirect(url_for('student_flashcard_hub'))

        cursor.execute("SELECT * FROM enrollments WHERE student_id = %s AND course_id = %s", (current_user_obj.id, course_id))
        if not cursor.fetchone():
            flash("Bạn chưa ghi danh vào khóa học này.", "warning")
            return redirect(url_for('student_flashcard_hub'))

        cursor.execute("""
            SELECT id, session_title, session_date 
            FROM course_sessions 
            WHERE course_id = %s 
            ORDER BY session_date DESC, id DESC
        """, (course_id,))
        sessions_list = cursor.fetchall()
    except Error as e:
        app.logger.error(f"Lỗi lấy buổi học cho flashcard, khóa {course_id}, action {action_type}: {e}")
        flash("Không thể tải danh sách buổi học.", "danger")
        return redirect(url_for('student_flashcard_hub'))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('student_select_session.html', 
                           course=course_data, 
                           sessions=sessions_list, 
                           action_type=action_type) # action_type này sẽ được dùng trong template để tạo link đúng


@app.route('/student/flashcards/create/course/<int:course_id>/session/<string:date_str>', methods=['GET'])
@login_required(role='student')
def student_create_flashcard_for_session(course_id, date_str):
    conn = get_db_connection()
    if not conn: return redirect(url_for('student_flashcard_hub'))
    
    course_data = None
    session_event_data = None
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, course_name FROM courses WHERE id = %s", (course_id,))
        course_data = cursor.fetchone()
        if not course_data:
            flash("Khóa học không tồn tại.", "danger")
            return redirect(url_for('student_flashcard_hub'))

        cursor.execute("SELECT id, session_title, session_date FROM course_sessions WHERE course_id = %s AND DATE_FORMAT(session_date, %s) = %s LIMIT 1", (course_id, '%Y-%m-%d', date_str))
        session_event_data = cursor.fetchone()
        if not session_event_data:
            flash(f"Buổi học ngày {date_str} không tồn tại cho khóa này.", "warning")
            return redirect(url_for('student_select_session_for_flashcard', course_id=course_id, action_type='create'))
            
    except Error as e:
        app.logger.error(f"Lỗi lấy thông tin tạo flashcard cho buổi học: {e}")
        flash("Lỗi tải thông tin.", "danger")
        return redirect(url_for('student_flashcard_hub'))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    context_title = f"Tạo Flashcard: {course_data['course_name']} - Buổi {session_event_data['session_date']}"
    return render_template('student_create_flashcard.html', 
                           context_title=context_title, 
                           course=course_data, 
                           session_event=session_event_data)


@app.route('/student/flashcards/view/course/<int:course_id>/session/<string:date_str>', methods=['GET'])
@login_required(role='student')
def student_view_flashcard_for_session(course_id, date_str):
    conn = get_db_connection()
    if not conn: return redirect(url_for('student_flashcard_hub'))
    
    course_data = None
    session_event_data = None
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, course_name FROM courses WHERE id = %s", (course_id,))
        course_data = cursor.fetchone()
        if not course_data:
            flash("Khóa học không tồn tại.", "danger")
            return redirect(url_for('student_flashcard_hub'))

        cursor.execute("SELECT id, session_title, session_date FROM course_sessions WHERE course_id = %s AND DATE_FORMAT(session_date, %s) = %s LIMIT 1", (course_id, '%Y-%m-%d', date_str))
        session_event_data = cursor.fetchone()
        if not session_event_data:
            flash(f"Buổi học ngày {date_str} không tồn tại cho khóa này.", "warning")
            return redirect(url_for('student_select_session_for_flashcard', course_id=course_id, action_type='view'))
            
    except Error as e:
        app.logger.error(f"Lỗi lấy thông tin xem flashcard cho buổi học: {e}")
        flash("Lỗi tải thông tin.", "danger")
        return redirect(url_for('student_flashcard_hub'))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    context_title = f"Xem Flashcard: {course_data['course_name']} - Buổi {session_event_data['session_date']}"
    storage_key = f"flashcards_umt_{course_id}_{date_str}" # Key cho localStorage
    return render_template('student_view_flashcards.html', 
                           context_title=context_title, 
                           course=course_data, 
                           session_event=session_event_data,
                           storage_key=storage_key)


# --- Quiz Routes ---
@app.route('/faculty/manage_quiz/<int:course_id>/session/<string:date_str>', methods=['GET', 'POST'])
@login_required(role='faculty')
def faculty_manage_quiz(course_id, date_str):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn: return redirect(url_for('faculty_dashboard'))

    course_info = None
    session_event_info = None
    quiz_data = None # Thông tin quiz hiện tại nếu có
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Lấy thông tin khóa học và kiểm tra quyền
        cursor.execute("SELECT id, course_code, course_name, faculty_id FROM courses WHERE id = %s", (course_id,))
        course_info = cursor.fetchone()
        if not course_info or course_info['faculty_id'] != current_user_obj.id:
            # Thêm kiểm tra nếu là giảng viên của buổi học
            cursor.execute("""
                SELECT cs.id FROM course_sessions cs 
                WHERE cs.course_id = %s AND DATE_FORMAT(cs.session_date, %s) = %s AND cs.lecturer_name = %s
            """, (course_id, '%Y-%m-%d', date_str, current_user_obj.full_name))
            if not cursor.fetchone() and (not course_info or course_info['faculty_id'] != current_user_obj.id) : # Nếu không phải GV chính và cũng không phải GV buổi đó
                flash("Khóa học không hợp lệ hoặc bạn không có quyền quản lý quiz cho khóa này.", "danger")
                return redirect(url_for('faculty_dashboard'))

        # Lấy thông tin buổi học
        cursor.execute("""
            SELECT id, session_title, session_date 
            FROM course_sessions 
            WHERE course_id = %s AND DATE_FORMAT(session_date, %s) = %s 
            LIMIT 1
        """, (course_id, '%Y-%m-%d', date_str))
        session_event_info = cursor.fetchone()
        if not session_event_info:
            flash(f"Không tìm thấy buổi học ngày {date_str} cho khóa {course_info['course_name']}.", "warning")
            return redirect(url_for('faculty_course_sessions', course_id=course_id))

        # Kiểm tra xem đã có quiz cho buổi học này chưa
        cursor.execute("""
            SELECT q.id as quiz_id, q.title as quiz_title, GROUP_CONCAT(
                JSON_OBJECT('id', qu.id, 'text', qu.question_text, 'type', qu.question_type, 'options', qu.options, 'correct_answer', qu.correct_answer)
            ) as questions_json
            FROM quizzes q
            LEFT JOIN questions qu ON q.id = qu.quiz_id
            WHERE q.course_id = %s AND q.session_id = %s AND q.created_by = %s
            GROUP BY q.id
            LIMIT 1
        """, (course_id, session_event_info['id'], current_user_obj.id))
        quiz_raw_data = cursor.fetchone()

        if quiz_raw_data:
            quiz_data = {
                'id': quiz_raw_data['quiz_id'],
                'title': quiz_raw_data['quiz_title'],
                'questions': []
            }
            if quiz_raw_data['questions_json']:
                # Do GROUP_CONCAT có thể trả về một chuỗi các JSON object, cần xử lý đúng
                # Cách đơn giản là lấy từng question một nếu GROUP_CONCAT phức tạp
                cursor.execute("SELECT id, question_text, question_type, options, correct_answer FROM questions WHERE quiz_id = %s ORDER BY id", (quiz_data['id'],))
                questions_db = cursor.fetchall()
                for q_db in questions_db:
                    options_list = []
                    if q_db['options']:
                        try:
                            options_list = json.loads(q_db['options'])
                        except json.JSONDecodeError:
                            options_list = [] # Hoặc ghi log lỗi
                    quiz_data['questions'].append({
                        'id': q_db['id'],
                        'text': q_db['question_text'],
                        'type': q_db['question_type'],
                        'options': options_list, # Đã parse
                        'correct_answer': q_db['correct_answer']
                    })


        if request.method == 'POST':
            quiz_title_form = request.form.get('quiz_title', f"Quiz cho {course_info['course_name']} - {session_event_info['session_date']}")
            
            # Logic lưu quiz và câu hỏi
            quiz_id_to_use = None
            if quiz_data and quiz_data.get('id'): # Cập nhật quiz hiện có
                quiz_id_to_use = quiz_data['id']
                update_quiz_q = "UPDATE quizzes SET title = %s WHERE id = %s"
                cursor.execute(update_quiz_q, (quiz_title_form, quiz_id_to_use))
                # Xóa câu hỏi cũ để thêm lại, hoặc logic cập nhật phức tạp hơn
                cursor.execute("DELETE FROM questions WHERE quiz_id = %s", (quiz_id_to_use,))
            else: # Tạo quiz mới
                insert_quiz_q = "INSERT INTO quizzes (course_id, session_id, title, created_by) VALUES (%s, %s, %s, %s)"
                cursor.execute(insert_quiz_q, (course_id, session_event_info['id'], quiz_title_form, current_user_obj.id))
                quiz_id_to_use = cursor.lastrowid
            
            # Thêm câu hỏi từ form
            question_texts = request.form.getlist('question_text[]')
            # Lưu ý: getlist cho options và correct_answer cần cẩn thận vì chúng lồng nhau theo câu hỏi
            
            num_questions_added = 0
            for i, q_text in enumerate(question_texts):
                if not q_text.strip(): continue # Bỏ qua câu hỏi trống

                # Giả sử form có cấu trúc name="option_{index}_{option_index}" và name="correct_answer_{index}"
                # Đây là phần phức tạp cần xử lý cẩn thận dựa trên cấu trúc form HTML của bạn
                options_for_this_q = [
                    request.form.get(f'option_{i}_0', '').strip(),
                    request.form.get(f'option_{i}_1', '').strip(),
                    request.form.get(f'option_{i}_2', '').strip(),
                    request.form.get(f'option_{i}_3', '').strip(),
                ]
                options_for_this_q_filtered = [opt for opt in options_for_this_q if opt] # Loại bỏ lựa chọn trống
                
                correct_answer_index_str = request.form.get(f'correct_answer_{i}') # Đây là index (0-3)
                correct_answer_text = ""

                if not options_for_this_q_filtered or len(options_for_this_q_filtered) < 2:
                    flash(f"Câu hỏi '{q_text[:20]}...' cần ít nhất 2 lựa chọn. Bỏ qua câu hỏi này.", "warning")
                    continue

                if correct_answer_index_str is not None:
                    try:
                        correct_idx = int(correct_answer_index_str)
                        if 0 <= correct_idx < len(options_for_this_q_filtered):
                            correct_answer_text = options_for_this_q_filtered[correct_idx]
                        else:
                            flash(f"Lựa chọn đáp án đúng không hợp lệ cho câu hỏi '{q_text[:20]}...'. Bỏ qua.", "warning")
                            continue
                    except ValueError:
                        flash(f"Định dạng đáp án đúng không hợp lệ cho câu hỏi '{q_text[:20]}...'. Bỏ qua.", "warning")
                        continue
                else: # Nếu không có radio nào được chọn
                    flash(f"Chưa chọn đáp án đúng cho câu hỏi '{q_text[:20]}...'. Bỏ qua.", "warning")
                    continue


                if q_text and correct_answer_text:
                    q_insert = """INSERT INTO questions (quiz_id, question_text, question_type, options, correct_answer)
                                  VALUES (%s, %s, %s, %s, %s)"""
                    # Mặc định là multiple_choice, bạn có thể thêm trường type vào form nếu cần
                    cursor.execute(q_insert, (quiz_id_to_use, q_text, 'multiple_choice', json.dumps(options_for_this_q_filtered), correct_answer_text))
                    num_questions_added +=1
            
            conn.commit()
            if num_questions_added > 0:
                flash(f"Quiz đã được lưu với {num_questions_added} câu hỏi!", "success")
            elif quiz_id_to_use: # Quiz được tạo/cập nhật nhưng không có câu hỏi nào được thêm
                 flash(f"Tiêu đề quiz '{quiz_title_form}' đã được lưu. Chưa có câu hỏi nào được thêm/lưu.", "info")
            else: # Không có gì được lưu
                flash("Không có thay đổi nào được lưu.", "warning")

            return redirect(url_for('faculty_manage_quiz', course_id=course_id, date_str=date_str))

    except Error as e:
        app.logger.error(f"Lỗi CSDL quản lý quiz: {e}")
        flash("Lỗi tải trang quản lý quiz.", "danger")
        return redirect(url_for('faculty_course_sessions', course_id=course_id))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('faculty_manage_quiz.html', 
                           course=course_info, 
                           session_event=session_event_info, 
                           quiz=quiz_data)


@app.route('/student/take_quiz/<int:quiz_id>')
@login_required(role='student')
def student_take_quiz(quiz_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn: return redirect(url_for('student_dashboard'))

    quiz_info_data = None 
    questions_list = [] 
    session_title_for_quiz = None # Để hiển thị tên buổi học nếu có
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT q.id, q.title, q.course_id, q.session_id, 
                   c.course_name, cs.session_title 
            FROM quizzes q 
            JOIN courses c ON q.course_id = c.id 
            LEFT JOIN course_sessions cs ON q.session_id = cs.id
            WHERE q.id = %s
        """, (quiz_id,))
        quiz_info_data = cursor.fetchone()

        if not quiz_info_data:
            flash("Quiz không tồn tại.", "danger")
            return redirect(url_for('student_dashboard'))
        
        session_title_for_quiz = quiz_info_data.get('session_title')
        
        cursor.execute("SELECT * FROM enrollments WHERE student_id = %s AND course_id = %s", (current_user_obj.id, quiz_info_data['course_id']))
        if not cursor.fetchone():
            flash("Bạn chưa ghi danh vào khóa học của quiz này.", "warning")
            return redirect(url_for('student_dashboard'))

        q_query = "SELECT id, question_text, question_type, options FROM questions WHERE quiz_id = %s ORDER BY id" 
        cursor.execute(q_query, (quiz_id,))
        questions_raw = cursor.fetchall()
        
        for q_item in questions_raw: 
            if q_item['question_type'] == 'multiple_choice' and q_item['options']:
                try:
                    q_item['options_list'] = json.loads(q_item['options']) 
                    if not isinstance(q_item['options_list'], list): q_item['options_list'] = [] 
                except (json.JSONDecodeError, TypeError):
                    q_item['options_list'] = []
                    app.logger.warning(f"Quiz {quiz_id}, Question {q_item['id']}: JSON options decode error or not a list. Options: {q_item['options']}")
            else:
                q_item['options_list'] = [] 
            questions_list.append(q_item)

    except Error as e:
        app.logger.error(f"Lỗi CSDL lấy quiz {quiz_id} cho sinh viên {current_user_obj.id}: {e}")
        flash("Lỗi tải quiz.", "danger")
        return redirect(url_for('student_dashboard')) 
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
        
    return render_template('student_take_quiz.html', 
                           quiz=quiz_info_data, 
                           questions=questions_list, 
                           course_name=quiz_info_data.get('course_name'),
                           session_title=session_title_for_quiz, # Truyền tên buổi học
                           quiz_id=quiz_id) # Truyền quiz_id để form action đúng


@app.route('/student/submit_quiz/<int:quiz_id>', methods=['POST'])
@login_required(role='student')
def student_submit_quiz(quiz_id):
    current_user_obj = get_current_user_object()
    conn = get_db_connection()
    if not conn:
        flash("Lỗi kết nối CSDL, không thể nộp bài.", "danger")
        return redirect(url_for('student_take_quiz', quiz_id=quiz_id))

    cursor = None
    attempt_id_created = None 
    score_achieved_count = 0 
    total_questions_in_quiz = 0 

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

        cursor.execute("SELECT id, correct_answer, question_type, options FROM questions WHERE quiz_id = %s", (quiz_id,))
        quiz_questions_from_db = cursor.fetchall() 
        questions_map_db = {
            q['id']: {
                'correct': q['correct_answer'], 
                'type': q['question_type'],
                'options_json': q.get('options') # Lấy options dạng JSON
            } for q in quiz_questions_from_db
        }
        total_questions_in_quiz = len(questions_map_db)

        if total_questions_in_quiz == 0:
            flash("Quiz này hiện không có câu hỏi nào. Không thể nộp bài.", "warning")
            return redirect(url_for('student_take_quiz', quiz_id=quiz_id))

        attempt_insert_query = "INSERT INTO quiz_attempts (quiz_id, student_id, score) VALUES (%s, %s, %s)"
        cursor.execute(attempt_insert_query, (quiz_id, current_user_obj.id, 0.0)) 
        attempt_id_created = cursor.lastrowid

        submitted_answers_from_form = request.form 

        for q_db_id, q_data_db in questions_map_db.items():
            student_answer_key_form_corrected = f"question_{q_db_id}" # Đúng với name trong student_take_quiz.html
            student_answer_value_submitted = submitted_answers_from_form.get(student_answer_key_form_corrected)
            
            is_answer_correct = False
            
            # Lấy đáp án đúng từ DB (đã được lưu dưới dạng text của lựa chọn đúng)
            correct_db_answer_normalized = q_data_db['correct'].strip().lower() if q_data_db['correct'] else ""
            
            # Chuẩn hóa câu trả lời của sinh viên
            student_submitted_answer_normalized = student_answer_value_submitted.strip().lower() if student_answer_value_submitted else ""

            if student_answer_value_submitted is not None:
                if q_data_db['type'] == 'multiple_choice':
                    # Đối với multiple choice, student_answer_value_submitted là text của lựa chọn
                    if student_submitted_answer_normalized == correct_db_answer_normalized:
                        is_answer_correct = True
                # (Thêm logic cho các loại câu hỏi khác nếu có)
            
            if is_answer_correct:
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
    except Exception as e: 
        app.logger.error(f"Lỗi không mong muốn khi nộp quiz {quiz_id} cho sinh viên {current_user_obj.id}: {e}")
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

    attempt_details_data = None 
    answers_details_list = [] 
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        attempt_query = """
            SELECT qa.id, qa.quiz_id, qa.student_id, qa.score, qa.attempted_at, 
                   q.title as quiz_title, q.course_id, c.course_name,
                   DATE_FORMAT(qa.attempted_at, '%d/%m/%Y %H:%i:%S') as timestamp 
            FROM quiz_attempts qa
            JOIN quizzes q ON qa.quiz_id = q.id
            JOIN courses c ON q.course_id = c.id
            WHERE qa.id = %s AND qa.student_id = %s 
        """ 
        cursor.execute(attempt_query, (attempt_id, current_user_obj.id))
        attempt_details_data = cursor.fetchone()

        if not attempt_details_data:
            flash("Không tìm thấy kết quả bài làm hoặc bạn không có quyền xem.", "danger")
            return redirect(url_for('student_dashboard'))
        
        answers_query = """
            SELECT aa.student_answer, aa.is_correct, 
                   q.id as question_id, q.question_text, q.correct_answer, q.options, q.question_type
            FROM attempt_answers aa
            JOIN questions q ON aa.question_id = q.id
            WHERE aa.attempt_id = %s
            ORDER BY q.id 
        """ 
        cursor.execute(answers_query, (attempt_id,))
        answers_raw_data = cursor.fetchall() 

        for ans_item in answers_raw_data: 
            ans_item['options_list'] = [] # Khởi tạo
            if ans_item['question_type'] == 'multiple_choice' and ans_item['options']:
                try:
                    # options được lưu dưới dạng JSON string list ["Option A", "Option B"]
                    loaded_options = json.loads(ans_item['options'])
                    if isinstance(loaded_options, list):
                        ans_item['options_list'] = loaded_options
                except (json.JSONDecodeError, TypeError):
                    app.logger.warning(f"Quiz Result Attempt {attempt_id}, Question {ans_item['question_id']}: JSON options decode error. Options: {ans_item['options']}")
            
            # Xử lý để template có thể hiển thị đúng/sai cho từng lựa chọn
            # Giả sử student_answer lưu text của lựa chọn
            # correct_answer cũng lưu text của lựa chọn đúng
            
            # Tạo một list các dictionary cho options để dễ dàng lặp trong template
            # và đánh dấu lựa chọn của sinh viên, đáp án đúng
            
            processed_options_for_template = []
            if ans_item['question_type'] == 'multiple_choice':
                for opt_text in ans_item['options_list']:
                    option_detail = {'text': opt_text, 'is_student_choice': False, 'is_correct_answer': False}
                    if opt_text == ans_item['student_answer']:
                        option_detail['is_student_choice'] = True
                    if opt_text == ans_item['correct_answer']:
                        option_detail['is_correct_answer'] = True
                    processed_options_for_template.append(option_detail)
            ans_item['processed_options'] = processed_options_for_template # Gán lại vào ans_item
            answers_details_list.append(ans_item)


    except Error as e:
        app.logger.error(f"Lỗi CSDL lấy kết quả quiz cho lần làm {attempt_id}, sinh viên {current_user_obj.id}: {e}")
        flash("Lỗi tải kết quả quiz.", "danger")
        return redirect(url_for('student_dashboard')) 
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
        
    return render_template('student_quiz_results.html', 
                           attempt=attempt_details_data, 
                           details=answers_details_list, # Đổi tên biến cho nhất quán với template
                           quiz_title=attempt_details_data.get('quiz_title'), 
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
    return redirect(url_for('login')) 

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.datetime.now().year}


if __name__ == '__main__':
    app.run(debug=True, port=5001) 
