(function () {
  'use strict';

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/static/js/sw.js').catch(err => console.error('SW reg failed', err));
    });
  }

  const NAV = {
    admin: [
      { id: 'admin-view-home', label: 'Home', icon: 'layout-dashboard' },
      { id: 'admin-view-people', label: 'Directory', icon: 'users' },
      { id: 'admin-view-fees', label: 'Fees', icon: 'wallet' },
      { id: 'admin-view-salary', label: 'Salaries', icon: 'banknote' },
      { id: 'admin-view-campus', label: 'Campus GPS', icon: 'map-pin' },
      { id: 'admin-view-otp', label: 'OTP Outbox', icon: 'inbox' },
    ],
    teacher: [
      { id: 'teacher-view-home', label: 'Home', icon: 'layout-dashboard' },
      { id: 'teacher-view-attendance', label: 'Attendance', icon: 'clipboard-check' },
      { id: 'teacher-view-marks', label: 'Marks', icon: 'award' },
    ],
    student: [
      { id: 'student-view-home', label: 'Home', icon: 'layout-dashboard' },
      { id: 'student-view-marks', label: 'My marks', icon: 'file-text' },
    ],
    parent: [
      { id: 'parent-view-home', label: 'Home', icon: 'layout-dashboard' },
      { id: 'parent-view-fees', label: 'Fees', icon: 'wallet' },
    ],
  };

  const DASH_MAP = {
    admin: 'adminDashboard',
    teacher: 'teacherDashboard',
    student: 'studentDashboard',
    parent: 'parentDashboard',
  };

  const DEFAULTERS_DEMO = [
    { roll: 'CS21A033', name: 'Arjun Mehta', dept: 'cse', pct: 58, missed: 19, severity: 'high', phone: '+91 98765 43210' },
    { roll: 'ECE21B007', name: 'Kiran Patel', dept: 'ece', pct: 49, missed: 24, severity: 'critical', phone: '+91 91234 56789' },
    { roll: 'ME21C014', name: 'Dev Sharma', dept: 'me', pct: 62, missed: 15, severity: 'medium', phone: '+91 99887 76655' },
    { roll: 'CS20A102', name: 'Ananya Roy', dept: 'cse', pct: 71, missed: 11, severity: 'medium', phone: '+91 90011 22334' },
    { roll: 'CE22A008', name: 'Imran Qureshi', dept: 'ce', pct: 45, missed: 27, severity: 'critical', phone: '+91 97777 88899' },
  ];

  let attendanceChart = null;
  let performanceChart = null;
  let cameraStream = null;
  let state = { user: null, apiOnline: false, role: null };
  let activeSessionId = null;
  let sessionPollInterval = null;
  let randomPingInterval = null;
  let sessionTimerInterval = null;

  function refreshIcons() {
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  function setApiBanner(msg) {
    const el = document.getElementById('apiOfflineBanner');
    if (!el) return;
    if (msg) {
      el.textContent = msg;
      el.classList.remove('hidden');
    } else {
      el.classList.add('hidden');
    }
  }

  async function apiFetch(path, opts = {}) {
    const headers = { ...opts.headers };
    if (opts.body && typeof opts.body === 'object' && !(opts.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
      opts = { ...opts, body: JSON.stringify(opts.body) };
    }
    const r = await fetch(path, { credentials: 'same-origin', ...opts, headers });
    state.apiOnline = true;
    setApiBanner('');
    return r;
  }

  async function apiJson(path, opts = {}) {
    const r = await apiFetch(path, opts);
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || r.statusText || String(r.status));
    return data;
  }

  async function tryApi() {
    try {
      const r = await fetch('/api/auth/me', { credentials: 'same-origin' });
      state.apiOnline = r.ok;
      if (!r.ok) throw new Error('offline');
      return r.json();
    } catch (e) {
      state.apiOnline = false;
      setApiBanner('');
      return { user: null };
    }
  }

  function destroyCharts() {
    if (attendanceChart) {
      attendanceChart.destroy();
      attendanceChart = null;
    }
    if (performanceChart) {
      performanceChart.destroy();
      performanceChart = null;
    }
  }

  async function initAdminCharts() {
    const ac = document.getElementById('attendanceChart');
    const pc = document.getElementById('performanceChart');
    if (!ac || !pc || typeof Chart === 'undefined') return;
    destroyCharts();

    const isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const gridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.05)';
    const textColor = isDark ? '#94a3b8' : '#64748b';

    attendanceChart = new Chart(ac.getContext('2d'), {
      type: 'line',
      data: {
        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        datasets: [
          {
            label: 'Attendance %',
            data: [82, 85, 84, 88, 87, 87.3],
            borderColor: '#3b6582',
            backgroundColor: 'rgba(59, 101, 130, 0.1)',
            fill: true,
            tension: 0.35,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        aspectRatio: 2,
        plugins: { legend: { display: false } },
        scales: {
          y: {
            min: 70,
            max: 100,
            grid: { color: gridColor },
            ticks: { color: textColor, callback: (v) => v + '%' }
          },
          x: {
            grid: { color: gridColor },
            ticks: { color: textColor }
          }
        },
      },
    });
    await loadDepartments();
    const mockData = activeDepartments.map(() => Math.floor(Math.random() * 20) + 75);
    const colors = ['#3b6582', '#687787', '#3b9b58', '#cda174', '#5a84a6', '#8e44ad', '#d35400', '#16a085'];
    const mockColors = activeDepartments.map((_, i) => colors[i % colors.length]);

    performanceChart = new Chart(pc.getContext('2d'), {
      type: 'bar',
      data: {
        labels: activeDepartments,
        datasets: [
          {
            label: 'Avg attendance %',
            data: mockData,
            backgroundColor: mockColors,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        aspectRatio: 2,
        plugins: { legend: { display: false } },
        scales: {
          y: {
            min: 0,
            max: 100,
            grid: { color: gridColor },
            ticks: { color: textColor, callback: (v) => v + '%' }
          },
          x: {
            grid: { color: gridColor },
            ticks: { color: textColor }
          }
        },
      },
    });
    refreshIcons();
  }

  function severityLabel(sev) {
    const map = { critical: 'Critical', high: 'High', medium: 'Medium' };
    return map[sev] || sev;
  }

  function deptLabel(code) {
    const map = { cse: 'Computer Science', ece: 'Electronics', me: 'Mechanical', ce: 'Civil' };
    return map[code] || code;
  }

  function renderDefaulterTable() {
    const tbody = document.getElementById('defaulterTableBody');
    const dept = document.getElementById('departmentFilter')?.value || 'all';
    const sev = document.getElementById('severityFilter')?.value || 'all';
    if (!tbody) return;
    let data = DEFAULTERS_DEMO.slice();
    if (dept !== 'all') data = data.filter((d) => d.dept === dept);
    if (sev !== 'all') data = data.filter((d) => d.severity === sev);
    tbody.innerHTML = data
      .map(
        (d) => `
      <tr>
        <td>${d.roll}</td>
        <td>${d.name}</td>
        <td>${deptLabel(d.dept)}</td>
        <td>${d.pct}%</td>
        <td>${d.missed}</td>
        <td><span class="badge badge-${d.severity === 'critical' ? 'danger' : d.severity === 'high' ? 'warning' : 'secondary'}">${severityLabel(d.severity)}</span></td>
        <td>${d.phone}</td>
        <td><button type="button" class="btn btn-sm btn-primary">Notify</button></td>
      </tr>`
      )
      .join('');
    refreshIcons();
  }

  async function renderStudentTableFromApi(filter) {
    const tbody = document.getElementById('studentTableBody');
    if (!tbody) return;
    showTableSkeleton('studentTableBody', 7, 5);
    if (!state.apiOnline) {
      tbody.innerHTML =
        '<tr><td colspan="7">Demo Mode: No database connected.</td></tr>';
      return;
    }
    try {
      const list = await apiJson('/api/directory/students');
      const rows = list.map((s) => {
        let row = 'good';
        let status = 'Good';
        let pct = 85;
        let classes = '—';
        return { ...s, row, status, pct, classes, last: '—' };
      });
      const filtered = rows.filter(() => true);
      tbody.innerHTML = filtered
        .map(
          (s) => `
        <tr class="${s.row}">
          <td>${s.roll_no}</td>
          <td>${s.name}</td>
          <td>${s.pct}%</td>
          <td>${s.classes}</td>
          <td>${s.status}</td>
          <td>${s.last}</td>
          <td><button type="button" class="btn btn-sm btn-secondary">View</button></td>
        </tr>`
        )
        .join('');
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="7">${e.message}</td></tr>`;
    }
    refreshIcons();
  }

  function showSection(role, sectionId) {
    const dashId = DASH_MAP[role];
    const root = document.getElementById(dashId);
    if (!root) return;
    root.querySelectorAll('.app-section').forEach((el) => {
      if (el.id === sectionId) el.classList.remove('hidden');
      else el.classList.add('hidden');
    });
    document.querySelectorAll('#sidebarNav button, #bottomNav button').forEach((b) => {
      b.classList.toggle('active', b.dataset.section === sectionId);
    });
    if (sectionId === 'admin-view-home' && role === 'admin') requestAnimationFrame(() => initAdminCharts());
    else if (sectionId === 'admin-view-otp' && role === 'admin') renderOtpOutbox();
    else if (role === 'admin') destroyCharts();
    refreshIcons();
  }

  function buildNav(role) {
    const items = NAV[role] || NAV.student;
    const sidebar = document.getElementById('sidebarNav');
    const bottom = document.getElementById('bottomNav');
    if (!sidebar || !bottom) return;
    sidebar.innerHTML = '';
    bottom.innerHTML = '';
    const go = (id) => {
      navigate(role, id);
      closeMobileSidebar();
    };
    items.forEach((item) => {
      const sb = document.createElement('button');
      sb.type = 'button';
      sb.dataset.section = item.id;
      sb.innerHTML = `<i data-lucide="${item.icon}"></i><span>${item.label}</span>`;
      sb.addEventListener('click', () => go(item.id));
      sidebar.appendChild(sb);
      const bb = document.createElement('button');
      bb.type = 'button';
      bb.dataset.section = item.id;
      bb.innerHTML = `<i data-lucide="${item.icon}"></i><span>${item.label}</span>`;
      bb.addEventListener('click', () => go(item.id));
      bottom.appendChild(bb);
    });
    navigate(role, items[0].id);
  }

  function navigate(role, sectionId) {
    if (sessionPollInterval) { clearInterval(sessionPollInterval); sessionPollInterval = null; }
    showSection(role, sectionId);
    if (sectionId === 'admin-view-people') loadDirectoryAdmin();
    if (sectionId === 'admin-view-fees') loadFeesAdmin();
    if (sectionId === 'admin-view-salary') loadSalaryAdmin();
    if (sectionId === 'admin-view-campus') loadCampusAdmin();
    if (sectionId === 'teacher-view-home') loadTeacherDashboard();
    if (sectionId === 'teacher-view-attendance') {
      const d = document.getElementById('manualAttDate');
      if (d && !d.value) d.value = new Date().toISOString().slice(0, 10);
      fetchActiveSessionStatus();
      sessionPollInterval = setInterval(fetchActiveSessionStatus, 3000);
    }
    if (sectionId === 'teacher-view-marks') loadMarkStudentSelect();
    if (sectionId === 'student-view-home') {
      checkActiveSessionStudent();
      loadStudentAttendanceSummary();
    }
    if (sectionId === 'student-view-marks') loadStudentMarks();
    if (sectionId === 'parent-view-fees') loadParentFees();
  }

  function openMobileSidebar() {
    document.getElementById('appSidebar')?.classList.add('open');
    document.getElementById('sidebarBackdrop')?.classList.remove('hidden');
    document.getElementById('sidebarToggle')?.setAttribute('aria-expanded', 'true');
  }

  function closeMobileSidebar() {
    document.getElementById('appSidebar')?.classList.remove('open');
    document.getElementById('sidebarBackdrop')?.classList.add('hidden');
    document.getElementById('sidebarToggle')?.setAttribute('aria-expanded', 'false');
  }

  // ===================================================================
  // GPS LIVE SESSION LOGIC
  // ===================================================================

  function getCurrentPosition() {
    return new Promise((resolve, reject) => {
      const fallback = () => {
        if (confirm("Could not read GPS (or not supported on HTTP). Use simulated campus location for demo?")) {
          resolve({ lat: 28.7041, lng: 77.1025, accuracy: 999 });
        } else {
          reject(new Error('Geolocation not supported or denied.'));
        }
      };

      if (!navigator.geolocation) return fallback();

      const gpsOptions = {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 0   // never use a cached position
      };

      // Try up to 3 times, keeping the reading with best accuracy
      let bestPos = null;
      let attempts = 0;
      const maxAttempts = 3;

      const tryOnce = () => {
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            const current = {
              lat: pos.coords.latitude,
              lng: pos.coords.longitude,
              accuracy: pos.coords.accuracy
            };
            if (!bestPos || current.accuracy < bestPos.accuracy) {
              bestPos = current;
            }
            attempts++;
            // If accuracy is already good (<30m) or we've used all attempts, resolve
            if (current.accuracy <= 30 || attempts >= maxAttempts) {
              resolve(bestPos);
            } else {
              setTimeout(tryOnce, 500);
            }
          },
          (err) => {
            attempts++;
            if (bestPos) {
              resolve(bestPos);   // got at least one good reading before
            } else if (attempts >= maxAttempts) {
              fallback();
            } else {
              setTimeout(tryOnce, 500);
            }
          },
          gpsOptions
        );
      };
      tryOnce();
    });
  }

  async function startClassSession() {
    try {
      const pos = await getCurrentPosition();
      const course_code = document.getElementById('sessionCourseCode')?.value || 'CS101';
      const room_name = document.getElementById('sessionRoomName')?.value || 'Classroom';
      const radius_m = parseFloat(document.getElementById('sessionRadius')?.value) || 20;

      const res = await apiJson('/api/attendance/session/start', {
        method: 'POST',
        body: { lat: pos.lat, lng: pos.lng, course_code, room_name, radius_m }
      });

      if (res.ok) {
        activeSessionId = res.session_id;
        fetchActiveSessionStatus();
      }
    } catch (e) {
      alert(e.message);
    }
  }

  async function endClassSession() {
    if (!activeSessionId) return;
    try {
      const res = await apiJson('/api/attendance/session/end', {
        method: 'POST',
        body: { session_id: activeSessionId }
      });
      if (res.ok) {
        alert(`Session ended. ${res.total_checkins} students checked in. Duration: ${res.duration_minutes} min.`);
        activeSessionId = null;
        if (sessionTimerInterval) clearInterval(sessionTimerInterval);
        fetchActiveSessionStatus();
      }
    } catch (e) {
      alert(e.message);
    }
  }

  async function fetchActiveSessionStatus() {
    // Stop polling if navigating away
    if (state.role !== 'teacher') return;
    
    try {
      const res = await apiJson('/api/attendance/session/active');
      const activeDiv = document.getElementById('sessionActive');
      const inactiveDiv = document.getElementById('sessionInactive');
      
      if (res.active && res.sessions.length > 0) {
        const s = res.sessions[0];
        activeSessionId = s.session_id;
        document.getElementById('sessionActiveCourse').textContent = s.course_code;
        document.getElementById('sessionActiveRoom').textContent = s.room_name;
        document.getElementById('sessionActiveRadius').textContent = `${s.radius_m}m radius`;
        document.getElementById('sessionCheckedInCount').textContent = s.checked_in_count;
        
        if (sessionTimerInterval) clearInterval(sessionTimerInterval);
        
        let startedAtStr = s.started_at;
        if (!startedAtStr.endsWith('Z')) startedAtStr += 'Z';
        const start = new Date(startedAtStr);

        document.getElementById('btnRefreshSession')?.addEventListener('click', fetchActiveSessionStatus);

        const updateTimer = () => {
          const diffMs = Date.now() - start.getTime();
          if (diffMs < 0) return;
          const totalSec = Math.floor(diffMs / 1000);
          const h = Math.floor(totalSec / 3600).toString().padStart(2, '0');
          const m = Math.floor((totalSec % 3600) / 60).toString().padStart(2, '0');
          const sec = (totalSec % 60).toString().padStart(2, '0');
          document.getElementById('sessionDuration').textContent = `${h}:${m}:${sec}`;
        };
        updateTimer(); // initial call
        sessionTimerInterval = setInterval(updateTimer, 1000);
        
        if (s.recent_checkins) {
          const markedList = document.getElementById('markedList');
          const failedList = document.getElementById('failedList');
          if (markedList && failedList) {
            markedList.innerHTML = '';
            failedList.innerHTML = '';
            s.recent_checkins.forEach(ci => {
              const li = document.createElement('li');
              li.style.marginBottom = '4px';
              
              const nameSpan = document.createElement('span');
              nameSpan.style.fontWeight = '500';
              nameSpan.textContent = ci.roll_no;
              
              const textSpan = document.createElement('span');
              textSpan.textContent = ` - ${ci.name}`;
              
              li.appendChild(nameSpan);
              li.appendChild(textSpan);
              
              if (ci.inside_radius) {
                markedList.appendChild(li);
              } else {
                const distSpan = document.createElement('span');
                distSpan.textContent = ` (${ci.distance_m}m away)`;
                distSpan.style.color = 'var(--gray-500)';
                distSpan.style.fontSize = '11px';
                distSpan.style.marginLeft = '4px';
                li.appendChild(distSpan);
                failedList.appendChild(li);
              }
            });
          }
        }
        
        inactiveDiv.classList.add('hidden');
        activeDiv.classList.remove('hidden');
      } else {
        activeSessionId = null;
        if (sessionTimerInterval) clearInterval(sessionTimerInterval);
        inactiveDiv.classList.remove('hidden');
        activeDiv.classList.add('hidden');
      }
    } catch (e) {
      console.error('Error fetching session status:', e);
    }
  }

  async function loadStudentAttendanceSummary() {
    if (state.role !== 'student') return;
    try {
      const data = await apiJson('/api/reports/student/attendance-summary');
      
      const overallEl = document.getElementById('studentOverallAttendanceRate');
      if (overallEl) {
        overallEl.textContent = `${data.overall_percentage}%`;
        overallEl.className = `stat-value ${data.overall_percentage >= 75 ? 'success' : (data.overall_percentage >= 60 ? 'warning' : 'danger')}`;
      }

      const listEl = document.getElementById('studentCourseAttendanceList');
      if (listEl) {
        if (!data.courses || data.courses.length === 0) {
          listEl.innerHTML = '<div style="padding: 10px; color: var(--gray-500); text-align: center;">No attendance data found yet.</div>';
          return;
        }

        listEl.innerHTML = data.courses.map(c => {
          let colorClass = 'success';
          if (c.percentage < 60) colorClass = 'danger';
          else if (c.percentage < 75) colorClass = 'warning';
          else if (c.percentage < 90) colorClass = 'primary';
          
          return `
            <div class="attendance-item">
                <span class="subject-name">${escapeHtml(c.course_code)}</span>
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill ${colorClass}" style="width: ${c.percentage}%"></div>
                    </div>
                    <span class="percentage ${colorClass}">${c.percentage}%</span>
                </div>
            </div>`;
        }).join('');
      }
    } catch (e) {
      console.error('Failed to load student attendance summary:', e);
      const listEl = document.getElementById('studentCourseAttendanceList');
      if (listEl) listEl.innerHTML = '<div style="padding: 10px; color: var(--danger); text-align: center;">Error loading data.</div>';
    }
  }

  async function checkActiveSessionStudent() {
    if (state.role !== 'student') return;
    try {
      const res = await apiJson('/api/attendance/session/active');
      const banner = document.getElementById('studentSessionBanner');
      
      if (res.active && res.sessions.length > 0) {
        const s = res.sessions[0];
        activeSessionId = s.session_id;
        document.getElementById('sessionBannerInfo').textContent = `${s.course_code} — ${s.room_name}`;
        
        const statusBadge = document.getElementById('sessionBannerStatus');
        const checkinBtn = document.getElementById('btnSessionCheckin');
        
        if (s.already_checked_in) {
          statusBadge.textContent = 'Attendance Verified';
          statusBadge.className = 'badge badge-success';
          checkinBtn.classList.add('hidden');
          
          // Start background pings if they aren't running already
          if (!randomPingInterval) startRandomPings(s.session_id);
        } else {
          statusBadge.textContent = 'Not checked in';
          statusBadge.className = 'badge badge-warning';
          checkinBtn.classList.remove('hidden');
          stopRandomPings();
        }
        banner.classList.remove('hidden');
      } else {
        activeSessionId = null;
        banner.classList.add('hidden');
        stopRandomPings();
      }
    } catch (e) {
      console.error('Student session check error:', e);
    }
  }

  function startRandomPings(sessionId) {
    if (randomPingInterval) return; // Already running
    
    function scheduleNext() {
      // Random interval between 2 to 5 minutes
      const delay = 120000 + Math.floor(Math.random() * 180000);
      randomPingInterval = setTimeout(async () => {
        if (!activeSessionId) {
          stopRandomPings();
          return;
        }
        
        try {
          const pos = await getCurrentPosition();
          const res = await apiJson('/api/attendance/session/ping', {
            method: 'POST',
            body: { session_id: sessionId, lat: pos.lat, lng: pos.lng }
          });
          
          if (!res.active) {
            stopRandomPings(); // Session ended
            checkActiveSessionStudent(); // update UI banner
            return;
          }
        } catch (e) {
          console.error('Ping failed:', e);
        }
        
        scheduleNext(); // Schedule the next one
      }, delay);
    }
    scheduleNext();
  }

  function stopRandomPings() {
    if (randomPingInterval) {
      clearTimeout(randomPingInterval);
      randomPingInterval = null;
    }
  }

  async function loadDirectoryAdmin() {
    showTableSkeleton('adminTeachersBody', 4, 3);
    showTableSkeleton('adminParentsBody', 3, 2);
    showTableSkeleton('adminStudentsBody', 4, 4);
    if (!state.apiOnline) return;
    try {
      const [teachers, parents, students] = await Promise.all([
        apiJson('/api/directory/teachers'),
        apiJson('/api/directory/parents'),
        apiJson('/api/directory/students'),
      ]);
      const tb = document.getElementById('adminTeachersBody');
      if (tb)
        tb.innerHTML = teachers
          .map(
            (t) =>
              `<tr><td>${escapeHtml(t.name)}</td><td>${escapeHtml(t.email)}</td><td>${escapeHtml(t.department)}</td><td>${t.monthly_salary}</td><td><code>${escapeHtml(t.uid || '—')}</code></td><td style="white-space:nowrap;"><button class="btn btn-secondary" style="padding:0.35rem 0.75rem;font-size:0.85rem;margin-right:6px;display:inline-flex;align-items:center;gap:4px;" onclick="openEditProfileModal('teacher', '${encodeURIComponent(JSON.stringify(t))}')"><i data-lucide="edit-2" style="width:14px;height:14px;"></i> Edit</button><button class="btn btn-danger" style="padding:0.35rem 0.75rem;font-size:0.85rem;display:inline-flex;align-items:center;gap:4px;" onclick="deleteProfile('teacher', ${t.id})"><i data-lucide="trash-2" style="width:14px;height:14px;"></i> Delete</button></td></tr>`
          )
          .join('');
      const pb = document.getElementById('adminParentsBody');
      if (pb)
        pb.innerHTML = parents
          .map((p) => `<tr><td>${escapeHtml(p.name)}</td><td>${escapeHtml(p.email)}</td><td>${escapeHtml(p.phone || '')}</td><td><code>${escapeHtml(p.uid || '—')}</code></td><td style="white-space:nowrap;"><button class="btn btn-secondary" style="padding:0.35rem 0.75rem;font-size:0.85rem;margin-right:6px;display:inline-flex;align-items:center;gap:4px;" onclick="openEditProfileModal('parent', '${encodeURIComponent(JSON.stringify(p))}')"><i data-lucide="edit-2" style="width:14px;height:14px;"></i> Edit</button><button class="btn btn-danger" style="padding:0.35rem 0.75rem;font-size:0.85rem;display:inline-flex;align-items:center;gap:4px;" onclick="deleteProfile('parent', ${p.id})"><i data-lucide="trash-2" style="width:14px;height:14px;"></i> Delete</button></td></tr>`)
          .join('');
      const sb = document.getElementById('adminStudentsBody');
      if (sb)
        sb.innerHTML = students
          .map(
            (s) =>
              `<tr><td>${escapeHtml(s.roll_no)}</td><td>${escapeHtml(s.name)}</td><td>${escapeHtml(s.department)}</td><td>${escapeHtml(s.email || '')}</td><td><code>${escapeHtml(s.uid || '—')}</code></td><td style="white-space:nowrap;"><button class="btn btn-secondary" style="padding:0.35rem 0.75rem;font-size:0.85rem;margin-right:6px;display:inline-flex;align-items:center;gap:4px;" onclick="openEditProfileModal('student', '${encodeURIComponent(JSON.stringify(s))}')"><i data-lucide="edit-2" style="width:14px;height:14px;"></i> Edit</button><button class="btn btn-danger" style="padding:0.35rem 0.75rem;font-size:0.85rem;display:inline-flex;align-items:center;gap:4px;" onclick="deleteProfile('student', ${s.id})"><i data-lucide="trash-2" style="width:14px;height:14px;"></i> Delete</button></td></tr>`
          )
          .join('');
      populateDeptDropdowns(activeDepartments.length ? activeDepartments : ['CSE', 'ECE', 'ME', 'CE', 'EEE']);
      const sel = document.getElementById('formStudentParentId');
      const editSel = document.getElementById('editProfileParentId');
      if (sel) {
        const cur = sel.value;
        const curEdit = editSel ? editSel.value : '';
        const optionsHTML = '<option value="">— None —</option>' + parents.map(p => `<option value="${p.id}">${escapeHtml(p.name)} (${escapeHtml(p.email)})</option>`).join('');
        sel.innerHTML = optionsHTML;
        sel.value = cur;
        if (editSel) {
            editSel.innerHTML = optionsHTML;
            editSel.value = curEdit;
        }
      }
    } catch (e) {
      console.error(e);
    }
    refreshIcons();
  }

  window.deleteProfile = async function(role, id) {
    if(!confirm(`Are you sure you want to delete this ${role}?`)) return;
    try {
      const res = await apiJson(`/api/directory/${role}s/${id}`, { method: 'DELETE' });
      if(res.ok) {
        loadDirectoryAdmin();
      } else {
        alert(res.error || 'Failed to delete');
      }
    } catch(e) {
      alert(e.message);
    }
  };

  async function loadTeacherDashboard() {
    showTableSkeleton('studentTableBody', 7, 5);
    if (!state.apiOnline) return;
    try {
      const data = await apiJson('/api/reports/teacher/analytics');
      const tbody = document.getElementById('studentTableBody');
      if (tbody && data.students) {
        tbody.innerHTML = data.students
          .map(
            (s) => `
          <tr class="${s.row_class || 'neutral'}">
            <td>${escapeHtml(s.roll_no)}</td>
            <td>${escapeHtml(s.name)}</td>
            <td>${s.percent}%</td>
            <td>${s.present}/${s.total}</td>
            <td>${escapeHtml(s.status)}</td>
            <td>—</td>
            <td><button type="button" class="btn btn-sm btn-secondary">View</button></td>
          </tr>`
          )
          .join('');
      }
    } catch (e) {
      console.error(e);
      const tbody = document.getElementById('studentTableBody');
      if (tbody) tbody.innerHTML = `<tr><td colspan="7">${e.message}</td></tr>`;
    }
    refreshIcons();
  }

  function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  async function loadFeesAdmin() {
    showTableSkeleton('feeStructureBody', 4, 3);
    showTableSkeleton('feePaymentsBody', 4, 3);
    if (!state.apiOnline) return;
    try {
      const structs = await apiJson('/api/finance/fee-structures');
      const pay = await apiJson('/api/finance/fee-payments');
      const students = await apiJson('/api/directory/students');
      const fb = document.getElementById('feeStructureBody');
      if (fb)
        fb.innerHTML = structs
          .map(
            (f) =>
              `<tr><td>${escapeHtml(f.program)}</td><td>${escapeHtml(f.item_name)}</td><td>${f.amount}</td><td>${escapeHtml(f.academic_year)}</td></tr>`
          )
          .join('');
      const pb = document.getElementById('feePaymentsBody');
      if (pb)
        pb.innerHTML = pay
          .map(
            (p) =>
              `<tr><td>${escapeHtml(p.student_name)}</td><td>${p.amount_paid}</td><td>${p.paid_on}</td><td>${escapeHtml(p.remarks || '')}</td></tr>`
          )
          .join('');
      const ps = document.getElementById('formPaymentStudent');
      if (ps) {
        ps.innerHTML = '';
        students.forEach((s) => {
          const o = document.createElement('option');
          o.value = s.id;
          o.textContent = `${s.roll_no} — ${s.name}`;
          ps.appendChild(o);
        });
      }
    } catch (e) {
      console.error(e);
    }
  }

  async function loadSalaryAdmin() {
    showTableSkeleton('salaryBody', 5, 3);
    if (!state.apiOnline) return;
    try {
      const salaries = await apiJson('/api/finance/salaries');
      const teachers = await apiJson('/api/directory/teachers');
      const body = document.getElementById('salaryBody');
      if (body)
        body.innerHTML = salaries
          .map(
            (s) =>
              `<tr><td>${escapeHtml(s.teacher_name)}</td><td>${escapeHtml(s.period_label)}</td><td>${s.gross}</td><td>${s.net}</td><td>${s.paid_on}</td></tr>`
          )
          .join('');
      const sel = document.getElementById('formSalaryTeacher');
      if (sel) {
        sel.innerHTML = '';
        teachers.forEach((t) => {
          const o = document.createElement('option');
          o.value = t.id;
          o.textContent = `${t.name}`;
          sel.appendChild(o);
        });
      }
    } catch (e) {
      console.error(e);
    }
  }

  async function loadCampusAdmin() {
    if (!state.apiOnline) return;
    try {
      const c = await apiJson('/api/attendance/campus');
      document.getElementById('campusLat').value = c.lat;
      document.getElementById('campusLng').value = c.lng;
      document.getElementById('campusRadius').value = c.radius_m;
      document.getElementById('campusCurrentText').textContent = `Current centre: ${c.lat}, ${c.lng} — radius ${c.radius_m} m`;
    } catch (e) {
      console.error(e);
    }
  }

  async function loadMarkStudentSelect() {
    if (!state.apiOnline) return;
    try {
      const students = await apiJson('/api/directory/students');
      const sel = document.getElementById('formMarkStudent');
      if (!sel) return;
      sel.innerHTML = '';
      students.forEach((s) => {
        const o = document.createElement('option');
        o.value = s.id;
        o.textContent = `${s.roll_no} — ${s.name}`;
        sel.appendChild(o);
      });
    } catch (e) {
      console.error(e);
    }
  }

  async function loadStudentMarks() {
    const tbody = document.getElementById('studentMarksBody');
    if (!tbody) return;
    showTableSkeleton('studentMarksBody', 5, 3);
    if (!state.apiOnline) {
      tbody.innerHTML = '<tr><td colspan="5">Demo Mode: No database connected.</td></tr>';
      return;
    }
    try {
      const rows = await apiJson('/api/marks/list');
      tbody.innerHTML = rows.length
        ? rows
            .map(
              (m) =>
                `<tr><td>${escapeHtml(m.course_code)}</td><td>${escapeHtml(m.exam_title)}</td><td>${m.score}</td><td>${m.max_score}</td><td>${escapeHtml(
                  m.graded_at || ''
                )}</td></tr>`
            )
            .join('')
        : '<tr><td colspan="5">No marks yet.</td></tr>';
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="5">${e.message}</td></tr>`;
    }
  }

  async function loadParentFees() {
    const tbody = document.getElementById('parentFeeBody');
    if (!tbody) return;
    showTableSkeleton('parentFeeBody', 4, 3);
    if (!state.apiOnline) {
      tbody.innerHTML = '<tr><td colspan="4">Demo Mode: No database connected.</td></tr>';
      return;
    }
    try {
      const rows = await apiJson('/api/finance/fee-payments');
      tbody.innerHTML = rows.length
        ? rows
            .map(
              (p) =>
                `<tr><td>${escapeHtml(p.student_name)}</td><td>${p.amount_paid}</td><td>${p.paid_on}</td><td>${escapeHtml(p.remarks || '')}</td></tr>`
            )
            .join('')
        : '<tr><td colspan="4">No payments recorded.</td></tr>';
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="4">${e.message}</td></tr>`;
    }
  }

  async function loadManualRoster() {
    if (!state.apiOnline) return;
    const course = document.getElementById('manualCourseCode')?.value || 'CS101';
    const date = document.getElementById('manualAttDate')?.value;
    const tbody = document.getElementById('manualAttendanceBody');
    if (!tbody) return;
    try {
      const q = new URLSearchParams({ course_code: course });
      if (date) q.set('date', date);
      const data = await apiJson('/api/attendance/manual?' + q.toString());
      tbody.innerHTML = data.students
        .map((s) => {
          const checked = s.present === true ? 'checked' : '';
          const absent = s.present === false ? 'checked' : '';
          const neutral = s.present === null || s.present === undefined ? 'checked' : '';
          return `<tr data-sid="${s.id}">
            <td>${escapeHtml(s.roll_no)}</td>
            <td>${escapeHtml(s.name)}</td>
            <td>
              <label class="inline-check"><input type="radio" name="p${s.id}" value="1" ${checked}> Present</label>
              <label class="inline-check"><input type="radio" name="p${s.id}" value="0" ${absent}> Absent</label>
              <label class="inline-check"><input type="radio" name="p${s.id}" value="" ${neutral}> —</label>
            </td>
          </tr>`;
        })
        .join('');
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="3">${e.message}</td></tr>`;
    }
  }

  async function saveManualRoster() {
    if (!state.apiOnline) return;
    const course = document.getElementById('manualCourseCode')?.value || 'CS101';
    const date = document.getElementById('manualAttDate')?.value;
    const tbody = document.getElementById('manualAttendanceBody');
    const entries = [];
    tbody?.querySelectorAll('tr[data-sid]').forEach((tr) => {
      const sid = parseInt(tr.dataset.sid, 10);
      const sel = tr.querySelector('input[type="radio"]:checked');
      if (!sel) return;
      if (sel.value === '') return;
      entries.push({ student_id: sid, present: sel.value === '1' });
    });
    try {
      await apiJson('/api/attendance/manual', {
        method: 'POST',
        body: { course_code: course, date, entries },
      });
      alert('Attendance saved (' + entries.length + ' rows).');
    } catch (e) {
      alert(e.message);
    }
  }

  function initials(name) {
    return (name || 'U')
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((w) => w[0])
      .join('')
      .toUpperCase();
  }

  let notifInterval = null;

  async function fetchNotifications() {
    if (!state.user || !state.apiOnline) return;
    try {
      const notifs = await apiJson('/api/notifications/list');
      const unread = notifs.filter(n => !n.is_read).length;
      
      const badge = document.querySelector('.nav-badge');
      if (badge) {
        badge.textContent = unread;
        badge.style.display = unread > 0 ? 'inline-block' : 'none';
      }

      const list = document.getElementById('notificationList');
      if (list) {
        if (notifs.length === 0) {
          list.innerHTML = '<div style="padding:1rem; text-align:center; color:#64748b;">No new notifications</div>';
        } else {
          list.innerHTML = notifs.map(n => `
            <div class="notification-item ${n.type || 'info'} ${!n.is_read ? 'unread' : ''}" style="${!n.is_read ? 'border-left-width: 4px;' : 'opacity:0.7;'}">
              <p class="notification-title">${escapeHtml(n.title)}</p>
              <p class="notification-text">${escapeHtml(n.message)}</p>
              <p style="font-size:0.75rem; color:#94a3b8; margin-top:0.25rem;">${new Date(n.created_at).toLocaleString()}</p>
            </div>
          `).join('');
        }
      }
    } catch (e) {
      console.error('Fetch notifs error:', e);
    }
  }

  function showTableSkeleton(tbodyId, columnsCount, rowsCount = 3) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;
    let html = '';
    for (let r = 0; r < rowsCount; r++) {
      html += '<tr>';
      for (let c = 0; c < columnsCount; c++) {
        html += `<td class="skeleton-row-cell"><span class="skeleton ${c === 0 ? 'skeleton-avatar' : 'skeleton-text'}"></span></td>`;
      }
      html += '</tr>';
    }
    tbody.innerHTML = html;
    refreshIcons();
  }

  const SIM_DATA = {
    admin: {
      title: 'Administrator Command Center',
      badge: 'System Owner',
      stats: [
        { val: '2,847', lbl: 'Students Enrolled' },
        { val: '156', lbl: 'Active Faculty' },
        { val: '94.2%', lbl: 'Avg Placement' }
      ],
      features: [
        'Create and manage complete campus structures & fee heads.',
        'Real-time college-wide insights and automated AI performance predictions.',
        'Map coordinate-bounded GPS boundary restrictions for geo-fencing.'
      ]
    },
    teacher: {
      title: 'Faculty Workspace & Roster',
      badge: 'Educator Portal',
      stats: [
        { val: 'CS101', lbl: 'Active Course' },
        { val: '45', lbl: 'Enrolled Students' },
        { val: '93.3%', lbl: 'Today\'s Attendance' }
      ],
      features: [
        'Mark instant present/absent student attendance rosters digitally.',
        'Grade, review, and release marks directly to student/parent feeds.',
        'Upload dynamic digital curriculum plans and homework instructions.'
      ]
    },
    student: {
      title: 'Academic Progress Hub',
      badge: 'Student Portal',
      stats: [
        { val: '8.7', lbl: 'Current CGPA' },
        { val: '92.5%', lbl: 'Subject Attendance' },
        { val: '5', lbl: 'Pending Tasks' }
      ],
      features: [
        'Mark coordinate-validated GPS attendance via Face Recognition directly on your phone.',
        'Inspect academic marks history and grade cards immediately.',
        'Access digital calendars, exam schedules, and curriculum resources.'
      ]
    },
    parent: {
      title: 'Family Progress Dashboard',
      badge: 'Parent Portal',
      stats: [
        { val: '95.2%', lbl: 'Child Attendance' },
        { val: '8.4', lbl: 'Child CGPA' },
        { val: '0', lbl: 'Child Unpaid Fees' }
      ],
      features: [
        'Real-time alerts regarding child attendance trends or critical dips.',
        'Check exam scores, grades, and teacher notes dynamically.',
        'Safe payment tracking for academic years and tuition structures.'
      ]
    }
  };

  function renderSimPane(role) {
    const pane = document.getElementById('simulatorPane');
    if (!pane) return;
    const data = SIM_DATA[role];
    if (!data) return;
    pane.innerHTML = `
      <div class="simulator-pane-layout">
        <div class="simulator-pane-header">
          <h3>${escapeHtml(data.title)}</h3>
          <span class="sim-badge">${escapeHtml(data.badge)}</span>
        </div>
        <div class="simulator-mock-grid">
          ${data.stats.map(s => `
            <div class="simulator-mock-card">
              <div class="sim-val">${escapeHtml(s.val)}</div>
              <div class="sim-lbl">${escapeHtml(s.lbl)}</div>
            </div>
          `).join('')}
        </div>
        <div class="simulator-features-list">
          ${data.features.map(f => `
            <div class="sim-feature-item">
              <i data-lucide="check-circle-2"></i>
              <span>${escapeHtml(f)}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;
    refreshIcons();
  }

  function showLanding() {
    if (notifInterval) { clearInterval(notifInterval); notifInterval = null; }
    document.body.classList.add('auth-login');
    document.getElementById('landingScreen')?.classList.remove('hidden');
    document.getElementById('loginScreen')?.classList.add('hidden');
    document.getElementById('mainDashboard')?.classList.add('hidden');
    document.getElementById('notificationPanel')?.classList.add('hidden');
    destroyCharts();
    ['adminDashboard', 'teacherDashboard', 'studentDashboard', 'parentDashboard'].forEach((id) => {
      document.getElementById(id)?.classList.add('hidden');
    });
    state.user = null;
    state.role = null;
    refreshIcons();
    renderSimPane('admin');
  }

  function showLogin() {
    if (notifInterval) { clearInterval(notifInterval); notifInterval = null; }
    document.body.classList.add('auth-login');
    document.getElementById('landingScreen')?.classList.add('hidden');
    document.getElementById('loginScreen')?.classList.remove('hidden');
    document.getElementById('mainDashboard')?.classList.add('hidden');
    document.getElementById('notificationPanel')?.classList.add('hidden');
    destroyCharts();
    ['adminDashboard', 'teacherDashboard', 'studentDashboard', 'parentDashboard'].forEach((id) => {
      document.getElementById(id)?.classList.add('hidden');
    });
    state.user = null;
    state.role = null;
    if (typeof window._stopNotifications === 'function') window._stopNotifications();
    refreshIcons();
  }

  function showDashboard(role, user) {
    document.body.classList.remove('auth-login');
    document.getElementById('landingScreen')?.classList.add('hidden');
    document.getElementById('loginScreen')?.classList.add('hidden');
    document.getElementById('mainDashboard')?.classList.remove('hidden');
    state.role = role;
    state.user = user;

    ['adminDashboard', 'teacherDashboard', 'studentDashboard', 'parentDashboard'].forEach((id) => {
      document.getElementById(id)?.classList.add('hidden');
    });
    const panel = document.getElementById(DASH_MAP[role]);
    if (panel) panel.classList.remove('hidden');
    
    if (role === 'admin') {
        apiJson('/api/reports/admin-stats').then(stats => {
            const e1 = document.getElementById('adminStatTotalStudents');
            if (e1) e1.textContent = stats.total_students;
            const e2 = document.getElementById('adminStatActiveTeachers');
            if (e2) e2.textContent = stats.active_teachers;
            const e3 = document.getElementById('adminStatAvgAttendance');
            if (e3) e3.textContent = stats.avg_attendance + '%';
            const e4 = document.getElementById('adminStatDefaulters');
            if (e4) e4.textContent = stats.defaulters;
            const e5 = document.getElementById('adminStatPlacementRate');
            if (e5) e5.textContent = stats.placement_rate + '%';
        }).catch(err => console.error("Stats fetch error:", err));
    }


    const userEl = document.getElementById('currentUser');
    if (userEl) userEl.textContent = user?.display_name || role;
    const av = document.getElementById('userAvatar');
    if (av) av.textContent = initials(user?.display_name || role);

    buildNav(role);
    closeMobileSidebar();
    refreshIcons();

    if (role === 'student') {
        loadStudentCurriculum();
    }

    fetchNotifications();
    if (!notifInterval) {
      notifInterval = setInterval(fetchNotifications, 30000); // poll every 30s (legacy)
    }

    // Start new notification badge polling
    if (typeof window._startNotificationsForUser === 'function') {
      window._startNotificationsForUser(role);
    }
  }

  async function loadStudentCurriculum() {
    const listBody = document.getElementById('curriculumListBody');
    if (!listBody) return;
    
    if (!state.apiOnline) {
      listBody.innerHTML = '<p class="small">Demo Mode: No backend connected to fetch curriculum.</p>';
      return;
    }
    
    try {
      const curriculums = await apiJson('/api/curriculum/list');
      if (curriculums.length === 0) {
        listBody.innerHTML = '<p class="small">No curriculum files uploaded yet.</p>';
        return;
      }
      
      listBody.innerHTML = curriculums.map(c => `
        <div class="schedule-item">
            <div class="schedule-content">
                <h4>${escapeHtml(c.filename)}</h4>
            </div>
            <a href="/api/curriculum/download/${encodeURIComponent(c.filename)}" class="btn btn-sm btn-secondary" target="_blank" download>
                <i data-lucide="download"></i> Download
            </a>
        </div>
      `).join('');
      refreshIcons();
    } catch (e) {
      listBody.innerHTML = '<p class="small alert-danger">Failed to load curriculum files.</p>';
    }
  }

  async function stopCamera() {
    if (cameraStream) {
      cameraStream.getTracks().forEach((t) => t.stop());
      cameraStream = null;
    }
    const video = document.getElementById('cameraVideo');
    if (video) video.srcObject = null;
  }

  async function openCameraModal() {
    const modal = document.getElementById('cameraModal');
    const status = document.getElementById('cameraStatus');
    const video = document.getElementById('cameraVideo');
    if (!modal || !video) return;
    modal.classList.remove('hidden');
    if (status) status.textContent = 'Requesting camera access…';
    try {
      cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false });
      video.srcObject = cameraStream;
      if (status) status.textContent = 'Position your face in the frame';
    } catch (e) {
      if (status) status.textContent = 'Camera unavailable.';
    }
    refreshIcons();
  }

  function closeCameraModal() {
    stopCamera();
    document.getElementById('cameraModal')?.classList.add('hidden');
  }

  document.addEventListener('DOMContentLoaded', async () => {
    document.body.classList.add('auth-login');

    document.getElementById('sidebarToggle')?.addEventListener('click', () => {
      const sb = document.getElementById('appSidebar');
      if (sb?.classList.contains('open')) closeMobileSidebar();
      else openMobileSidebar();
    });
    document.getElementById('sidebarBackdrop')?.addEventListener('click', closeMobileSidebar);

    const me = await tryApi();
    // Always start on landing page on every refresh — user must log in again
    showLanding();

    document.getElementById('loginForm')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const identifier = document.getElementById('loginEmail')?.value?.trim() || '';
      const password = document.getElementById('loginPassword')?.value || '';
      if (!identifier) {
        alert('Please enter your Portal ID or email.');
        return;
      }

      // Auto-detect role from UID prefix
      let roleSelect = document.getElementById('userRole')?.value || 'admin';
      if (identifier.toUpperCase().startsWith('STU-')) roleSelect = 'student';
      else if (identifier.toUpperCase().startsWith('EMP-')) roleSelect = 'teacher';
      else if (identifier.toUpperCase().startsWith('PAR-')) roleSelect = 'parent';

      if (!state.apiOnline) {
        showDashboard(roleSelect, { id: 1, role: roleSelect, email: identifier, display_name: identifier.split('@')[0] });
        return;
      }
      try {
        const data = await apiJson('/api/auth/login', { method: 'POST', body: { identifier, password } });
        showDashboard(data.user.role, data.user);
      } catch (err) {
        alert(err.message || 'Login failed. Check your Portal ID / email and password.');
      }
    });

    document.getElementById('logoutBtn')?.addEventListener('click', async (e) => {
      e.preventDefault();
      try {
        await apiFetch('/api/auth/logout', { method: 'POST' });
      } catch (_) {}
      showLogin();
    });

    document.getElementById('biometricBtn')?.addEventListener('click', async () => {
      const identifier = document.getElementById('loginEmail')?.value?.trim() || '';
      if (!identifier) {
        alert('Enter your Portal ID or email first, then use biometric login.');
        return;
      }
      let roleSelect = document.getElementById('userRole')?.value || 'admin';
      if (identifier.toUpperCase().startsWith('STU-')) roleSelect = 'student';
      else if (identifier.toUpperCase().startsWith('EMP-')) roleSelect = 'teacher';
      else if (identifier.toUpperCase().startsWith('PAR-')) roleSelect = 'parent';

      if (!state.apiOnline) {
        showDashboard(roleSelect, { id: 1, role: roleSelect, email: identifier, display_name: identifier.split('@')[0] });
        return;
      }
      try {
        const data = await apiJson('/api/auth/biometric/login', { method: 'POST', body: { identifier } });
        showDashboard(data.user.role, data.user);
      } catch (err) {
        alert(err.message || 'Biometric login failed');
      }
    });

    document.getElementById('addTeacherForm')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const data = await apiJson('/api/directory/teachers', {
          method: 'POST',
          body: {
            name: document.getElementById('addTeacherName').value,
            email: document.getElementById('addTeacherEmail').value,
            department: document.getElementById('addTeacherDept').value,
            monthly_salary: document.getElementById('addTeacherSalary').value,
            primary_phone: document.getElementById('addTeacherPrimaryPhone').value,
            secondary_phone: document.getElementById('addTeacherSecondaryPhone').value,
            guardian_phone: document.getElementById('addTeacherGuardianPhone').value,
          },
        });
        loadDirectoryAdmin();
        document.getElementById('addTeacherForm').reset();
        alert(`✅ Teacher saved! Portal ID: ${data.uid}`);
      } catch (e) {
        alert(e.message);
      }
    });

    document.getElementById('addParentForm')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const data = await apiJson('/api/directory/parents', {
          method: 'POST',
          body: {
            name: document.getElementById('addParentName').value,
            email: document.getElementById('addParentEmail').value,
            primary_phone: document.getElementById('addParentPrimaryPhone').value,
            secondary_phone: document.getElementById('addParentSecondaryPhone').value,
            guardian_phone: document.getElementById('addParentGuardianPhone').value,
          },
        });
        loadDirectoryAdmin();
        document.getElementById('addParentForm').reset();
        alert(`✅ Parent saved! Portal ID: ${data.uid}`);
      } catch (e) {
        alert(e.message);
      }
    });

    document.getElementById('addStudentForm')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const data = await apiJson('/api/directory/students', {
          method: 'POST',
          body: {
            roll_no: document.getElementById('addStudentRoll').value,
            name: document.getElementById('addStudentName').value,
            email: document.getElementById('addStudentEmail').value,
            department: document.getElementById('addStudentDept').value,
            primary_phone: document.getElementById('addStudentPrimaryPhone').value,
            secondary_phone: document.getElementById('addStudentSecondaryPhone').value,
            guardian_phone: document.getElementById('addStudentGuardianPhone').value,
          },
        });
        loadDirectoryAdmin();
        renderStudentTableFromApi('all');
        document.getElementById('addStudentForm').reset();
        alert(`✅ Student saved! Portal ID: ${data.uid}`);
      } catch (e) {
        alert(e.message);
      }
    });

    document.getElementById('btnAddFeeStructure')?.addEventListener('click', async () => {
      try {
        await apiJson('/api/finance/fee-structures', {
          method: 'POST',
          body: {
            program: document.getElementById('formFeeProgram').value,
            item_name: document.getElementById('formFeeItem').value,
            amount: document.getElementById('formFeeAmount').value,
            academic_year: document.getElementById('formFeeYear').value,
          },
        });
        loadFeesAdmin();
      } catch (e) {
        alert(e.message);
      }
    });
    document.getElementById('btnAddFeePayment')?.addEventListener('click', async () => {
      try {
        await apiJson('/api/finance/fee-payments', {
          method: 'POST',
          body: {
            student_id: document.getElementById('formPaymentStudent').value,
            amount_paid: document.getElementById('formPaymentAmount').value,
            remarks: document.getElementById('formPaymentRemarks').value,
          },
        });
        loadFeesAdmin();
      } catch (e) {
        alert(e.message);
      }
    });
    document.getElementById('btnAddSalary')?.addEventListener('click', async () => {
      try {
        const gross = parseFloat(document.getElementById('formSalaryGross').value || '0');
        const ded = parseFloat(document.getElementById('formSalaryDed').value || '0');
        let net = parseFloat(document.getElementById('formSalaryNet').value || '0');
        if (!net) net = gross - ded;
        await apiJson('/api/finance/salaries', {
          method: 'POST',
          body: {
            teacher_id: document.getElementById('formSalaryTeacher').value,
            period_label: document.getElementById('formSalaryPeriod').value,
            gross,
            deductions: ded,
            net,
            notes: document.getElementById('formSalaryNotes').value,
          },
        });
        loadSalaryAdmin();
      } catch (e) {
        alert(e.message);
      }
    });
    document.getElementById('btnSaveCampus')?.addEventListener('click', async () => {
      try {
        await apiJson('/api/attendance/campus', {
          method: 'PUT',
          body: {
            lat: parseFloat(document.getElementById('campusLat').value),
            lng: parseFloat(document.getElementById('campusLng').value),
            radius_m: parseFloat(document.getElementById('campusRadius').value),
          },
        });
        loadCampusAdmin();
        alert('Campus boundary saved.');
      } catch (e) {
        alert(e.message);
      }
    });

    document.getElementById('btnStartSession')?.addEventListener('click', startClassSession);
    document.getElementById('btnEndSession')?.addEventListener('click', endClassSession);
    
    document.getElementById('btnSessionCheckin')?.addEventListener('click', async () => {
      try {
        const pos = await getCurrentPosition();
        pendingLocation = pos;
        await openCameraModal();
      } catch (e) {
        alert(e.message);
      }
    });

    document.getElementById('btnLoadManualAttendance')?.addEventListener('click', loadManualRoster);
    document.getElementById('btnSaveManualAttendance')?.addEventListener('click', saveManualRoster);

    // CSV Export
    document.getElementById('btnExportCSV')?.addEventListener('click', () => {
      const course = document.getElementById('manualCourseCode')?.value || 'CS101';
      const dateVal = document.getElementById('manualAttDate')?.value || '';
      let url = `/api/reports/attendance/export-csv?course_code=${encodeURIComponent(course)}`;
      if (dateVal) {
        url += `&from=${dateVal}&to=${dateVal}`;
      }
      window.open(url, '_blank');
    });

    // Session History
    document.getElementById('btnLoadSessionHistory')?.addEventListener('click', async () => {
      const tbody = document.getElementById('sessionHistoryBody');
      if (!tbody) return;
      try {
        const data = await apiJson('/api/reports/session-history');
        if (data.length === 0) {
          tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--gray-400);">No past sessions found</td></tr>';
          return;
        }
        tbody.innerHTML = data.map(s => {
          const dt = new Date(s.started_at);
          const dateStr = dt.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
          const timeStr = dt.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
          const durH = Math.floor(s.duration_minutes / 60);
          const durM = Math.round(s.duration_minutes % 60);
          const durStr = durH > 0 ? `${durH}h ${durM}m` : `${durM}m`;
          return `<tr>
            <td><strong>${escapeHtml(s.course_code)}</strong></td>
            <td>${escapeHtml(s.room_name)}</td>
            <td>${dateStr}<br><small style="color:var(--gray-500)">${timeStr}</small></td>
            <td>${durStr}</td>
            <td><strong>${s.checkin_count}</strong> checked in</td>
          </tr>`;
        }).join('');
      } catch (e) {
        tbody.innerHTML = `<tr><td colspan="5">${e.message}</td></tr>`;
      }
    });
    document.getElementById('btnAddMark')?.addEventListener('click', async () => {
      try {
        await apiJson('/api/marks/add', {
          method: 'POST',
          body: {
            student_id: document.getElementById('formMarkStudent').value,
            course_code: document.getElementById('formMarkCourse').value,
            exam_title: document.getElementById('formMarkTitle').value,
            score: document.getElementById('formMarkScore').value,
            max_score: document.getElementById('formMarkMax').value,
          },
        });
        alert('Marks saved.');
      } catch (e) {
        alert(e.message);
      }
    });

    const notifBtn = document.getElementById('notificationBtn');
    const notifPanel = document.getElementById('notificationPanel');
    notifBtn?.addEventListener('click', (ev) => {
      ev.stopPropagation();
      notifPanel?.classList.toggle('hidden');
    });
    document.addEventListener('click', () => notifPanel?.classList.add('hidden'));
    notifPanel?.addEventListener('click', (ev) => ev.stopPropagation());
    
    document.getElementById('markAllReadBtn')?.addEventListener('click', async (ev) => {
      ev.stopPropagation();
      try {
        await apiJson('/api/notifications/mark-read', { method: 'POST' });
        fetchNotifications();
      } catch (e) {
        console.error(e);
      }
    });

    document.getElementById('viewDefaultersBtn')?.addEventListener('click', () => {
      document.getElementById('defaulterModal')?.classList.remove('hidden');
      renderDefaulterTable();
      refreshIcons();
    });
    document.getElementById('teacherDefaultersBtn')?.addEventListener('click', () => {
      document.getElementById('defaulterModal')?.classList.remove('hidden');
      renderDefaulterTable();
      refreshIcons();
    });
    document.getElementById('closeDefaulterModal')?.addEventListener('click', () => {
      document.getElementById('defaulterModal')?.classList.add('hidden');
    });
    document.getElementById('departmentFilter')?.addEventListener('change', renderDefaulterTable);
    document.getElementById('severityFilter')?.addEventListener('change', renderDefaulterTable);
    document.getElementById('exportDefaultersBtn')?.addEventListener('click', () => alert('Export CSV can be added to the API.'));


    document.getElementById('closeDataModal')?.addEventListener('click', () => {
        document.getElementById('dataModal').style.display = 'none';
    });

    document.getElementById('academicCalendarBtn')?.addEventListener('click', async () => {
        try {
            const data = await apiJson('/api/reports/academic-calendar');
            document.getElementById('dataModalTitle').textContent = 'Academic Calendar';
            let html = '<ul style="list-style-type:none; padding:0;">';
            data.forEach(e => {
                html += `<li style="margin-bottom:1rem; padding:1rem; border:1px solid #e2e8f0; border-radius:4px;">
                    <strong>${e.title}</strong> (${e.type})<br>
                    <span style="color:#64748b; font-size:0.9em;">Date: ${e.date}</span>
                </li>`;
            });
            html += '</ul>';
            document.getElementById('dataModalBody').innerHTML = html;
            document.getElementById('dataModal').style.display = 'flex';
        } catch (err) { alert('Error loading calendar: ' + err.message); }
    });

    document.getElementById('examScheduleBtn')?.addEventListener('click', async () => {
        try {
            const data = await apiJson('/api/reports/exam-schedule');
            document.getElementById('dataModalTitle').textContent = 'Exam Schedule';
            let html = '<table class="table" style="width:100%; text-align:left;"><thead><tr><th>Course</th><th>Title</th><th>Date</th></tr></thead><tbody>';
            data.forEach(e => {
                html += `<tr><td>${e.course_code}</td><td>${e.exam_title}</td><td>${e.exam_date}</td></tr>`;
            });
            html += '</tbody></table>';
            document.getElementById('dataModalBody').innerHTML = html;
            document.getElementById('dataModal').style.display = 'flex';
        } catch (err) { alert('Error loading schedule: ' + err.message); }
    });

    document.getElementById('placementStatsBtn')?.addEventListener('click', async () => {
        try {
            const stats = await apiJson('/api/reports/placement-stats');
            document.getElementById('dataModalTitle').textContent = 'Placement Statistics';
            let html = `
                <div style="font-size:1.1em; line-height:1.6;">
                    <p><strong>Total Eligible Students:</strong> ${stats.total_eligible}</p>
                    <p><strong>Placed Students:</strong> ${stats.placed}</p>
                    <p><strong>Unplaced Students:</strong> ${stats.unplaced}</p>
                    <p><strong>Placement Rate:</strong> <span style="color:#0ea5e9; font-weight:bold;">${stats.placement_rate}%</span></p>
                </div>
            `;
            document.getElementById('dataModalBody').innerHTML = html;
            document.getElementById('dataModal').style.display = 'flex';
        } catch (err) { alert('Error loading stats: ' + err.message); }
    });


    document.getElementById('viewReportsBtn')?.addEventListener('click', async () => {
      if (!state.apiOnline) {
        alert('Demo Mode: Connect backend to view real analytics.');
        return;
      }
      try {
        const data = await apiJson('/api/reports/teacher/analytics?course_code=CS101');
        document.getElementById('reportTotalStudents').textContent = data.total_students;
        document.getElementById('reportOverallAttendance').textContent = data.overall_attendance_percent + '%';
        document.getElementById('reportAverageExam').textContent = data.average_exam_percent + '%';
        document.getElementById('reportExcellentCount').textContent = data.attendance_breakdown.excellent;
        document.getElementById('reportGoodCount').textContent = data.attendance_breakdown.good;
        document.getElementById('reportWarningCount').textContent = data.attendance_breakdown.warning;
        document.getElementById('reportDefaulterCount').textContent = data.attendance_breakdown.defaulter;
        
        navigate('teacher', 'teacher-view-reports');
      } catch (e) {
        alert('Failed to load reports: ' + e.message);
      }
    });

    document.getElementById('uploadCurriculumBtn')?.addEventListener('click', () => {
      document.getElementById('curriculumFileInput')?.click();
    });

    document.getElementById('curriculumFileInput')?.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      if (!state.apiOnline) {
        alert('Demo Mode: File selected but no backend is connected.');
        return;
      }

      const formData = new FormData();
      formData.append('file', file);

      try {
        const res = await apiFetch('/api/curriculum/upload', {
          method: 'POST',
          body: formData
        });

        if (res.ok) {
          const data = await res.json();
          alert('Upload successful: ' + data.filename);
        } else {
          const data = await res.json();
          alert('Upload failed: ' + (data.error || res.statusText));
        }
      } catch (err) {
        alert('Upload error: ' + err.message);
      }
      
      // Clear the input
      e.target.value = '';
    });

    document.getElementById('takeAttendanceBtn')?.addEventListener('click', () => {
      if (state.role === 'teacher') navigate('teacher', 'teacher-view-attendance');
      else alert('Switch to the teacher account to use manual attendance.');
    });

    document.getElementById('exportAttendanceBtn')?.addEventListener('click', () => alert('Use server export when implemented.'));

    document.getElementById('markAttendanceBtn')?.addEventListener('click', () => {
      document.getElementById('attendanceModal')?.classList.remove('hidden');
      refreshIcons();
    });
    document.getElementById('closeAttendanceModal')?.addEventListener('click', () => {
      document.getElementById('attendanceModal')?.classList.add('hidden');
    });

    let pendingLocation = null;

    document.getElementById('combinedAttendanceBtn')?.addEventListener('click', async () => {
      document.getElementById('attendanceModal')?.classList.add('hidden');
      if (!navigator.geolocation) {
        alert('Geolocation not supported.');
        return;
      }
      if (!state.apiOnline) {
        alert('Running in Demo Mode: No backend server connected. Location will not be verified.');
        return;
      }
      navigator.geolocation.getCurrentPosition(
        async (pos) => {
          pendingLocation = {
            lat: pos.coords.latitude,
            lng: pos.coords.longitude
          };
          // Verify location first
          try {
            const v = await apiJson('/api/attendance/verify-location', { method: 'POST', body: pendingLocation });
            if (!v.ok) {
              alert(v.message + ' Distance: ' + v.distance_m + ' m');
              return;
            }
            if (state.user?.role !== 'student') {
              alert('Location OK (' + Math.round(v.distance_m) + ' m from campus centre). Students can mark from their account.');
              return;
            }
            // Location is good, proceed to face capture
            await openCameraModal();
          } catch (e) {
            alert(e.message);
          }
        },
        () => alert('Could not read GPS. Allow location permission.')
      );
    });

    document.getElementById('closeCameraModal')?.addEventListener('click', closeCameraModal);
    document.getElementById('captureBtn')?.addEventListener('click', async () => {
      const video = document.getElementById('cameraVideo');
      if (!video || !state.apiOnline || !pendingLocation) {
        closeCameraModal();
        return;
      }
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(async (blob) => {
        if (!blob) {
          alert('Could not capture frame.');
          closeCameraModal();
          return;
        }
        const fd = new FormData();
        fd.append('image', blob, 'capture.jpg');
        fd.append('lat', pendingLocation.lat);
        fd.append('lng', pendingLocation.lng);

        if (activeSessionId) {
          // New Live Session check-in flow
          fd.append('session_id', activeSessionId);
          try {
            const r = await fetch('/api/attendance/session/checkin', { method: 'POST', body: fd, credentials: 'same-origin' });
            const data = await r.json().catch(() => ({}));
            if (!r.ok) throw new Error(data.reason || data.error || 'Check-in failed');
            alert('Attendance marked! Background verification started.');
            fetchNotifications();
            checkActiveSessionStudent(); // Refresh the banner UI
          } catch (e) {
            alert(e.message);
          }
        } else {
          // Old combined attendance flow (campus-wide)
          fd.append('course_code', 'CS101');
          try {
            const r = await fetch('/api/attendance/mark-combined', { method: 'POST', body: fd, credentials: 'same-origin' });
            const data = await r.json().catch(() => ({}));
            if (!r.ok) throw new Error(data.reason || data.error || 'Combined verify failed');
            alert('GPS + Face attendance successfully recorded.');
            fetchNotifications(); // Refresh notifications
          } catch (e) {
            alert(e.message);
          }
        }
        closeCameraModal();
      }, 'image/jpeg', 0.85);
    });

    document.getElementById('attendanceFilter')?.addEventListener('change', (e) => {
      renderStudentTableFromApi(e.target.value);
    });
    renderStudentTableFromApi('all');

    document.querySelectorAll('.modal').forEach((modal) => {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.add('hidden');
      });
    });

    // Landing Screen Listeners
    document.getElementById('launchPortalNavBtn')?.addEventListener('click', showLogin);
    document.getElementById('enterPortalBtn')?.addEventListener('click', showLogin);
    document.getElementById('backToLandingBtn')?.addEventListener('click', showLanding);
    document.getElementById('scrollFeaturesBtn')?.addEventListener('click', () => {
      document.getElementById('featuresSection')?.scrollIntoView({ behavior: 'smooth' });
    });
    document.querySelectorAll('.simulator-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.simulator-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        renderSimPane(tab.dataset.sim);
      });
    });

    // FAQ Accordion Click Listeners
    document.querySelectorAll('.faq-header').forEach(btn => {
      btn.addEventListener('click', () => {
        const card = btn.closest('.faq-card');
        const content = card.querySelector('.faq-content');
        const isActive = card.classList.contains('active');
        
        // Close all other FAQs
        document.querySelectorAll('.faq-card').forEach(c => {
          c.classList.remove('active');
          const otherContent = c.querySelector('.faq-content');
          if (otherContent) otherContent.style.maxHeight = null;
        });
        
        if (!isActive) {
          card.classList.add('active');
          if (content) content.style.maxHeight = content.scrollHeight + "px";
        }
      });
    });

    // ── Scroll-Reveal IntersectionObserver ──
    const revealElements = document.querySelectorAll('.scroll-reveal');
    if (revealElements.length > 0) {
      const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            revealObserver.unobserve(entry.target);
          }
        });
      }, {
        threshold: 0.12,
        rootMargin: '0px 0px -40px 0px'
      });
      revealElements.forEach(el => revealObserver.observe(el));
    }

    // Footer link scroll triggers
    document.getElementById('footerEnterPortal')?.addEventListener('click', (e) => {
      e.preventDefault();
      showLogin();
    });
    document.getElementById('footerStats')?.addEventListener('click', (e) => {
      e.preventDefault();
      document.querySelector('.landing-stats-banner')?.scrollIntoView({ behavior: 'smooth' });
    });
    document.getElementById('footerSim')?.addEventListener('click', (e) => {
      e.preventDefault();
      document.querySelector('.simulator-section')?.scrollIntoView({ behavior: 'smooth' });
    });

    // Listen for OS theme changes to redrawn chart grids
    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        const activeSection = document.querySelector('.app-section:not(.hidden)');
        if (activeSection && activeSection.id === 'admin-view-home' && state.role === 'admin') {
          initAdminCharts();
        }
      });
    }

    refreshIcons();
    window.closeProfileModal = function () {
      const modal = document.getElementById('profileModal');
      if (modal) modal.style.display = 'none';
    };

    document.getElementById('myProfileBtn')?.addEventListener('click', async () => {
      try {
        const p = await apiJson('/api/profile/me');
        // Hidden plain text fields
        document.getElementById('profileName').textContent = p.display_name;
        document.getElementById('profileUid').textContent = p.uid;
        document.getElementById('profileEmail').textContent = p.email;
        document.getElementById('profileRole').textContent = p.role;
        
        // Virtual ID Card
        document.getElementById('virtualIdName').textContent = p.display_name;
        document.getElementById('virtualIdRole').textContent = p.role;
        document.getElementById('virtualIdUid').textContent = p.uid;
        
        const photoEl = document.getElementById('virtualIdPhoto');
        if (p.profile_picture) {
            photoEl.style.backgroundImage = `url(${p.profile_picture})`;
            document.getElementById('virtualIdInitials').textContent = "";
        } else {
            photoEl.style.backgroundImage = "none";
            document.getElementById('virtualIdInitials').textContent = p.display_name.charAt(0).toUpperCase();
        }

        // Navbar Avatar
        const avatarEl = document.getElementById('userAvatar');
        if (avatarEl) {
            if (p.profile_picture) {
                avatarEl.style.backgroundImage = `url(${p.profile_picture})`;
                avatarEl.style.backgroundSize = "cover";
                avatarEl.textContent = "";
            } else {
                avatarEl.style.backgroundImage = "none";
                avatarEl.textContent = p.display_name.substring(0,2).toUpperCase();
            }
        }
        
        // Form Inputs
        document.getElementById('profilePrimaryPhone').value = p.primary_phone || '';
        document.getElementById('profileSecondaryPhone').value = p.secondary_phone || '';
        document.getElementById('profileGuardianPhone').value = p.guardian_phone || '';
        document.getElementById('profileAddress').value = p.address || '';
        document.getElementById('profileDob').value = p.dob || '';
        document.getElementById('profileBloodGroup').value = p.blood_group || '';
        document.getElementById('profilePicture').value = '';
        
        const modal = document.getElementById('profileModal');
        if (modal) modal.style.display = 'flex';
      } catch (e) {
        alert("Could not load profile: " + e.message);
      }
    });

    document.getElementById('profilePhoneForm')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const fileInput = document.getElementById('profilePicture');
        if (fileInput.files.length > 0) {
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            const uploadRes = await fetch('/api/profile/upload-picture', {
                method: 'POST',
                body: formData
            });
            if (!uploadRes.ok) throw new Error('Failed to upload picture');
        }

        await apiJson('/api/profile/me', {
          method: 'PUT',
          body: {
            primary_phone: document.getElementById('profilePrimaryPhone').value,
            secondary_phone: document.getElementById('profileSecondaryPhone').value,
            guardian_phone: document.getElementById('profileGuardianPhone').value,
            address: document.getElementById('profileAddress').value,
            dob: document.getElementById('profileDob').value,
            blood_group: document.getElementById('profileBloodGroup').value,
          }
        });
        alert('Profile details updated successfully!');
        
        // Refresh the profile to update the Virtual ID Card and Avatar
        document.getElementById('myProfileBtn').click();
      } catch (e) {
        alert('Error updating profile: ' + e.message);
      }
    });

    document.getElementById('profilePasswordForm')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const current = document.getElementById('profileCurrentPassword').value;
      const newPass = document.getElementById('profileNewPassword').value;
      const confirmPass = document.getElementById('profileConfirmPassword').value;

      if (newPass !== confirmPass) {
        alert("New passwords do not match!");
        return;
      }

      try {
        await apiJson('/api/profile/change-password', {
          method: 'POST',
          body: { current_password: current, new_password: newPass }
        });
        alert('Password changed successfully!');
        document.getElementById('profilePasswordForm').reset();
      } catch (e) {
        alert('Error changing password: ' + e.message);
      }
    });

    window.generateMissingCredentials = async function () {
      if (!confirm("Are you sure you want to generate missing Portal IDs and set the default password 'Welcome@123' for profiles without accounts?")) return;
      try {
        const res = await apiJson('/api/directory/generate-missing-credentials', { method: 'POST' });
        alert(`Successfully generated credentials for ${res.generated_count} users!`);
        loadDirectoryAdmin();
      } catch (e) {
        alert("Error generating credentials: " + e.message);
      }
    };
  });

    // --- OTP & Forgot Password Flow ---
    const loginForm = document.getElementById('loginForm');
    const otpRequestForm = document.getElementById('otpRequestForm');
    const otpVerifyForm = document.getElementById('otpVerifyForm');
    const otpResetForm = document.getElementById('otpResetForm');

    function hideAllLoginForms() {
        if(loginForm) loginForm.classList.add('hidden');
        if(otpRequestForm) otpRequestForm.classList.add('hidden');
        if(otpVerifyForm) otpVerifyForm.classList.add('hidden');
        if(otpResetForm) otpResetForm.classList.add('hidden');
    }

    document.getElementById('forgotPassBtn')?.addEventListener('click', () => {
        hideAllLoginForms();
        if(otpRequestForm) otpRequestForm.classList.remove('hidden');
    });

    document.getElementById('backToLoginBtn')?.addEventListener('click', () => {
        hideAllLoginForms();
        if(loginForm) loginForm.classList.remove('hidden');
    });

    document.getElementById('backToRequestBtn')?.addEventListener('click', () => {
        hideAllLoginForms();
        if(otpRequestForm) otpRequestForm.classList.remove('hidden');
    });

    document.getElementById('backToVerifyBtn')?.addEventListener('click', () => {
        hideAllLoginForms();
        if(otpVerifyForm) otpVerifyForm.classList.remove('hidden');
    });

    otpRequestForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const identifier = document.getElementById('otpIdentifier').value;
        const btn = e.target.querySelector('button[type="submit"]');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i data-lucide="loader-2" class="spin"></i> Sending...';
        btn.disabled = true;
        
        // Remove old inline messages
        const oldMsg = e.target.querySelector('.inline-error');
        if(oldMsg) oldMsg.remove();

        try {
            const res = await apiJson('/api/auth/request-otp', {
                method: 'POST', body: { identifier }
            });
            if (res.ok) {
                // Success
                hideAllLoginForms();
                otpVerifyForm.classList.remove('hidden');
                
                // Show success message in the verify form
                let verifyMsg = otpVerifyForm.querySelector('.inline-success');
                if(!verifyMsg) {
                    verifyMsg = document.createElement('div');
                    verifyMsg.className = 'inline-success alert alert-success';
                    verifyMsg.style.marginBottom = '1rem';
                    otpVerifyForm.insertBefore(verifyMsg, otpVerifyForm.firstChild);
                }
                verifyMsg.textContent = res.message || "Success! Please check your email inbox (and spam folder) for your secure 6-digit OTP.";
            }
        } catch(err) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'inline-error alert alert-danger';
            errorDiv.style.marginBottom = '1rem';
            errorDiv.textContent = err.message || "Failed to send OTP.";
            e.target.insertBefore(errorDiv, e.target.firstChild);
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
            if(window.lucide) lucide.createIcons();
        }
    });

    document.getElementById('otpLoginSubmitBtn')?.addEventListener('click', async () => {
        const identifier = document.getElementById('otpIdentifier').value;
        const otp = document.getElementById('otpCode').value;
        try {
            const res = await apiJson('/api/auth/verify-otp-login', {
                method: 'POST', body: { identifier, otp }
            });
            if (res.ok) {
                showDashboard(res.user.role, res.user);
                hideAllLoginForms();
                loginForm.classList.remove('hidden'); // Reset for next time
            }
        } catch(err) {
            alert(err.message);
        }
    });

    document.getElementById('otpResetSubmitBtn')?.addEventListener('click', () => {
        const otp = document.getElementById('otpCode').value;
        if(!otp) return alert("Please enter the OTP first!");
        hideAllLoginForms();
        otpResetForm.classList.remove('hidden');
    });

    otpResetForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const identifier = document.getElementById('otpIdentifier').value;
        const otp = document.getElementById('otpCode').value;
        const new_password = document.getElementById('otpNewPassword').value;
        try {
            const res = await apiJson('/api/auth/reset-password', {
                method: 'POST', body: { identifier, otp, new_password }
            });
            if (res.ok) {
                alert("Password successfully reset! You can now log in with your new password.");
                hideAllLoginForms();
                loginForm.classList.remove('hidden');
            }
        } catch(err) {
            alert(err.message);
        }
    });


