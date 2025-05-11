# app.py
from flask import Flask, render_template
import datetime # Thêm thư viện datetime

app = Flask(__name__)

# Dữ liệu mẫu (sau này sẽ được thay thế bằng cơ sở dữ liệu và logic thực tế)
user_info = {
    "name": "Sinh viên UMT",
    "major": "Công nghệ thông tin"
}

courses_sample = [
    {"id": "CS101", "name": "Nhập môn Lập trình", "schedule": "Thứ 2, Tiết 1-3"},
    {"id": "MA101", "name": "Toán cao cấp A1", "schedule": "Thứ 3, Tiết 4-6"},
    {"id": "EN101", "name": "Tiếng Anh học thuật 1", "schedule": "Thứ 4, Tiết 1-3"},
    {"id": "BM202", "name": "Quản trị Marketing", "schedule": "Thứ 5, Tiết 7-9"},
    {"id": "ECO101", "name": "Kinh tế vi mô", "schedule": "Thứ 6, Tiết 1-3"},
]

# Dữ liệu mẫu cho các sự kiện lịch
# Trong thực tế, ngày tháng cần được xử lý động
today = datetime.date.today()
calendar_events_sample = [
    {
        "id": "event1",
        "course_id": "CS101",
        "title": "Nhập môn Lập trình",
        "date": today.strftime("%Y-%m-%d"),
        "start_time": "07:30",
        "end_time": "09:30",
        "lecturer_materials_url": "#", # Placeholder
        "notes_link": "/notes/CS101" # Liên kết đến trang ghi chú chung của môn học
    },
    {
        "id": "event2",
        "course_id": "MA101",
        "title": "Toán cao cấp A1",
        "date": (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
        "start_time": "09:45",
        "end_time": "11:45",
        "lecturer_materials_url": "#",
        "notes_link": "/notes/MA101"
    },
    {
        "id": "event3",
        "course_id": "EN101",
        "title": "Tiếng Anh học thuật 1",
        "date": (today + datetime.timedelta(days=2)).strftime("%Y-%m-%d"),
        "start_time": "07:30",
        "end_time": "09:30",
        "lecturer_materials_url": "#",
        "notes_link": "/notes/EN101"
    },
     {
        "id": "event4",
        "course_id": "CS101", # Một buổi học khác của CS101
        "title": "Nhập môn Lập trình - Lab",
        "date": (today + datetime.timedelta(days=5)).strftime("%Y-%m-%d"),
        "start_time": "13:30",
        "end_time": "15:30",
        "lecturer_materials_url": "#",
        "notes_link": "/notes/CS101"
    }
]

# Route cho trang chính (Dashboard)
@app.route('/')
def dashboard():
    """
    Hiển thị trang tổng quan chính của ứng dụng.
    """
    upcoming_reviews = [
        {"subject": "Nhập môn Lập trình", "topic": "Biến và kiểu dữ liệu", "due_date": "Ngày mai"},
        {"subject": "Toán cao cấp A1", "topic": "Giới hạn hàm số", "due_date": "Trong 2 ngày"},
    ]
    # Lấy 3 sự kiện lịch gần nhất cho dashboard
    upcoming_events = sorted([event for event in calendar_events_sample if datetime.datetime.strptime(event['date'], '%Y-%m-%d').date() >= today], key=lambda x: x['date'])[:3]

    return render_template(
        'index.html',
        user=user_info,
        courses=courses_sample,
        reviews=upcoming_reviews,
        calendar_events=calendar_events_sample, # Truyền dữ liệu lịch
        upcoming_events_dashboard = upcoming_events # Truyền dữ liệu lịch cho dashboard
    )

# Route cho trang ghi chú (ví dụ)
@app.route('/notes/<course_id>')
def notes(course_id):
    """
    Hiển thị trang ghi chú cho một môn học cụ thể.
    """
    course = next((c for c in courses_sample if c["id"] == course_id), None)
    if not course:
        return "Không tìm thấy môn học", 404
    return render_template('notes_template.html', course=course, user=user_info)

# (Thêm) Route giả lập để lấy tài liệu (ví dụ)
@app.route('/materials/<course_id>/<event_date>')
def get_materials(course_id, event_date):
    """
    Giả lập việc lấy tài liệu cho một buổi học cụ thể.
    Trong thực tế, bạn sẽ truy vấn CSDL hoặc API Canvas/SIS.
    """
    course = next((c for c in courses_sample if c["id"] == course_id), None)
    if not course:
        return {"error": "Course not found"}, 404
    
    # Giả sử tài liệu là một danh sách các link hoặc tên file
    materials = [
        f"Slide bài giảng {course['name']} - Buổi {event_date}.pdf",
        f"Bài tập về nhà {event_date}.docx",
        "Link tham khảo thêm: example.com/resource"
    ]
    return {"course_name": course['name'], "event_date": event_date, "materials": materials}


if __name__ == '__main__':
    app.run(debug=True)
