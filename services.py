from db import get_db
from sms_gateway import send_sms_notification

MONTHS = [
    (1, "January"), (2, "February"), (3, "March"), (4, "April"),
    (5, "May"), (6, "June"), (7, "July"), (8, "August"),
    (9, "September"), (10, "October"), (11, "November"), (12, "December")
]

def notify_fee_payment(student_name, month_name, year, amount, parent_phone, teacher_phone, receipt_no):
    """
    Notifies BOTH Parent and Tuition Teacher via SMS when fees are paid.
    """
    # 1. SMS to Parent
    parent_msg = (
        f"Dear Parent, Fee payment of Rs. {amount:,.2f} for {student_name} "
        f"for {month_name} {year} has been successfully received. "
        f"Receipt No: {receipt_no}. Thank you!"
    )
    send_sms_notification(parent_phone, 'Parent', parent_msg)

    # 2. SMS to Teacher
    teacher_msg = (
        f"ALERT: Fee payment received! Rs. {amount:,.2f} paid for {student_name} "
        f"for {month_name} {year}. (Receipt: {receipt_no}, Parent Contact: {parent_phone})"
    )
    send_sms_notification(teacher_phone, 'Teacher', teacher_msg)

def ensure_student_fee_records(student_id, year=2026):
    """
    Ensures 12 month records exist for the student in fee_records table.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Get student monthly fee
    cursor.execute("SELECT monthly_fee FROM students WHERE id = ?", (student_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return
    monthly_fee = row['monthly_fee']

    for m_idx, m_name in MONTHS:
        cursor.execute('''
            INSERT OR IGNORE INTO fee_records (student_id, year, month_index, month_name, amount, status)
            VALUES (?, ?, ?, ?, ?, 'unpaid')
        ''', (student_id, year, m_idx, m_name, monthly_fee))
        
    conn.commit()
    conn.close()

