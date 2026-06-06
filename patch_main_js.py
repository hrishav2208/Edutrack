def patch_main():
    with open('static/js/main.js', 'r', encoding='utf-8') as f:
        js = f.read()

    # 1. Patch NAV
    old_nav = """  const NAV = {
    admin: [
      { id: 'admin-view-home', label: 'Home', icon: 'layout-dashboard' },
      { id: 'admin-view-people', label: 'Directory', icon: 'users' },
      { id: 'admin-view-fees', label: 'Fees', icon: 'wallet' },
      { id: 'admin-view-salary', label: 'Salaries', icon: 'banknote' },
      { id: 'admin-view-campus', label: 'Campus GPS', icon: 'map-pin' },
    ],"""
    new_nav = """  const NAV = {
    admin: [
      { id: 'admin-view-home', label: 'Home', icon: 'layout-dashboard' },
      { id: 'admin-view-people', label: 'Directory', icon: 'users' },
      { id: 'admin-view-fees', label: 'Fees', icon: 'wallet' },
      { id: 'admin-view-salary', label: 'Salaries', icon: 'banknote' },
      { id: 'admin-view-campus', label: 'Campus GPS', icon: 'map-pin' },
      { id: 'admin-view-otp', label: 'OTP Outbox', icon: 'inbox' },
    ],"""
    
    if old_nav in js:
        js = js.replace(old_nav, new_nav)
        print('Patched NAV array')

    # 2. Append renderOtpOutbox function
    if 'renderOtpOutbox' not in js:
        js += """

// Expose globally so inline onclick works
window.renderOtpOutbox = async function() {
  const tbody = document.getElementById('otpOutboxBody');
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="4" style="text-align: center;">Loading...</td></tr>`;
  try {
    const res = await apiFetch('/api/admin/otp-logs');
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
"""
        print('Appended renderOtpOutbox function')
        
    # 3. Call renderOtpOutbox when admin-view-otp is opened
    old_show = """if (sectionId === 'admin-view-home' && role === 'admin') requestAnimationFrame(() => initAdminCharts());"""
    new_show = """if (sectionId === 'admin-view-home' && role === 'admin') requestAnimationFrame(() => initAdminCharts());
    else if (sectionId === 'admin-view-otp' && role === 'admin') renderOtpOutbox();"""
    
    if old_show in js:
        js = js.replace(old_show, new_show)
        print('Patched showSection for OTP outbox')

    with open('static/js/main.js', 'w', encoding='utf-8') as f:
        f.write(js)

if __name__ == '__main__':
    patch_main()
