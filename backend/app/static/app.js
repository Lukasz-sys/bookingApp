const DEFAULT_API_URL = 'http://localhost:8000';
function normalizeApiUrl(value) {
  return String(value || '').replace(/\/$/, '');
}
function detectApiUrl() {
  if (window.BOOKING_API_URL) return normalizeApiUrl(window.BOOKING_API_URL);
  if (window.location.port === '8000') return normalizeApiUrl(window.location.origin);
  return DEFAULT_API_URL;
}
const API_URL = detectApiUrl();
const TOKEN_KEY = 'booking_access_token';

const state = {
  token: localStorage.getItem(TOKEN_KEY),
  user: null,
  doctors: [],
  services: [],
  settings: { business_start_hour: 9, business_end_hour: 17, slot_minutes: 30 }
};

const $ = selector => document.querySelector(selector);
const els = {
  userBadge: $('#userBadge'),
  logoutBtn: $('#logoutBtn'),
  showLogin: $('#showLogin'),
  showRegister: $('#showRegister'),
  loginForm: $('#loginForm'),
  registerForm: $('#registerForm'),
  registerRole: $('#registerRole'),
  companyFields: $('#companyFields'),
  doctorFields: $('#doctorFields'),
  authMessage: $('#authMessage'),
  resendBox: $('#resendBox'),
  resendForm: $('#resendForm'),
  resendEmail: $('#resendEmail'),
  doctorSelect: $('#doctorSelect'),
  doctorInfo: $('#doctorInfo'),
  serviceSelect: $('#serviceSelect'),
  bookingDate: $('#bookingDate'),
  hoursInfo: $('#hoursInfo'),
  slots: $('#slots'),
  startsAt: $('#startsAt'),
  bookingForm: $('#bookingForm'),
  bookingMessage: $('#bookingMessage'),
  adminDate: $('#adminDate'),
  appointments: $('#appointments'),
  refreshAppointments: $('#refreshAppointments')
};

function isoLocalDate(date = new Date()) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function tomorrowISO() {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return isoLocalDate(d);
}

