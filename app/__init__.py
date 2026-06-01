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
    ClassSession,
    FeeStructure,
    Mark,
    Parent,
    SalaryDisbursement,
    SessionCheckIn,
    Student,
    Teacher,
    User,
)

migrate = Migrate()


def seed_database(app):
    """One-time demo data; password for all demo users: demo123"""
    if User.query.first():
        return

    ph = generate_password_hash("demo123")

    parent = Parent(name="Mrs. Sharma", email="parent@edutrack.com", phone="+91 90000 00001")
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
    )
    db.session.add(student)
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

    db.session.commit()


def create_app(config_name=None):
    if not config_name:
        config_name = os.environ.get("FLASK_ENV", "dev")

    # static_folder is resolved relative to this app package
    static_folder_path = os.path.join(BASE_DIR, "static")
    app = Flask(__name__, static_folder=static_folder_path, static_url_path="/static")
    
    app.config.from_object(config_by_name[config_name])
    os.makedirs(INSTANCE_DIR, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)

    # Import and register blueprints
    from app.auth import auth_bp
    from app.attendance import attendance_bp
    from app.directory import directory_bp
    from app.finance import finance_bp
    from app.marks import marks_bp
    from app.notifications import notifications_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(attendance_bp, url_prefix="/api/attendance")
    app.register_blueprint(directory_bp, url_prefix="/api/directory")
    app.register_blueprint(finance_bp, url_prefix="/api/finance")
    app.register_blueprint(marks_bp, url_prefix="/api/marks")
    app.register_blueprint(notifications_bp, url_prefix="/api/notifications")

    @app.route("/")
    def index():
        return send_from_directory(BASE_DIR, "index.html")

    with app.app_context():
        # Keep create_all for development SQLite auto-setup, but bypass during migrations
        import sys
        is_migration_command = any(cmd in sys.argv for cmd in ["db", "migrate", "upgrade", "init", "alembic"])
        if not is_migration_command:
            db.create_all()
            seed_database(app)

    return app