// Expose globally so inline onclick works
window.renderOtpOutbox = async function() {
  const tbody = document.getElementById('otpOutboxBody');
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="4" style="text-align: center;">Loading...</td></tr>`;
  try {
    const res = await apiFetch('/api/auth/admin/otp-logs');
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    if (!data.logs || data.logs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align: center;">No active OTPs right now.</td></tr>`;
      return;
    }
    tbody.innerHTML = data.logs.map(log => `
      <tr>
        <td><strong>${log.identifier}</strong></td>
        <td><span class="badge ${log.role}">${log.role}</span></td>
        <td><span style="font-size: 1.2rem; font-weight: bold; font-family: monospace; letter-spacing: 2px;">${log.otp}</span></td>
        <td>${new Date(log.expiry + 'Z').toLocaleString()}</td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: red;">Error: ${err.message}</td></tr>`;
  }
};


// --- Department Management Logic ---
let activeDepartments = [];

async function loadDepartments() {
  try {
    const data = await apiJson('/api/auth/admin/departments');
    activeDepartments = data.departments || ['CSE', 'ECE', 'ME', 'CE', 'EEE'];
    renderDepartmentTags();
  } catch (err) {
    console.error('Failed to load departments', err);
    activeDepartments = ['CSE', 'ECE', 'ME', 'CE', 'EEE'];
  }
}

