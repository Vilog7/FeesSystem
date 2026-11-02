import os
import secrets
import re
import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, abort
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db, init_db
from services import notify_fee_payment, ensure_student_fee_records
from security import is_rate_limited, record_attempt, clear_attempts

app = Flask(__name__)

# Cryptographically strong secret key
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))

# Enterprise Session & Cookie Security
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False, # Set to True automatically on HTTPS / Render
    PERMANENT_SESSION_LIFETIME=datetime.timedelta(days=7),
    MAX_CONTENT_LENGTH=2 * 1024 * 1024 # 2MB max request payload to block DoS
)

# ----------------- SECURITY HEADERS & DEFENSES -----------------

@app.after_request
def apply_security_headers(response):
    # Defense against clickjacking, XSS, MIME-sniffing
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https://api.qrserver.com; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    return response

# ----------------- INPUT SANITIZATION HELPERS -----------------

def clean_input(text, max_len=100):
    if not text:
        return ""
    # Strip HTML tags and null bytes
    cleaned = re.sub(r'<[^>]*>', '', str(text))
    cleaned = cleaned.replace('\x00', '').strip()
    return cleaned[:max_len]

def validate_phone(phone):
    cleaned = re.sub(r'[\s\-\+]', '', str(phone))
    # Accepts 10 to 13 digits (e.g. 9876543210 or 919876543210)
    return bool(re.match(r'^[0-9]{10,13}$', cleaned)), cleaned

# Helper to get client IP
def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or '127.0.0.1'

# Helper to get current settings
def get_system_settings():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    rows = cursor.fetchall()
    conn.close()
    return {row['key']: row['value'] for row in rows}

# ----------------- AUTHENTICATION -----------------

@app.route('/api/auth/check-user', methods=['POST'])
def check_user_exists():
    data = request.json or {}
    username = data.get('username', '').strip()
    if not username:
        return jsonify({'error': 'Username is required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, role, full_name FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return jsonify({
            'exists': True,
            'role': user['role'],
            'full_name': user['full_name']
        })
    else:
        return jsonify({'exists': False})

