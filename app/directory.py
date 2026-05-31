"""CRUD for teachers, students, parents (admin)."""

from flask import Blueprint, jsonify, request

from app.auth import require_login
from app.models import Parent, Student, Teacher, User, db

directory_bp = Blueprint("directory", __name__)


@directory_bp.route("/teachers", methods=["GET"])
def list_teachers():
    u, err = require_login()
    if err:
        return err
    rows = Teacher.query.order_by(Teacher.name).all()
    return jsonify(
        [
            {
                "id": t.id,
                "name": t.name,
                "email": t.email,
                "department": t.department,
                "monthly_salary": t.monthly_salary,
            }
            for t in rows
        ]
    )


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
    if not name or not email:
        return jsonify({"error": "name and email required"}), 400
    if Teacher.query.filter_by(email=email).first():
        return jsonify({"error": "Email already used"}), 400
    t = Teacher(name=name, email=email, department=department, monthly_salary=monthly_salary)
    db.session.add(t)
    db.session.commit()
    return jsonify({"ok": True, "id": t.id})


@directory_bp.route("/parents", methods=["GET"])
def list_parents():
    u, err = require_login()
    if err:
        return err
    rows = Parent.query.order_by(Parent.name).all()
    return jsonify(
        [
            {"id": p.id, "name": p.name, "email": p.email, "phone": p.phone}
            for p in rows
        ]
    )


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
    if not name or not email:
        return jsonify({"error": "name and email required"}), 400
    if Parent.query.filter_by(email=email).first():
        return jsonify({"error": "Email already used"}), 400
    p = Parent(name=name, email=email, phone=phone)
    db.session.add(p)
    db.session.commit()
    return jsonify({"ok": True, "id": p.id})


@directory_bp.route("/students", methods=["GET"])
def list_students():
    u, err = require_login()
    if err:
        return err
    rows = Student.query.order_by(Student.roll_no).all()
    return jsonify(
        [
            {
                "id": s.id,
                "roll_no": s.roll_no,
                "name": s.name,
                "email": s.email,
                "department": s.department,
                "parent_id": s.parent_id,
            }
            for s in rows
        ]
    )


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
    email = (data.get("email") or "").strip()
    department = (data.get("department") or "CSE").strip()
    parent_id = data.get("parent_id")
    parent_id = int(parent_id) if parent_id else None
    if not roll or not name:
        return jsonify({"error": "roll_no and name required"}), 400
    if Student.query.filter_by(roll_no=roll).first():
        return jsonify({"error": "Roll number exists"}), 400
    s = Student(roll_no=roll, name=name, email=email, department=department, parent_id=parent_id)
    db.session.add(s)
    db.session.commit()
    return jsonify({"ok": True, "id": s.id})
