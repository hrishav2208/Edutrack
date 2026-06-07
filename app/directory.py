"""CRUD for teachers, students, parents (admin). Auto-generates Portal UIDs and User accounts."""

import re
from datetime import datetime

from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash

from app.auth import require_login
from app.models import (
    Parent, Student, Teacher, User, db, Notification, AttendanceRecord, Mark,
    FeePayment, ClassSession, SessionCheckIn, SalaryDisbursement
)

directory_bp = Blueprint("directory", __name__)

DEFAULT_PASSWORD = "Welcome@123"


# ─────────────────────────────────────────────
# UID GENERATION HELPERS
# ─────────────────────────────────────────────

def _name_prefix(name: str, length: int = 3) -> str:
    """Extract first `length` uppercase alphabetical chars from the first word of name."""
    first_word = re.sub(r"[^a-zA-Z]", "", name.split()[0])
    return first_word[:length].upper().ljust(length, "X")


def _dept_code(department: str, length: int = 3) -> str:
    """Shorten department to a max-4-char uppercase code."""
    # Known mappings
    MAP = {
        "computer science": "CS",
        "cse": "CSE",
        "ece": "ECE",
        "electronics": "ECE",
        "mechanical": "ME",
        "civil": "CE",
        "electrical": "EEE",
        "information technology": "IT",
        "general": "GEN",
    }
    dept_lower = department.strip().lower()
    if dept_lower in MAP:
        return MAP[dept_lower]
    # Fallback: take first `length` consonants/letters of department
    return re.sub(r"[^A-Z]", "", department.upper())[:length] or "GEN"


def _year_suffix() -> str:
    """Return last 2 digits of current year."""
    return str(datetime.utcnow().year)[-2:]


def _next_sequence(prefix_pattern: str) -> str:
    """Find the next available 3-digit sequence number for a given uid prefix."""
    existing = User.query.filter(User.uid.like(prefix_pattern + "%")).count()
    return str(existing + 1).zfill(3)


def generate_student_uid(name: str, department: str) -> str:
    """STU-<DEPT><YY><NAME3><SEQ> e.g. STU-CSE26ADI001"""
    dept = _dept_code(department)
    yr = _year_suffix()
    nam = _name_prefix(name)
    prefix = f"STU-{dept}{yr}{nam}"
    seq = _next_sequence(prefix)
    return f"{prefix}{seq}"


def generate_teacher_uid(name: str, department: str) -> str:
    """EMP-<DEPT><YY><NAME3><SEQ> e.g. EMP-CS26PRI001"""
    dept = _dept_code(department, length=2)
    yr = _year_suffix()
    nam = _name_prefix(name)
    prefix = f"EMP-{dept}{yr}{nam}"
    seq = _next_sequence(prefix)
    return f"{prefix}{seq}"


def generate_parent_uid(name: str) -> str:
    """PAR-<YY><NAME3><SEQ> e.g. PAR-26RAJ001"""
    yr = _year_suffix()
    nam = _name_prefix(name)
    prefix = f"PAR-{yr}{nam}"
    seq = _next_sequence(prefix)
    return f"{prefix}{seq}"


# ─────────────────────────────────────────────
# TEACHERS
# ─────────────────────────────────────────────

@directory_bp.route("/teachers", methods=["GET"])
def list_teachers():
    u, err = require_login()
    if err:
        return err
    rows = Teacher.query.order_by(Teacher.name).all()
    result = []
    for t in rows:
        user = User.query.filter_by(teacher_id=t.id).first()
        result.append({
            "id": t.id,
            "name": t.name,
            "email": t.email,
            "department": t.department,
            "monthly_salary": t.monthly_salary,
            "uid": user.uid if user else None,
        })
    return jsonify(result)


