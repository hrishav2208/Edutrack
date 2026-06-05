"""CRUD for teachers, students, parents (admin). Auto-generates Portal UIDs and User accounts."""

import re
from datetime import datetime

from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash

from app.auth import require_login
from app.models import Parent, Student, Teacher, User, db

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

    t = Teacher(name=name, email=email, department=department, monthly_salary=monthly_salary)
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

    if not name:
        return jsonify({"error": "name is required"}), 400

    uid = generate_parent_uid(name)

    if not email:
        email = f"{uid.lower()}@edutrack.internal"

    if Parent.query.filter_by(email=email).first():
        return jsonify({"error": "Email already used"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already used by another account"}), 400

    p = Parent(name=name, email=email, phone=phone)
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

    s = Student(roll_no=roll, name=name, email=email, department=department, parent_id=parent_id)
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
