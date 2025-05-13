from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
import datetime
import mysql.connector # Import MySQL connector
from mysql.connector import Error # Import Error for exception handling

app = Flask(__name__)
app.secret_key = 'your_very_secret_key_here' # Change this in a real application!
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- Database Configuration ---
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "Khag12344@" # Your provided password
DB_NAME = "umtsmartnotes"

# --- Database Helper Functions ---
def get_db_connection():
    """Establishes a connection to the MySQL database."""
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return conn
    except Error as e:
        app.logger.error(f"Error connecting to MySQL database: {e}")
        flash(f"Database connection error: {e}", "danger")
        return None

# --- Example Table Schemas (CREATE THESE IN YOUR MYSQL DATABASE) ---
# CREATE TABLE users (
#     id INT AUTO_INCREMENT PRIMARY KEY,
#     username VARCHAR(255) UNIQUE NOT NULL,
#     password VARCHAR(255) NOT NULL, -- Store hashed passwords in production!
#     role VARCHAR(50) NOT NULL, -- 'student' or 'faculty'
#     full_name VARCHAR(255)
# );

# CREATE TABLE courses (
#     id INT AUTO_INCREMENT PRIMARY KEY,
#     course_code VARCHAR(50) UNIQUE NOT NULL,
#     course_name VARCHAR(255) NOT NULL,
#     faculty_id INT,
#     FOREIGN KEY (faculty_id) REFERENCES users(id) ON DELETE SET NULL -- Assuming faculty is a user
# );

# CREATE TABLE enrollments (
#    student_id INT NOT NULL,
#    course_id INT NOT NULL,
#    PRIMARY KEY (student_id, course_id),
#    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
#    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
# );

# CREATE TABLE course_sessions (
#     id INT AUTO_INCREMENT PRIMARY KEY,
#     course_id INT NOT NULL,
#     session_title VARCHAR(255) NOT NULL,
#     session_date DATE,
#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#     FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
# );

# CREATE TABLE notes (
#     id INT AUTO_INCREMENT PRIMARY KEY,
#     session_id INT, -- Can be NULL if note is not tied to a specific session
#     user_id INT NOT NULL,
#     title VARCHAR(255),
#     content TEXT,
#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
#     FOREIGN KEY (session_id) REFERENCES course_sessions(id) ON DELETE SET NULL,
#     FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
# );

# CREATE TABLE flashcard_hubs (
#    id INT AUTO_INCREMENT PRIMARY KEY,
#    user_id INT NOT NULL,
#    course_id INT NOT NULL, -- Or associate with a session_id or make it more general
#    name VARCHAR(255) NOT NULL,
#    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
#    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE -- Example association
# );

# CREATE TABLE flashcards (
#    id INT AUTO_INCREMENT PRIMARY KEY,
#    hub_id INT NOT NULL,
#    question TEXT NOT NULL,
#    answer TEXT NOT NULL,
#    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#    FOREIGN KEY (hub_id) REFERENCES flashcard_hubs(id) ON DELETE CASCADE
# );

# CREATE TABLE quizzes (
#    id INT AUTO_INCREMENT PRIMARY KEY,
#    course_id INT NOT NULL,
#    session_id INT, -- Optional: link quiz to a specific session
#    title VARCHAR(255) NOT NULL,
#    created_by INT NOT NULL, -- faculty user_id
#    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
#    FOREIGN KEY (session_id) REFERENCES course_sessions(id) ON DELETE SET NULL,
#    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
# );

# CREATE TABLE questions (
#    id INT AUTO_INCREMENT PRIMARY KEY,
#    quiz_id INT NOT NULL,
#    question_text TEXT NOT NULL,
#    question_type VARCHAR(50) NOT NULL, -- 'multiple_choice', 'true_false', 'short_answer'
#    -- For multiple choice, store options as JSON or in a separate options table
#    options JSON, -- Example: '["Option A", "Option B", "Option C"]'
#    correct_answer TEXT NOT NULL, -- For MC, could be the index or text of the correct option
#    FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
# );

# CREATE TABLE quiz_attempts (
#    id INT AUTO_INCREMENT PRIMARY KEY,
#    quiz_id INT NOT NULL,
#    student_id INT NOT NULL,
#    score DECIMAL(5,2), -- Example: 85.50
#    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#    FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE,
#    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
# );

# CREATE TABLE attempt_answers (
#    id INT AUTO_INCREMENT PRIMARY KEY,
#    attempt_id INT NOT NULL,
#    question_id INT NOT NULL,
#    student_answer TEXT,
#    is_correct BOOLEAN,
#    FOREIGN KEY (attempt_id) REFERENCES quiz_attempts(id) ON DELETE CASCADE,
#    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
# );

# CREATE TABLE session_materials (
#    id INT AUTO_INCREMENT PRIMARY KEY,
#    session_id INT NOT NULL,
#    file_name VARCHAR(255) NOT NULL,
#    file_path VARCHAR(512) NOT NULL,
#    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#    uploaded_by INT NOT NULL, -- user_id of faculty
#    FOREIGN KEY (session_id) REFERENCES course_sessions(id) ON DELETE CASCADE,
#    FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE CASCADE
# );
# --- End Example Table Schemas ---


# --- User Authentication and Management ---
class User:
    """Represents a user, mirroring Flask-Login's UserMixin for session management."""
    def __init__(self, id, username, role, full_name=None):
        self.id = id
        self.username = username
        self.role = role
        self.full_name = full_name
        self.is_active = True  # Assuming all users fetched are active

    def get_id(self):
        return str(self.id)

    @property
    def is_authenticated(self):
        return True # If a User object exists, they are considered authenticated for this session

    @property
    def is_anonymous(self):
        return False

# Mocking Flask-Login's current_user and login_required
def login_user_session(user):
    """Stores user information in the session."""
    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role
    session['full_name'] = user.full_name

def logout_user_session():
    """Clears user information from the session."""
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('role', None)
    session.pop('full_name', None)

def get_current_user():
    """Retrieves the current user from the session if logged in."""
    if 'user_id' in session:
        # In a real app, you might re-fetch from DB to ensure data is fresh,
        # but for simplicity, we'll use session data.
        return User(session['user_id'], session['username'], session['role'], session.get('full_name'))
    return None