function renderDepartmentTags() {
  const container = document.getElementById('deptTagsContainer');
  if (!container) return;
  container.innerHTML = activeDepartments.map(d => `
    <span class="badge primary" style="display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem; font-size: 1rem;">
      ${d}
      <i data-lucide="x" style="cursor: pointer; width: 16px; height: 16px;" onclick="removeDepartment('${d}')"></i>
    </span>
  `).join('');
  refreshIcons();
}

window.addDepartment = async function() {
  const input = document.getElementById('newDeptInput');
  const val = input.value.trim().toUpperCase();
  if (!val) return;
  if (activeDepartments.includes(val)) {
    input.value = '';
    return;
  }
  
  const newList = [...activeDepartments, val];
  try {
    await apiJson('/api/auth/admin/departments', { method: 'POST', body: { departments: newList } });
    activeDepartments = newList;
    input.value = '';
    renderDepartmentTags();
    initAdminCharts(); // Re-render chart!
  } catch (err) {
    alert('Failed to add department: ' + err.message);
  }
};

window.removeDepartment = async function(dept) {
  if (!confirm(`Are you sure you want to remove ${dept}?`)) return;
  const newList = activeDepartments.filter(d => d !== dept);
  try {
    await apiJson('/api/auth/admin/departments', { method: 'POST', body: { departments: newList } });
    activeDepartments = newList;
    renderDepartmentTags();
    initAdminCharts(); // Re-render chart!
  } catch (err) {
    alert('Failed to remove department: ' + err.message);
  }
};

