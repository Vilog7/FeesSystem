let appHierarchy = [];
let currentUser = null;
let currentViewingStudentCode = null;
let currentViewingStudentData = null;
let debounceTimer = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
  await loadSettings();
  await checkSession();
});

// Toast message helper
function showToast(msg, isSuccess = true) {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.style.background = isSuccess ? '#065f46' : '#991b1b';
  toast.style.display = 'block';
  setTimeout(() => {
    toast.style.display = 'none';
  }, 4000);
}

// ---------------- AUTHENTICATION & SESSION ----------------

async function checkSession() {
  try {
    const res = await fetch('/api/auth/session');
    const data = await res.json();
    if (data.logged_in) {
      currentUser = data;
      renderAuthHeader();
      loadRoleDashboard();
    } else {
      currentUser = null;
      renderAuthHeader();
      showAuthSection();
    }
  } catch (err) {
    console.error("Session check error", err);
    showAuthSection();
  }
}

function renderAuthHeader() {
  const area = document.getElementById('authHeaderArea');
  if (currentUser) {
    const roleBadge = currentUser.role === 'teacher' 
      ? '<span class="badge badge-teacher">Tuition Teacher</span>'
      : '<span class="badge badge-parent">Parent</span>';

    area.innerHTML = `
      <div style="text-align: right; line-height: 1.2;">
        <div style="font-weight: 600; font-size: 0.95rem;">${escapeHtml(currentUser.full_name)}</div>
        ${roleBadge}
      </div>
      <button class="btn btn-outline" style="font-size: 0.85rem;" onclick="handleLogout()">Sign Out</button>
    `;
  } else {
    area.innerHTML = `
      <button class="btn btn-primary" onclick="showAuthSection()">Sign In</button>
    `;
  }
}

function showAuthSection() {
  document.getElementById('authSection').style.display = 'block';
  document.getElementById('teacherDashboard').style.display = 'none';
  document.getElementById('parentDashboard').style.display = 'none';
}

function switchAuthTab(tab) {
  const tabLogin = document.getElementById('tabLoginBtn');
  const tabSignup = document.getElementById('tabSignupBtn');
  const formLogin = document.getElementById('loginForm');
  const formSignup = document.getElementById('signupForm');

  if (tab === 'login') {
    tabLogin.classList.add('active');
    tabSignup.classList.remove('active');
    formLogin.style.display = 'block';
    formSignup.style.display = 'none';
  } else {
    tabSignup.classList.add('active');
    tabLogin.classList.remove('active');
    formLogin.style.display = 'none';
    formSignup.style.display = 'block';
  }
}

// Automatic user detection on username blur/change
document.getElementById('loginUsername')?.addEventListener('blur', async (e) => {
  const username = e.target.value.trim();
  const hint = document.getElementById('roleHint');
  if (!username) {
    hint.textContent = '';
    return;
  }
  try {
    const res = await fetch('/api/auth/check-user', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username })
    });
    const data = await res.json();
    if (data.exists) {
      hint.textContent = `Recognized: ${data.role === 'teacher' ? 'Tuition Teacher' : 'Parent'} (${data.full_name})`;
    } else {
      hint.textContent = 'New user? You can switch to Sign Up to create a parent account.';
    }
  } catch (err) {}
});

async function handleLogin(e) {
  e.preventDefault();
  const username = document.getElementById('loginUsername').value.trim();
  const password = document.getElementById('loginPassword').value;

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (res.ok) {
      showToast(`Welcome back, ${data.full_name}!`);
      await checkSession();
    } else {
      showToast(data.error || 'Login failed', false);
    }
  } catch (err) {
    showToast('Network error during login', false);
  }
}