def login_required(role=None):
    """Decorator to protect routes that require login."""
    def decorator(f):
        @wraps(f) # Important for preserving function metadata
        def decorated_function(*args, **kwargs):
            current_user = get_current_user()
            if not current_user:
                flash("Vui lòng đăng nhập để truy cập trang này.", "warning")
                return redirect(url_for('login', next=request.url))
            if role and current_user.role != role:
                flash(f"Bạn không có quyền truy cập vào trang này. Cần vai trò: {role}.", "danger")
                # Redirect to appropriate dashboard based on user's actual role
                if current_user.role == 'student':
                    return redirect(url_for('student_dashboard'))
                elif current_user.role == 'faculty':
                    return redirect(url_for('faculty_dashboard'))
                else:
                    return redirect(url_for('login')) # Fallback
            return f(*args, **kwargs)
        return decorated_function
    return decorator

from functools import wraps # Make sure to import wraps

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role'] # 'student' or 'faculty'

        conn = get_db_connection()
        if not conn:
            return render_template('login.html', error="Lỗi kết nối cơ sở dữ liệu.")

        cursor = None
        try:
            cursor = conn.cursor(dictionary=True) # dictionary=True to get results as dicts
            # IMPORTANT: Store and check HASHED passwords in a real application!
            # Example: SELECT id, username, password_hash, role, full_name FROM users WHERE username = %s AND role = %s
            query = "SELECT id, username, password, role, full_name FROM users WHERE username = %s AND role = %s"
            cursor.execute(query, (username, role))
            user_data = cursor.fetchone()

            if user_data and user_data['password'] == password: # Replace with password hash check
                user_obj = User(user_data['id'], user_data['username'], user_data['role'], user_data.get('full_name'))
                login_user_session(user_obj) # Use custom session login
                flash('Đăng nhập thành công!', 'success')
                if role == 'student':
                    return redirect(url_for('student_dashboard'))
                elif role == 'faculty':
                    return redirect(url_for('faculty_dashboard'))
            else:
                flash('Tên đăng nhập, mật khẩu hoặc vai trò không đúng.', 'danger')
        except Error as e:
            app.logger.error(f"Database query error during login: {e}")
            flash(f"Lỗi truy vấn cơ sở dữ liệu: {e}", "danger")
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
        
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Handles user logout."""
    logout_user_session() # Use custom session logout
    flash('Bạn đã đăng xuất.', 'info')
    return redirect(url_for('login'))

def get_user_by_id(user_id):
    """Fetches a user by their ID from the database."""
    conn = get_db_connection()
    if not conn:
        return None
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username, role, full_name FROM users WHERE id = %s", (user_id,))
        user_data = cursor.fetchone()
        if user_data:
            return User(user_data['id'], user_data['username'], user_data['role'], user_data.get('full_name'))
        return None
    except Error as e:
        app.logger.error(f"Error fetching user by ID {user_id}: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# --- Student Routes ---
@app.route('/student/dashboard')
@login_required(role='student')
def student_dashboard():
    """Displays the student dashboard."""
    current_user = get_current_user()
    conn = get_db_connection()
    if not conn:
        flash("Lỗi kết nối cơ sở dữ liệu.", "danger")
        return redirect(url_for('login'))

    student_courses = []
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Query to get courses the student is enrolled in
        # Assumes an 'enrollments' table: enrollments(student_id, course_id)
        query = """
            SELECT c.id, c.course_code, c.course_name
            FROM courses c
            JOIN enrollments e ON c.id = e.course_id
            WHERE e.student_id = %s
        """
        cursor.execute(query, (current_user.id,))
        student_courses = cursor.fetchall()
    except Error as e:
        app.logger.error(f"Error fetching student courses for user {current_user.id}: {e}")
        flash("Không thể tải danh sách khóa học.", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            
    return render_template('student_dashboard.html', current_user=current_user, courses=student_courses)


@app.route('/student/select_session/<int:course_id>')
@login_required(role='student')
def student_select_session(course_id):
    """Allows a student to select a session for a course."""
    current_user = get_current_user()
    conn = get_db_connection()
    if not conn:
        flash("Lỗi kết nối cơ sở dữ liệu.", "danger")
        return redirect(url_for('student_dashboard'))

    course = None
    sessions = []
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Get course details
        cursor.execute("SELECT id, course_code, course_name FROM courses WHERE id = %s", (course_id,))
        course = cursor.fetchone()

        if not course:
            flash("Khóa học không tồn tại.", "danger")
            return redirect(url_for('student_dashboard'))

        # Get sessions for the course
        cursor.execute("SELECT id, session_title, session_date FROM course_sessions WHERE course_id = %s ORDER BY session_date DESC, id DESC", (course_id,))
        sessions = cursor.fetchall()

    except Error as e:
        app.logger.error(f"Error fetching sessions for course {course_id}: {e}")
        flash("Không thể tải danh sách buổi học.", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

    return render_template('student_select_session.html', current_user=current_user, course=course, sessions=sessions)

# --- Faculty Routes ---
@app.route('/faculty/dashboard')
@login_required(role='faculty')
def faculty_dashboard():
    """Displays the faculty dashboard."""
    current_user = get_current_user()
    conn = get_db_connection()
    if not conn:
        flash("Lỗi kết nối cơ sở dữ liệu.", "danger")
        return redirect(url_for('login'))

    faculty_courses = []
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Get courses managed by this faculty member
        query = "SELECT id, course_code, course_name FROM courses WHERE faculty_id = %s"
        cursor.execute(query, (current_user.id,))
        faculty_courses = cursor.fetchall()
    except Error as e:
        app.logger.error(f"Error fetching faculty courses for user {current_user.id}: {e}")
        flash("Không thể tải danh sách khóa học.", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            
    return render_template('faculty_dashboard.html', current_user=current_user, courses=faculty_courses)


@app.route('/faculty/course_sessions/<int:course_id>', methods=['GET', 'POST'])
@login_required(role='faculty')
def faculty_course_sessions(course_id):
    """Manages course sessions for a faculty member."""
    current_user = get_current_user()
    conn = get_db_connection()
    if not conn:
        flash("Lỗi kết nối cơ sở dữ liệu.", "danger")
        return redirect(url_for('faculty_dashboard'))

    course = None
    sessions = []
    cursor = None # Define cursor outside try block

    try:
        cursor = conn.cursor(dictionary=True)
        # Verify faculty owns this course
        cursor.execute("SELECT id, course_code, course_name FROM courses WHERE id = %s AND faculty_id = %s", (course_id, current_user.id))
        course = cursor.fetchone()

        if not course:
            flash("Khóa học không hợp lệ hoặc bạn không có quyền truy cập.", "danger")
            return redirect(url_for('faculty_dashboard'))

        if request.method == 'POST':
            session_title = request.form.get('session_title')
            session_date_str = request.form.get('session_date')
            
            if not session_title or not session_date_str:
                flash("Tiêu đề buổi học và ngày là bắt buộc.", "warning")
            else:
                try:
                    session_date = datetime.datetime.strptime(session_date_str, '%Y-%m-%d').date()
                    insert_query = "INSERT INTO course_sessions (course_id, session_title, session_date) VALUES (%s, %s, %s)"
                    cursor.execute(insert_query, (course_id, session_title, session_date))
                    conn.commit()
                    flash("Buổi học đã được tạo thành công!", "success")
                except ValueError:
                    flash("Định dạng ngày không hợp lệ. Vui lòng sử dụng YYYY-MM-DD.", "danger")
                except Error as e:
                    app.logger.error(f"Error creating session for course {course_id}: {e}")
                    flash(f"Lỗi khi tạo buổi học: {e}", "danger")
                    conn.rollback() # Rollback on error
            return redirect(url_for('faculty_course_sessions', course_id=course_id)) # Redirect to refresh

        # Get existing sessions for the course
        cursor.execute("SELECT id, session_title, session_date FROM course_sessions WHERE course_id = %s ORDER BY session_date DESC, id DESC", (course_id,))
        sessions = cursor.fetchall()

    except Error as e:
        app.logger.error(f"Database error in faculty_course_sessions for course {course_id}: {e}")
        flash(f"Lỗi cơ sở dữ liệu: {e}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            
    return render_template('faculty_course_sessions.html', current_user=current_user, course=course, sessions=sessions)


@app.route('/faculty/upload_material/<int:session_id>', methods=['GET', 'POST'])
@login_required(role='faculty')
def faculty_upload_material(session_id):
    """Handles material uploads for a specific session by faculty."""
    current_user = get_current_user()
    conn = get_db_connection()
    if not conn:
        flash("Lỗi kết nối cơ sở dữ liệu.", "danger")
        return redirect(url_for('faculty_dashboard')) # Or a more relevant page

    session_details = None
    materials = []
    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)
        # Get session details and verify faculty ownership through course
        query_session = """
            SELECT cs.id, cs.session_title, cs.course_id, c.faculty_id
            FROM course_sessions cs
            JOIN courses c ON cs.course_id = c.id
            WHERE cs.id = %s AND c.faculty_id = %s
        """
        cursor.execute(query_session, (session_id, current_user.id))
        session_details = cursor.fetchone()

        if not session_details:
            flash("Buổi học không tồn tại hoặc bạn không có quyền tải lên tài liệu cho buổi học này.", "danger")
            return redirect(url_for('faculty_dashboard')) # Or faculty_course_sessions if course_id is known

        if request.method == 'POST':
            if 'material_file' not in request.files:
                flash('Không có tệp nào được chọn.', 'warning')
                return redirect(request.url)
            
            file = request.files['material_file']
            if file.filename == '':
                flash('Không có tệp nào được chọn.', 'warning')
                return redirect(request.url)

            if file: # Add allowed_file check if needed
                filename = secure_filename(file.filename)
                # Create a unique path for the file to avoid overwrites and organize by session
                session_upload_path = os.path.join(app.config['UPLOAD_FOLDER'], 'session_materials', str(session_id))
                if not os.path.exists(session_upload_path):
                    os.makedirs(session_upload_path)
                
                file_path = os.path.join(session_upload_path, filename)
                
                # Check if file with the same name already exists in this session's material list
                cursor.execute("SELECT id FROM session_materials WHERE session_id = %s AND file_name = %s", (session_id, filename))
                if cursor.fetchone():
                    flash(f"Tệp '{filename}' đã tồn tại cho buổi học này. Vui lòng đổi tên tệp hoặc xóa tệp cũ.", "warning")
                else:
                    try:
                        file.save(file_path)
                        # Save file metadata to database
                        insert_query = """
                            INSERT INTO session_materials (session_id, file_name, file_path, uploaded_by)
                            VALUES (%s, %s, %s, %s)
                        """
                        # Store relative path for flexibility if UPLOAD_FOLDER moves
                        relative_file_path = os.path.join('session_materials', str(session_id), filename)
                        cursor.execute(insert_query, (session_id, filename, relative_file_path, current_user.id))
                        conn.commit()
                        flash(f"Tệp '{filename}' đã được tải lên thành công.", 'success')
                    except Error as e:
                        app.logger.error(f"DB Error saving material for session {session_id}: {e}")
                        flash(f"Lỗi khi lưu thông tin tệp vào cơ sở dữ liệu: {e}", "danger")
                        conn.rollback()
                    except Exception as e: # Catch other potential errors like file system issues
                        app.logger.error(f"File save error for session {session_id}, file {filename}: {e}")
                        flash(f"Lỗi khi lưu tệp: {e}", "danger")

                return redirect(url_for('faculty_upload_material', session_id=session_id))

        # Get existing materials for the session
        cursor.execute("SELECT id, file_name, uploaded_at FROM session_materials WHERE session_id = %s ORDER BY uploaded_at DESC", (session_id,))
        materials = cursor.fetchall()

    except Error as e:
        app.logger.error(f"Database error in faculty_upload_material for session {session_id}: {e}")
        flash(f"Lỗi cơ sở dữ liệu: {e}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            
    return render_template('faculty_upload_material.html', current_user=current_user, session=session_details, materials=materials)


@app.route('/download_material/<int:material_id>')
@login_required() # Accessible by both students and faculty if they have access to the session
def download_material(material_id):
    """Allows downloading of a specific material."""
    current_user = get_current_user()
    conn = get_db_connection()
    if not conn:
        flash("Lỗi kết nối cơ sở dữ liệu.", "danger")
        return redirect(request.referrer or url_for('login')) # Go back or to login

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Fetch material details
        query = "SELECT file_name, file_path, session_id FROM session_materials WHERE id = %s"
        cursor.execute(query, (material_id,))
        material = cursor.fetchone()

        if not material:
            flash("Tài liệu không tồn tại.", "danger")
            return redirect(request.referrer or url_for('student_dashboard' if current_user.role == 'student' else 'faculty_dashboard'))

        # Security check: Ensure the current user (student or faculty) has access to the course/session of this material.
        # This is a simplified check. A more robust check would verify enrollment or teaching status for the course.
        session_access_query = """
            SELECT cs.id FROM course_sessions cs
            JOIN courses c ON cs.course_id = c.id
            LEFT JOIN enrollments e ON c.id = e.course_id AND e.student_id = %s
            WHERE cs.id = %s AND (c.faculty_id = %s OR e.student_id = %s)
        """
        cursor.execute(session_access_query, (current_user.id, material['session_id'], current_user.id, current_user.id))
        if not cursor.fetchone() and current_user.role != 'faculty': # Faculty might have broader access if they uploaded it
             # Re-check if faculty is the one who uploaded it or manages the course
            cursor.execute("""
                SELECT sm.id FROM session_materials sm
                JOIN course_sessions cs ON sm.session_id = cs.id
                JOIN courses c ON cs.course_id = c.id
                WHERE sm.id = %s AND (sm.uploaded_by = %s OR c.faculty_id = %s)
            """, (material_id, current_user.id, current_user.id))
            if not cursor.fetchone():
                flash("Bạn không có quyền tải xuống tài liệu này.", "danger")
                return redirect(request.referrer or url_for('student_dashboard' if current_user.role == 'student' else 'faculty_dashboard'))

        # Construct the full path from the UPLOAD_FOLDER and the stored relative file_path
        # Ensure material['file_path'] is the relative path like 'session_materials/session_id/filename.pdf'
        full_file_path = os.path.join(app.config['UPLOAD_FOLDER'], material['file_path'])
        directory = os.path.dirname(full_file_path)
        filename = os.path.basename(full_file_path)
        
        if not os.path.exists(full_file_path):
            app.logger.error(f"Material file not found at path: {full_file_path} for material_id: {material_id}")
            flash("Tệp tài liệu không tìm thấy trên máy chủ.", "danger")
            return redirect(request.referrer or url_for('student_dashboard' if current_user.role == 'student' else 'faculty_dashboard'))

        return send_from_directory(directory=directory, path=filename, as_attachment=True)

    except Error as e:
        app.logger.error(f"Database error downloading material {material_id}: {e}")
        flash(f"Lỗi cơ sở dữ liệu khi tải tài liệu: {e}", "danger")
    except Exception as e:
        app.logger.error(f"General error downloading material {material_id}: {e}")
        flash(f"Lỗi không xác định khi tải tài liệu: {e}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
    
    # Fallback redirect
    return redirect(request.referrer or url_for('student_dashboard' if current_user.role == 'student' else 'faculty_dashboard'))


# --- Notes Routes (Example - Needs to be fully converted) ---
@app.route('/notes/session/<int:session_id>')
@login_required() # Accessible by student or faculty if they have access to session
def course_notes_overview(session_id):
    """Displays notes for a specific session."""
    current_user = get_current_user()
    conn = get_db_connection()
    if not conn:
        flash("Lỗi kết nối cơ sở dữ liệu.", "danger")
        return redirect(url_for('login'))

    session_info = None
    notes_list = []
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Get session details and course name
        query_session = """
            SELECT cs.id, cs.session_title, cs.course_id, c.course_name, c.course_code
            FROM course_sessions cs
            JOIN courses c ON cs.course_id = c.id
            WHERE cs.id = %s
        """
        cursor.execute(query_session, (session_id,))
        session_info = cursor.fetchone()

        if not session_info:
            flash("Buổi học không tồn tại.", "danger")
            return redirect(url_for('student_dashboard') if current_user.role == 'student' else url_for('faculty_dashboard'))
        
        # Security: Check if user has access to this session's course
        # (Simplified: assumes if they can reach this, they have access, or add specific enrollment/faculty check)

        # Get notes for this session created by the current user
        # Or, if faculty, maybe show all notes for the session? (Adjust logic as needed)
        # For now, only user's own notes for the session
        notes_query = "SELECT id, title, LEFT(content, 100) as preview, updated_at FROM notes WHERE session_id = %s AND user_id = %s ORDER BY updated_at DESC"
        cursor.execute(notes_query, (session_id, current_user.id))
        notes_list = cursor.fetchall()

    except Error as e:
        app.logger.error(f"Error fetching notes for session {session_id}, user {current_user.id}: {e}")
        flash("Không thể tải ghi chú.", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            
    return render_template('course_notes_overview.html', current_user=current_user, session_info=session_info, notes=notes_list)


@app.route('/notes/create/<int:session_id>', methods=['GET', 'POST'])
@login_required()
def create_note(session_id):
    """Creates a new note for a session."""
    current_user = get_current_user()
    conn = get_db_connection()
    if not conn:
        flash("Lỗi kết nối cơ sở dữ liệu.", "danger")
        return redirect(url_for('course_notes_overview', session_id=session_id)) # Or appropriate redirect

    session_info = None
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Fetch session info to display on the page
        query_session = """
            SELECT cs.id, cs.session_title, c.course_name 
            FROM course_sessions cs
            JOIN courses c ON cs.course_id = c.id
            WHERE cs.id = %s
        """
        cursor.execute(query_session, (session_id,))
        session_info = cursor.fetchone()
        if not session_info:
            flash("Buổi học không hợp lệ.", "danger")
            return redirect(url_for('student_dashboard') if current_user.role == 'student' else url_for('faculty_dashboard'))

        if request.method == 'POST':
            title = request.form.get('title', 'Ghi chú không tiêu đề')
            content = request.form.get('content', '')

            insert_query = "INSERT INTO notes (session_id, user_id, title, content) VALUES (%s, %s, %s, %s)"
            cursor.execute(insert_query, (session_id, current_user.id, title, content))
            conn.commit()
            new_note_id = cursor.lastrowid # Get the ID of the newly inserted note
            flash('Ghi chú đã được tạo thành công!', 'success')
            return redirect(url_for('edit_note', note_id=new_note_id)) # Redirect to edit view of the new note
            
    except Error as e:
        app.logger.error(f"Error creating note for session {session_id}, user {current_user.id}: {e}")
        flash(f"Lỗi khi tạo ghi chú: {e}", "danger")
        if conn: conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('notes_template.html', current_user=current_user, session_info=session_info, note=None, is_new=True)


@app.route('/notes/edit/<int:note_id>', methods=['GET', 'POST'])
@login_required()
def edit_note(note_id):
    """Edits an existing note."""
    current_user = get_current_user()
    conn = get_db_connection()
    if not conn:
        flash("Lỗi kết nối cơ sở dữ liệu.", "danger")
        return redirect(url_for('login')) 

    note_data = None
    session_info = None
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Fetch note and ensure current user owns it
        query_note = """
            SELECT n.id, n.title, n.content, n.session_id, n.user_id,
                   cs.session_title, crs.course_name
            FROM notes n
            LEFT JOIN course_sessions cs ON n.session_id = cs.id
            LEFT JOIN courses crs ON cs.course_id = crs.id
            WHERE n.id = %s AND n.user_id = %s
        """
        cursor.execute(query_note, (note_id, current_user.id))
        note_data = cursor.fetchone()

        if not note_data:
            flash("Ghi chú không tồn tại hoặc bạn không có quyền chỉnh sửa.", "danger")
            # Determine a sensible redirect based on user role
            if current_user.role == 'student':
                 # Try to find if the note belongs to a session they have access to
                cursor.execute("SELECT session_id FROM notes WHERE id = %s", (note_id,))
                original_note_session = cursor.fetchone()
                if original_note_session and original_note_session['session_id']:
                    return redirect(url_for('course_notes_overview', session_id=original_note_session['session_id']))
                return redirect(url_for('student_dashboard'))
            else: # faculty or other roles
                return redirect(url_for('faculty_dashboard'))


        # Construct session_info if session_id is present
        if note_data['session_id']:
            session_info = {
                'id': note_data['session_id'],
                'session_title': note_data['session_title'],
                'course_name': note_data['course_name']
            }

        if request.method == 'POST':
            title = request.form.get('title', note_data['title'])
            content = request.form.get('content', note_data['content'])
            
            update_query = "UPDATE notes SET title = %s, content = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s AND user_id = %s"
            cursor.execute(update_query, (title, content, note_id, current_user.id))
            conn.commit()
            flash('Ghi chú đã được cập nhật!', 'success')
            # Refresh note_data after update
            cursor.execute(query_note, (note_id, current_user.id)) # Re-fetch
            note_data = cursor.fetchone()
            # return redirect(url_for('edit_note', note_id=note_id)) # Stay on page or redirect to overview

    except Error as e:
        app.logger.error(f"Error editing note {note_id} for user {current_user.id}: {e}")
        flash(f"Lỗi khi cập nhật ghi chú: {e}", "danger")
        if conn: conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    if not note_data: # If fetching failed initially or after an error
        # This case should ideally be caught earlier, but as a fallback:
        flash("Không thể tải ghi chú để chỉnh sửa.", "danger")
        return redirect(url_for('student_dashboard') if current_user.role == 'student' else url_for('faculty_dashboard'))
        
    return render_template('notes_template.html', current_user=current_user, note=note_data, session_info=session_info, is_new=False)


@app.route('/notes/delete/<int:note_id>', methods=['POST'])
@login_required()
def delete_note(note_id):
    """Deletes a note."""
    current_user = get_current_user()
    conn = get_db_connection()
    if not conn:
        flash("Lỗi kết nối cơ sở dữ liệu.", "danger")
        return jsonify({'success': False, 'message': 'Lỗi kết nối cơ sở dữ liệu.'})

    cursor = None
    original_session_id = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Get session_id before deleting for redirection
        cursor.execute("SELECT session_id FROM notes WHERE id = %s AND user_id = %s", (note_id, current_user.id))
        note_info = cursor.fetchone()
        if note_info:
            original_session_id = note_info['session_id']

        delete_query = "DELETE FROM notes WHERE id = %s AND user_id = %s"
        cursor.execute(delete_query, (note_id, current_user.id))
        conn.commit()

        if cursor.rowcount > 0:
            flash('Ghi chú đã được xóa.', 'success')
            if original_session_id:
                 return jsonify({'success': True, 'redirect_url': url_for('course_notes_overview', session_id=original_session_id)})
            else: # If note was not tied to a session or session_id is lost
                 return jsonify({'success': True, 'redirect_url': url_for('student_dashboard' if current_user.role == 'student' else 'faculty_dashboard')})
        else:
            flash('Không tìm thấy ghi chú hoặc bạn không có quyền xóa.', 'warning')
            return jsonify({'success': False, 'message': 'Không tìm thấy ghi chú hoặc không có quyền xóa.'})

    except Error as e:
        app.logger.error(f"Error deleting note {note_id} for user {current_user.id}: {e}")
        flash(f"Lỗi khi xóa ghi chú: {e}", "danger")
        if conn: conn.rollback()
        return jsonify({'success': False, 'message': f'Lỗi cơ sở dữ liệu: {e}'})
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    
    # Fallback redirect if original_session_id was not found
    fallback_redirect = url_for('student_dashboard') if current_user.role == 'student' else url_for('faculty_dashboard')
    return jsonify({'success': False, 'message': 'Lỗi không xác định.', 'redirect_url': fallback_redirect })


# --- Flashcard Routes (Example - Needs to be fully converted) ---
@app.route('/student/flashcard_hub/course/<int:course_id>')
@login_required(role='student')
def student_flashcard_hub_course(course_id):
    """Displays flashcard hubs for a specific course for a student."""
    current_user = get_current_user()
    conn = get_db_connection()
    if not conn: return redirect(url_for('student_dashboard')) # Simplified error handling

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

        # Get flashcard hubs for this user and course
        hub_query = "SELECT id, name, created_at FROM flashcard_hubs WHERE user_id = %s AND course_id = %s ORDER BY name"
        cursor.execute(hub_query, (current_user.id, course_id))
        hubs = cursor.fetchall()
    except Error as e:
        app.logger.error(f"DB error fetching flashcard hubs for course {course_id}, user {current_user.id}: {e}")
        flash("Lỗi tải bộ flashcard.", "danger")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('student_flashcard_hub.html', current_user=current_user, course=course_info, hubs=hubs)

@app.route('/student/flashcard_hub/create/<int:course_id>', methods=['POST'])
@login_required(role='student')
def create_flashcard_hub(course_id):
    """Creates a new flashcard hub for a student within a course."""
    current_user = get_current_user()
    hub_name = request.form.get('hub_name')
    if not hub_name:
        flash("Tên bộ flashcard là bắt buộc.", "warning")
        return redirect(url_for('student_flashcard_hub_course', course_id=course_id))

    conn = get_db_connection()
    if not conn: return redirect(url_for('student_flashcard_hub_course', course_id=course_id))

    cursor = None
    try:
        cursor = conn.cursor()
        insert_query = "INSERT INTO flashcard_hubs (user_id, course_id, name) VALUES (%s, %s, %s)"
        cursor.execute(insert_query, (current_user.id, course_id, hub_name))
        conn.commit()
        flash(f"Bộ flashcard '{hub_name}' đã được tạo.", "success")
    except Error as e:
        app.logger.error(f"DB error creating flashcard hub for course {course_id}, user {current_user.id}: {e}")
        flash(f"Lỗi tạo bộ flashcard: {e}", "danger")
        if conn: conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
        
    return redirect(url_for('student_flashcard_hub_course', course_id=course_id))


@app.route('/student/flashcards/view/<int:hub_id>')
@login_required(role='student')
def student_view_flashcards(hub_id):
    """Displays flashcards within a specific hub for a student."""
    current_user = get_current_user()
    conn = get_db_connection()
    if not conn: return redirect(url_for('student_dashboard')) # Simplified

    hub_info = None
    flashcards_list = []
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Get hub info and verify ownership
        hub_query = """
            SELECT fh.id, fh.name, fh.course_id, c.course_name 
            FROM flashcard_hubs fh
            JOIN courses c ON fh.course_id = c.id
            WHERE fh.id = %s AND fh.user_id = %s
        """
        cursor.execute(hub_query, (hub_id, current_user.id))
        hub_info = cursor.fetchone()

        if not hub_info:
            flash("Bộ flashcard không tồn tại hoặc bạn không có quyền truy cập.", "danger")
            return redirect(url_for('student_dashboard')) # Or a more relevant course page

        # Get flashcards for this hub
        fc_query = "SELECT id, question, answer FROM flashcards WHERE hub_id = %s ORDER BY id"
        cursor.execute(fc_query, (hub_id,))
        flashcards_list = cursor.fetchall()
    except Error as e:
        app.logger.error(f"DB error fetching flashcards for hub {hub_id}, user {current_user.id}: {e}")
        flash("Lỗi tải flashcards.", "danger")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
        
    return render_template('student_view_flashcards.html', current_user=current_user, hub=hub_info, flashcards=flashcards_list)


@app.route('/student/flashcards/add_to_hub/<int:hub_id>', methods=['POST'])
@login_required(role='student')
def add_flashcard_to_hub(hub_id):
    """Adds a new flashcard to a student's hub."""
    current_user = get_current_user()
    question = request.form.get('question')
    answer = request.form.get('answer')

    if not question or not answer:
        flash("Câu hỏi và câu trả lời không được để trống.", "warning")
        return redirect(url_for('student_view_flashcards', hub_id=hub_id))

    conn = get_db_connection()
    if not conn: return redirect(url_for('student_view_flashcards', hub_id=hub_id))

    cursor = None
    try:
        cursor = conn.cursor()
        # Verify user owns the hub first (important for security)
        cursor.execute("SELECT id FROM flashcard_hubs WHERE id = %s AND user_id = %s", (hub_id, current_user.id))
        if not cursor.fetchone():
            flash("Bạn không có quyền thêm flashcard vào bộ này.", "danger")
            return redirect(url_for('student_dashboard'))

        insert_query = "INSERT INTO flashcards (hub_id, question, answer) VALUES (%s, %s, %s)"
        cursor.execute(insert_query, (hub_id, question, answer))
        conn.commit()
        flash("Flashcard đã được thêm.", "success")
    except Error as e:
        app.logger.error(f"DB error adding flashcard to hub {hub_id}, user {current_user.id}: {e}")
        flash(f"Lỗi thêm flashcard: {e}", "danger")
        if conn: conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return redirect(url_for('student_view_flashcards', hub_id=hub_id))