function esc(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function fmtDT(value) {
  return new Date(value).toLocaleString('pl-PL', {
    year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
  });
}

function fmtT(value) {
  return new Date(value).toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit' });
}

function hourLabel(hour) {
  return `${String(hour).padStart(2, '0')}:00`;
}

function msg(el, text, type = '') {
  el.className = `message ${type}`.trim();
  el.textContent = text || '';
}

async function request(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12000);
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;

  try {
    const response = await fetch(`${API_URL}${path}`, { ...options, headers, signal: controller.signal });
    const text = await response.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { detail: text };
    }
    if (!response.ok) throw new Error(data?.detail || data?.message || `Błąd API: ${response.status}`);
    return data;
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('Backend nie odpowiada. Uruchom w głównym folderze projektu: docker compose up --build');
    }
    if (error instanceof TypeError) {
      throw new Error(`Nie można połączyć się z API pod adresem ${API_URL}. Uruchom w głównym folderze projektu: docker compose up --build`);
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

function roleLabel(role) {
  return { patient: 'Pacjent', doctor: 'Lekarz', company_admin: 'Firma / placówka' }[role] || role;
}

function updateUserUI() {
  if (!state.user) {
    els.userBadge.className = 'user-badge guest';
    els.userBadge.innerHTML = `<span class="status-dot"></span><span><strong>Gość</strong><small>Nie zalogowano</small></span>`;
    els.logoutBtn.classList.add('hidden');
    return;
  }
  els.userBadge.className = 'user-badge logged';
  els.userBadge.innerHTML = `<span class="status-dot"></span><span><strong>${esc(state.user.full_name)}</strong><small>${esc(roleLabel(state.user.role))}</small></span>`;
  els.logoutBtn.classList.remove('hidden');
  if (state.user.role === 'patient') {
    $('#patientName').value = state.user.full_name || '';
    $('#patientEmail').value = state.user.email || '';
    $('#patientPhone').value = state.user.phone || '';
  }
}

function switchAuthTab(tab) {
  const isRegister = tab === 'register';
  els.registerForm.classList.toggle('hidden', !isRegister);
  els.loginForm.classList.toggle('hidden', isRegister);
  els.resendBox.classList.toggle('hidden', !isRegister);
  els.showRegister.classList.toggle('active', isRegister);
  els.showLogin.classList.toggle('active', !isRegister);
  msg(els.authMessage, '');
}

function updateRoleFields() {
  const role = els.registerRole.value;
  els.companyFields.classList.toggle('hidden', role !== 'company_admin');
  els.doctorFields.classList.toggle('hidden', role !== 'doctor');
}

function updateHoursInfo() {
  const s = state.settings;
  els.hoursInfo.textContent = `Godziny przyjęć: ${hourLabel(s.business_start_hour)}–${hourLabel(s.business_end_hour)}, slot co ${s.slot_minutes} min. Domyślnie pokazuję jutro, żeby od razu było widać wolne terminy.`;
}

function updateDoctorInfo() {
  const doctor = state.doctors.find(d => String(d.id) === String(els.doctorSelect.value));
  if (!doctor) {
    els.doctorInfo.textContent = '';
    return;
  }
  els.doctorInfo.innerHTML = `<strong>${esc(doctor.full_name)}</strong>${doctor.specialization ? ` • ${esc(doctor.specialization)}` : ''}${doctor.company_name ? ` • ${esc(doctor.company_name)}` : ' • lekarz niezależny'}<br>${doctor.bio ? esc(doctor.bio) : 'Brak opisu.'}`;
}

async function loadSettings() {
  try {
    const settings = await request('/api/settings');
    state.settings = { ...state.settings, ...settings };
  } catch (error) {
    msg(els.bookingMessage, error.message, 'warn');
  }
  updateHoursInfo();
}

async function loadMe() {
  if (!state.token) {
    state.user = null;
    updateUserUI();
    return;
  }
  try {
    state.user = await request('/api/me');
  } catch (error) {
    localStorage.removeItem(TOKEN_KEY);
    state.token = null;
    state.user = null;
    msg(els.authMessage, error.message, 'warn');
  }
  updateUserUI();
}

async function loadDoctors() {
  els.doctorSelect.innerHTML = '<option value="">Ładowanie lekarzy...</option>';
  try {
    state.doctors = await request('/api/doctors');
    if (!state.doctors.length) {
      els.doctorSelect.innerHTML = '<option value="">Brak lekarzy. Uruchom python init_db.py albo zarejestruj lekarza.</option>';
      els.serviceSelect.innerHTML = '<option value="">Brak usług</option>';
      els.slots.textContent = 'Brak lekarzy w systemie.';
      return;
    }
    els.doctorSelect.innerHTML = state.doctors.map(doctor => {
      const label = `${doctor.full_name}${doctor.specialization ? ' — ' + doctor.specialization : ''}${doctor.company_name ? ' / ' + doctor.company_name : ' / niezależny'}`;
      return `<option value="${doctor.id}">${esc(label)}</option>`;
    }).join('');
    updateDoctorInfo();
    await loadServices();
    await loadAvailability();
  } catch (error) {
    els.doctorSelect.innerHTML = '<option value="">Błąd ładowania</option>';
    els.slots.innerHTML = `<span class="message error">${esc(error.message)}</span>`;
  }
}

async function loadServices() {
  const doctorId = els.doctorSelect.value;
  if (!doctorId) return;
  els.serviceSelect.innerHTML = '<option value="">Ładowanie usług...</option>';
  try {
    state.services = await request(`/api/services?doctor_id=${encodeURIComponent(doctorId)}`);
    if (!state.services.length) {
      els.serviceSelect.innerHTML = '<option value="">Wizyta standardowa</option>';
      return;
    }
    els.serviceSelect.innerHTML = state.services.map(service => {
      const price = service.price_cents != null ? ` • ${(service.price_cents / 100).toFixed(2)} zł` : '';
      return `<option value="${service.id}">${esc(service.name)} • ${service.duration_minutes} min${price}</option>`;
    }).join('');
  } catch (error) {
    els.serviceSelect.innerHTML = '<option value="">Błąd ładowania usług</option>';
    msg(els.bookingMessage, error.message, 'error');
  }
}

async function loadAvailability() {
  els.startsAt.value = '';
  const doctorId = els.doctorSelect.value;
  const day = els.bookingDate.value;
  const serviceId = els.serviceSelect.value;
  if (!doctorId || !day) {
    els.slots.textContent = 'Wybierz lekarza i datę.';
    return;
  }

  els.slots.textContent = 'Ładowanie dostępnych godzin...';
  try {
    const params = new URLSearchParams({ doctor_id: doctorId, day });
    if (serviceId) params.set('service_id', serviceId);
    const slots = await request(`/api/availability?${params.toString()}`);
    els.slots.innerHTML = '';
    if (!slots.length) {
      els.slots.textContent = 'Brak dostępnych slotów w tym dniu.';
      return;
    }
    slots.forEach(slot => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = `slot ${slot.available ? '' : 'busy'}`;
      button.textContent = fmtT(slot.starts_at);
      button.disabled = !slot.available;
      button.title = slot.available ? 'Kliknij, aby wybrać godzinę' : 'Zajęte albo niedostępne';
      button.addEventListener('click', () => {
        document.querySelectorAll('.slot').forEach(item => item.classList.remove('selected'));
        button.classList.add('selected');
        els.startsAt.value = slot.starts_at;
      });
      els.slots.appendChild(button);
    });
  } catch (error) {
    els.slots.innerHTML = `<span class="message error">${esc(error.message)}</span>`;
  }
}

