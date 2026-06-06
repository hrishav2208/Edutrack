"""SQLAlchemy models — single SQLite file in instance/ (no per-machine edits)."""

from datetime import date, datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    uid = db.Column(db.String(40), unique=True, nullable=True, index=True)  # Portal ID e.g. STU-CSE24ADI001
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin | teacher | student | parent
    display_name = db.Column(db.String(120), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("parents.id"), nullable=True)
    security_question = db.Column(db.String(255), nullable=True)
    security_answer_hash = db.Column(db.String(256), nullable=True)


class Teacher(db.Model):
    __tablename__ = "teachers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    department = db.Column(db.String(80), nullable=False, default="General")
    monthly_salary = db.Column(db.Float, nullable=False, default=0.0)
    primary_phone = db.Column(db.String(40), default="")
    secondary_phone = db.Column(db.String(40), default="")
    guardian_phone = db.Column(db.String(40), default="")
    address = db.Column(db.String(255), default="")
    dob = db.Column(db.Date, nullable=True)
    blood_group = db.Column(db.String(10), default="")
    profile_picture = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Parent(db.Model):
    __tablename__ = "parents"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(40), default="")
    primary_phone = db.Column(db.String(40), default="")
    secondary_phone = db.Column(db.String(40), default="")
    guardian_phone = db.Column(db.String(40), default="")
    address = db.Column(db.String(255), default="")
    dob = db.Column(db.Date, nullable=True)
    blood_group = db.Column(db.String(10), default="")
    profile_picture = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Student(db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    roll_no = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), default="")
    department = db.Column(db.String(80), nullable=False, default="CSE")
    parent_id = db.Column(db.Integer, db.ForeignKey("parents.id"), nullable=True)
    primary_phone = db.Column(db.String(40), default="")
    secondary_phone = db.Column(db.String(40), default="")
    guardian_phone = db.Column(db.String(40), default="")
    address = db.Column(db.String(255), default="")
    dob = db.Column(db.Date, nullable=True)
    blood_group = db.Column(db.String(10), default="")
    profile_picture = db.Column(db.String(255), default="")
    is_placed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CampusSettings(db.Model):
    __tablename__ = "campus_settings"
    id = db.Column(db.Integer, primary_key=True, default=1)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    radius_m = db.Column(db.Float, nullable=False, default=500.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AttendanceRecord(db.Model):
    __tablename__ = "attendance_records"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    course_code = db.Column(db.String(40), nullable=False, default="GEN101")
    session_date = db.Column(db.Date, nullable=False, default=date.today)
    present = db.Column(db.Boolean, nullable=False, default=True)
    method = db.Column(db.String(24), nullable=False, default="manual")  # manual | face | qr | gps | biometric
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("student_id", "course_code", "session_date", name="uq_attendance_day"),)


class Mark(db.Model):
    __tablename__ = "marks"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=True)
    course_code = db.Column(db.String(40), nullable=False)
    exam_title = db.Column(db.String(120), nullable=False)
    score = db.Column(db.Float, nullable=False)
    max_score = db.Column(db.Float, nullable=False, default=100.0)
    graded_at = db.Column(db.DateTime, default=datetime.utcnow)


class FeeStructure(db.Model):
    __tablename__ = "fee_structures"
    id = db.Column(db.Integer, primary_key=True)
    program = db.Column(db.String(120), nullable=False)
    item_name = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    academic_year = db.Column(db.String(20), nullable=False, default="2025-26")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FeePayment(db.Model):
    __tablename__ = "fee_payments"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    structure_id = db.Column(db.Integer, db.ForeignKey("fee_structures.id"), nullable=True)
    amount_paid = db.Column(db.Float, nullable=False)
    paid_on = db.Column(db.Date, nullable=False, default=date.today)
    remarks = db.Column(db.String(200), default="")


class SalaryDisbursement(db.Model):
    __tablename__ = "salary_disbursements"
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False)
    period_label = db.Column(db.String(40), nullable=False)  # e.g. 2026-01
    gross = db.Column(db.Float, nullable=False)
    deductions = db.Column(db.Float, nullable=False, default=0.0)
    net = db.Column(db.Float, nullable=False)
    paid_on = db.Column(db.Date, nullable=False, default=date.today)
    notes = db.Column(db.String(200), default="")


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(40), default="info") # info, success, warning, danger
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ClassSession(db.Model):
    """Represents an active class session started by a teacher with GPS geofence."""
    __tablename__ = "class_sessions"
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False)
    course_code = db.Column(db.String(40), nullable=False)
    room_name = db.Column(db.String(80), default="")
    # GPS center of the classroom
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    radius_m = db.Column(db.Float, nullable=False, default=20.0)
    # Session lifecycle
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    # Attendance summary (populated on end)
    total_checkins = db.Column(db.Integer, default=0)


class SessionCheckIn(db.Model):
    """Logs each GPS check-in (initial or random ping) from a student during a session."""
    __tablename__ = "session_checkins"
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("class_sessions.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    inside_radius = db.Column(db.Boolean, nullable=False)
    distance_m = db.Column(db.Float, nullable=False)
    check_type = db.Column(db.String(20), default="ping")  # initial | ping
    checked_at = db.Column(db.DateTime, default=datetime.utcnow)


class AcademicEvent(db.Model):
    """Represents a calendar event for the institution."""
    __tablename__ = "academic_events"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(255), default="")
    type = db.Column(db.String(40), default="event")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ExamScheduleItem(db.Model):
    """Represents an upcoming exam."""
    __tablename__ = "exam_schedules"
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(40), nullable=False)
    exam_title = db.Column(db.String(120), nullable=False)
    exam_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