# --- Quiz Routes (Example - Needs to be fully converted) ---
@app.route('/faculty/manage_quiz/<int:course_id>', methods=['GET', 'POST'])
@login_required(role='faculty')
def faculty_manage_quiz(course_id):
    """Allows faculty to manage quizzes for a course (view existing, link to create new)."""
    current_user = get_current_user()
    conn = get_db_connection()
    if not conn: return redirect(url_for('faculty_dashboard'))

    course_info = None
    quizzes_list = []
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Verify faculty owns course
        cursor.execute("SELECT id, course_code, course_name FROM courses WHERE id = %s AND faculty_id = %s", (course_id, current_user.id))
        course_info = cursor.fetchone()
        if not course_info:
            flash("Khóa học không hợp lệ hoặc bạn không có quyền quản lý quiz cho khóa học này.", "danger")
            return redirect(url_for('faculty_dashboard'))

        # Get quizzes for this course
        quiz_query = "SELECT id, title, created_at FROM quizzes WHERE course_id = %s AND created_by = %s ORDER BY created_at DESC"
        cursor.execute(quiz_query, (course_id, current_user.id))
        quizzes_list = cursor.fetchall()
    except Error as e:
        app.logger.error(f"DB error fetching quizzes for course {course_id}, faculty {current_user.id}: {e}")
        flash("Lỗi tải danh sách quiz.", "danger")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('faculty_manage_quiz.html', current_user=current_user, course=course_info, quizzes=quizzes_list)


