"""Flask application factory. Initializes extensions and registers blueprints."""

import os
from flask import Flask, send_from_directory
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app.config import config_by_name, BASE_DIR, INSTANCE_DIR
from app.models import (
    db,
    CampusSettings,
    FeeStructure,
    Mark,
    Parent,
    SalaryDisbursement,
    Student,
    Teacher,
    User,
    AcademicEvent,
    ExamScheduleItem,
    TimetableEntry,
)

migrate = Migrate()


def seed_database(app):
    """One-time demo data; password for all demo users: demo123"""
    if User.query.first():
        return

    ph = generate_password_hash("demo123")

    parent = Parent(
        name="Mrs. Sharma",
        email="parent@edutrack.com",
        phone="+91 90000 00001",
    )
    db.session.add(parent)
    db.session.flush()

    teacher = Teacher(
        name="Dr. Sarah Chen",
        email="teacher@edutrack.com",
        department="Computer Science",
        monthly_salary=85000.0,
    )
    db.session.add(teacher)
    db.session.flush()

    student = Student(
        roll_no="CS21A001",
        name="Alex Kumar",
        email="student@edutrack.com",
        department="CSE",
        parent_id=parent.id,
        is_placed=True,
    )
    db.session.add(student)
    db.session.flush()

    t1 = Teacher(name="Andrew Tate", email="andrew33@gmail.com", department="AIML", monthly_salary=40000.0)
    t2 = Teacher(name="Hrishav Bisht", email="hrishav888@gmail.com", department="AIML", monthly_salary=90000.0)
    t3 = Teacher(name="Hrishav Hrishav Hrishav", email="bishthrishav@gmail.com", department="CSE", monthly_salary=100000.0)
    p1 = Parent(name="SANJAY GAIKWAD", email="sanjay@gmail.com", phone="+91 8373711116")
    s1 = Student(roll_no="CS21554", name="WILSON GAIKWAD", email="wilsongaikwad@gmail.com", department="AIML")
    db.session.add_all([t1, t2, t3, p1, s1])
    db.session.flush()

    db.session.add_all(
        [
            User(
                email="admin@edutrack.com",
                password_hash=ph,
                role="admin",
                display_name="Admin User",
            ),
            User(
                email="teacher@edutrack.com",
                password_hash=ph,
                role="teacher",
                display_name="Dr. Sarah Chen",
                teacher_id=teacher.id,
            ),
            User(
                email="student@edutrack.com",
                password_hash=ph,
                role="student",
                display_name="Alex Kumar",
                student_id=student.id,
            ),
            User(
                email="parent@edutrack.com",
                password_hash=ph,
                role="parent",
                display_name="Mrs. Sharma",
                parent_id=parent.id,
            ),
            User(email=t1.email, uid="EMP-AI26AND001", password_hash=ph, role="teacher", display_name=t1.name, teacher_id=t1.id),
            User(email=t2.email, uid="EMP-AI26HRI001", password_hash=ph, role="teacher", display_name=t2.name, teacher_id=t2.id),
            User(email=t3.email, uid="EMP-CSE26HRI001", password_hash=ph, role="teacher", display_name=t3.name, teacher_id=t3.id),
            User(email=p1.email, uid="PAR-26SAN001", password_hash=ph, role="parent", display_name=p1.name, parent_id=p1.id),
            User(email=s1.email, uid="STU-AIM26WIL001", password_hash=ph, role="student", display_name=s1.name, student_id=s1.id),
        ]
    )

    db.session.add(
        CampusSettings(
            id=1,
            lat=app.config["DEFAULT_CAMPUS_LAT"],
            lng=app.config["DEFAULT_CAMPUS_LNG"],
            radius_m=app.config["DEFAULT_CAMPUS_RADIUS_M"],
        )
    )

    db.session.add_all(
        [
            FeeStructure(
                program="B.Tech CSE",
                item_name="Tuition (annual)",
                amount=185000.0,
                academic_year="2025-26",
            ),
            FeeStructure(
                program="B.Tech CSE",
                item_name="Lab & facilities",
                amount=24000.0,
                academic_year="2025-26",
            ),
        ]
    )

    db.session.add(
        Mark(
            student_id=student.id,
            teacher_id=teacher.id,
            course_code="CS101",
            exam_title="Mid-term",
            score=42.0,
            max_score=50.0,
        )
    )

    db.session.add(
        SalaryDisbursement(
            teacher_id=teacher.id,
            period_label="2026-01",
            gross=85000.0,
            deductions=8500.0,
            net=76500.0,
            notes="January payout",
        )
    )

    db.session.add_all([
        AcademicEvent(title="Spring Semester Starts", date=date(2026, 1, 15), type="calendar"),
        AcademicEvent(title="Annual Tech Fest", date=date(2026, 3, 10), type="event"),
        AcademicEvent(title="Final Exams Week", date=date(2026, 5, 20), type="calendar"),
        ExamScheduleItem(course_code="CS101", exam_title="Final Exam", exam_date=date(2026, 5, 21)),
        ExamScheduleItem(course_code="CS102", exam_title="Final Exam", exam_date=date(2026, 5, 23)),
    ])

    db.session.commit()


