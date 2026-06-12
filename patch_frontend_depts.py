def patch_frontend():
    # 1. Update index.html
    with open('index.html', 'r', encoding='utf-8') as f:
        html = f.read()

    dept_ui = """
                <!-- Manage Departments -->
                <div class="card" id="admin-manage-depts" style="margin-top: 1.5rem;">
                    <div class="card-header">
                        <h3 class="card-title">Manage Departments</h3>
                    </div>
                    <div style="display: flex; gap: 0.5rem; margin-bottom: 1rem;">
                        <input type="text" id="newDeptInput" class="form-control" placeholder="e.g. AIML, IT, DS" style="max-width: 200px;">
                        <button class="btn btn-primary" onclick="addDepartment()">Add</button>
                    </div>
                    <div id="deptTagsContainer" style="display: flex; flex-wrap: wrap; gap: 0.5rem;">
                        <!-- Department tags will be loaded here -->
                    </div>
                </div>
"""
    if "admin-manage-depts" not in html:
        # Insert after the second chart-grid which contains Performance & Alerts
        # Find: <h3 class="card-title">Fee & Placement Status</h3> ... </div></div></div>
        # Or just append it right before the "Recent Alerts" card: <!-- Recent Alerts -->
        idx = html.find('<!-- Recent Alerts -->')
        if idx != -1:
            html = html[:idx] + dept_ui + html[idx:]
            with open('index.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print('Patched index.html with Department UI')
        else:
            print('Could not find Recent Alerts in index.html')

    # 2. Update main.js
    with open('static/js/main.js', 'r', encoding='utf-8') as f:
        js = f.read()

    dept_js = """
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
"""

    if "loadDepartments" not in js:
        # Insert right before the last })();
        idx = js.rfind('})();')
        if idx != -1:
            js = js[:idx] + dept_js + '\\n' + js[idx:]
            print('Patched main.js with Department JS')

    # Update initAdminCharts to be async and use activeDepartments
    old_init = "function initAdminCharts() {"
    new_init = "async function initAdminCharts() {"
    
    if old_init in js:
        js = js.replace(old_init, new_init)
        
        # Replace the hardcoded labels and data in performanceChart
        old_perf = """    performanceChart = new Chart(pc.getContext('2d'), {
      type: 'bar',
      data: {
        labels: ['CSE', 'ECE', 'ME', 'CE', 'EEE'],
        datasets: [
          {
            label: 'Avg attendance %',
            data: [94, 86, 81, 79, 88],
            backgroundColor: ['#3b6582', '#687787', '#3b9b58', '#cda174', '#5a84a6'],
          },
        ],
      },"""
        
        new_perf = """    await loadDepartments();
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
      },"""
        
        js = js.replace(old_perf, new_perf)
        
        with open('static/js/main.js', 'w', encoding='utf-8') as f:
            f.write(js)
        print('Patched initAdminCharts')

if __name__ == '__main__':
    patch_frontend()