@app.route('/faculty/quiz/create/<int:course_id>', methods=['GET', 'POST'])
@login_required(role='faculty')
def faculty_create_quiz(course_id):
    """Allows faculty to create a new quiz with questions."""
    current_user = get_current_user()
    conn = get_db_connection()
    if not conn:
        flash("Lỗi kết nối cơ sở dữ liệu.", "danger")
        return redirect(url_for('faculty_manage_quiz', course_id=course_id))

    course_info = None
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Verify faculty owns course
        cursor.execute("SELECT id, course_code, course_name FROM courses WHERE id = %s AND faculty_id = %s", (course_id, current_user.id))
        course_info = cursor.fetchone()
        if not course_info:
            flash("Khóa học không hợp lệ.", "danger")
            return redirect(url_for('faculty_dashboard'))

        if request.method == 'POST':
            quiz_title = request.form.get('quiz_title')
            if not quiz_title:
                flash("Tiêu đề quiz là bắt buộc.", "warning")
                return render_template('faculty_create_quiz_form.html', current_user=current_user, course=course_info, quiz=None, questions=[]) # Reshow form

            quiz_id = None
            try:
                # Start transaction
                # conn.start_transaction() # For connectors that support it explicitly
                
                # Insert quiz
                quiz_insert_query = "INSERT INTO quizzes (course_id, title, created_by) VALUES (%s, %s, %s)"
                cursor.execute(quiz_insert_query, (course_id, quiz_title, current_user.id))
                quiz_id = cursor.lastrowid

                # Process questions
                # Questions are expected to be submitted in a structured way, e.g.,
                # question_text_1, question_type_1, options_1_1, options_1_2, correct_answer_1
                # question_text_2, ...
                
                # This is a simplified way to get questions; a dynamic JS form would be better
                # For now, let's assume a fixed number or a way to count them from form keys
                i = 0
                while True:
                    i += 1
                    question_text = request.form.get(f'questions[{i-1}][question_text]')
                    if not question_text:
                        break # No more questions

                    question_type = request.form.get(f'questions[{i-1}][question_type]')
                    # For multiple choice, options might be like: questions[0][options][0], questions[0][options][1]
                    # This part needs careful handling based on your HTML form structure
                    options_list = []
                    opt_idx = 0
                    while True:
                        option_val = request.form.get(f'questions[{i-1}][options][{opt_idx}]')
                        if option_val is None : # Check for None, as empty string could be a valid (though unlikely) option
                            break
                        if option_val.strip() != "": # Only add non-empty options
                           options_list.append(option_val.strip())
                        opt_idx += 1
                    
                    options_json = None
                    if question_type == 'multiple_choice' and options_list:
                        options_json = jsonify(options_list).get_data(as_text=True) # Store as JSON string
                    
                    correct_answer = request.form.get(f'questions[{i-1}][correct_answer]')

                    if question_text and question_type and correct_answer:
                        q_insert = """INSERT INTO questions (quiz_id, question_text, question_type, options, correct_answer)
                                      VALUES (%s, %s, %s, %s, %s)"""
                        cursor.execute(q_insert, (quiz_id, question_text, question_type, options_json, correct_answer))
                
                conn.commit()
                flash(f"Quiz '{quiz_title}' đã được tạo thành công!", "success")
                return redirect(url_for('faculty_manage_quiz', course_id=course_id))

            except Error as e:
                app.logger.error(f"DB Error creating quiz/questions for course {course_id}: {e}")
                flash(f"Lỗi khi tạo quiz: {e}", "danger")
                if conn: conn.rollback()
            except Exception as e: # Catch other errors
                app.logger.error(f"General error creating quiz: {e}")
                flash(f"Lỗi không xác định: {e}", "danger")
                if conn: conn.rollback() # Ensure rollback for non-DB errors too if transaction started

        # GET request: show form to create quiz
        return render_template('faculty_create_quiz_form.html', current_user=current_user, course=course_info, quiz=None, questions=[])

    except Error as e:
        app.logger.error(f"DB error in faculty_create_quiz GET for course {course_id}: {e}")
        flash(f"Lỗi tải trang tạo quiz: {e}", "danger")
        return redirect(url_for('faculty_manage_quiz', course_id=course_id))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()


