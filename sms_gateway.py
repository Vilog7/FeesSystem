import os
import requests
from db import get_db

# Choose your provider: 'SIMULATED', 'FAST2SMS', 'TWILIO'
SMS_PROVIDER = os.getenv('SMS_PROVIDER', 'SIMULATED')

# Fast2SMS Credentials (India)
FAST2SMS_API_KEY = os.getenv('FAST2SMS_API_KEY', '')

# Twilio Credentials (Global)
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')

def send_sms_notification(recipient_phone, recipient_type, message):
    """
    Sends live SMS using the configured gateway (Fast2SMS / Twilio) or fallback log.
    """
    status = 'DELIVERED'
    
    # 1. Fast2SMS (Popular in India for UPI/Tuition fee alerts)
    if SMS_PROVIDER == 'FAST2SMS' and FAST2SMS_API_KEY:
        try:
            url = "https://www.fast2sms.com/dev/bulkV2"
            headers = {"authorization": FAST2SMS_API_KEY}
            payload = {
                "route": "v3",
                "sender_id": "TXTIND",
                "message": message,
                "language": "english",
                "flash": 0,
                "numbers": recipient_phone
            }
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            if not res.ok:
                status = f"FAILED: {res.text[:50]}"
        except Exception as e:
            status = f"ERROR: {str(e)[:50]}"

    # 2. Twilio (Global)
    elif SMS_PROVIDER == 'TWILIO' and TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        try:
            from twilio.rest import Client
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            # Ensure Indian numbers have +91 prefix
            to_phone = recipient_phone if recipient_phone.startswith('+') else f"+91{recipient_phone}"
            client.messages.create(
                body=message,
                from_=TWILIO_PHONE_NUMBER,
                to=to_phone
            )
        except Exception as e:
            status = f"TWILIO ERROR: {str(e)[:50]}"

    # Always log into SQLite database for dashboard visibility
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO sms_logs (recipient_phone, recipient_type, message, status)
        VALUES (?, ?, ?, ?)
    ''', (recipient_phone, recipient_type, message, status))
    conn.commit()
    conn.close()
    return status