async function handleSignup(e) {
  e.preventDefault();
  const phone_number = document.getElementById('signupPhone').value.trim();
  const student_name = document.getElementById('signupStudentName').value.trim();
  const student_school = document.getElementById('signupSchool').value.trim();
  const student_class = document.getElementById('signupClass').value.trim();
  const password = document.getElementById('signupPassword').value;

  try {
    const res = await fetch('/api/auth/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone_number, student_name, student_school, student_class, password })
    });
    const data = await res.json();
    if (res.ok) {
      showToast('Sign up successful! Welcome to your fee dashboard.');
      await checkSession();
    } else {
      showToast(data.error || 'Sign up failed', false);
    }
  } catch (err) {
    showToast('Network error during sign up', false);
  }
}

async function handleLogout() {
  await fetch('/api/auth/logout', { method: 'POST' });
  currentUser = null;
  checkSession();
}

// ---------------- DASHBOARD ROUTING ----------------

function loadRoleDashboard() {
  document.getElementById('authSection').style.display = 'none';

  if (currentUser.role === 'teacher') {
    document.getElementById('teacherDashboard').style.display = 'block';
    document.getElementById('parentDashboard').style.display = 'none';
    initTeacherDashboard();
  } else {
    document.getElementById('teacherDashboard').style.display = 'none';
    document.getElementById('parentDashboard').style.display = 'block';
    initParentDashboard();
  }
}

// ---------------- TEACHER DASHBOARD ----------------

async function initTeacherDashboard() {
  await loadHierarchy();
  await loadStudents();
}

async function loadHierarchy() {
  try {
    const res = await fetch('/api/hierarchy');
    appHierarchy = await res.json();

    // Populate School filter
    const schoolSelect = document.getElementById('filterSchool');
    const newStuSchool = document.getElementById('newStuSchool');
    schoolSelect.innerHTML = '<option value="">-- All Schools --</option>';
    newStuSchool.innerHTML = '<option value="">Select School</option>';

    appHierarchy.forEach(school => {
      const opt = `<option value="${school.id}">${escapeHtml(school.name)}</option>`;
      schoolSelect.insertAdjacentHTML('beforeend', opt);
      newStuSchool.insertAdjacentHTML('beforeend', opt);
    });
  } catch (err) {
    console.error('Error loading hierarchy', err);
  }
}

function onSchoolChanged() {
  const schoolId = document.getElementById('filterSchool').value;
  const classSelect = document.getElementById('filterClass');
  classSelect.innerHTML = '<option value="">-- All Classes --</option>';

  if (schoolId) {
    const school = appHierarchy.find(s => s.id == schoolId);
    if (school && school.classes) {
      school.classes.forEach(c => {
        classSelect.insertAdjacentHTML('beforeend', `<option value="${c.id}">${escapeHtml(c.name)}</option>`);
      });
    }
  }
  loadStudents();
}

function onClassChanged() {
  loadStudents();
}

function debounceLoadStudents() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    loadStudents();
  }, 300);
}

async function loadStudents() {
  const schoolId = document.getElementById('filterSchool').value;
  const classId = document.getElementById('filterClass').value;
  const search = document.getElementById('filterSearch').value.trim();

  const url = new URL('/api/students', window.location.origin);
  if (schoolId) url.searchParams.append('school_id', schoolId);
  if (classId) url.searchParams.append('class_id', classId);
  if (search) url.searchParams.append('search', search);

  try {
    const res = await fetch(url);
    const students = await res.json();
    renderStudentsTable(students);
  } catch (err) {
    console.error('Error fetching students', err);
  }
}