def create_app(config_name=None):
    if not config_name:
        config_name = os.environ.get("FLASK_ENV", "dev")

    # static_folder is resolved relative to this app package
    static_folder_path = os.path.join(BASE_DIR, "static")
    app = Flask(
        __name__, static_folder=static_folder_path, static_url_path="/static"
    )

    app.config.from_object(config_by_name[config_name])
    os.makedirs(INSTANCE_DIR, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)

    from app.extensions import limiter
    limiter.init_app(app)

    # Import and register blueprints
    from app.auth import auth_bp
    from app.attendance import attendance_bp
    from app.directory import directory_bp
    from app.finance import finance_bp
    from app.marks import marks_bp
    from app.notifications import notifications_bp
    from app.curriculum import curriculum_bp
    from app.reports import reports_bp
    from app.profile import profile_bp
    from app.departments import departments_bp
    from app.timetable import timetable_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(attendance_bp, url_prefix="/api/attendance")
    app.register_blueprint(directory_bp, url_prefix="/api/directory")
    app.register_blueprint(finance_bp, url_prefix="/api/finance")
    app.register_blueprint(marks_bp, url_prefix="/api/marks")
    app.register_blueprint(notifications_bp, url_prefix="/api/notifications")
    app.register_blueprint(curriculum_bp, url_prefix="/api/curriculum")
    app.register_blueprint(reports_bp, url_prefix="/api/reports")
    app.register_blueprint(profile_bp, url_prefix="/api/profile")
    app.register_blueprint(departments_bp, url_prefix="/api/departments")
    app.register_blueprint(timetable_bp, url_prefix="/api/timetable")

    @app.route("/api/admin/otp-logs", methods=["GET"])
    def legacy_otp_logs():
        from app.auth import get_otp_logs
        return get_otp_logs()

    @app.route("/")
    def index():
        return send_from_directory(BASE_DIR, "index.html")

    with app.app_context():
        # Keep create_all for development SQLite auto-setup, but bypass during migrations
        import sys

        is_migration_command = any(
            cmd in sys.argv
            for cmd in ["db", "migrate", "upgrade", "init", "alembic"]
        )
        if not is_migration_command:
            db.create_all()

            # --- AUTO-MIGRATE MISSING COLUMNS ---
            try:
                from sqlalchemy import text, inspect

                inspector = inspect(db.engine)
                # Ensure users table exists before checking columns
                if "users" in inspector.get_table_names():
                    columns = [
                        col["name"] for col in inspector.get_columns("users")
                    ]
                    if "uid" not in columns:
                        db.session.execute(text("ALTER TABLE users ADD COLUMN uid VARCHAR(40) UNIQUE"))
                        db.session.commit()
                    if "current_otp" not in columns:
                        db.session.execute(text("ALTER TABLE users ADD COLUMN current_otp VARCHAR(10)"))
                        db.session.commit()
                    if "otp_expiry" not in columns:
                        db.session.execute(text("ALTER TABLE users ADD COLUMN otp_expiry TIMESTAMP"))
                        db.session.commit()
                if "students" in inspector.get_table_names():
                    columns = [col["name"] for col in inspector.get_columns("students")]
                    if "is_placed" not in columns:
                        db.session.execute(text("ALTER TABLE students ADD COLUMN is_placed BOOLEAN DEFAULT FALSE"))
                        db.session.commit()
                if "campus_settings" in inspector.get_table_names():
                    columns = [col["name"] for col in inspector.get_columns("campus_settings")]
                    if "departments_json" not in columns:
                        db.session.execute(text("ALTER TABLE campus_settings ADD COLUMN departments_json TEXT DEFAULT '[\"CSE\", \"ECE\", \"ME\", \"CE\", \"EEE\"]'"))
                        db.session.commit()
                # Auto-create messages table columns if needed
                if "messages" in inspector.get_table_names():
                    msg_cols = [col["name"] for col in inspector.get_columns("messages")]
                    if "recipient_dept" not in msg_cols:
                        db.session.execute(text("ALTER TABLE messages ADD COLUMN recipient_dept VARCHAR(80)"))
                        db.session.commit()
                    if "recipient_role" not in msg_cols:
                        db.session.execute(text("ALTER TABLE messages ADD COLUMN recipient_role VARCHAR(40)"))
                        db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(
                    f"Auto-migration failed (this is usually safe to ignore if already migrated): {e}"
                )

            seed_database(app)

    return app
