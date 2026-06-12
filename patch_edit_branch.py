import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Replace hardcoded Teacher dept select with a dynamically populated one
old_teacher_dept_select = '''<select id="addTeacherDept" class="select">
                                            <option value="CSE">Computer Science (CSE)</option>
                                            <option value="ECE">Electronics (ECE)</option>
                                            <option value="ME">Mechanical (ME)</option>
                                            <option value="CE">Civil (CE)</option>
                                            <option value="EEE">Electrical (EEE)</option>
                                            <option value="IT">Information Tech (IT)</option>
                                            <option value="General">General/Admin</option>
                                        </select>'''

new_teacher_dept_select = '''<select id="addTeacherDept" class="select">
                                            <option value="">Loading departments...</option>
                                        </select>'''

html = html.replace(old_teacher_dept_select, new_teacher_dept_select)

# 2. Replace hardcoded Student dept select with a dynamic one
old_student_dept_select = '''<select id="addStudentDept" class="select">
                                            <option value="CSE">Computer Science (CSE)</option>
                                            <option value="ECE">Electronics (ECE)</option>
                                            <option value="ME">Mechanical (ME)</option>
                                            <option value="CE">Civil (CE)</option>
                                            <option value="EEE">Electrical (EEE)</option>
                                            <option value="IT">Information Tech (IT)</option>
                                        </select>'''

new_student_dept_select = '''<select id="addStudentDept" class="select">
                                            <option value="">Loading departments...</option>
                                        </select>'''

html = html.replace(old_student_dept_select, new_student_dept_select)

# 3. Update Teachers table to add an Actions column
old_teachers_table_header = '<th>Name</th><th>Email</th><th>Dept</th><th>Salary/mo</th><th>Portal ID</th>'
new_teachers_table_header = '<th>Name</th><th>Email</th><th>Dept</th><th>Salary/mo</th><th>Portal ID</th><th>Actions</th>'
html = html.replace(old_teachers_table_header, new_teachers_table_header)

# 4. Update Students table to add an Actions column
old_students_table_header = '<th>Roll</th><th>Name</th><th>Dept</th><th>Email</th><th>Portal ID</th>'
new_students_table_header = '<th>Roll</th><th>Name</th><th>Dept</th><th>Email</th><th>Portal ID</th><th>Actions</th>'
html = html.replace(old_students_table_header, new_students_table_header)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Patched index.html successfully")
