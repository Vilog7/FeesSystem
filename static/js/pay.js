let feeChartData = null;
const studentCode = document.getElementById('pageStudentCode').value;
const preselectedMonth = parseInt(document.getElementById('pageTargetMonth').value) || null;

document.addEventListener('DOMContentLoaded', async () => {
  await loadPaymentPageData();
});

function showToast(msg, isSuccess = true) {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.style.background = isSuccess ? '#065f46' : '#991b1b';
  toast.style.display = 'block';
  setTimeout(() => {
    toast.style.display = 'none';
  }, 4000);
}

async function loadPaymentPageData() {
  try {
    const res = await fetch(`/api/fee-chart/${studentCode}`);
    if (!res.ok) {
      document.body.innerHTML = `<div class="card" style="max-width:500px; margin:4rem auto; text-align:center; color:red;"><h3>Student Not Found</h3><p>The payment link appears to be invalid.</p><a href="/" class="btn btn-primary" style="margin-top:1rem;">Go to Home</a></div>`;
      return;
    }

    feeChartData = await res.json();
    renderStudentHeader();
    populateMonthSelector();
    updateCheckoutBox();
    renderDirectFeeChart();

  } catch (err) {
    console.error('Error loading payment page', err);
    showToast('Failed to load student details', false);
  }
}

function renderStudentHeader() {
  const stu = feeChartData.student;
  document.getElementById('payStudentName').textContent = stu.full_name;
  document.getElementById('payStudentDetails').textContent = 
    `${stu.school_name} • ${stu.class_name} • Code: ${stu.student_code} • Parent: ${stu.parent_name}`;

  document.getElementById('payMonthlyRate').textContent = `₹${stu.monthly_fee.toLocaleString()}`;
  document.getElementById('payTotalPaidCount').textContent = `${feeChartData.summary.paid_months} / 12`;
  document.getElementById('payPendingCount').textContent = `${feeChartData.summary.unpaid_months} / 12`;
}

function populateMonthSelector() {
  const dropdown = document.getElementById('selectMonthDropdown');
  dropdown.innerHTML = '';

  let defaultIndex = null;

  feeChartData.months.forEach(m => {
    const opt = document.createElement('option');
    opt.value = m.month_index;
    opt.textContent = `${m.month_name} ${m.status === 'paid' ? '(Paid ✓)' : '(Pending)'}`;
    
    // Auto-select first unpaid month, or the preselected month if passed in URL
    if (preselectedMonth && m.month_index === preselectedMonth) {
      defaultIndex = m.month_index;
    } else if (defaultIndex === null && m.status !== 'paid') {
      defaultIndex = m.month_index;
    }

    dropdown.appendChild(opt);
  });

  if (defaultIndex) {
    dropdown.value = defaultIndex;
  }
}

function onSelectedMonthChange() {
  updateCheckoutBox();
}

function updateCheckoutBox() {
  const dropdown = document.getElementById('selectMonthDropdown');
  const selectedIndex = parseInt(dropdown.value);
  const targetMonth = feeChartData.months.find(m => m.month_index === selectedIndex);

  if (!targetMonth) return;

  const stu = feeChartData.student;
  const upi = feeChartData.upi_settings;

  document.getElementById('directMonthLabel').textContent = `${targetMonth.month_name} 2026`;
  document.getElementById('directPayAmountText').textContent = `₹${targetMonth.amount.toLocaleString()}`;
  document.getElementById('directUpiIdText').textContent = upi.tuition_upi_id;

  // Build UPI URI (Supports teacher phone number VPA e.g. +91xxxxxxxxxx@upi or direct ID)
  let vpa = upi.tuition_upi_id || '9876543210@upi';
  if (upi.teacher_phone && !vpa.includes('@')) {
    vpa = `${upi.teacher_phone}@upi`;
  }
  const payeeVpa = encodeURIComponent(vpa);
  const payeeName = encodeURIComponent(upi.tuition_name || 'Tuition Academy');
  const note = encodeURIComponent(`Fees ${stu.student_code} ${targetMonth.month_name}`);
  const upiUri = `upi://pay?pa=${payeeVpa}&pn=${payeeName}&am=${targetMonth.amount}&tn=${note}&cu=INR`;

  // Deep Link button
  document.getElementById('directGPayBtn').href = upiUri;

  // Dynamic QR Code
  const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(upiUri)}`;
  document.getElementById('directUpiQr').src = qrUrl;

  // If already paid, change button appearance
  const submitBtn = document.querySelector('#activeCheckoutCard button[type="submit"]');
  if (targetMonth.status === 'paid') {
    submitBtn.textContent = 'Already Paid (Re-verify / Update Record)';
    submitBtn.classList.remove('btn-success');
    submitBtn.classList.add('btn-outline');
  } else {
    submitBtn.textContent = '✓ Mark as Paid & Dispatch SMS Notifications';
    submitBtn.classList.remove('btn-outline');
    submitBtn.classList.add('btn-success');
  }
}

function renderDirectFeeChart() {
  const grid = document.getElementById('directChartGrid');
  grid.innerHTML = '';

  feeChartData.months.forEach(m => {
    const isPaid = m.status === 'paid';
    const card = document.createElement('div');
    card.className = `month-card ${isPaid ? 'status-paid' : 'status-unpaid'}`;

    card.innerHTML = `
      <div>
        <div class="month-title">
          <span>${escapeHtml(m.month_name)}</span>
          <span class="status-badge ${isPaid ? 'paid' : 'unpaid'}">
            ${isPaid ? '✓ PAID' : '✕ UNPAID'}
          </span>
        </div>
        <div class="month-amount">₹${m.amount.toLocaleString()}</div>
        ${isPaid ? `
          <div style="font-size: 0.75rem; color: var(--text-muted); line-height: 1.4;">
            <div>Mode: <b>${escapeHtml(m.payment_mode || 'UPI')}</b></div>
            <div>Receipt: <b>${escapeHtml(m.receipt_no || '-')}</b></div>
          </div>
        ` : `
          <div style="font-size: 0.8rem; color: #b91c1c;">
            Payment pending
          </div>
        `}
      </div>
      <div style="margin-top: 1rem;">
        <button class="btn ${isPaid ? 'btn-outline' : 'btn-success'}" style="width: 100%; font-size: 0.8rem; padding: 0.4rem;" onclick="selectMonthForPayment(${m.month_index})">
          ${isPaid ? 'View Details' : 'Pay This Month'}
        </button>
      </div>
    `;
    grid.appendChild(card);
  });
}

function selectMonthForPayment(monthIndex) {
  const dropdown = document.getElementById('selectMonthDropdown');
  dropdown.value = monthIndex;
  updateCheckoutBox();
  document.getElementById('activeCheckoutCard').scrollIntoView({ behavior: 'smooth' });
}

async function submitPersonalPayment(e) {
  e.preventDefault();
  const dropdown = document.getElementById('selectMonthDropdown');
  const month_index = parseInt(dropdown.value);
  const payment_mode = document.getElementById('personalPayMode').value;
  const transaction_ref = document.getElementById('personalUtr').value;

  try {
    const res = await fetch('/api/pay-fee', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        student_code: studentCode,
        month_index,
        year: 2026,
        payment_mode,
        transaction_ref
      })
    });
    const data = await res.json();
    if (res.ok) {
      showToast('Fee payment confirmed! SMS receipt dispatched.');
      await loadPaymentPageData();
    } else {
      showToast(data.error || 'Payment submission failed', false);
    }
  } catch (err) {
    showToast('Network error processing payment', false);
  }
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