function renderStudentsTable(students) {
  const tbody = document.getElementById('studentsTableBody');
  const countHeader = document.getElementById('studentsCountHeader');
  countHeader.textContent = `Students (${students.length})`;
  
  // Update overview stats
  const statStudents = document.getElementById('statTotalStudents');
  const statClasses = document.getElementById('statActiveClasses');
  const statSchools = document.getElementById('statTotalSchools');
  if (statStudents) statStudents.textContent = students.length;
  if (statSchools) statSchools.textContent = appHierarchy.length;
  if (statClasses) {
    let classCount = 0;
    appHierarchy.forEach(s => { classCount += (s.classes ? s.classes.length : 0); });
    statClasses.textContent = classCount;
  }

  tbody.innerHTML = '';

  if (students.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 2.5rem; color: var(--text-muted);">No students registered yet. Students will appear here automatically when parents sign up.</td></tr>`;
    return;
  }

  students.forEach(st => {
    const personalPayUrl = `${window.location.origin}/pay/${st.student_code}`;
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><span class="badge" style="background: rgba(255,255,255,0.06); color: #cbd5e1; border: 1px solid rgba(255,255,255,0.1);">${escapeHtml(st.student_code)}</span></td>
      <td><b style="color: #fff; font-size: 0.95rem;">${escapeHtml(st.full_name)}</b></td>
      <td><span style="color: var(--text-secondary);">${escapeHtml(st.school_name)}</span></td>
      <td><span style="color: var(--text-secondary);">${escapeHtml(st.class_name)}</span></td>
      <td>
        <div style="color: #fff;">${escapeHtml(st.parent_name)}</div>
        <small style="color: var(--text-muted);">${escapeHtml(st.parent_phone)}</small>
      </td>
      <td>
        <div style="display: flex; gap: 0.4rem; align-items: center;">
          <a href="/pay/${st.student_code}" target="_blank" class="btn btn-outline" style="padding: 0.35rem 0.65rem; font-size: 0.8rem;">Open ↗</a>
          <button class="btn btn-outline" style="padding: 0.35rem 0.65rem; font-size: 0.8rem;" onclick="copyToClipboard('${personalPayUrl}')">Copy Link</button>
        </div>
      </td>
      <td>
        <button class="btn btn-primary" style="padding: 0.4rem 0.85rem; font-size: 0.85rem;" onclick="viewStudentFeeChart('${st.student_code}')">
          📊 View Fee Chart
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

async function viewStudentFeeChart(studentCode) {
  currentViewingStudentCode = studentCode;
  const container = document.getElementById('teacherChartContainer');
  const section = document.getElementById('teacherStudentDetailSection');
  section.style.display = 'block';
  section.scrollIntoView({ behavior: 'smooth' });

  container.innerHTML = '<div class="card" style="text-align: center; padding: 2rem;">Loading student fee chart...</div>';
  await renderFeeChart(studentCode, container);
}

// ---------------- PARENT DASHBOARD ----------------

async function initParentDashboard() {
  const container = document.getElementById('parentChartContainer');
  const title = document.getElementById('parentWelcomeTitle');
  const sub = document.getElementById('parentStudentSubtitle');
  const payBtnArea = document.getElementById('parentPayButtonArea');

  title.textContent = `Welcome, ${currentUser.full_name}`;

  if (!currentUser.student_code) {
    sub.textContent = 'No student linked to this account yet.';
    container.innerHTML = `
      <div class="card" style="text-align:center; padding: 3rem;">
        <h3>No Student Linked</h3>
        <p style="color: var(--text-muted); margin: 0.5rem 0 1.5rem;">Please provide your child's student code (e.g. STU1001) given by your tuition teacher.</p>
        <div style="max-width: 320px; margin: 0 auto; display: flex; gap: 0.5rem;">
          <input type="text" id="linkStudentInput" class="form-control" placeholder="Enter Student Code">
          <button class="btn btn-primary" onclick="linkStudentToParent()">Link</button>
        </div>
      </div>
    `;
    return;
  }

  currentViewingStudentCode = currentUser.student_code;
  payBtnArea.innerHTML = `
    <a href="/pay/${currentUser.student_code}" target="_blank" class="btn btn-gpay">
      ⚡ Open Personal Payment Page
    </a>
  `;
  await renderFeeChart(currentUser.student_code, container);
}

async function linkStudentToParent() {
  const code = document.getElementById('linkStudentInput').value.trim();
  if (!code) return;
  // Trigger update
  try {
    const res = await fetch(`/api/fee-chart/${code}`);
    if (res.ok) {
      currentUser.student_code = code;
      showToast('Student linked successfully!');
      initParentDashboard();
    } else {
      showToast('Invalid student code', false);
    }
  } catch (err) {
    showToast('Failed to link student', false);
  }
}

// ---------------- UNIVERSAL 12-MONTH FEE CHART RENDERER ----------------

async function renderFeeChart(studentCode, targetElement) {
  try {
    const res = await fetch(`/api/fee-chart/${studentCode}`);
    const data = await res.json();
    if (!res.ok) {
      targetElement.innerHTML = `<div class="card" style="color: var(--danger);">Error: ${data.error}</div>`;
      return;
    }

    currentViewingStudentData = data;

    // Use Template
    const template = document.getElementById('feeChartTemplate');
    const clone = template.content.cloneNode(true);

    // Fill Student Meta
    clone.querySelector('.student-chart-name').textContent = data.student.full_name;
    clone.querySelector('.student-chart-meta').textContent = `${data.student.school_name} • ${data.student.class_name} • Code: ${data.student.student_code}`;
    clone.querySelector('.student-chart-contact').textContent = `Parent: ${data.student.parent_name} (${data.student.parent_phone})`;

    // Fill Stats
    clone.querySelector('.chart-stat-paid').textContent = `${data.summary.paid_months} / 12`;
    clone.querySelector('.chart-stat-due').textContent = `${data.summary.unpaid_months} / 12`;

    // Fill 12 Months
    const grid = clone.querySelector('.chart-grid-container');
    data.months.forEach(m => {
      const isPaid = m.status === 'paid';
      const card = document.createElement('div');
      card.className = `month-card ${isPaid ? 'status-paid' : 'status-unpaid'}`;

      card.innerHTML = `
        <div>
          <div class="month-title">
            <span>${escapeHtml(m.month_name)}</span>
            <span class="status-pill ${isPaid ? 'paid' : 'pending'}">
              ${isPaid ? '✓ Paid' : '⏳ Pending'}
            </span>
          </div>
          ${isPaid ? `
            <div style="font-size: 0.78rem; color: var(--text-muted); line-height: 1.5; margin-top: 0.85rem;">
              <div>Payment Mode: <b style="color: #cbd5e1;">${escapeHtml(m.payment_mode || 'UPI')}</b></div>
              <div>Receipt: <b style="color: #cbd5e1;">${escapeHtml(m.receipt_no || '-')}</b></div>
              <div>Recorded: ${m.paid_at ? m.paid_at.substring(0, 10) : 'Done'}</div>
            </div>
          ` : `
            <div style="font-size: 0.82rem; color: #fbbf24; margin-top: 0.85rem;">
              Monthly fee payment pending
            </div>
          `}
        </div>
        <div style="margin-top: 1.25rem;">
          ${isPaid ? `
            <button class="btn btn-outline" style="width: 100%; font-size: 0.8rem; padding: 0.45rem;" onclick="showReceiptAlert('${m.receipt_no}', '${data.student.full_name}', '${m.month_name}')">
              📄 View Receipt
            </button>
          ` : `
            <button class="btn btn-success" style="width: 100%; font-size: 0.85rem; padding: 0.5rem;" onclick="openPaymentModal('${data.student.student_code}', ${m.month_index}, '${m.month_name}')">
              💳 Pay Month Fee
            </button>
          `}
        </div>
      `;
      grid.appendChild(card);
    });

    targetElement.innerHTML = '';
    targetElement.appendChild(clone);

  } catch (err) {
    console.error('Failed to render fee chart', err);
    targetElement.innerHTML = '<div class="card" style="color: red;">Failed to load fee chart.</div>';
  }
}

function showReceiptAlert(recNo, student, month) {
  alert(`=== TUITION FEE PAYMENT RECEIPT ===\nReceipt No: ${recNo}\nStudent: ${student}\nMonth: ${month} 2026\nStatus: VERIFIED & PAID\nSMS sent to parent & teacher.`);
}

function copyPersonalLink() {
  if (currentViewingStudentCode) {
    const url = `${window.location.origin}/pay/${currentViewingStudentCode}`;
    copyToClipboard(url);
    showToast('Personal payment link copied to clipboard!');
  }
}

// ---------------- PAYMENT MODAL (UPI & SMS TRIGGER) ----------------

function openPaymentModal(studentCode, monthIndex, monthName) {
  const modal = document.getElementById('paymentModal');
  document.getElementById('payStudentCode').value = studentCode;
  document.getElementById('payMonthIndex').value = monthIndex;

  const stu = currentViewingStudentData ? currentViewingStudentData.student : {};
  const upiSettings = currentViewingStudentData ? currentViewingStudentData.upi_settings : {};

  document.getElementById('payModalTitle').textContent = `Pay Fees for ${monthName} 2026`;
  document.getElementById('payModalUpiId').textContent = upiSettings.tuition_upi_id || 'tuitionteacher@upi';

  document.getElementById('payModalStudentDetails').innerHTML = `
    <div><b>Student:</b> ${escapeHtml(stu.full_name || '')} (${studentCode})</div>
    <div><b>School & Class:</b> ${escapeHtml(stu.school_name || '')} - ${escapeHtml(stu.class_name || '')}</div>
    <div><b>Parent SMS Mobile:</b> ${escapeHtml(stu.parent_phone || '')}</div>
  `;

  // Standard UPI URI deep link (Uses Teacher's Phone Number VPA or custom UPI ID)
  let payeeVpa = upiSettings.tuition_upi_id || '9876543210@upi';
  if (upiSettings.teacher_phone && !payeeVpa.includes('@')) {
    payeeVpa = `${upiSettings.teacher_phone}@upi`;
  }
  const payeeName = encodeURIComponent(upiSettings.tuition_name || 'Tuition Academy');
  const note = encodeURIComponent(`Fees ${studentCode} ${monthName}`);
  const upiUri = `upi://pay?pa=${encodeURIComponent(payeeVpa)}&pn=${payeeName}&tn=${note}&cu=INR`;

  // Set GPay / UPI Deep Link button
  document.getElementById('upiDeepLinkBtn').href = upiUri;

  // Generate QR code using public QR API
  const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(upiUri)}`;
  document.getElementById('upiQrCodeImg').src = qrUrl;

  modal.style.display = 'flex';
}

async function submitFeePayment(e) {
  e.preventDefault();
  const student_code = document.getElementById('payStudentCode').value;
  const month_index = parseInt(document.getElementById('payMonthIndex').value);
  const payment_mode = document.getElementById('payMode').value;
  const transaction_ref = document.getElementById('payUtr').value;

  try {
    const res = await fetch('/api/pay-fee', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        student_code,
        month_index,
        year: 2026,
        payment_mode,
        transaction_ref
      })
    });
    const data = await res.json();
    if (res.ok) {
      closeModal('paymentModal');
      showToast(`Payment saved! SMS alerts dispatched to parent and teacher.`);
      
      // Refresh current viewing chart
      if (currentUser.role === 'teacher') {
        const container = document.getElementById('teacherChartContainer');
        renderFeeChart(student_code, container);
      } else {
        const container = document.getElementById('parentChartContainer');
        renderFeeChart(student_code, container);
      }
    } else {
      showToast(data.error || 'Payment failed', false);
    }
  } catch (err) {
    showToast('Failed to record payment', false);
  }
}

// ---------------- NEW STUDENT MODAL ----------------

function openAddStudentModal() {
  document.getElementById('addStudentModal').style.display = 'flex';
}

function populateNewStudentClasses() {
  const schoolId = document.getElementById('newStuSchool').value;
  const classSelect = document.getElementById('newStuClass');
  classSelect.innerHTML = '<option value="">Select Class</option>';

  if (schoolId) {
    const school = appHierarchy.find(s => s.id == schoolId);
    if (school && school.classes) {
      school.classes.forEach(c => {
        classSelect.insertAdjacentHTML('beforeend', `<option value="${c.id}">${escapeHtml(c.name)}</option>`);
      });
    }
  }
}

async function submitNewStudent(e) {
  e.preventDefault();
  const full_name = document.getElementById('newStuName').value.trim();
  const school_id = document.getElementById('newStuSchool').value;
  const class_id = document.getElementById('newStuClass').value;
  const monthly_fee = parseFloat(document.getElementById('newStuFee').value);
  const parent_name = document.getElementById('newStuParentName').value.trim();
  const parent_phone = document.getElementById('newStuParentPhone').value.trim();

  try {
    const res = await fetch('/api/students', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ full_name, school_id, class_id, monthly_fee, parent_name, parent_phone })
    });
    const data = await res.json();
    if (res.ok) {
      closeModal('addStudentModal');
      showToast(`Student ${full_name} registered (${data.student_code})!`);
      loadStudents();
    } else {
      showToast(data.error || 'Failed to add student', false);
    }
  } catch (err) {
    showToast('Network error adding student', false);
  }
}

// ---------------- SMS LOGS MODAL ----------------

async function openSmsLogsModal() {
  const modal = document.getElementById('smsLogsModal');
  const tbody = document.getElementById('smsLogsTableBody');
  tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">Loading SMS logs...</td></tr>';
  modal.style.display = 'flex';

  try {
    const res = await fetch('/api/sms-logs');
    const logs = await res.json();
    tbody.innerHTML = '';
    if (logs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">No SMS records yet.</td></tr>';
      return;
    }
    logs.forEach(l => {
      tbody.insertAdjacentHTML('beforeend', `
        <tr>
          <td><small>${l.sent_at || '-'}</small></td>
          <td><b>${escapeHtml(l.recipient_phone)}</b></td>
          <td><span class="badge ${l.recipient_type === 'Teacher' ? 'badge-teacher' : 'badge-parent'}">${l.recipient_type}</span></td>
          <td style="font-size: 0.8rem;">${escapeHtml(l.message)}</td>
          <td><span class="status-badge paid">DELIVERED</span></td>
        </tr>
      `);
    });
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="5" style="color:red; text-align:center;">Failed to load logs.</td></tr>';
  }
}

// ---------------- SETTINGS MODAL ----------------

async function openSettingsModal() {
  const modal = document.getElementById('settingsModal');
  try {
    const res = await fetch('/api/settings');
    const settings = await res.json();
    document.getElementById('settingTuitionName').value = settings.tuition_name || '';
    document.getElementById('settingUpiId').value = settings.tuition_upi_id || '';
    document.getElementById('settingTeacherPhone').value = settings.teacher_phone || '';
    modal.style.display = 'flex';
  } catch (err) {
    showToast('Failed to load settings', false);
  }
}

async function saveSettings(e) {
  e.preventDefault();
  const tuition_name = document.getElementById('settingTuitionName').value.trim();
  const tuition_upi_id = document.getElementById('settingUpiId').value.trim();
  const teacher_phone = document.getElementById('settingTeacherPhone').value.trim();

  try {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tuition_name, tuition_upi_id, teacher_phone })
    });
    if (res.ok) {
      closeModal('settingsModal');
      showToast('Settings updated successfully!');
      loadSettings();
    } else {
      showToast('Failed to save settings', false);
    }
  } catch (err) {
    showToast('Network error saving settings', false);
  }
}

async function loadSettings() {
  try {
    const res = await fetch('/api/settings');
    const settings = await res.json();
    if (settings.tuition_name) {
      const nav = document.getElementById('navTuitionName');
      if (nav) nav.textContent = settings.tuition_name;
    }
  } catch (err) {}
}

// ---------------- HELPERS ----------------

function closeModal(modalId) {
  document.getElementById(modalId).style.display = 'none';
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    showToast('Link copied to clipboard!');
  }).catch(() => {
    prompt('Copy this link:', text);
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