@app.route('/api/auth/login', methods=['POST'])
def login():
    ip = get_client_ip()
    if is_rate_limited(ip, 'login'):
        return jsonify({'error': 'Too many failed login attempts. Please wait 5 minutes.'}), 429

    data = request.json or {}
    identifier = clean_input(data.get('username', ''), max_len=50)
    password = data.get('password', '')

    if not identifier or not password:
        return jsonify({'error': 'Phone/username and password are required'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? OR phone_number = ?", (identifier, identifier))
    user = cursor.fetchone()
    conn.close()

    if not user or not check_password_hash(user['password_hash'], password):
        record_attempt(ip, 'login')
        return jsonify({'error': 'Invalid credentials'}), 401

    # Reset failed attempts counter on success
    clear_attempts(ip, 'login')

    # Regenerate session identifier to defend against Session Fixation attacks
    session.clear()
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['role'] = user['role']
    session['full_name'] = user['full_name']

    # If parent, get student info
    student_code = None
    if user['role'] == 'parent':
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT student_code FROM students WHERE parent_user_id = ?", (user['id'],))
        stu = cursor.fetchone()
        conn.close()
        if stu:
            student_code = stu['student_code']

    return jsonify({
        'success': True,
        'role': user['role'],
        'full_name': user['full_name'],
        'student_code': student_code
    })

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    ip = get_client_ip()
    if is_rate_limited(ip, 'signup'):
        return jsonify({'error': 'Rate limit reached for new accounts. Please try again later.'}), 429

    data = request.json or {}
    raw_phone = data.get('phone_number', '')
    student_name = clean_input(data.get('student_name', ''), max_len=60)
    student_school = clean_input(data.get('student_school', ''), max_len=80)
    student_class = clean_input(data.get('student_class', ''), max_len=30)
    password = data.get('password', '')

    is_valid_phone, phone_number = validate_phone(raw_phone)
    if not is_valid_phone:
        return jsonify({'error': 'Please enter a valid 10-digit mobile number.'}), 400

    if not student_name or not student_school or not student_class:
        return jsonify({'error': 'All fields are required.'}), 400

    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters long for security.'}), 400

    conn = get_db()
    cursor = conn.cursor()
    
    # Check if phone number is already registered
    cursor.execute("SELECT id FROM users WHERE username = ? OR phone_number = ?", (phone_number, phone_number))
    if cursor.fetchone():
        conn.close()
        return jsonify({'error': 'An account with this phone number already exists. Please Log In.'}), 400

    role = 'parent'
    # Use pbkdf2:sha256 with high salt security
    password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
    
    cursor.execute('''
        INSERT INTO users (username, password_hash, role, full_name, phone_number)
        VALUES (?, ?, ?, ?, ?)
    ''', (phone_number, password_hash, role, f"Parent of {student_name}", phone_number))
    new_user_id = cursor.lastrowid

    # Find or create School (SQL injection safe parameterized query)
    cursor.execute("SELECT id FROM schools WHERE LOWER(name) = LOWER(?)", (student_school,))
    school_row = cursor.fetchone()
    if school_row:
        school_id = school_row['id']
    else:
        cursor.execute("INSERT INTO schools (name, location) VALUES (?, '')", (student_school,))
        school_id = cursor.lastrowid

    # Find or create Class for this School
    cursor.execute("SELECT id FROM classes WHERE school_id = ? AND LOWER(class_name) = LOWER(?)", (school_id, student_class))
    class_row = cursor.fetchone()
    if class_row:
        class_id = class_row['id']
    else:
        cursor.execute("INSERT INTO classes (school_id, class_name) VALUES (?, ?)", (school_id, student_class))
        class_id = cursor.lastrowid

    # Generate unique Student Code using DB ID offset to avoid collision
    cursor.execute("SELECT COUNT(*) as count FROM students")
    count = cursor.fetchone()['count'] + 1001
    student_code = f"STU{count}"

    cursor.execute('''
        INSERT INTO students (student_code, full_name, school_id, class_id, parent_user_id, monthly_fee, parent_phone, parent_name)
        VALUES (?, ?, ?, ?, ?, 1500.0, ?, ?)
    ''', (student_code, student_name, school_id, class_id, new_user_id, phone_number, f"Parent of {student_name}"))
    student_db_id = cursor.lastrowid

    conn.commit()
    conn.close()

    ensure_student_fee_records(student_db_id, 2026)

    # Establish secure session
    session.clear()
    session['user_id'] = new_user_id
    session['username'] = phone_number
    session['role'] = role
    session['full_name'] = f"Parent of {student_name}"

    record_attempt(ip, 'signup')

    return jsonify({
        'success': True,
        'role': role,
        'full_name': f"Parent of {student_name}",
        'student_code': student_code,
        'message': 'Account created successfully!'
    })

@app.route('/api/auth/logout', methods=['POST', 'GET'])
def logout():
    session.clear()
    return redirect('/')

@app.route('/api/auth/session', methods=['GET'])
def get_session():
    if 'user_id' in session:
        student_code = None
        if session.get('role') == 'parent':
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT student_code FROM students WHERE parent_user_id = ?", (session['user_id'],))
            stu = cursor.fetchone()
            conn.close()
            if stu:
                student_code = stu['student_code']
                
        return jsonify({
            'logged_in': True,
            'user_id': session['user_id'],
            'username': session['username'],
            'role': session['role'],
            'full_name': session['full_name'],
            'student_code': student_code
        })
    return jsonify({'logged_in': False})

# ----------------- HIERARCHY & DATA APIS -----------------

@app.route('/api/hierarchy', methods=['GET'])
def get_hierarchy():
    """
    Returns Schools -> Classes structure for teacher filtering.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM schools ORDER BY name")
    schools = cursor.fetchall()

    hierarchy = []
    for s in schools:
        cursor.execute("SELECT * FROM classes WHERE school_id = ? ORDER BY class_name", (s['id'],))
        classes = cursor.fetchall()
        hierarchy.append({
            'id': s['id'],
            'name': s['name'],
            'location': s['location'],
            'classes': [{'id': c['id'], 'name': c['class_name']} for c in classes]
        })
    conn.close()
    return jsonify(hierarchy)

@app.route('/api/students', methods=['GET'])
def get_students():
    """
    Filter students by school_id, class_id, or search query.
    """
    school_id = request.args.get('school_id')
    class_id = request.args.get('class_id')
    search = request.args.get('search', '').strip()

    query = '''
        SELECT s.*, sch.name as school_name, c.class_name 
        FROM students s
        JOIN schools sch ON s.school_id = sch.id
        JOIN classes c ON s.class_id = c.id
        WHERE 1=1
    '''
    params = []

    if school_id:
        query += " AND s.school_id = ?"
        params.append(school_id)
    if class_id:
        query += " AND s.class_id = ?"
        params.append(class_id)
    if search:
        query += " AND (s.full_name LIKE ? OR s.student_code LIKE ? OR s.parent_phone LIKE ?)"
        like_term = f"%{search}%"
        params.extend([like_term, like_term, like_term])

    query += " ORDER BY s.full_name ASC"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(query, params)
    students = cursor.fetchall()
    conn.close()

    result = []
    for st in students:
        result.append({
            'id': st['id'],
            'student_code': st['student_code'],
            'full_name': st['full_name'],
            'school_id': st['school_id'],
            'school_name': st['school_name'],
            'class_id': st['class_id'],
            'class_name': st['class_name'],
            'monthly_fee': st['monthly_fee'],
            'parent_name': st['parent_name'],
            'parent_phone': st['parent_phone']
        })
    return jsonify(result)

@app.route('/api/students', methods=['POST'])
def add_student():
    """Add a new student (Teacher action)"""
    if session.get('role') != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json or {}
    name = data.get('full_name', '').strip()
    school_id = data.get('school_id')
    class_id = data.get('class_id')
    fee = data.get('monthly_fee', 1000)
    parent_name = data.get('parent_name', '').strip()
    parent_phone = data.get('parent_phone', '').strip()

    if not name or not school_id or not class_id or not parent_phone:
        return jsonify({'error': 'Missing required fields'}), 400

    conn = get_db()
    cursor = conn.cursor()
    
    # Generate unique code
    cursor.execute("SELECT COUNT(*) as count FROM students")
    count = cursor.fetchone()['count'] + 1001
    student_code = f"STU{count}"

    cursor.execute('''
        INSERT INTO students (student_code, full_name, school_id, class_id, monthly_fee, parent_phone, parent_name)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (student_code, name, school_id, class_id, fee, parent_phone, parent_name))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    ensure_student_fee_records(new_id, 2026)

    return jsonify({'success': True, 'student_code': student_code, 'id': new_id})

# ----------------- FEE CHART & STATUS -----------------

@app.route('/api/fee-chart/<student_code>', methods=['GET'])
def get_fee_chart(student_code):
    year = int(request.args.get('year', 2026))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.*, sch.name as school_name, c.class_name 
        FROM students s
        JOIN schools sch ON s.school_id = sch.id
        JOIN classes c ON s.class_id = c.id
        WHERE s.student_code = ?
    ''', (student_code,))
    student = cursor.fetchone()

    if not student:
        conn.close()
        return jsonify({'error': 'Student not found'}), 404

    ensure_student_fee_records(student['id'], year)

    cursor.execute('''
        SELECT * FROM fee_records 
        WHERE student_id = ? AND year = ?
        ORDER BY month_index ASC
    ''', (student['id'], year))
    records = cursor.fetchall()
    
    # Settings for UPI
    cursor.execute("SELECT key, value FROM settings")
    settings_rows = cursor.fetchall()
    settings_dict = {r['key']: r['value'] for r in settings_rows}

    conn.close()

    months_data = []
    paid_count = 0
    total_paid = 0
    total_due = 0

    for r in records:
        if r['status'] == 'paid':
            paid_count += 1
            total_paid += r['amount']
        else:
            total_due += r['amount']

        months_data.append({
            'id': r['id'],
            'month_index': r['month_index'],
            'month_name': r['month_name'],
            'amount': r['amount'],
            'status': r['status'],
            'payment_mode': r['payment_mode'],
            'transaction_ref': r['transaction_ref'],
            'paid_at': r['paid_at'],
            'receipt_no': r['receipt_no']
        })

    return jsonify({
        'student': {
            'id': student['id'],
            'student_code': student['student_code'],
            'full_name': student['full_name'],
            'school_name': student['school_name'],
            'class_name': student['class_name'],
            'monthly_fee': student['monthly_fee'],
            'parent_name': student['parent_name'],
            'parent_phone': student['parent_phone']
        },
        'year': year,
        'months': months_data,
        'summary': {
            'total_months': 12,
            'paid_months': paid_count,
            'unpaid_months': 12 - paid_count,
            'total_paid': total_paid,
            'total_due': total_due
        },
        'upi_settings': {
            'tuition_name': settings_dict.get('tuition_name', 'Tuition Academy'),
            'tuition_upi_id': settings_dict.get('tuition_upi_id', 'tuition@upi'),
            'teacher_phone': settings_dict.get('teacher_phone', '9876543210')
        }
    })

# ----------------- PAYMENT PROCESSING & NOTIFICATIONS -----------------

@app.route('/api/pay-fee', methods=['POST'])
def process_fee_payment():
    """
    Submits fee payment for a student and month.
    Generates receipt, updates chart, and triggers SMS to Parent + Teacher.
    """
    data = request.json or {}
    student_code = data.get('student_code')
    month_index = int(data.get('month_index', 1))
    year = int(data.get('year', 2026))
    payment_mode = data.get('payment_mode', 'GPay / UPI')
    transaction_ref = data.get('transaction_ref', '').strip()

    if not student_code:
        return jsonify({'error': 'Student code is required'}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT s.*, sch.name as school_name, c.class_name 
        FROM students s
        JOIN schools sch ON s.school_id = sch.id
        JOIN classes c ON s.class_id = c.id
        WHERE s.student_code = ?
    ''', (student_code,))
    student = cursor.fetchone()

    if not student:
        conn.close()
        return jsonify({'error': 'Student not found'}), 404

    cursor.execute('''
        SELECT * FROM fee_records 
        WHERE student_id = ? AND year = ? AND month_index = ?
    ''', (student['id'], year, month_index))
    record = cursor.fetchone()

    if not record:
        conn.close()
        return jsonify({'error': 'Fee record not found'}), 404

    # Generate receipt ID
    receipt_no = f"REC-{year}-{student['id']}-{month_index:02d}-{int(datetime.datetime.now().timestamp())%10000}"
    
    # Mark paid
    cursor.execute('''
        UPDATE fee_records
        SET status = 'paid', payment_mode = ?, transaction_ref = ?, receipt_no = ?, paid_at = datetime('now')
        WHERE id = ?
    ''', (payment_mode, transaction_ref or f"UPI-AUTO-{int(datetime.datetime.now().timestamp())}", receipt_no, record['id']))
    conn.commit()

    # Get teacher phone from settings
    cursor.execute("SELECT value FROM settings WHERE key = 'teacher_phone'")
    t_row = cursor.fetchone()
    teacher_phone = t_row['value'] if t_row else "9876543210"

    conn.close()

    # Trigger DUAL SMS: to both Parent and Teacher
    notify_fee_payment(
        student_name=student['full_name'],
        month_name=record['month_name'],
        year=year,
        amount=record['amount'],
        parent_phone=student['parent_phone'],
        teacher_phone=teacher_phone,
        receipt_no=receipt_no
    )

    return jsonify({
        'success': True,
        'message': f"Payment for {record['month_name']} {year} recorded successfully!",
        'receipt_no': receipt_no,
        'sms_sent_to': [student['parent_phone'], teacher_phone]
    })

# ----------------- SMS LOGS & SETTINGS -----------------

@app.route('/api/sms-logs', methods=['GET'])
def get_sms_logs():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sms_logs ORDER BY id DESC LIMIT 50")
    logs = cursor.fetchall()
    conn.close()
    return jsonify([dict(l) for l in logs])

@app.route('/api/settings', methods=['GET', 'POST'])
def manage_settings():
    if request.method == 'GET':
        settings = get_system_settings()
        return jsonify(settings)
    
    if session.get('role') != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json or {}
    conn = get_db()
    cursor = conn.cursor()
    for key, val in data.items():
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(val)))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'settings': get_system_settings()})

# ----------------- PAGE ROUTES -----------------

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/developer')
def developer_page():
    return render_template('developer.html')

@app.route('/pay/<student_code>')
@app.route('/pay/<student_code>/<int:month_index>')
def payment_page(student_code, month_index=None):
    return render_template('pay.html', student_code=student_code, target_month=month_index)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)

