"""
EduTrack Documentation PDF Generator
Uses only Python's built-in capabilities + fpdf2 (will be auto-installed via pip)
"""
import subprocess, sys

# Install fpdf2 if not present
try:
    from fpdf import FPDF
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fpdf2"], stdout=subprocess.DEVNULL)
    from fpdf import FPDF

# ─── Color Palette ───────────────────────────────────────────────────────────
NAVY     = (30, 58, 90)
STEEL    = (74, 107, 138)
TEAL     = (59, 155, 88)
GOLD     = (205, 161, 116)
RED      = (220, 82, 82)
LIGHT_BG = (245, 248, 251)
WHITE    = (255, 255, 255)
DARK     = (30, 40, 55)
MID_GRAY = (100, 116, 140)
BORDER   = (220, 228, 236)


def S(text):
    """Sanitize text: replace common Unicode chars with latin-1-safe equivalents."""
    replacements = {
        '\u2014': '--',   # em dash
        '\u2013': '-',    # en dash
        '\u2018': "'",    # left single quote
        '\u2019': "'",    # right single quote
        '\u201c': '"',    # left double quote
        '\u201d': '"',    # right double quote
        '\u2022': '*',    # bullet
        '\u2026': '...',  # ellipsis
        '\u00a0': ' ',    # non-breaking space
        '\u2192': '->',   # right arrow
        '\u2190': '<-',   # left arrow
        '\u00b7': '*',    # middle dot
        '\u2122': '(TM)', # trademark
        '\u00ae': '(R)',  # registered
        '\u00a9': '(C)',  # copyright
        '\u00e2': 'a',
        '\u0080': '',
        '\u0099': '',
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    # Final safety: encode to latin-1, replacing unknowns
    return text.encode('latin-1', errors='replace').decode('latin-1')


class EduDoc(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(left=18, top=18, right=18)

    def normalize_text(self, text):
        """Override to sanitize unicode before fpdf encodes it."""
        return super().normalize_text(S(str(text)))

    # ── Page header / footer ──────────────────────────────────────────────────
    def header(self):
        if self.page_no() == 1:
            return
        # Thin top bar
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 8, 'F')
        self.set_y(10)
        self.set_font('Helvetica', 'B', 8)
        self.set_text_color(*WHITE)
        self.cell(0, 5, '  EduTrack — College Management System  |  Technical Documentation', align='L')
        self.set_text_color(*DARK)
        self.ln(6)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-13)
        self.set_fill_color(*LIGHT_BG)
        self.rect(0, 284, 210, 13, 'F')
        self.set_font('Helvetica', '', 8)
        self.set_text_color(*MID_GRAY)
        self.cell(0, 8, f'Page {self.page_no()}  |  EduTrack v1.0  |  Confidential', align='C')
        self.set_text_color(*DARK)

    # ── Helper primitives ─────────────────────────────────────────────────────
    def colored_rect(self, x, y, w, h, color, style='F'):
        self.set_fill_color(*color)
        self.rect(x, y, w, h, style)

    def section_title(self, txt):
        self.ln(4)
        y = self.get_y()
        # Left accent bar
        self.set_fill_color(*STEEL)
        self.rect(18, y, 3, 8, 'F')
        self.set_x(24)
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(*NAVY)
        self.cell(0, 8, S(txt))
        self.ln(4)
        # Divider line
        self.set_draw_color(*BORDER)
        self.line(18, self.get_y(), 192, self.get_y())
        self.ln(4)
        self.set_text_color(*DARK)

    def sub_heading(self, txt):
        self.ln(2)
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(*STEEL)
        self.cell(0, 7, S(txt))
        self.ln(5)
        self.set_text_color(*DARK)

    def body(self, txt):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(*DARK)
        self.multi_cell(0, 5.5, S(txt))
        self.ln(2)

    def bullet(self, items):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(*DARK)
        for item in items:
            self.set_x(22)
            self.cell(5, 5.5, chr(149))   # bullet dot
            self.multi_cell(0, 5.5, S(item))
        self.ln(1)

    def info_box(self, title, color, items):
        """Colored info box with title and bullet list."""
        y = self.get_y()
        self.set_fill_color(*color)
        self.set_draw_color(*color)
        self.rect(18, y, 174, 7, 'F')
        self.set_x(20)
        self.set_y(y)
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(*WHITE)
        self.cell(0, 7, S(f'  {title}'))
        self.ln(8)
        self.set_text_color(*DARK)
        for item in items:
            self.set_x(22)
            self.set_font('Helvetica', '', 9.5)
            self.cell(4, 5, '-')
            self.multi_cell(0, 5, S(item))
        self.ln(2)

    def table(self, headers, rows, col_widths):
        """Simple shaded table."""
        # Header row
        self.set_fill_color(*NAVY)
        self.set_text_color(*WHITE)
        self.set_font('Helvetica', 'B', 9)
        x = 18
        for i, h in enumerate(headers):
            self.set_xy(x, self.get_y())
            self.cell(col_widths[i], 7, S(f' {h}'), border=0, fill=True)
            x += col_widths[i]
        self.ln(7)
        # Data rows
        self.set_font('Helvetica', '', 9)
        shade = False
        for row in rows:
            if shade:
                self.set_fill_color(*LIGHT_BG)
            else:
                self.set_fill_color(*WHITE)
            self.set_text_color(*DARK)
            x = 18
            for i, cell in enumerate(row):
                self.set_xy(x, self.get_y())
                self.cell(col_widths[i], 6, S(f' {cell}'), border=0, fill=True)
                x += col_widths[i]
            self.ln(6)
            shade = not shade
        # Bottom border
        self.set_draw_color(*BORDER)
        self.line(18, self.get_y(), 192, self.get_y())
        self.ln(3)

    def code_box(self, code_text):
        """Monospace light-background code block."""
        self.set_fill_color(235, 240, 246)
        self.set_draw_color(*BORDER)
        lines = S(code_text).strip().split('\n')
        h = len(lines) * 5 + 6
        y = self.get_y()
        self.rect(18, y, 174, h, 'FD')
        self.set_font('Courier', '', 8.5)
        self.set_text_color(40, 60, 80)
        self.set_xy(21, y + 3)
        for line in lines:
            self.set_x(21)
            self.cell(0, 5, S(line))
            self.ln(5)
        self.set_text_color(*DARK)
        self.ln(3)


