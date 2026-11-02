import sqlite3

def clean_database():
    conn = sqlite3.connect('fees_system.db')
    c = conn.cursor()

    # Clear all fee records, sample students, and sample SMS logs
    c.execute("DELETE FROM fee_records")
    c.execute("DELETE FROM students")
    c.execute("DELETE FROM sms_logs")

    # Delete all sample parents, keep only the teacher admin
    c.execute("DELETE FROM users WHERE role != 'teacher'")

    # Reset SQLite autoincrement counters
    c.execute("DELETE FROM sqlite_sequence WHERE name IN ('students', 'fee_records', 'sms_logs')")

    conn.commit()
    conn.close()
    print("Cleaned: All fake users, parents, students, and demo fee records have been removed.")

if __name__ == '__main__':
    clean_database()