// --- Edit Profile Logic ---
function populateDeptDropdowns(departments) {
  const deptOptions = departments.map(d => `<option value="${d}">${d}</option>`).join('');
  const teacherSel = document.getElementById('addTeacherDept');
  const studentSel = document.getElementById('addStudentDept');
  const editDeptSel = document.getElementById('editProfileDept');
  if (teacherSel) teacherSel.innerHTML = deptOptions;
  if (studentSel) studentSel.innerHTML = deptOptions;
  if (editDeptSel) editDeptSel.innerHTML = deptOptions;
}

window.openEditProfileModal = function(type, dataStr) {
  const data = JSON.parse(decodeURIComponent(dataStr));
  document.getElementById('editProfileId').value = data.id;
  document.getElementById('editProfileType').value = type;
  
  // Reset all optional groups
  document.getElementById('editFormGroupRollNo').style.display = 'none';
  document.getElementById('editFormGroupPhone').style.display = 'none';
  document.getElementById('editFormGroupDeptSalary').style.display = 'none';
  document.getElementById('editFormGroupSalary').style.display = 'none';
  document.getElementById('editFormGroupParent').style.display = 'none';
  
  // Common fields
  document.getElementById('editProfileName').value = data.name || '';
  document.getElementById('editProfileEmail').value = data.email || '';
  
  if (type === 'teacher') {
    document.getElementById('editFormGroupPhone').style.display = 'block';
    document.getElementById('editProfilePhone').value = data.primary_phone || '';
    document.getElementById('editFormGroupDeptSalary').style.display = 'flex';
    document.getElementById('editFormGroupSalary').style.display = 'block';
    document.getElementById('editProfileDept').value = data.department || '';
    document.getElementById('editProfileSalary').value = data.monthly_salary || 0;
  } else if (type === 'student') {
    document.getElementById('editFormGroupRollNo').style.display = 'block';
    document.getElementById('editProfileRollNo').value = data.roll_no || '';
    document.getElementById('editFormGroupPhone').style.display = 'block';
    document.getElementById('editProfilePhone').value = data.primary_phone || '';
    document.getElementById('editFormGroupDeptSalary').style.display = 'flex';
    document.getElementById('editProfileDept').value = data.department || '';
    document.getElementById('editFormGroupParent').style.display = 'block';
    document.getElementById('editProfileParentId').value = data.parent_id || '';
  } else if (type === 'parent') {
    document.getElementById('editFormGroupPhone').style.display = 'block';
    document.getElementById('editProfilePhone').value = data.phone || data.primary_phone || '';
  }
  
  document.getElementById('editProfileModal').style.display = 'flex';
  document.getElementById('editProfileModal').classList.remove('hidden');
};