# ─── BUILD PDF ────────────────────────────────────────────────────────────────

def build():
    doc = EduDoc()

    # ═══════════════════════════════════════════════════════════════
    # COVER PAGE
    # ═══════════════════════════════════════════════════════════════
    doc.add_page()

    # Top gradient bar
    doc.set_fill_color(*NAVY)
    doc.rect(0, 0, 210, 60, 'F')
    doc.set_fill_color(*STEEL)
    doc.rect(0, 55, 210, 8, 'F')

    doc.set_y(14)
    doc.set_font('Helvetica', 'B', 36)
    doc.set_text_color(*WHITE)
    doc.cell(0, 14, 'EduTrack', align='C')
    doc.ln(16)
    doc.set_font('Helvetica', '', 16)
    doc.cell(0, 8, 'College Management System', align='C')
    doc.ln(10)
    doc.set_font('Helvetica', 'B', 10)
    doc.set_fill_color(*GOLD)
    doc.rect(65, doc.get_y(), 80, 8, 'F')
    doc.set_text_color(*NAVY)
    doc.cell(0, 8, 'Full Technical Documentation  v1.0', align='C')

    # Summary card
    doc.set_y(82)
    doc.set_fill_color(*WHITE)
    doc.rect(22, 82, 166, 80, 'FD')
    doc.set_fill_color(*TEAL)
    doc.rect(22, 82, 4, 80, 'F')

    doc.set_y(90)
    doc.set_x(32)
    doc.set_font('Helvetica', 'B', 13)
    doc.set_text_color(*NAVY)
    doc.cell(0, 8, 'What is EduTrack?')
    doc.ln(9)
    doc.set_x(32)
    doc.set_font('Helvetica', '', 10)
    doc.set_text_color(*DARK)
    doc.multi_cell(150, 5.5,
        'EduTrack is a full-stack college management web application built with '
        'Python (Flask) on the backend and vanilla HTML/CSS/JavaScript on the frontend. '
        'It provides a centralised portal for four distinct user roles — Admin, Teacher, '
        'Student, and Parent — each with a personalised dashboard, live notifications, '
        'and full database persistence using SQLite (dev) or PostgreSQL (prod).')
    doc.ln(4)
    doc.set_x(32)
    doc.set_font('Helvetica', 'B', 10)
    doc.set_text_color(*STEEL)
    doc.cell(0, 6, 'Key Highlights:')
    doc.ln(7)
    highlights = [
        'Role-based login with Portal IDs, OTP email reset, and biometric stub',
        'GPS-based classroom geofencing with live session check-in',
        'Real-time in-app messaging & notification system (polling every 30s)',
        'Full CRUD for Teachers, Students, and Parents with auto-UID generation',
        'Finance module: fee structures, payments, salary disbursements',
        'Marks entry & auto-notification to students and parents',
        'Docker-ready with Gunicorn production server support',
    ]
    doc.set_font('Helvetica', '', 9.5)
    doc.set_text_color(*DARK)
    for h in highlights:
        doc.set_x(32)
        doc.cell(5, 5.5, chr(149))
        doc.cell(0, 5.5, h)
        doc.ln(5.5)

    # Bottom metadata
    doc.set_y(188)
    doc.set_fill_color(*LIGHT_BG)
    doc.rect(18, 188, 174, 28, 'F')
    doc.set_y(193)
    meta = [
        ('Tech Stack', 'Python 3.11 · Flask 3 · SQLAlchemy · SQLite / PostgreSQL · Vanilla JS'),
        ('Frontend', 'Single-Page Application (SPA) · Lucide Icons · Chart.js · CSS Custom Properties'),
        ('Auth', 'Session-based · Portal UID / Email login · OTP via EmailJS · Biometric stub'),
        ('Deployment', 'Gunicorn + Docker · GitHub repository'),
    ]
    doc.set_font('Helvetica', '', 9)
    doc.set_text_color(*MID_GRAY)
    for label, val in meta:
        doc.set_x(22)
        doc.set_font('Helvetica', 'B', 9)
        doc.set_text_color(*NAVY)
        doc.cell(32, 5.5, label + ':')
        doc.set_font('Helvetica', '', 9)
        doc.set_text_color(*DARK)
        doc.cell(0, 5.5, val)
        doc.ln(5.5)

    doc.set_y(235)
    doc.set_fill_color(*NAVY)
    doc.rect(0, 235, 210, 62, 'F')

    toc = [
        ('1', 'Project Structure & File Map'),
        ('2', 'How The App Starts (Application Factory)'),
        ('3', 'Database: Models & Tables'),
        ('4', 'Authentication & User Roles'),
        ('5', 'API Blueprint Reference'),
        ('6', 'Directory & UID Auto-Generation'),
        ('7', 'Attendance System (Manual + GPS Session)'),
        ('8', 'Finance Module'),
        ('9', 'Marks & Notifications'),
        ('10', 'In-App Messaging System'),
        ('11', 'Frontend Architecture (SPA)'),
        ('12', 'Deployment & Running Locally'),
    ]
    doc.set_y(240)
    doc.set_font('Helvetica', 'B', 11)
    doc.set_text_color(*GOLD)
    doc.cell(0, 7, '  Table of Contents', align='L')
    doc.ln(9)
    doc.set_font('Helvetica', '', 9)
    doc.set_text_color(*WHITE)
    col = 0
    for no, title in toc:
        x = 22 if col == 0 else 112
        doc.set_xy(x, doc.get_y())
        doc.cell(85, 5, f'  {no}.  {title}')
        col += 1
        if col == 2:
            col = 0
            doc.ln(5)

    # ═══════════════════════════════════════════════════════════════
    # PAGE 2 — PROJECT STRUCTURE
    # ═══════════════════════════════════════════════════════════════
    doc.add_page()
    doc.section_title('1. Project Structure & File Map')

    doc.body(
        'EduTrack follows the Flask Application Factory pattern. All Python '
        'application code lives inside the app/ package, while static assets and '
        'the single-page HTML shell live at the project root / static folder.'
    )

    doc.code_box(
        'Edutrack/\n'
        '  app/                   # Flask application package\n'
        '    __init__.py          # Application Factory — create_app()\n'
        '    models.py            # All SQLAlchemy DB models\n'
        '    auth.py              # Login, logout, OTP, biometric endpoints\n'
        '    directory.py         # Teacher / Student / Parent CRUD\n'
        '    attendance.py        # Manual attendance + GPS live session\n'
        '    marks.py             # Grade entry and retrieval\n'
        '    finance.py           # Fee structures, payments, salaries\n'
        '    notifications.py     # Alerts + in-app messaging API\n'
        '    curriculum.py        # Curriculum file upload/download\n'
        '    reports.py           # Admin stats & report aggregations\n'
        '    profile.py           # User profile management\n'
        '    config.py            # Config classes (Dev / Prod)\n'
        '    face_recognition.py  # GPS Haversine + face stub helpers\n'
        '  static/\n'
        '    css/style.css        # All app styling (2500+ lines)\n'
        '    js/main.js           # Full SPA logic (~2700 lines)\n'
        '    js/sw.js             # Service Worker (PWA offline cache)\n'
        '    manifest.json        # PWA manifest\n'
        '  index.html             # Single HTML shell (all views in DOM)\n'
        '  wsgi.py                # Entry point for Gunicorn / python run\n'
        '  requirements.txt       # Python dependencies\n'
        '  Dockerfile             # Docker build instructions\n'
        '  docker-compose.yml     # Multi-service docker setup\n'
        '  .env                   # Secret keys (not committed to git)\n'
    )

    doc.sub_heading('How Requests Flow')
    doc.body(
        'Browser → index.html (loaded once) → JavaScript makes fetch() API calls → '
        'Flask blueprint routes → SQLAlchemy ORM → SQLite database → '
        'JSON response → JavaScript updates the DOM without page refresh.'
    )

    # ═══════════════════════════════════════════════════════════════
    # PAGE — APPLICATION FACTORY
    # ═══════════════════════════════════════════════════════════════
    doc.add_page()
    doc.section_title('2. How The App Starts (Application Factory Pattern)')

    doc.body(
        'The entire Flask application is created inside the create_app() function '
        'in app/__init__.py. This pattern avoids circular imports and allows '
        'the same codebase to run in dev, production, or test modes simply by '
        'changing the FLASK_ENV environment variable.'
    )

    doc.sub_heading('Step-by-Step Startup Sequence')
    doc.bullet([
        'FLASK_ENV is read → selects Dev or Prod config (config.py)',
        'Flask() object is created with the static folder path',
        'SQLAlchemy db.init_app(app) is called — connects ORM to the app',
        'Flask-Migrate migrate.init_app(app, db) is called — handles schema versioning',
        'All Blueprints are imported and registered with URL prefixes (e.g., /api/auth)',
        'Within app context: db.create_all() creates tables if they do not exist',
        'Auto-migration block runs: ALTER TABLE for new columns on existing DBs',
        'seed_database(app) is called — inserts demo data on first run only',
        'The / route is registered to serve index.html',
    ])

    doc.sub_heading('Registered Blueprints & Their URL Prefixes')
    doc.table(
        ['Blueprint', 'File', 'URL Prefix', 'Purpose'],
        [
            ['auth_bp', 'auth.py', '/api/auth', 'Login, logout, OTP, biometric'],
            ['attendance_bp', 'attendance.py', '/api/attendance', 'Attendance management'],
            ['directory_bp', 'directory.py', '/api/directory', 'People CRUD'],
            ['finance_bp', 'finance.py', '/api/finance', 'Fees & salaries'],
            ['marks_bp', 'marks.py', '/api/marks', 'Grades'],
            ['notifications_bp', 'notifications.py', '/api/notifications', 'Alerts & messages'],
            ['curriculum_bp', 'curriculum.py', '/api/curriculum', 'File uploads'],
            ['reports_bp', 'reports.py', '/api/reports', 'Admin analytics'],
            ['profile_bp', 'profile.py', '/api/profile', 'User profile'],
        ],
        [28, 28, 38, 80]
    )

    doc.sub_heading('Auto-Migration System')
    doc.body(
        'Because the database is SQLite in development and may already have data, '
        'a custom auto-migration block uses SQLAlchemy\'s inspect() to check existing '
        'columns and runs raw ALTER TABLE SQL if a new column is missing. This means '
        'you never lose data when a new feature adds a column.'
    )

    doc.sub_heading('Seed Data (First-Run Only)')
    doc.body(
        'If the users table is empty, seed_database() inserts 9 demo profiles — '
        '1 admin, 3 teachers, 2 students, 2 parents, plus campus settings, '
        'fee structures, a sample mark, and a salary disbursement. '
        'All demo passwords are demo123.'
    )

    # ═══════════════════════════════════════════════════════════════
    # PAGE — DATABASE MODELS
    # ═══════════════════════════════════════════════════════════════
    doc.add_page()
    doc.section_title('3. Database: Models & Tables')

    doc.body(
        'All database tables are defined using SQLAlchemy ORM in app/models.py. '
        'SQLite is used automatically in development. For production, set the '
        'DATABASE_URL environment variable to a PostgreSQL connection string.'
    )

    tables = [
        ('users', 'Central login table. Holds email, password hash, role, and foreign keys to teacher/student/parent rows. Also stores Portal UID, OTP fields.'),
        ('teachers', 'Teacher profile: name, email, department, monthly salary, phone numbers, DOB, blood group, profile picture.'),
        ('students', 'Student profile: roll number, name, email, department, parent link, contact fields, placement flag.'),
        ('parents', 'Parent profile: name, email, phone, contact fields.'),
        ('notifications', 'One notification row per user per event. Has title, message, type (info/success/warning/danger), and is_read flag.'),
        ('messages', 'In-app messages. Sender → recipient (individual, role group, or department). Links to notifications for bell badge.'),
        ('attendance_records', 'One record per student per course per date. Includes method: manual, gps_face, gps_session, biometric, qr.'),
        ('class_sessions', 'Live GPS classroom session started by a teacher. Stores lat/lng/radius and lifecycle timestamps.'),
        ('session_checkins', 'Each GPS ping or initial check-in during a live session. Stores distance and inside_radius flag.'),
        ('marks', 'Grade entry: student, teacher, course code, exam title, score, max_score.'),
        ('fee_structures', 'Programme fee items (tuition, lab etc.) per academic year.'),
        ('fee_payments', 'Payment record: which student paid, which structure, amount, date.'),
        ('salary_disbursements', 'Monthly teacher salary records: gross, deductions, net.'),
        ('campus_settings', 'Single row (id=1): campus GPS coordinates, radius, departments JSON list.'),
        ('academic_events', 'Calendar events: title, date, type (calendar / event).'),
        ('exam_schedules', 'Upcoming exam rows: course code, title, date.'),
    ]

    doc.set_font('Helvetica', 'B', 9)
    doc.set_fill_color(*NAVY)
    doc.set_text_color(*WHITE)
    doc.set_xy(18, doc.get_y())
    doc.cell(38, 7, ' Table Name', fill=True, border=0)
    doc.cell(136, 7, ' Description', fill=True, border=0)
    doc.ln(7)

    shade = False
    doc.set_font('Helvetica', '', 9)
    for name, desc in tables:
        bg = LIGHT_BG if shade else WHITE
        doc.set_fill_color(*bg)
        doc.set_text_color(*STEEL)
        doc.set_xy(18, doc.get_y())
        doc.cell(38, 6, f' {name}', fill=True)
        doc.set_text_color(*DARK)
        doc.multi_cell(136, 6, f' {desc}', fill=True)
        shade = not shade

    doc.ln(2)
    doc.info_box('Key Relationships', STEEL, [
        'users.teacher_id  →  teachers.id  (FK)',
        'users.student_id  →  students.id  (FK)',
        'users.parent_id   →  parents.id   (FK)',
        'students.parent_id  →  parents.id  (FK, optional)',
        'marks: student_id → students.id,  teacher_id → teachers.id',
        'attendance_records: student_id → students.id',
        'messages: sender_id → users.id,  recipient_id → users.id (nullable for broadcast)',
    ])

    # ═══════════════════════════════════════════════════════════════
    # PAGE — AUTH
    # ═══════════════════════════════════════════════════════════════
    doc.add_page()
    doc.section_title('4. Authentication & User Roles')

    doc.sub_heading('Login Methods')
    doc.bullet([
        'Password Login: POST /api/auth/login with identifier (Portal UID or email) + password. '
          'Uses werkzeug.security.check_password_hash. Sets Flask session["user_id"].',
        'OTP Login: POST /api/auth/request-otp → generates 6-digit OTP, stores hash+expiry '
          'on the User row, sends via EmailJS API. POST /api/auth/verify-otp-login to log in.',
        'Biometric Login (Stub): POST /api/auth/biometric/login with identifier. '
          'In demo mode this always succeeds. Real WebAuthn would replace the stub.',
        'Password Reset: request-otp → verify OTP → POST /api/auth/reset-password with new password.',
    ])

    doc.sub_heading('Four User Roles')
    roles_data = [
        ('admin', 'Full system access. Can view all users, manage fees, salaries, campus GPS, OTP logs, departments, and send messages to anyone.'),
        ('teacher', 'Can manage attendance for their classes, grade students, view salary slips, and send messages to students/parents.'),
        ('student', 'Can view own marks, attendance %, curriculum files, and check in to live GPS sessions.'),
        ('parent', 'Can view child\'s fee payment records and receive notifications about attendance/marks.'),
    ]
    for role, desc in roles_data:
        doc.set_fill_color(*LIGHT_BG)
        doc.set_draw_color(*BORDER)
        y = doc.get_y()
        doc.rect(18, y, 174, 12, 'FD')
        doc.set_xy(20, y + 1)
        doc.set_font('Helvetica', 'B', 10)
        doc.set_text_color(*NAVY)
        doc.cell(25, 5, role.upper())
        doc.set_font('Helvetica', '', 9.5)
        doc.set_text_color(*DARK)
        doc.set_x(44)
        doc.multi_cell(142, 5, desc)
        doc.ln(3)

    doc.sub_heading('Session Management')
    doc.body(
        'Flask\'s server-side session stores the user_id. The require_login() helper '
        'function (in auth.py) is called at the top of every protected route. '
        'It reads session["user_id"], looks up the User row, and returns the user '
        'object or a 401 JSON error. The JavaScript frontend always calls '
        '/api/auth/me on page load to restore state.'
    )

    doc.sub_heading('Portal UID Format')
    doc.table(
        ['Role', 'Pattern', 'Example'],
        [
            ['Teacher', 'EMP-{DEPT}{YY}{NAME3}{SEQ}', 'EMP-CSE26SAR001'],
            ['Student', 'STU-{DEPT}{YY}{NAME3}{SEQ}', 'STU-CSE26ALE001'],
            ['Parent', 'PAR-{YY}{NAME3}{SEQ}', 'PAR-26MRS001'],
        ],
        [30, 65, 79]
    )
    doc.body(
        'UIDs are generated in directory.py using regex helpers. The sequence '
        'number is determined by counting how many existing UIDs share the same prefix, '
        'then zero-padding to 3 digits. This guarantees uniqueness without a separate counter.'
    )

    # ═══════════════════════════════════════════════════════════════
    # PAGE — API REFERENCE
    # ═══════════════════════════════════════════════════════════════
    doc.add_page()
    doc.section_title('5. API Blueprint Reference — All Endpoints')

    apis = [
        ('AUTH', '/api/auth', [
            ('POST', '/login', 'Login with identifier + password'),
            ('POST', '/logout', 'Clear session'),
            ('GET',  '/me', 'Get current logged-in user'),
            ('POST', '/request-otp', 'Send OTP to email'),
            ('POST', '/verify-otp-login', 'Login via OTP code'),
            ('POST', '/reset-password', 'Reset password after OTP verify'),
            ('POST', '/biometric/challenge', 'Get WebAuthn challenge'),
            ('POST', '/biometric/verify', 'Complete biometric auth'),
            ('POST', '/biometric/login', 'Passwordless biometric login'),
            ('GET',  '/admin/otp-logs', 'View active OTPs (admin only)'),
            ('GET',  '/admin/departments', 'Get department list'),
            ('POST', '/admin/departments', 'Update department list'),
        ]),
        ('DIRECTORY', '/api/directory', [
            ('GET',  '/teachers', 'List all teachers'),
            ('POST', '/teachers', 'Add new teacher + auto-create user'),
            ('PATCH','/teachers/<id>', 'Edit teacher full profile'),
            ('DELETE','/teachers/<id>', 'Delete teacher + cascade user'),
            ('GET',  '/students', 'List all students'),
            ('POST', '/students', 'Add new student'),
            ('PATCH','/students/<id>', 'Edit student full profile'),
            ('DELETE','/students/<id>', 'Delete student'),
            ('GET',  '/parents', 'List all parents'),
            ('POST', '/parents', 'Add new parent'),
            ('PATCH','/parents/<id>', 'Edit parent profile'),
            ('DELETE','/parents/<id>', 'Delete parent'),
        ]),
        ('ATTENDANCE', '/api/attendance', [
            ('GET',  '/campus', 'Get campus GPS settings'),
            ('PUT',  '/campus', 'Update campus GPS (admin)'),
            ('POST', '/verify-location', 'Check if coordinates are inside campus'),
            ('GET',  '/manual', 'Get attendance roster for course+date'),
            ('POST', '/manual', 'Save bulk attendance entries'),
            ('POST', '/mark-combined', 'Student self-mark (GPS + face)'),
            ('POST', '/session/start', 'Teacher starts a live GPS session'),
            ('POST', '/session/end', 'Teacher ends the live session'),
            ('GET',  '/session/active', 'Get currently active session(s)'),
            ('POST', '/session/checkin', 'Student checks in to live session'),
            ('POST', '/session/ping', 'Background GPS ping from student'),
        ]),
        ('NOTIFICATIONS', '/api/notifications', [
            ('GET',  '/list', 'Get all notifications for current user'),
            ('GET',  '/unread-count', 'Get count of unread notifications (badge polling)'),
            ('POST', '/mark-read', 'Mark one or all notifications as read'),
            ('POST', '/messages/send', 'Send a message (admin/teacher only)'),
            ('GET',  '/messages/inbox', 'Get received messages'),
            ('GET',  '/messages/sent', 'Get sent messages'),
            ('POST', '/messages/mark-read/<id>', 'Mark a message as read'),
            ('GET',  '/messages/recipients', 'Get list of sendable users'),
        ]),
        ('FINANCE', '/api/finance', [
            ('GET',  '/fee-structures', 'List fee structures'),
            ('POST', '/fee-structures', 'Add fee structure (admin)'),
            ('GET',  '/fee-payments', 'List payments (role-filtered)'),
            ('POST', '/fee-payments', 'Record a payment (admin)'),
            ('GET',  '/salaries', 'List salary records'),
            ('POST', '/salaries', 'Disburse salary (admin)'),
        ]),
        ('MARKS', '/api/marks', [
            ('GET',  '/list', 'Get marks (role-filtered)'),
            ('POST', '/add', 'Add grade + notify student/parent'),
        ]),
    ]

    for section_name, prefix, endpoints in apis:
        doc.set_fill_color(*NAVY)
        y = doc.get_y()
        doc.rect(18, y, 174, 7, 'F')
        doc.set_xy(20, y)
        doc.set_font('Helvetica', 'B', 9)
        doc.set_text_color(*WHITE)
        doc.cell(40, 7, section_name)
        doc.set_font('Helvetica', '', 9)
        doc.cell(0, 7, prefix)
        doc.ln(7)

        shade = False
        for method, path, desc in endpoints:
            bg = LIGHT_BG if shade else WHITE
            doc.set_fill_color(*bg)
            doc.set_xy(18, doc.get_y())
            method_color = {'GET': TEAL, 'POST': STEEL, 'PATCH': GOLD, 'DELETE': RED, 'PUT': GOLD}.get(method, DARK)
            doc.set_text_color(*method_color)
            doc.set_font('Helvetica', 'B', 8)
            doc.cell(16, 5.5, f' {method}', fill=True)
            doc.set_text_color(*NAVY)
            doc.set_font('Helvetica', 'B', 8.5)
            doc.cell(58, 5.5, path, fill=True)
            doc.set_text_color(*DARK)
            doc.set_font('Helvetica', '', 8.5)
            doc.cell(100, 5.5, desc, fill=True)
            doc.ln(5.5)
            shade = not shade
        doc.ln(3)

    # ═══════════════════════════════════════════════════════════════
    # PAGE — ATTENDANCE DEEP DIVE
    # ═══════════════════════════════════════════════════════════════
    doc.add_page()
    doc.section_title('7. Attendance System — Deep Dive')

    doc.sub_heading('A. Manual Attendance (Teacher)')
    doc.body(
        'Teachers open the Attendance tab, pick a course code and date, and see '
        'a roster of all students. They toggle each student Present/Absent and click Save. '
        'The frontend sends a POST /api/attendance/manual with an array of entries.'
    )
    doc.body(
        'If a student is marked absent, the system automatically creates two Notification '
        'rows — one for the student, one for their linked parent — with type "danger".'
    )

    doc.sub_heading('B. GPS + Face Recognition Self-Marking (Student)')
    doc.bullet([
        'Student clicks "Mark Attendance" → browser requests GPS coordinates.',
        'POST /api/attendance/mark-combined sends lat/lng + selfie image.',
        'Server computes Haversine distance between student and campus GPS point.',
        'If distance > campus radius → rejected with "Outside campus boundary" error.',
        'If inside radius → face image is checked by verify_face_stub() (demo: always passes).',
        'On success → AttendanceRecord is upserted. Student gets a "Attendance Marked" notification.',
    ])

    doc.sub_heading('C. Live GPS Classroom Session (Teacher + Students)')
    doc.body('This is the most advanced attendance feature. Here is the full flow:')
    steps = [
        '1. Teacher opens their GPS session panel and clicks "Start Session".',
        '2. Browser gets teacher GPS → POST /api/attendance/session/start.',
        '3. Server creates a ClassSession row with teacher lat/lng/radius (default 20m).',
        '4. All students receive a "Class Started" notification immediately.',
        '5. Student opens app, sees session banner → clicks "Check In".',
        '6. Browser gets student GPS + captures selfie → POST /api/attendance/session/checkin.',
        '7. Server checks: is student within session radius? Is face present? If yes → SessionCheckIn row (type=initial).',
        '8. After check-in, JS starts background random pings every 2–5 minutes.',
        '9. Each ping sends GPS only (no photo) to POST /api/attendance/session/ping.',
        '10. If student is found outside the radius during a ping → teacher gets a "Student Left" warning notification.',
        '11. Teacher clicks "End Session" → POST /api/attendance/session/end.',
        '12. Server counts unique students with inside_radius=True check-ins → saves to AttendanceRecord.',
    ]
    doc.set_font('Helvetica', '', 9.5)
    doc.set_text_color(*DARK)
    for s in steps:
        doc.set_x(20)
        doc.multi_cell(170, 5.5, s)
    doc.ln(2)

    doc.sub_heading('Haversine Distance Formula')
    doc.body(
        'The haversine_m() function in face_recognition.py computes great-circle distance '
        'between two GPS coordinates (lat/lng) in metres. This is the standard formula used '
        'for GPS boundary checks — it accounts for Earth\'s curvature correctly over short distances.'
    )

    # ═══════════════════════════════════════════════════════════════
    # PAGE — MESSAGING SYSTEM
    # ═══════════════════════════════════════════════════════════════
    doc.add_page()
    doc.section_title('10. In-App Messaging & Notification System')

    doc.sub_heading('Notification Bell (All Users)')
    doc.body(
        'Every user has a notification bell in the top navigation bar. '
        'Every 30 seconds, the JavaScript polls GET /api/notifications/unread-count. '
        'If count > 0, the badge shows the number and pulses with a CSS animation. '
        'Clicking the bell opens a glassmorphism dropdown panel with three tabs.'
    )

    doc.table(
        ['Tab', 'Who Sees It', 'Contents'],
        [
            ['Alerts', 'Everyone', 'System notifications (absent alert, new marks, class started, etc.)'],
            ['Inbox', 'Everyone', 'Direct messages and broadcast messages received'],
            ['Sent', 'Admin / Teacher', 'All messages sent by this user'],
        ],
        [28, 38, 108]
    )

    doc.sub_heading('Sending Messages (Admin + Teacher Only)')
    doc.body('A "Compose" button appears in the panel footer for admin and teacher users. It opens a modal with three targeting modes:')
    doc.bullet([
        'Individual — pick a specific user from a dropdown (role-labeled)',
        'Role Group — message all students, all teachers, all parents, or everyone',
        'Department — message all students + teachers in a specific department',
    ])
    doc.body(
        'When a message is sent, the backend fans out: it creates a Notification row '
        'for every recipient. This means the bell badge lights up for each recipient '
        'within the next 30-second poll cycle.'
    )

    doc.sub_heading('Teacher Restrictions')
    doc.body(
        'Teachers can only message students and parents. They cannot message other '
        'teachers or administrators. This restriction is enforced on the backend in '
        '/api/notifications/messages/send and on the frontend recipient dropdown.'
    )

    doc.sub_heading('Auto-Generated Notifications')
    doc.body('The following actions automatically create notification rows in the database:')
    doc.table(
        ['Action', 'Who Gets Notified', 'Type'],
        [
            ['Teacher marks student absent', 'Student + Parent', 'danger (red)'],
            ['Teacher adds marks', 'Student + Parent', 'success / info'],
            ['Teacher starts GPS session', 'All students', 'info'],
            ['Student checks in successfully', 'Student only', 'success'],
            ['Student pings outside classroom', 'Teacher', 'warning'],
            ['Admin/Teacher sends a message', 'All recipients', 'info'],
        ],
        [65, 55, 54]
    )

    # ═══════════════════════════════════════════════════════════════
    # PAGE — FRONTEND SPA
    # ═══════════════════════════════════════════════════════════════
    doc.add_page()
    doc.section_title('11. Frontend Architecture — Single-Page Application')

    doc.sub_heading('How It Works')
    doc.body(
        'EduTrack is a Single-Page Application (SPA). The browser loads index.html '
        'exactly once. All views — login screen, dashboards, modals — are already in '
        'the HTML DOM, just hidden with CSS class "hidden". JavaScript toggles '
        'visibility to simulate navigation without page reloads.'
    )

    doc.sub_heading('main.js Structure (inside an IIFE)')
    doc.code_box(
        '(function() {\n'
        '  "use strict";\n'
        '\n'
        '  // Constants\n'
        '  const NAV = { admin: [...], teacher: [...], student: [...], parent: [...] };\n'
        '  const DASH_MAP = { admin: "adminDashboard", teacher: "teacherDashboard", ... };\n'
        '\n'
        '  // State\n'
        '  let state = { user: null, apiOnline: false, role: null };\n'
        '\n'
        '  // Core helpers: apiFetch(), apiJson(), tryApi(), escapeHtml()\n'
        '  // Chart helpers: initAdminCharts(), destroyCharts()\n'
        '  // Render functions: renderStudentTableFromApi(), loadDirectoryAdmin(), ...\n'
        '  // Section loaders: loadFeesAdmin(), loadSalaryAdmin(), ...\n'
        '  // Attendance: startClassSession(), endClassSession(), checkActiveSessionStudent()\n'
        '  // Navigation: buildNav(), showDashboard(), hideDashboard()\n'
        '  // Event listeners: loginForm.submit, logoutBtn.click, ...\n'
        '\n'
        '  // App init: DOMContentLoaded → tryApi() → showDashboard(role, user)\n'
        '})();'
    )

    doc.sub_heading('Key JavaScript Functions')
    doc.table(
        ['Function', 'Purpose'],
        [
            ['apiJson(path, opts)', 'Fetch JSON from backend; throws on non-2xx responses'],
            ['showDashboard(role, user)', 'Show role dashboard; hide login; start notification polling'],
            ['buildNav(role)', 'Build sidebar & bottom nav from NAV[role] config array'],
            ['loadDirectoryAdmin()', 'Fetch & render Teachers, Students, Parents tables'],
            ['openEditProfileModal(type, data)', 'Show edit modal pre-filled with profile data'],
            ['startClassSession()', 'Get GPS, POST to /session/start, begin polling'],
            ['startRandomPings(sessionId)', 'Background GPS ping every 2-5 minutes'],
            ['initNotificationPanel()', 'Wire bell button, poll unread count every 30s'],
            ['openComposeModal()', 'Load recipient list, open compose message modal'],
            ['_showToast(msg)', 'Display bottom-right toast notification for 3 seconds'],
        ],
        [60, 114]
    )

    doc.sub_heading('Navigation System')
    doc.body(
        'Navigation items are defined as JS objects {id, label, icon} per role in the NAV constant. '
        'buildNav() generates both a sidebar nav (desktop) and a bottom tab bar (mobile). '
        'Clicking a nav item adds class "active" to that button and shows/hides the '
        'matching .app-section div by its id.'
    )

    doc.sub_heading('CSS Architecture')
    doc.body(
        'All styles live in static/css/style.css (2500+ lines). The design system is '
        'defined as CSS Custom Properties (--primary-600, --gray-200, etc.) in the '
        ':root block. These are referenced throughout all components. '
        'The colour palette is Steel Blue + Warm Champagne with semantic Emerald, Coral, and Amber.'
    )

    # ═══════════════════════════════════════════════════════════════
    # PAGE — DEPLOYMENT
    # ═══════════════════════════════════════════════════════════════
    doc.add_page()
    doc.section_title('12. Deployment & Running Locally')

    doc.sub_heading('Running Locally (Development)')
    doc.code_box(
        '# 1. Clone the repository\n'
        'git clone https://github.com/hrishav2208/Edutrack.git\n'
        'cd Edutrack\n'
        '\n'
        '# 2. Create virtual environment\n'
        'python -m venv venv\n'
        'venv\\Scripts\\activate          # Windows\n'
        'source venv/bin/activate        # macOS / Linux\n'
        '\n'
        '# 3. Install dependencies\n'
        'pip install -r requirements.txt\n'
        '\n'
        '# 4. Set environment variables (optional for dev)\n'
        'copy .env.example .env          # then edit .env\n'
        '\n'
        '# 5. Run the server\n'
        'python wsgi.py\n'
        '# OR use the included batch file on Windows:\n'
        'run.bat\n'
        '\n'
        '# App runs at: http://127.0.0.1:5000'
    )

    doc.sub_heading('Environment Variables (.env)')
    doc.table(
        ['Variable', 'Purpose', 'Example Value'],
        [
            ['SECRET_KEY', 'Flask session encryption key', 'any-random-secret-string'],
            ['DATABASE_URL', 'Postgres URL for production', 'postgresql://user:pw@host/db'],
            ['FLASK_ENV', 'Config profile', 'dev  OR  prod'],
            ['EMAILJS_SERVICE_ID', 'EmailJS service for OTP', 'service_abc123'],
            ['EMAILJS_TEMPLATE_ID', 'EmailJS template for OTP', 'template_xyz'],
            ['EMAILJS_PUBLIC_KEY', 'EmailJS public key', 'user_pubkey'],
            ['DEFAULT_CAMPUS_LAT', 'Default campus latitude', '28.6139'],
            ['DEFAULT_CAMPUS_LNG', 'Default campus longitude', '77.2090'],
            ['DEFAULT_CAMPUS_RADIUS_M', 'Geofence radius in metres', '500'],
        ],
        [50, 64, 60]
    )

    doc.sub_heading('Production with Gunicorn')
    doc.code_box(
        '# Direct Gunicorn (Linux/Mac server)\n'
        'gunicorn wsgi:app --workers=4 --bind=0.0.0.0:5000\n'
        '\n'
        '# Or use the config file\n'
        'gunicorn -c gunicorn.conf.py wsgi:app'
    )

    doc.sub_heading('Docker Deployment')
    doc.code_box(
        '# Build and start with Docker Compose\n'
        'docker-compose up --build\n'
        '\n'
        '# The Dockerfile:\n'
        '#   Base: python:3.11-slim\n'
        '#   Installs requirements.txt\n'
        '#   Runs: gunicorn wsgi:app\n'
        '#   Exposes port 5000'
    )

    doc.sub_heading('Default Demo Login Credentials')
    doc.table(
        ['Role', 'Email / UID', 'Password'],
        [
            ['Admin', 'admin@edutrack.com', 'demo123'],
            ['Teacher (Dr. Sarah Chen)', 'teacher@edutrack.com', 'demo123'],
            ['Teacher (Hrishav Bisht)', 'EMP-AI26HRI001', 'demo123'],
            ['Student (Alex Kumar)', 'student@edutrack.com', 'demo123'],
            ['Student (Wilson Gaikwad)', 'STU-AIM26WIL001', 'demo123'],
            ['Parent (Mrs. Sharma)', 'parent@edutrack.com', 'demo123'],
            ['Parent (Sanjay Gaikwad)', 'PAR-26SAN001', 'demo123'],
        ],
        [40, 80, 54]
    )

    doc.ln(5)
    doc.info_box('Quick Summary — The 3 Things That Make EduTrack Work', NAVY, [
        '1. Flask Application Factory (app/__init__.py) boots everything: config, DB, blueprints, seed data.',
        '2. SQLAlchemy ORM (app/models.py) defines all 16 tables; db.create_all() + auto-migration keeps schema fresh.',
        '3. JavaScript SPA (static/js/main.js) is a ~2700-line IIFE that handles all UI state, API calls, and dynamic rendering.',
    ])

    # ─── Save ─────────────────────────────────────────────────────────────────
    out = r'C:\free\Edutrack\EduTrack_Technical_Documentation.pdf'
    doc.output(out)
    print(f"SUCCESS: PDF saved to: {out}")

if __name__ == '__main__':
    build()
