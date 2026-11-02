import time
from collections import defaultdict

# IP -> list of attempt timestamps
login_attempts = defaultdict(list)
signup_attempts = defaultdict(list)

MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_WINDOW = 300  # 5 attempts per 5 minutes

MAX_SIGNUP_ATTEMPTS = 5
SIGNUP_LOCKOUT_WINDOW = 600 # 5 signups per 10 minutes per IP

def is_rate_limited(ip_address, action='login'):
    now = time.time()
    store = login_attempts if action == 'login' else signup_attempts
    max_attempts = MAX_LOGIN_ATTEMPTS if action == 'login' else MAX_SIGNUP_ATTEMPTS
    window = LOGIN_LOCKOUT_WINDOW if action == 'login' else SIGNUP_LOCKOUT_WINDOW

    # Filter out timestamps outside the active window
    store[ip_address] = [t for t in store[ip_address] if now - t < window]

    if len(store[ip_address]) >= max_attempts:
        return True

    return False

def record_attempt(ip_address, action='login'):
    store = login_attempts if action == 'login' else signup_attempts
    store[ip_address].append(time.time())

def clear_attempts(ip_address, action='login'):
    store = login_attempts if action == 'login' else signup_attempts
    if ip_address in store:
        del store[ip_address]
