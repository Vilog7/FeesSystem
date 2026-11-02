# Tuition Fee Management System

A fee management website with universal authentication, hierarchy filtering (School -> Class -> Student), personal payment pages with UPI/GPay links & dynamic QR codes, a 12-month visual fee status tracker, and dual SMS notifications.

---

## 🚀 Features

1. **Role-Based Authentication**:
   - Single unified login & registration portal.
   - Detects whether the user is the **Tuition Teacher** or a **Parent** using secure password hashing.
   - Parents can register with their name, phone number, and child's student code.

2. **Hierarchical Filtering (Supports Thousands of Students)**:
   - Filter flow: **School** $\longrightarrow$ **Class/Grade** $\longrightarrow$ **Student Name**.
   - Live search bar by student name, roll code, or parent mobile number.

3. **Dedicated Personal Payment Link (`/pay/<student_code>`)**:
   - Every student has their personal payment link (e.g. `http://localhost:5000/pay/STU1001`).
   - Supports 1-click **GPay / PhonePe / Paytm / BHIM UPI** deep-linking on smartphones.
   - Shows dynamic UPI QR code on desktop.
   - Pre-fills student ID and month in the transaction note.

4. **12-Month Fee Status Tracker**:
   - Color-coded monthly tracker (🟢 Paid vs 🔴 Unpaid).
   - Shows payment mode, receipt number, and payment date for paid months.
   - Real-time chart update upon payment.
   - Parents view their child's chart; the tuition teacher can browse any student's chart.

5. **Dual SMS Notifications (Parent & Teacher)**:
   - When fees are paid, an SMS is sent to:
     1. **Parent's mobile number**: Receipt confirmation with amount & month.
     2. **Tuition Teacher's phone**: Payment alert with student name, class, school, and amount.
   - SMS History audit log tab available directly inside the Teacher Portal.

6. **Teacher Customization Portal**:
   - Update Tuition/Academy Name.
   - Update Teacher UPI ID (GPay / PhonePe receiver).
   - Update Teacher Phone Number for incoming SMS alerts.
   - Add new students and automatically generate their personal links.

---

## 💻 Running the Application

### 1. Start the Flask Server
Run the following in PowerShell / Command Prompt:
```powershell
python app.py
```

### 2. Access the Application
- **Main Portal**: `http://localhost:5000`
- **Student Personal Payment Link**: `http://localhost:5000/pay/STU1001`

---

## 🔑 Login Credentials

| Role | Username | Default Password | Notes |
| :--- | :--- | :--- | :--- |
| **Tuition Teacher (Admin)** | `teacher` | `teacher123` | Full access to add students, view fee charts, customize UPI, and view SMS logs |
| **New Parents** | *Created during Sign Up* | *Parent chosen password* | Sign up with phone number and child's student code |