window.closeEditProfileModal = function() {
  document.getElementById('editProfileModal').style.display = 'none';
  document.getElementById('editProfileModal').classList.add('hidden');
};

document.getElementById('editProfileForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const id = document.getElementById('editProfileId').value;
  const type = document.getElementById('editProfileType').value;
  
  const payload = {
    name: document.getElementById('editProfileName').value,
    email: document.getElementById('editProfileEmail').value
  };
  
  if (type === 'teacher') {
    payload.department = document.getElementById('editProfileDept').value;
    payload.monthly_salary = document.getElementById('editProfileSalary').value;
    payload.primary_phone = document.getElementById('editProfilePhone').value;
  } else if (type === 'student') {
    payload.roll_no = document.getElementById('editProfileRollNo').value;
    payload.department = document.getElementById('editProfileDept').value;
    payload.primary_phone = document.getElementById('editProfilePhone').value;
    payload.parent_id = document.getElementById('editProfileParentId').value;
  } else if (type === 'parent') {
    payload.phone = document.getElementById('editProfilePhone').value;
    payload.primary_phone = document.getElementById('editProfilePhone').value;
  }
  
  try {
    await apiJson(`/api/directory/${type}s/${id}`, { method: 'PATCH', body: payload });
    closeEditProfileModal();
    if (typeof loadDirectoryAdmin === 'function') {
      loadDirectoryAdmin();
    }
  } catch (err) {
    alert('Failed to update profile: ' + err.message);
  }
});

})();