@directory_bp.route("/teachers", methods=["POST"])
def add_teacher():
    u, err = require_login()
    if err:
        return err
    if u.role != "admin":
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    department = (data.get("department") or "General").strip()
    monthly_salary = float(data.get("monthly_salary") or 0)
    password = (data.get("password") or DEFAULT_PASSWORD).strip()
    primary_phone = (data.get("primary_phone") or "").strip()
    secondary_phone = (data.get("secondary_phone") or "").strip()
    guardian_phone = (data.get("guardian_phone") or "").strip()

    if not name:
        return jsonify({"error": "name is required"}), 400

    # Generate UID first so we can derive the internal email if none given
    uid = generate_teacher_uid(name, department)

    # Use provided email or fallback to uid-based internal email
    if not email:
        email = f"{uid.lower()}@edutrack.internal"

    if Teacher.query.filter_by(email=email).first():
        return jsonify({"error": "Email already used"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already used by another account"}), 400

    t = Teacher(
        name=name, email=email, department=department, monthly_salary=monthly_salary,
        primary_phone=primary_phone, secondary_phone=secondary_phone, guardian_phone=guardian_phone
    )
    db.session.add(t)
    db.session.flush()

    user = User(
        email=email,
        uid=uid,
        password_hash=generate_password_hash(password),
        role="teacher",
        display_name=name,
        teacher_id=t.id,
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({"ok": True, "id": t.id, "uid": uid, "email": email})


# ─────────────────────────────────────────────
# PARENTS
# ─────────────────────────────────────────────

@directory_bp.route("/parents", methods=["GET"])
def list_parents():
    u, err = require_login()
    if err:
        return err
    rows = Parent.query.order_by(Parent.name).all()
    result = []
    for p in rows:
        user = User.query.filter_by(parent_id=p.id).first()
        result.append({
            "id": p.id,
            "name": p.name,
            "email": p.email,
            "phone": p.phone,
            "uid": user.uid if user else None,
        })
    return jsonify(result)


@directory_bp.route("/parents", methods=["POST"])
def add_parent():
    u, err = require_login()
    if err:
        return err
    if u.role != "admin":
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    password = (data.get("password") or DEFAULT_PASSWORD).strip()
    primary_phone = (data.get("primary_phone") or "").strip()
    secondary_phone = (data.get("secondary_phone") or "").strip()
    guardian_phone = (data.get("guardian_phone") or "").strip()

    if not name:
        return jsonify({"error": "name is required"}), 400

    uid = generate_parent_uid(name)

    if not email:
        email = f"{uid.lower()}@edutrack.internal"

    if Parent.query.filter_by(email=email).first():
        return jsonify({"error": "Email already used"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already used by another account"}), 400

    p = Parent(
        name=name, email=email, phone=phone,
        primary_phone=primary_phone, secondary_phone=secondary_phone, guardian_phone=guardian_phone
    )
    db.session.add(p)
    db.session.flush()

    user = User(
        email=email,
        uid=uid,
        password_hash=generate_password_hash(password),
        role="parent",
        display_name=name,
        parent_id=p.id,
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({"ok": True, "id": p.id, "uid": uid, "email": email})


# ─────────────────────────────────────────────
# STUDENTS
# ─────────────────────────────────────────────

@directory_bp.route("/students", methods=["GET"])
def list_students():
    u, err = require_login()
    if err:
        return err
    rows = Student.query.order_by(Student.roll_no).all()
    result = []
    for s in rows:
        user = User.query.filter_by(student_id=s.id).first()
        result.append({
            "id": s.id,
            "roll_no": s.roll_no,
            "name": s.name,
            "email": s.email,
            "department": s.department,
            "parent_id": s.parent_id,
            "uid": user.uid if user else None,
        })
    return jsonify(result)


@directory_bp.route("/students", methods=["POST"])
def add_student():
    u, err = require_login()
    if err:
        return err
    if u.role != "admin":
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json(silent=True) or {}
    roll = (data.get("roll_no") or "").strip()
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    department = (data.get("department") or "CSE").strip()
    parent_id = data.get("parent_id")
    parent_id = int(parent_id) if parent_id else None
    password = (data.get("password") or DEFAULT_PASSWORD).strip()
    primary_phone = (data.get("primary_phone") or "").strip()
    secondary_phone = (data.get("secondary_phone") or "").strip()
    guardian_phone = (data.get("guardian_phone") or "").strip()

    if not name:
        return jsonify({"error": "name is required"}), 400
    if not roll:
        return jsonify({"error": "roll_no is required"}), 400

    if Student.query.filter_by(roll_no=roll).first():
        return jsonify({"error": "Roll number already exists"}), 400

    uid = generate_student_uid(name, department)

    if not email:
        email = f"{uid.lower()}@edutrack.internal"

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already used by another account"}), 400

    s = Student(
        roll_no=roll, name=name, email=email, department=department, parent_id=parent_id,
        primary_phone=primary_phone, secondary_phone=secondary_phone, guardian_phone=guardian_phone
    )
    db.session.add(s)
    db.session.flush()

    user = User(
        email=email,
        uid=uid,
        password_hash=generate_password_hash(password),
        role="student",
        display_name=name,
        student_id=s.id,
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({"ok": True, "id": s.id, "uid": uid, "email": email})


@directory_bp.route("/generate-missing-credentials", methods=["POST"])
def generate_missing_credentials():
    u, err = require_login()
    if err:
        return err
    if u.role != "admin":
        return jsonify({"error": "Forbidden"}), 403

    generated_count = 0
    password_hash = generate_password_hash(DEFAULT_PASSWORD)

    # Teachers without User
    for t in Teacher.query.all():
        if not User.query.filter_by(teacher_id=t.id).first():
            uid = generate_teacher_uid(t.name, t.department)
            db.session.add(User(
                email=t.email, uid=uid, password_hash=password_hash,
                role="teacher", display_name=t.name, teacher_id=t.id
            ))
            generated_count += 1

    # Parents without User
    for p in Parent.query.all():
        if not User.query.filter_by(parent_id=p.id).first():
            uid = generate_parent_uid(p.name)
            db.session.add(User(
                email=p.email, uid=uid, password_hash=password_hash,
                role="parent", display_name=p.name, parent_id=p.id
            ))
            generated_count += 1

    # Students without User
    for s in Student.query.all():
        if not User.query.filter_by(student_id=s.id).first():
            uid = generate_student_uid(s.name, s.department)
            db.session.add(User(
                email=s.email, uid=uid, password_hash=password_hash,
                role="student", display_name=s.name, student_id=s.id
            ))
            generated_count += 1

    db.session.commit()
    return jsonify({"ok": True, "generated_count": generated_count})


@directory_bp.route("/teachers/<int:teacher_id>/dept", methods=["PATCH"])
def update_teacher_dept(teacher_id):
    u, err = require_login()
    if err:
        return err
    if u.role != "admin":
        return jsonify({"error": "Unauthorized"}), 403
    data = request.get_json() or {}
    dept = data.get("department", "").strip().upper()
    if not dept:
        return jsonify({"error": "Department is required"}), 400
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        return jsonify({"error": "Teacher not found"}), 404
    teacher.department = dept
    db.session.commit()
    return jsonify({"ok": True, "department": dept})


@directory_bp.route("/students/<int:student_id>/dept", methods=["PATCH"])
def update_student_dept(student_id):
    u, err = require_login()
    if err:
        return err
    if u.role != "admin":
        return jsonify({"error": "Unauthorized"}), 403
    data = request.get_json() or {}
    dept = data.get("department", "").strip().upper()
    if not dept:
        return jsonify({"error": "Department is required"}), 400
    student = Student.query.get(student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404
    student.department = dept
    db.session.commit()
    return jsonify({"ok": True, "department": dept})


@directory_bp.route("/teachers/<int:teacher_id>", methods=["DELETE"])
def delete_teacher(teacher_id):
    u, err = require_login()
    if err:
        return err
    if u.role != "admin":
        return jsonify({"error": "Forbidden"}), 403

    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        return jsonify({"error": "Not found"}), 404

    user = User.query.filter_by(teacher_id=teacher_id).first()
    if user:
        Notification.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
    
    SalaryDisbursement.query.filter_by(teacher_id=teacher_id).delete()
    ClassSession.query.filter_by(teacher_id=teacher_id).delete()
    db.session.query(Mark).filter(Mark.teacher_id == teacher_id).update({"teacher_id": None})
    
    db.session.delete(teacher)
    db.session.commit()
    return jsonify({"ok": True})


@directory_bp.route("/parents/<int:parent_id>", methods=["DELETE"])
def delete_parent(parent_id):
    u, err = require_login()
    if err:
        return err
    if u.role != "admin":
        return jsonify({"error": "Forbidden"}), 403

    parent = Parent.query.get(parent_id)
    if not parent:
        return jsonify({"error": "Not found"}), 404

    user = User.query.filter_by(parent_id=parent_id).first()
    if user:
        Notification.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
    
    db.session.query(Student).filter(Student.parent_id == parent_id).update({"parent_id": None})
    
    db.session.delete(parent)
    db.session.commit()
    return jsonify({"ok": True})


@directory_bp.route("/students/<int:student_id>", methods=["DELETE"])
def delete_student(student_id):
    u, err = require_login()
    if err:
        return err
    if u.role != "admin":
        return jsonify({"error": "Forbidden"}), 403

    student = Student.query.get(student_id)
    if not student:
        return jsonify({"error": "Not found"}), 404

    user = User.query.filter_by(student_id=student_id).first()
    if user:
        Notification.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
    
    AttendanceRecord.query.filter_by(student_id=student_id).delete()
    Mark.query.filter_by(student_id=student_id).delete()
    FeePayment.query.filter_by(student_id=student_id).delete()
    SessionCheckIn.query.filter_by(student_id=student_id).delete()

    db.session.delete(student)
    db.session.commit()
    return jsonify({"ok": True})
