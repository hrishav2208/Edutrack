from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from app.auth import require_login
from app.models import db, User, Teacher, Student, Parent

profile_bp = Blueprint("profile", __name__)

@profile_bp.route("/me", methods=["GET"])
def get_profile():
    u, err = require_login()
    if err:
        return err

    data = {
        "id": u.id,
        "role": u.role,
        "uid": u.uid,
        "display_name": u.display_name,
        "email": u.email,
        "primary_phone": "",
        "secondary_phone": "",
        "guardian_phone": ""
    }

    if u.role == "teacher" and u.teacher_id:
        t = Teacher.query.get(u.teacher_id)
        if t:
            data["primary_phone"] = t.primary_phone
            data["secondary_phone"] = t.secondary_phone
            data["guardian_phone"] = t.guardian_phone
            data["department"] = t.department
    elif u.role == "student" and u.student_id:
        s = Student.query.get(u.student_id)
        if s:
            data["primary_phone"] = s.primary_phone
            data["secondary_phone"] = s.secondary_phone
            data["guardian_phone"] = s.guardian_phone
            data["department"] = s.department
            data["roll_no"] = s.roll_no
    elif u.role == "parent" and u.parent_id:
        p = Parent.query.get(u.parent_id)
        if p:
            data["primary_phone"] = p.primary_phone
            data["secondary_phone"] = p.secondary_phone
            data["guardian_phone"] = p.guardian_phone

    return jsonify(data)

@profile_bp.route("/me", methods=["PUT"])
def update_profile():
    u, err = require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    primary_phone = (data.get("primary_phone") or "").strip()
    secondary_phone = (data.get("secondary_phone") or "").strip()
    guardian_phone = (data.get("guardian_phone") or "").strip()

    if u.role == "teacher" and u.teacher_id:
        t = Teacher.query.get(u.teacher_id)
        if t:
            t.primary_phone = primary_phone
            t.secondary_phone = secondary_phone
            t.guardian_phone = guardian_phone
    elif u.role == "student" and u.student_id:
        s = Student.query.get(u.student_id)
        if s:
            s.primary_phone = primary_phone
            s.secondary_phone = secondary_phone
            s.guardian_phone = guardian_phone
    elif u.role == "parent" and u.parent_id:
        p = Parent.query.get(u.parent_id)
        if p:
            p.primary_phone = primary_phone
            p.secondary_phone = secondary_phone
            p.guardian_phone = guardian_phone

    db.session.commit()
    return jsonify({"ok": True})

@profile_bp.route("/change-password", methods=["POST"])
def change_password():
    u, err = require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")

    if not current_password or not new_password:
        return jsonify({"error": "Current and new passwords are required."}), 400

    if not check_password_hash(u.password_hash, current_password):
        return jsonify({"error": "Incorrect current password."}), 400

    u.password_hash = generate_password_hash(new_password)
    db.session.commit()

    return jsonify({"ok": True, "message": "Password changed successfully."})