window.viewDirectory = function(targetId) {
  const allSections = document.querySelectorAll('.app-section');
  allSections.forEach(el => {
    if (el.id === 'admin-view-people') el.classList.remove('hidden');
    else if (el.closest && el.closest('#admin-dashboard')) el.classList.add('hidden');
  });
  document.querySelectorAll('#sidebarNav button, #bottomNav button').forEach(b => {
    b.classList.toggle('active', b.dataset.section === 'admin-view-people');
  });
  setTimeout(() => {
    const el = document.getElementById(targetId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      const card = el.closest('.card');
      if (card) {
        card.style.transition = 'box-shadow 0.3s';
        card.style.boxShadow = '0 0 0 2px var(--primary-color, #3b6582)';
        setTimeout(() => { card.style.boxShadow = 'none'; }, 1500);
      }
    }
  }, 150);
};

// =============================================================================
// NOTIFICATION & MESSAGING SYSTEM
// =============================================================================

let _notifPollTimer = null;
let _notifPanelOpen = false;
let _recipientsList = [];

// ── Helpers ──────────────────────────────────────────────────────────────────

function _timeAgo(isoStr) {
  const diff = Date.now() - new Date(isoStr).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1)  return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function _showToast(msg, isError = false) {
  const el = document.getElementById('toastNotif');
  const txt = document.getElementById('toastNotifText');
  if (!el || !txt) return;
  txt.textContent = msg;
  el.style.background = isError ? '#7f1d1d' : '#1a2e40';
  el.classList.add('show');
  setTimeout(() => { el.classList.remove('show'); el.style.display = 'none'; }, 3000);
}

