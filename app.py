from flask import Flask, request, jsonify, render_template, session, redirect, url_for # Đảm bảo các import cần thiết
import pytesseract
from PIL import Image
import io
import fitz  # PyMuPDF
import os
import sqlite3 # Giả sử bạn dùng SQLite, điều chỉnh nếu khác
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename # For secure filenames

# Initialize Flask App
app = Flask(__name__)
app.secret_key = os.urandom(24) # Needed for session management

# Database setup (giả sử tên DB là umtsmartnotes.db)
DATABASE = 'umtsmartnotes.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row # Access columns by name
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()
# Nếu bạn chưa có schema.sql, bạn cần tạo nó để định nghĩa bảng users, notes, etc.
# Ví dụ schema.sql (rất cơ bản):
# CREATE TABLE IF NOT EXISTS users (
# id INTEGER PRIMARY KEY AUTOINCREMENT,
# username TEXT UNIQUE NOT NULL,
# password TEXT NOT NULL,
# role TEXT NOT NULL CHECK(role IN ('student', 'faculty'))
# );
# CREATE TABLE IF NOT EXISTS courses (
# id INTEGER PRIMARY KEY AUTOINCREMENT,
# course_name TEXT NOT NULL,
# faculty_id INTEGER,
# FOREIGN KEY (faculty_id) REFERENCES users (id)
# );
# -- Thêm các bảng khác nếu cần: notes, flashcards, quizzes, course_materials, sessions

# --- OCR Configuration and Upload Folder ---
# Configure Tesseract path if necessary (example for Windows, adjust for your OS)
# try:
#     pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe' # Windows
#     # For Linux/macOS, Tesseract is often in PATH, so this might not be needed.
#     # If not found, you might need to install Tesseract:
#     # sudo apt-get install tesseract-ocr (Debian/Ubuntu)
#     # brew install tesseract (macOS)
# except Exception as e:
#     print(f"Pytesseract config error (this might be ignorable if Tesseract is in PATH): {e}")


UPLOAD_FOLDER = 'temp_uploads_ocr' # Folder for temporary OCR files
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Helper Functions for OCR ---
def ocr_image(image_path):
    """
    Performs OCR on a single image file.
    Args:
        image_path (str): Path to the image file.
    Returns:
        str: Extracted text, or None if an error occurred.
    """
    try:
        text = pytesseract.image_to_string(Image.open(image_path), lang='vie+eng') # Thêm tiếng Việt (vie) và tiếng Anh (eng)
        return text
    except Exception as e:
        print(f"Error during image OCR: {e}")
        return None

def ocr_pdf(pdf_path):
    """
    Performs OCR on a PDF file, page by page.
    Converts each page to an image before OCR.
    Args:
        pdf_path (str): Path to the PDF file.
    Returns:
        str: Concatenated extracted text from all pages, or None if an error occurred.
    """
    full_text = ""
    doc = None # Initialize doc to None
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # Increase resolution for better OCR accuracy
            zoom_x = 2.0  # Zoom factor for x-axis
            zoom_y = 2.0  # Zoom factor for y-axis
            mat = fitz.Matrix(zoom_x, zoom_y)
            pix = page.get_pixmap(matrix=mat, alpha=False) # Get pixmap of the page, no alpha for smaller size
            
            img_byte_arr = io.BytesIO() # Create a BytesIO object
            img = Image.open(io.BytesIO(pix.tobytes("png"))) # Convert pixmap to PIL Image via PNG bytes
            
            # Perform OCR on the image of the page
            # Using lang='vie+eng' for Vietnamese and English
            page_text = pytesseract.image_to_string(img, lang='vie+eng') 
            full_text += page_text + "\n\n--- Trang " + str(page_num + 1) + " ---\n\n"
        
        return full_text
    except Exception as e:
        print(f"Error during PDF OCR for {pdf_path}: {e}")
        return None
    finally:
        if doc:
            doc.close() # Ensure the document is closed

# --- Routes ---
# (Giả sử bạn đã có các route cho login, register, dashboard, etc.)
# Ví dụ một route login đơn giản:
from flask import g # for get_db

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            # Redirect based on role
            if user['role'] == 'student':
                return redirect(url_for('student_dashboard'))
            elif user['role'] == 'faculty':
                return redirect(url_for('faculty_dashboard'))
        else:
            flash('Tên đăng nhập hoặc mật khẩu không đúng.') # Cần import flash từ flask
            return render_template('login.html', error="Tên đăng nhập hoặc mật khẩu không đúng.")
    return render_template('login.html') # Đảm bảo bạn có file login.html

@app.route('/student_dashboard')
def student_dashboard():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))
    # Thêm logic cho student dashboard ở đây
    return f"Welcome Student {session.get('username')}! <a href='/scan_document'>Scan Document</a> <a href='/logout'>Logout</a>"

@app.route('/faculty_dashboard')
def faculty_dashboard():
    if 'user_id' not in session or session.get('role') != 'faculty':
        return redirect(url_for('login'))
    # Thêm logic cho faculty dashboard ở đây
    return f"Welcome Faculty {session.get('username')}! <a href='/scan_document'>Scan Document</a> <a href='/logout'>Logout</a>"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Route to serve the scan document page
@app.route('/scan_document')
def scan_document_page():
    if 'user_id' not in session: # Basic authentication check
        return redirect(url_for('login'))
    return render_template('scan_document.html')

# Route to handle OCR processing
@app.route('/perform_ocr', methods=['POST'])
def perform_ocr_route(): # Changed function name to avoid conflict
    if 'user_id' not in session: # Basic authentication check
        return jsonify({'error': 'Unauthorized access'}), 401

    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected for uploading'}), 400

    if file:
        # Use secure_filename to prevent security issues with filenames
        filename = secure_filename(file.filename) 
        temp_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(temp_file_path) # Save the uploaded file temporarily
            
            extracted_text = ""
            # Determine file type and perform OCR accordingly
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
                extracted_text = ocr_image(temp_file_path)
            elif filename.lower().endswith('.pdf'):
                extracted_text = ocr_pdf(temp_file_path)
            else:
                # Unsupported file type
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                return jsonify({'error': 'Unsupported file type. Please upload an image or PDF.'}), 400
            
            # Clean up the temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

            if extracted_text is not None:
                return jsonify({'text': extracted_text})
            else:
                return jsonify({'error': 'Could not extract text from the file. The file might be empty or corrupted, or OCR failed.'}), 500
        
        except Exception as e:
            # Log the exception for debugging
            print(f"Exception in perform_ocr_route: {e}")
            # Clean up temp file in case of an error during processing
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            return jsonify({'error': f'An server error occurred: {str(e)}'}), 500
            
    return jsonify({'error': 'File processing failed unexpectedly.'}), 500

# Make sure to import 'g' and 'flash' from flask if you use them
from flask import g, flash

if __name__ == '__main__':
    # Create the UPLOAD_FOLDER if it doesn't exist when the app starts
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    # init_db() # Khởi tạo DB nếu cần, chỉ chạy một lần hoặc khi schema thay đổi
    app.run(debug=True, host='0.0.0.0', port=5001) # Example run configuration
