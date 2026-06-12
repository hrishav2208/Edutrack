with open('static/js/main.js', 'r', encoding='utf-8') as f:
    js = f.read()

edit_branch_js = r"""
// --- Edit Branch Logic ---
function populateDeptDropdowns(departments) {
  const deptOptions = departments.map(d => `<option value="${d}">${d}</option>`).join('');
  const teacherSel = document.getElementById('addTeacherDept');
  const studentSel = document.getElementById('addStudentDept');
  if (teacherSel) teacherSel.innerHTML = deptOptions;
  if (studentSel) studentSel.innerHTML = deptOptions;
}

window.openEditBranchModal = async function(type, id, currentDept) {
  const departments = activeDepartments.length ? activeDepartments : ['CSE', 'ECE', 'ME', 'CE', 'EEE'];
  const opts = departments.map((d, i) => `${i+1}. ${d}`).join('\n');
  const choice = prompt(`Select new department for this ${type}:\n\n${opts}\n\nType department name exactly:`, currentDept);
  if (!choice) return;
  const dept = choice.trim().toUpperCase();
  if (!departments.includes(dept)) {
    alert('Invalid department: ' + dept + '. Please type one of the listed options exactly.');
    return;
  }
  try {
    const url = type === 'teacher' ? `/api/directory/teachers/${id}/dept` : `/api/directory/students/${id}/dept`;
    await apiJson(url, { method: 'PATCH', body: { department: dept } });
    loadDirectoryAdmin();
  } catch(err) {
    alert('Failed to update department: ' + err.message);
  }
};
"""

if 'openEditBranchModal' not in js:
    idx = js.rfind('})()')
    if idx != -1:
        js = js[:idx] + edit_branch_js + '\n' + js[idx:]

with open('static/js/main.js', 'w', encoding='utf-8') as f:
    f.write(js)

print('Done')