// ── Badge polling ─────────────────────────────────────────────────────────────

async function _pollUnreadCount() {
  try {
    const data = await fetch('/api/notifications/unread-count', { credentials: 'same-origin' })
      .then(r => r.json()).catch(() => ({ count: 0 }));
    const badge = document.getElementById('notifBadge');
    if (!badge) return;
    const count = data.count || 0;
    if (count > 0) {
      badge.textContent = count > 99 ? '99+' : count;
      badge.classList.remove('hidden');
      badge.classList.add('has-new');
    } else {
      badge.classList.add('hidden');
      badge.classList.remove('has-new');
    }
  } catch (e) { /* silent fail */ }
}

function startNotifPolling() {
  _pollUnreadCount();
  _notifPollTimer = setInterval(_pollUnreadCount, 30000);
}

function stopNotifPolling() {
  if (_notifPollTimer) { clearInterval(_notifPollTimer); _notifPollTimer = null; }
}

// ── Panel open/close ──────────────────────────────────────────────────────────

function initNotificationPanel() {
  const btn = document.getElementById('notificationBtn');
  const panel = document.getElementById('notifPanel');
  if (!btn || !panel) return;

  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    _notifPanelOpen = !_notifPanelOpen;
    panel.classList.toggle('hidden', !_notifPanelOpen);
    if (_notifPanelOpen) {
      loadNotifPanelAlerts();
      // Show compose footer only for admin/teacher
      const role = window._currentUserRole || '';
      const footer = document.getElementById('notifComposeFooter');
      if (footer) footer.style.display = (role === 'admin' || role === 'teacher') ? 'block' : 'none';
    }
  });

  document.addEventListener('click', (e) => {
    const wrapper = document.getElementById('notifWrapper');
    if (wrapper && !wrapper.contains(e.target)) {
      panel.classList.add('hidden');
      _notifPanelOpen = false;
    }
  });

  const markAllBtn = document.getElementById('markAllReadBtn');
  if (markAllBtn) {
    markAllBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      await fetch('/api/notifications/mark-read', { method: 'POST', credentials: 'same-origin', headers: {'Content-Type':'application/json'}, body: '{}' });
      _pollUnreadCount();
      loadNotifPanelAlerts();
    });
  }

  document.getElementById('composeForm')?.addEventListener('submit', handleComposeSend);
}