@app.route('/student/take_quiz/<int:quiz_id>')
@login_required(role='student')
def student_take_quiz(quiz_id):
    """Allows a student to take a quiz."""
    current_user = get_current_user()
    conn = get_db_connection()
    if not conn: return redirect(url_for('student_dashboard'))

    quiz_info = None
    questions = []
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Get quiz details
        cursor.execute("SELECT id, title, course_id FROM quizzes WHERE id = %s", (quiz_id,))
        quiz_info = cursor.fetchone()
        if not quiz_info:
            flash("Quiz không tồn tại.", "danger")
            return redirect(url_for('student_dashboard')) # Or a course page

        # Get questions for the quiz
        # Options are stored as JSON string, need to parse them in template or here
        q_query = "SELECT id, question_text, question_type, options FROM questions WHERE quiz_id = %s ORDER BY id"
        cursor.execute(q_query, (quiz_id,))
        questions_raw = cursor.fetchall()
        
        # Process options if they are JSON
        import json
        for q in questions_raw:
            if q['question_type'] == 'multiple_choice' and q['options']:
                try:
                    q['options_list'] = json.loads(q['options'])
                except json.JSONDecodeError:
                    q['options_list'] = [] # Handle malformed JSON
            else:
                q['options_list'] = []
            questions.append(q)


    except Error as e:
        app.logger.error(f"DB error fetching quiz {quiz_id} for student {current_user.id}: {e}")
        flash("Lỗi tải quiz.", "danger")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    if not quiz_info: # Should be caught earlier
        return redirect(url_for('student_dashboard'))
        
    return render_template('student_take_quiz.html', current_user=current_user, quiz=quiz_info, questions=questions)