async function loadAppointments() {
  if (!state.user) {
    els.appointments.textContent = 'Zaloguj się, aby zobaczyć wizyty.';
    return;
  }
  els.appointments.textContent = 'Ładowanie wizyt...';
  const query = els.adminDate.value ? `?day=${encodeURIComponent(els.adminDate.value)}` : '';
  let path = `/api/my/appointments${query}`;
  if (state.user.role === 'doctor') path = `/api/doctor/appointments${query}`;
  if (state.user.role === 'company_admin') path = `/api/company/appointments${query}`;
  try {
    renderAppointments(await request(path));
  } catch (error) {
    els.appointments.innerHTML = `<span class="message error">${esc(error.message)}</span>`;
  }
}

function renderAppointments(items) {
  els.appointments.innerHTML = '';
  if (!items.length) {
    els.appointments.textContent = 'Brak wizyt.';
    return;
  }
  items.forEach(item => {
    const canManage = state.user && ['doctor', 'company_admin'].includes(state.user.role);
    const canCancel = item.status === 'confirmed';
    const div = document.createElement('div');
    div.className = 'appointment';
    div.innerHTML = `
      <div class="appointment-top">
        <strong>${esc(item.patient_name)}</strong>
        <span class="badge ${esc(item.status)}">${esc(item.status)}</span>
      </div>
      <span><b>Termin:</b> ${fmtDT(item.starts_at)} - ${fmtDT(item.ends_at)}</span>
      <span><b>Lekarz:</b> ${esc(item.doctor_name)}${item.doctor_specialization ? ' • ' + esc(item.doctor_specialization) : ''}</span>
      <span><b>Placówka:</b> ${esc(item.company_name || 'brak')}</span>
      <span><b>Usługa:</b> ${esc(item.service_name)}</span>
      <span><b>Kontakt:</b> ${esc(item.patient_email)}${item.patient_phone ? ' • ' + esc(item.patient_phone) : ''}</span>
      ${item.notes ? `<small>${esc(item.notes)}</small>` : ''}
      <div class="appointment-actions">
        ${canManage && item.status === 'confirmed' ? `<button class="secondary" data-complete="${item.id}">Zakończ</button>` : ''}
        ${canCancel ? `<button class="danger" data-cancel="${item.id}">Anuluj</button>` : ''}
        ${canManage ? `<button class="danger" data-delete="${item.id}">Usuń</button>` : ''}
      </div>`;
    els.appointments.appendChild(div);
  });
}

els.showLogin.addEventListener('click', () => switchAuthTab('login'));
els.showRegister.addEventListener('click', () => switchAuthTab('register'));
els.registerRole.addEventListener('change', updateRoleFields);

els.loginForm.addEventListener('submit', async event => {
  event.preventDefault();
  msg(els.authMessage, 'Logowanie...');
  try {
    const data = await request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email: $('#loginEmail').value, password: $('#loginPassword').value })
    });
    state.token = data.access_token;
    state.user = data.user;
    localStorage.setItem(TOKEN_KEY, state.token);
    msg(els.authMessage, 'Zalogowano.', 'ok');
    updateUserUI();
    await loadAppointments();
  } catch (error) {
    msg(els.authMessage, error.message, 'error');
  }
});