// ── Tab switching ─────────────────────────────────────────────────────────────

window.switchNotifTab = function(tab) {
  ['notifs', 'inbox', 'sent'].forEach(t => {
    document.getElementById(`notifTabContent${t.charAt(0).toUpperCase() + t.slice(1)}`)?.classList.toggle('hidden', t !== tab);
    document.getElementById(`notifTab${t.charAt(0).toUpperCase() + t.slice(1)}`)?.classList.toggle('active', t === tab);
  });
  if (tab === 'inbox') loadInbox();
  if (tab === 'sent') loadSent();
};

// ── Alerts tab ────────────────────────────────────────────────────────────────

async function loadNotifPanelAlerts() {
  const list = document.getElementById('notifList');
  if (!list) return;
  list.innerHTML = '<div class="notif-empty">Loading...</div>';
  try {
    const notifs = await apiJson('/api/notifications/list');
    if (!notifs.length) {
      list.innerHTML = '<div class="notif-empty">No notifications yet 🎉</div>';
      return;
    }
    list.innerHTML = notifs.map(n => `
      <div class="notif-item ${n.is_read ? 'read' : 'unread'}" onclick="markNotifRead(${n.id})" data-id="${n.id}">
        <div class="notif-item-dot"></div>
        <div class="notif-item-content">
          <div class="notif-item-title">${escapeHtml(n.title)}</div>
          <div class="notif-item-msg">${escapeHtml(n.message)}</div>
        </div>
        <div class="notif-item-time">${_timeAgo(n.created_at)}</div>
      </div>`).join('');
  } catch(e) {
    list.innerHTML = '<div class="notif-empty">Failed to load.</div>';
  }
}

window.markNotifRead = async function(id) {
  await fetch('/api/notifications/mark-read', {
    method: 'POST', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id })
  });
  const el = document.querySelector(`.notif-item[data-id="${id}"]`);
  if (el) { el.classList.remove('unread'); el.classList.add('read'); }
  _pollUnreadCount();
};

// ── Inbox tab ─────────────────────────────────────────────────────────────────

async function loadInbox() {
  const list = document.getElementById('inboxList');
  if (!list) return;
  list.innerHTML = '<div class="notif-empty">Loading...</div>';
  try {
    const msgs = await apiJson('/api/notifications/messages/inbox');
    if (!msgs.length) {
      list.innerHTML = '<div class="notif-empty">No messages in your inbox</div>';
      return;
    }
    list.innerHTML = msgs.map(m => `
      <div class="msg-item ${m.is_read ? '' : 'unread'}" onclick="openMsgView(${JSON.stringify(m).replace(/"/g, '&quot;')})">
        <div class="msg-item-header">
          <span class="msg-item-from">From: ${escapeHtml(m.sender_name)}</span>
          <span class="msg-item-time">${_timeAgo(m.sent_at)}</span>
        </div>
        <div class="msg-item-subject">${escapeHtml(m.subject || '(no subject)')}</div>
        <div class="msg-item-preview">${escapeHtml(m.body)}</div>
      </div>`).join('');
  } catch(e) {
    list.innerHTML = '<div class="notif-empty">Failed to load inbox.</div>';
  }
}

// ── Sent tab ──────────────────────────────────────────────────────────────────

async function loadSent() {
  const list = document.getElementById('sentList');
  if (!list) return;
  list.innerHTML = '<div class="notif-empty">Loading...</div>';
  try {
    const msgs = await apiJson('/api/notifications/messages/sent');
    if (!msgs.length) {
      list.innerHTML = '<div class="notif-empty">No sent messages</div>';
      return;
    }
    list.innerHTML = msgs.map(m => {
      let toLabel = '';
      if (m.recipient_role) toLabel = `All ${m.recipient_role}s`;
      else if (m.recipient_dept) toLabel = `Dept: ${m.recipient_dept}`;
      else toLabel = 'Individual';
      return `
      <div class="msg-item" onclick="openMsgView(${JSON.stringify(m).replace(/"/g, '&quot;')})">
        <div class="msg-item-header">
          <span class="msg-item-from">To: ${escapeHtml(toLabel)}</span>
          <span class="msg-item-time">${_timeAgo(m.sent_at)}</span>
        </div>
        <div class="msg-item-subject">${escapeHtml(m.subject || '(no subject)')}</div>
        <div class="msg-item-preview">${escapeHtml(m.body)}</div>
      </div>`;
    }).join('');
  } catch(e) {
    list.innerHTML = '<div class="notif-empty">Failed to load sent messages.</div>';
  }
}

// ── Message view modal ────────────────────────────────────────────────────────

window.openMsgView = function(msg) {
  if (typeof msg === 'string') msg = JSON.parse(msg);
  document.getElementById('msgViewSubject').textContent = msg.subject || '(no subject)';
  document.getElementById('msgViewMeta').textContent = `From: ${msg.sender_name}  ·  ${new Date(msg.sent_at).toLocaleString()}`;
  document.getElementById('msgViewBody').textContent = msg.body;
  const modal = document.getElementById('msgViewModal');
  modal.style.display = 'flex';
  modal.classList.remove('hidden');
};

window.closeMsgViewModal = function() {
  const modal = document.getElementById('msgViewModal');
  modal.style.display = 'none';
  modal.classList.add('hidden');
};

// ── Compose modal ─────────────────────────────────────────────────────────────

window.openComposeModal = async function() {
  // Close notification panel first
  document.getElementById('notifPanel')?.classList.add('hidden');
  _notifPanelOpen = false;

  const modal = document.getElementById('composeModal');
  modal.style.display = 'flex';
  modal.classList.remove('hidden');
  document.getElementById('composeBody').value = '';
  document.getElementById('composeSubject').value = '';
  document.getElementById('composeRecipientPreview').textContent = '';
  document.getElementById('composeTargetType').value = 'user';
  onComposeTargetTypeChange();

  // Load recipients
  try {
    const users = await apiJson('/api/notifications/messages/recipients');
    _recipientsList = users;
    const sel = document.getElementById('composeTargetUser');
    sel.innerHTML = users.length
      ? users.map(u => `<option value="${u.id}">[${u.role.toUpperCase()}] ${escapeHtml(u.display_name)} (${escapeHtml(u.email || u.uid || '')})</option>`).join('')
      : '<option value="">No recipients available</option>';
    onComposeTargetTypeChange();
  } catch(e) {
    document.getElementById('composeTargetUser').innerHTML = '<option value="">Error loading users</option>';
  }

  // Populate dept options from active departments
  const deptSel = document.getElementById('composeTargetDept');
  if (deptSel) {
    try {
      const deptData = await apiJson('/api/auth/admin/departments');
      const depts = deptData.departments || ['CSE', 'ECE', 'ME', 'CE', 'EEE'];
      deptSel.innerHTML = depts.map(d => `<option value="${d}">${d}</option>`).join('');
    } catch(e) { /* use existing options */ }
  }

  if (typeof lucide !== 'undefined') lucide.createIcons();
};

window.closeComposeModal = function() {
  document.getElementById('composeModal').style.display = 'none';
  document.getElementById('composeModal').classList.add('hidden');
};

window.onComposeTargetTypeChange = function() {
  const type = document.getElementById('composeTargetType')?.value;
  const userSel = document.getElementById('composeTargetUser');
  const roleSel = document.getElementById('composeTargetRole');
  const deptSel = document.getElementById('composeTargetDept');
  if (!userSel || !roleSel || !deptSel) return;
  userSel.classList.toggle('hidden', type !== 'user');
  roleSel.classList.toggle('hidden', type !== 'role');
  deptSel.classList.toggle('hidden', type !== 'dept');

  // Update preview text
  const preview = document.getElementById('composeRecipientPreview');
  if (type === 'role') preview.textContent = '→ Will be sent to all users in the selected role group';
  else if (type === 'dept') preview.textContent = '→ Will be sent to all students & teachers in the selected department';
  else preview.textContent = '';
};

async function handleComposeSend(e) {
  e.preventDefault();
  const type = document.getElementById('composeTargetType').value;
  let targetValue = '';
  if (type === 'user') targetValue = document.getElementById('composeTargetUser').value;
  else if (type === 'role') targetValue = document.getElementById('composeTargetRole').value;
  else if (type === 'dept') targetValue = document.getElementById('composeTargetDept').value;

  if (!targetValue) { _showToast('Please select a recipient.', true); return; }

  const subject = document.getElementById('composeSubject').value;
  const body = document.getElementById('composeBody').value;
  if (!body.trim()) { _showToast('Message body is required.', true); return; }

  const btn = document.getElementById('composeSendBtn');
  btn.disabled = true;
  btn.textContent = 'Sending...';

  try {
    const res = await apiJson('/api/notifications/messages/send', {
      method: 'POST',
      body: { target_type: type, target_value: targetValue, subject, body }
    });
    closeComposeModal();
    _showToast(`✅ Message sent to ${res.recipients_count} recipient(s)!`);
    _pollUnreadCount();
  } catch(err) {
    _showToast('Failed to send: ' + err.message, true);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i data-lucide="send" style="width:14px;height:14px;"></i> Send Message';
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }
}

// ── Wire up after login ───────────────────────────────────────────────────────
// Store role globally so notification panel can access it
const _origInitForUser = window._initForUser;
document.addEventListener('DOMContentLoaded', () => {
  initNotificationPanel();
});

// Expose to be called from login success
window._startNotificationsForUser = function(role) {
  window._currentUserRole = role;
  startNotifPolling();
  const footer = document.getElementById('notifComposeFooter');
  if (footer) footer.style.display = (role === 'admin' || role === 'teacher') ? 'block' : 'none';
};

window._stopNotifications = function() {
  stopNotifPolling();
  window._currentUserRole = null;
};

