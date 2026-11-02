import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_FILE = os.path.join(os.path.dirname(__file__), 'fees_system.db')

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('teacher', 'parent')),
        full_name TEXT NOT NULL,
        phone_number TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Schools table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS schools (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        location TEXT
    )
    ''')

    # Classes table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER NOT NULL,
        class_name TEXT NOT NULL,
        FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE,
        UNIQUE(school_id, class_name)
    )
    ''')

    # Students table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_code TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        school_id INTEGER NOT NULL,
        class_id INTEGER NOT NULL,
        parent_user_id INTEGER,
        monthly_fee REAL NOT NULL DEFAULT 1000.0,
        parent_phone TEXT NOT NULL,
        parent_name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (school_id) REFERENCES schools(id),
        FOREIGN KEY (class_id) REFERENCES classes(id),
        FOREIGN KEY (parent_user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')

    # Fee Records table (tracking each month)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fee_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        year INTEGER NOT NULL,
        month_index INTEGER NOT NULL CHECK(month_index BETWEEN 1 AND 12),
        month_name TEXT NOT NULL,
        amount REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'unpaid' CHECK(status IN ('paid', 'unpaid', 'verifying')),
        payment_mode TEXT,
        transaction_ref TEXT,
        paid_at TIMESTAMP,
        receipt_no TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        UNIQUE(student_id, year, month_index)
    )
    ''')

    # Settings table (UPI, Tuition info, Teacher phone)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')

    # SMS logs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sms_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipient_phone TEXT NOT NULL,
        recipient_type TEXT NOT NULL,
        message TEXT NOT NULL,
        status TEXT NOT NULL,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()

    # Seed initial default settings if empty
    default_settings = [
        ('tuition_name', 'Bright Minds Tuition Academy'),
        ('tuition_upi_id', 'tuitionteacher@upi'),
        ('teacher_phone', '9876543210'),
        ('current_year', '2026'),
        ('sms_service_enabled', 'true')
    ]
    for key, val in default_settings:
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val))

    # Seed default Teacher account if not present
    cursor.execute("SELECT id FROM users WHERE username = 'teacher'")
    if not cursor.fetchone():
        teacher_pass = generate_password_hash('teacher123')
        cursor.execute('''
            INSERT INTO users (username, password_hash, role, full_name, phone_number)
            VALUES (?, ?, ?, ?, ?)
        ''', ('teacher', teacher_pass, 'teacher', 'Head Tuition Teacher', '9876543210'))

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == '__main__':
    init_db()