els.registerForm.addEventListener('submit', async event => {
  event.preventDefault();
  msg(els.authMessage, 'Tworzenie konta...');
  const role = els.registerRole.value;
  const payload = {
    role,
    email: $('#registerEmail').value,
    password: $('#registerPassword').value,
    full_name: $('#registerName').value,
    phone: $('#registerPhone').value || null
  };
  if (role === 'company_admin') {
    payload.company_name = $('#companyName').value;
    payload.company_nip = $('#companyNip').value || null;
    payload.company_address = $('#companyAddress').value || null;
  }
  if (role === 'doctor') {
    payload.specialization = $('#specialization').value || null;
    payload.license_number = $('#licenseNumber').value || null;
    payload.bio = $('#doctorBio').value || null;
    payload.company_id = $('#doctorCompanyId').value ? Number($('#doctorCompanyId').value) : null;
  }

  try {
    const data = await request('/api/auth/register', { method: 'POST', body: JSON.stringify(payload) });
    const link = data.dev_verification_url ? ` Link testowy: ${data.dev_verification_url}` : '';
    msg(els.authMessage, `${data.message}${link} Po weryfikacji przejdź do zakładki Logowanie.`, 'ok');
    els.resendEmail.value = payload.email;
    els.registerForm.reset();
    updateRoleFields();
    els.resendBox.classList.remove('hidden');
    await loadDoctors();
  } catch (error) {
    msg(els.authMessage, error.message, 'error');
  }
});

els.resendForm.addEventListener('submit', async event => {
  event.preventDefault();
  const email = els.resendEmail.value || $('#registerEmail').value;
  if (!email) {
    msg(els.authMessage, 'Wpisz e-mail, na który ma zostać wysłany link.', 'warn');
    return;
  }
  try {
    const data = await request('/api/auth/resend-verification', { method: 'POST', body: JSON.stringify({ email }) });
    msg(els.authMessage, `${data.message}${data.dev_verification_url ? ' Link testowy: ' + data.dev_verification_url : ''}`, 'ok');
  } catch (error) {
    msg(els.authMessage, error.message, 'error');
  }
});

els.logoutBtn.addEventListener('click', () => {
  localStorage.removeItem(TOKEN_KEY);
  state.token = null;
  state.user = null;
  updateUserUI();
  loadAppointments();
  msg(els.authMessage, 'Wylogowano.', 'ok');
});

els.doctorSelect.addEventListener('change', async () => {
  updateDoctorInfo();
  await loadServices();
  await loadAvailability();
});
els.serviceSelect.addEventListener('change', loadAvailability);
els.bookingDate.addEventListener('change', loadAvailability);
els.adminDate.addEventListener('change', loadAppointments);
els.refreshAppointments.addEventListener('click', loadAppointments);

els.bookingForm.addEventListener('submit', async event => {
  event.preventDefault();
  msg(els.bookingMessage, '');
  if (!els.startsAt.value) {
    msg(els.bookingMessage, 'Wybierz dostępną godzinę.', 'error');
    return;
  }
  if (!els.doctorSelect.value) {
    msg(els.bookingMessage, 'Wybierz lekarza.', 'error');
    return;
  }
  const payload = {
    doctor_id: Number(els.doctorSelect.value),
    service_id: els.serviceSelect.value ? Number(els.serviceSelect.value) : null,
    patient_name: $('#patientName').value,
    patient_email: $('#patientEmail').value,
    patient_phone: $('#patientPhone').value || null,
    starts_at: els.startsAt.value,
    notes: $('#notes').value || null
  };
  try {
    await request('/api/appointments', { method: 'POST', body: JSON.stringify(payload) });
    msg(els.bookingMessage, 'Rezerwacja została utworzona.', 'ok');
    $('#notes').value = '';
    await loadAvailability();
    await loadAppointments();
  } catch (error) {
    msg(els.bookingMessage, error.message, 'error');
  }
});

els.appointments.addEventListener('click', async event => {
  const cancelId = event.target.dataset.cancel;
  const deleteId = event.target.dataset.delete;
  const completeId = event.target.dataset.complete;
  if (!cancelId && !deleteId && !completeId) return;
  try {
    if (cancelId) await request(`/api/appointments/${cancelId}/cancel`, { method: 'POST' });
    if (deleteId) await request(`/api/appointments/${deleteId}`, { method: 'DELETE' });
    if (completeId) await request(`/api/appointments/${completeId}`, { method: 'PATCH', body: JSON.stringify({ status: 'completed' }) });
    await loadAvailability();
    await loadAppointments();
  } catch (error) {
    alert(error.message);
  }
});

(async function bootstrap() {
  els.bookingDate.min = isoLocalDate();
  els.bookingDate.value = tomorrowISO();
  els.adminDate.value = isoLocalDate();
  updateRoleFields();
  switchAuthTab('login');
  updateHoursInfo();
  await loadSettings();
  await loadMe();
  await loadDoctors();
  await loadAppointments();
})();