@app.route('/student/submit_quiz/<int:quiz_id>', methods=['POST'])
@login_required(role='student')
def student_submit_quiz(quiz_id):
    """Handles submission of a student's quiz attempt."""
    current_user = get_current_user()
    conn = get_db_connection()
    if not conn:
        flash("Lỗi kết nối cơ sở dữ liệu.", "danger")
        return redirect(url_for('student_take_quiz', quiz_id=quiz_id))

    cursor = None
    attempt_id = None
    total_score = 0
    num_questions = 0

    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get all questions and their correct answers for this quiz
        cursor.execute("SELECT id, correct_answer, question_type FROM questions WHERE quiz_id = %s", (quiz_id,))
        quiz_questions = {q['id']: {'correct': q['correct_answer'], 'type': q['question_type']} for q in cursor.fetchall()}
        num_questions = len(quiz_questions)

        if not num_questions:
            flash("Quiz này không có câu hỏi nào.", "warning")
            return redirect(url_for('student_dashboard')) # Or course page

        # Create a quiz attempt entry
        attempt_insert_query = "INSERT INTO quiz_attempts (quiz_id, student_id, score) VALUES (%s, %s, %s)"
        # Initial score, will be updated
        cursor.execute(attempt_insert_query, (quiz_id, current_user.id, 0.0)) 
        attempt_id = cursor.lastrowid

        # Process submitted answers
        # Form data is expected like: answers[question_id_1], answers[question_id_2]
        submitted_answers = request.form # Or request.form.to_dict() if needed

        for q_id, q_data in quiz_questions.items():
            student_ans_key = f"answers[{q_id}]" # Assuming form names like this
            student_answer = submitted_answers.get(student_ans_key)
            
            is_correct = False
            # Simple comparison, might need more sophisticated logic for different question types
            # For MC, correct_answer might be the option text or an index. This assumes text.
            if student_answer and student_answer.strip().lower() == q_data['correct'].strip().lower():
                is_correct = True
                total_score += 1
            
            ans_insert_query = """
                INSERT INTO attempt_answers (attempt_id, question_id, student_answer, is_correct)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(ans_insert_query, (attempt_id, q_id, student_answer, is_correct))

        # Update the score in quiz_attempts table
        final_percentage_score = (total_score / num_questions) * 100 if num_questions > 0 else 0
        cursor.execute("UPDATE quiz_attempts SET score = %s WHERE id = %s", (final_percentage_score, attempt_id))
        
        conn.commit()
        flash(f"Bài quiz đã được nộp! Điểm của bạn: {total_score}/{num_questions} ({final_percentage_score:.2f}%)", "success")
        return redirect(url_for('student_quiz_results', attempt_id=attempt_id))

    except Error as e:
        app.logger.error(f"DB error submitting quiz {quiz_id} for student {current_user.id}: {e}")
        flash(f"Lỗi khi nộp bài quiz: {e}", "danger")
        if conn: conn.rollback()
        return redirect(url_for('student_take_quiz', quiz_id=quiz_id))
    except Exception as e: # Catch other unexpected errors
        app.logger.error(f"Unexpected error submitting quiz {quiz_id}: {e}")
        flash(f"Lỗi không mong muốn: {e}", "danger")
        if conn: conn.rollback()
        return redirect(url_for('student_take_quiz', quiz_id=quiz_id))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()


@app.route('/student/quiz_results/<int:attempt_id>')
@login_required(role='student')
def student_quiz_results(attempt_id):
    """Displays the results of a specific quiz attempt for a student."""
    current_user = get_current_user()
    conn = get_db_connection()
    if not conn: return redirect(url_for('student_dashboard'))

    attempt_details = None
    answers_details = []
    quiz_title = ""
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Get attempt details and verify student ownership
        attempt_query = """
            SELECT qa.id, qa.quiz_id, qa.student_id, qa.score, qa.attempted_at, q.title as quiz_title
            FROM quiz_attempts qa
            JOIN quizzes q ON qa.quiz_id = q.id
            WHERE qa.id = %s AND qa.student_id = %s
        """
        cursor.execute(attempt_query, (attempt_id, current_user.id))
        attempt_details = cursor.fetchone()

        if not attempt_details:
            flash("Không tìm thấy kết quả bài làm hoặc bạn không có quyền xem.", "danger")
            return redirect(url_for('student_dashboard'))
        
        quiz_title = attempt_details['quiz_title']

        # Get answers for this attempt with question text and correct answer
        answers_query = """
            SELECT aa.student_answer, aa.is_correct, q.question_text, q.correct_answer, q.options, q.question_type
            FROM attempt_answers aa
            JOIN questions q ON aa.question_id = q.id
            WHERE aa.attempt_id = %s
            ORDER BY q.id
        """
        cursor.execute(answers_query, (attempt_id,))
        answers_raw = cursor.fetchall()

        import json
        for ans in answers_raw:
            if ans['question_type'] == 'multiple_choice' and ans['options']:
                try:
                    ans['options_list'] = json.loads(ans['options'])
                except json.JSONDecodeError:
                    ans['options_list'] = []
            else:
                ans['options_list'] = []
            answers_details.append(ans)


    except Error as e:
        app.logger.error(f"DB error fetching quiz results for attempt {attempt_id}, student {current_user.id}: {e}")
        flash("Lỗi tải kết quả quiz.", "danger")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    if not attempt_details: # Should be caught
        return redirect(url_for('student_dashboard'))
        
    return render_template('student_quiz_results.html', current_user=current_user, attempt=attempt_details, answers=answers_details, quiz_title=quiz_title)

# --- General Routes ---
@app.route('/')
def index():
    """Redirects to login page or appropriate dashboard if logged in."""
    current_user = get_current_user()
    if current_user:
        if current_user.role == 'student':
            return redirect(url_for('student_dashboard'))
        elif current_user.role == 'faculty':
            return redirect(url_for('faculty_dashboard'))
    return redirect(url_for('login'))

@app.context_processor
def inject_current_year():
    """Injects the current year into all templates."""
    return {'current_year': datetime.datetime.now().year}

if __name__ == '__main__':
    # For development, ensure the MySQL server is running and accessible.
    # You might need to create the 'umtsmartnotes' database manually first if it doesn't exist.
    # Example: mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS umtsmartnotes;"
    # Then, create the tables as per the schemas defined above.
    app.run(debug=True)
