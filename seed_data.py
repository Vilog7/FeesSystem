from db import get_db, init_db
from werkzeug.security import generate_password_hash
from services import ensure_student_fee_records

def seed_sample_data():
    init_db()
    conn = get_db()
    cursor = conn.cursor()

    # Create Sample Schools
    schools = [
        ("St. Xavier's High School", "Downtown Campus"),
        ("Delhi Public School", "Green Valley"),
        ("Kendriya Vidyalaya", "Civil Lines")
    ]
    school_ids = {}
    for name, loc in schools:
        cursor.execute("INSERT OR IGNORE INTO schools (name, location) VALUES (?, ?)", (name, loc))
        cursor.execute("SELECT id FROM schools WHERE name = ?", (name,))
        school_ids[name] = cursor.fetchone()['id']

    # Create Classes for each School
    classes = ["Grade 8", "Grade 9", "Grade 10", "Grade 11", "Grade 12"]
    class_map = {}
    for s_name, s_id in school_ids.items():
        for c_name in classes:
            cursor.execute("INSERT OR IGNORE INTO classes (school_id, class_name) VALUES (?, ?)", (s_id, c_name))
            cursor.execute("SELECT id FROM classes WHERE school_id = ? AND class_name = ?", (s_id, c_name))
            class_map[(s_id, c_name)] = cursor.fetchone()['id']

    # Create Sample Parents & Students
    sample_students = [
        {
            "code": "STU1001",
            "name": "Aarav Sharma",
            "school": "St. Xavier's High School",
            "class": "Grade 10",
            "fee": 1500.0,
            "parent_user": "parent_aarav",
            "parent_name": "Ramesh Sharma",
            "parent_phone": "9811122233",
            "paid_months": [1, 2] # Jan, Feb
        },
        {
            "code": "STU1002",
            "name": "Ananya Patel",
            "school": "St. Xavier's High School",
            "class": "Grade 10",
            "fee": 1500.0,
            "parent_user": "parent_ananya",
            "parent_name": "Suresh Patel",
            "parent_phone": "9822233344",
            "paid_months": [1, 2, 3] # Jan, Feb, Mar
        },
        {
            "code": "STU1003",
            "name": "Rohan Gupta",
            "school": "St. Xavier's High School",
            "class": "Grade 9",
            "fee": 1400.0,
            "parent_user": "parent_rohan",
            "parent_name": "Vikram Gupta",
            "parent_phone": "9833344455",
            "paid_months": [1] # Jan
        },
        {
            "code": "STU1004",
            "name": "Priya Verma",
            "school": "Delhi Public School",
            "class": "Grade 10",
            "fee": 1800.0,
            "parent_user": "parent_priya",
            "parent_name": "Deepak Verma",
            "parent_phone": "9844455566",
            "paid_months": [1, 2, 3, 4]
        },
        {
            "code": "STU1005",
            "name": "Kabir Singh",
            "school": "Kendriya Vidyalaya",
            "class": "Grade 12",
            "fee": 2000.0,
            "parent_user": "parent_kabir",
            "parent_name": "Rajinder Singh",
            "parent_phone": "9855566677",
            "paid_months": [] # None paid yet
        }
    ]

    for item in sample_students:
        # Create parent user
        pwd_hash = generate_password_hash("parent123")
        cursor.execute("SELECT id FROM users WHERE username = ?", (item['parent_user'],))
        existing_user = cursor.fetchone()
        if not existing_user:
            cursor.execute('''
                INSERT INTO users (username, password_hash, role, full_name, phone_number)
                VALUES (?, ?, 'parent', ?, ?)
            ''', (item['parent_user'], pwd_hash, item['parent_name'], item['parent_phone']))
            parent_uid = cursor.lastrowid
        else:
            parent_uid = existing_user['id']

        s_id = school_ids[item['school']]
        c_id = class_map[(s_id, item['class'])]

        # Create or update student
        cursor.execute("SELECT id FROM students WHERE student_code = ?", (item['code'],))
        existing_stu = cursor.fetchone()
        if not existing_stu:
            cursor.execute('''
                INSERT INTO students (student_code, full_name, school_id, class_id, parent_user_id, monthly_fee, parent_phone, parent_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (item['code'], item['name'], s_id, c_id, parent_uid, item['fee'], item['parent_phone'], item['parent_name']))
            student_db_id = cursor.lastrowid
        else:
            student_db_id = existing_stu['id']

        # Ensure all 12 month records exist
        ensure_student_fee_records(student_db_id, 2026)

        # Mark paid months for demonstration
        for m in item['paid_months']:
            receipt_no = f"REC-2026-{student_db_id}-{m:02d}"
            cursor.execute('''
                UPDATE fee_records 
                SET status = 'paid', payment_mode = 'GPay / UPI', transaction_ref = 'UPI9837423982', receipt_no = ?, paid_at = datetime('now')
                WHERE student_id = ? AND year = 2026 AND month_index = ?
            ''', (receipt_no, student_db_id, m))

    conn.commit()
    conn.close()
    print("Sample test data seeded successfully!")

if __name__ == '__main__':
    seed_sample_data()

