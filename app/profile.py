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
        "guardian_phone": "",
        "address": "",
        "dob": "",
        "blood_group": "",
        "profile_picture": "",
        "security_question": u.security_question or ""
    }

    if u.role == "teacher" and u.teacher_id:
        t = Teacher.query.get(u.teacher_id)
        if t:
            data["primary_phone"] = t.primary_phone
            data["secondary_phone"] = t.secondary_phone
            data["guardian_phone"] = t.guardian_phone
            data["department"] = t.department
            data["address"] = t.address
            data["dob"] = t.dob.isoformat() if t.dob else ""
            data["blood_group"] = t.blood_group
            data["profile_picture"] = t.profile_picture
    elif u.role == "student" and u.student_id:
        s = Student.query.get(u.student_id)
        if s:
            data["primary_phone"] = s.primary_phone
            data["secondary_phone"] = s.secondary_phone
            data["guardian_phone"] = s.guardian_phone
            data["department"] = s.department
            data["roll_no"] = s.roll_no
            data["address"] = s.address
            data["dob"] = s.dob.isoformat() if s.dob else ""
            data["blood_group"] = s.blood_group
            data["profile_picture"] = s.profile_picture
    elif u.role == "parent" and u.parent_id:
        p = Parent.query.get(u.parent_id)
        if p:
            data["primary_phone"] = p.primary_phone
            data["secondary_phone"] = p.secondary_phone
            data["guardian_phone"] = p.guardian_phone
            data["address"] = p.address
            data["dob"] = p.dob.isoformat() if p.dob else ""
            data["blood_group"] = p.blood_group
            data["profile_picture"] = p.profile_picture

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
    address = (data.get("address") or "").strip()
    dob_str = (data.get("dob") or "").strip()
    blood_group = (data.get("blood_group") or "").strip()
    
    # Allow saving security question info on user
    sec_q = (data.get("security_question") or "").strip()
    sec_a = (data.get("security_answer") or "").strip()
    
    if sec_q and sec_a:
        u.security_question = sec_q
        u.security_answer_hash = generate_password_hash(sec_a)
        
    from datetime import datetime
    dob_date = None
    if dob_str:
        try:
            dob_date = datetime.strptime(dob_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    if u.role == "teacher" and u.teacher_id:
        t = Teacher.query.get(u.teacher_id)
        if t:
            t.primary_phone = primary_phone
            t.secondary_phone = secondary_phone
            t.guardian_phone = guardian_phone
            t.address = address
            t.blood_group = blood_group
            if dob_date: t.dob = dob_date
    elif u.role == "student" and u.student_id:
        s = Student.query.get(u.student_id)
        if s:
            s.primary_phone = primary_phone
            s.secondary_phone = secondary_phone
            s.guardian_phone = guardian_phone
            s.address = address
            s.blood_group = blood_group
            if dob_date: s.dob = dob_date
    elif u.role == "parent" and u.parent_id:
        p = Parent.query.get(u.parent_id)
        if p:
            p.primary_phone = primary_phone
            p.secondary_phone = secondary_phone
            p.guardian_phone = guardian_phone
            p.address = address
            p.blood_group = blood_group
            if dob_date: p.dob = dob_date

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
