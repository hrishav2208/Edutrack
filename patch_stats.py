import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace Total Students stat card
total_students_card = '''<div class="stat-card">
                        <div class="stat-content">
                            <div class="stat-info">
                                <p class="stat-label">Total Students</p>
                                <p class="stat-value" id="adminStatTotalStudents">2,847</p>
                            </div>
                            <div class="stat-icon primary">
                                <i data-lucide="users"></i>
                            </div>
                        </div>
                    </div>'''

clickable_students = total_students_card.replace(
    '<div class="stat-card">',
    '<div class="stat-card" style="cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform=\'translateY(-5px)\'" onmouseout="this.style.transform=\'none\'" onclick="viewDirectory(\'admin-students-card\')">'
)

html = html.replace(total_students_card, clickable_students)

# Replace Active Teachers stat card
active_teachers_card = '''<div class="stat-card">
                        <div class="stat-content">
                            <div class="stat-info">
                                <p class="stat-label">Active Teachers</p>
                                <p class="stat-value" id="adminStatActiveTeachers">156</p>
                            </div>
                            <div class="stat-icon success">
                                <i data-lucide="user-check"></i>
                            </div>
                        </div>
                    </div>'''

clickable_teachers = active_teachers_card.replace(
    '<div class="stat-card">',
    '<div class="stat-card" style="cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform=\'translateY(-5px)\'" onmouseout="this.style.transform=\'none\'" onclick="viewDirectory(\'admin-teachers-card\')">'
)

html = html.replace(active_teachers_card, clickable_teachers)

# Add ids to the h3 elements in the directory section
html = html.replace(
    '<h3 class="card-title">Teachers</h3>',
    '<h3 class="card-title" id="admin-teachers-card">Teachers</h3>'
)

html = html.replace(
    '<h3 class="card-title">Students</h3>',
    '<h3 class="card-title" id="admin-students-card">Students</h3>'
)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
