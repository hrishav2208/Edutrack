"""Endpoints for advanced Department Management."""
import json
from flask import Blueprint, jsonify, request
from app.models import db, CampusSettings, Teacher, Student, FeeStructure, FeePayment
from app.auth import current_user

departments_bp = Blueprint("departments", __name__)

@departments_bp.route("/stats", methods=["GET"])
def department_stats():
    u = current_user()
    if not u or u.role != 'admin':
        return jsonify({"error": "Unauthorized"}), 403

    settings = CampusSettings.query.first()
    dept_list = []
    if settings and settings.departments_json:
        try:
            dept_list = json.loads(settings.departments_json)
        except:
            dept_list = ["CSE", "ECE", "ME", "CE", "EEE"]
    else:
        dept_list = ["CSE", "ECE", "ME", "CE", "EEE"]

    stats = []
    for dept in dept_list:
        teachers_count = Teacher.query.filter_by(department=dept).count()
        students_count = Student.query.filter_by(department=dept).count()
        
        # Calculate Fee Fulfillment
        students = Student.query.filter_by(department=dept).all()
        total_expected = 0.0
        total_paid = 0.0
        
        for student in students:
            # All fee structures applying to all programs for simplicity (as defined in current schema)
            structures = FeeStructure.query.all()
            for s in structures:
                total_expected += s.amount
            
            payments = FeePayment.query.filter_by(student_id=student.id).all()
            for p in payments:
                total_paid += p.amount_paid
                
        fee_pct = 0
        if total_expected > 0:
            fee_pct = min(100, int((total_paid / total_expected) * 100))
        elif students_count > 0:
            # If no fee structures exist but there are students, we can assume 100% or 0%. Let's default to 0.
            fee_pct = 0
            
        stats.append({
            "name": dept,
            "teachers": teachers_count,
            "students": students_count,
            "fee_pct": fee_pct
        })

    return jsonify({"stats": stats})

@departments_bp.route("/rename", methods=["POST"])
def rename_department():
    u = current_user()
    if not u or u.role != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.get_json() or {}
    old_name = data.get("old_name", "").strip()
    new_name = data.get("new_name", "").strip()
    
    if not old_name or not new_name:
        return jsonify({"error": "Both old and new names are required"}), 400
        
    settings = CampusSettings.query.first()
    if not settings:
        return jsonify({"error": "No campus settings found"}), 404
        
    try:
        dept_list = json.loads(settings.departments_json or "[]")
    except:
        dept_list = []
        
    if old_name not in dept_list:
        return jsonify({"error": "Department not found"}), 404
        
    if new_name in dept_list:
        return jsonify({"error": "A department with the new name already exists"}), 400
        
    # Rename in the list
    idx = dept_list.index(old_name)
    dept_list[idx] = new_name
    settings.departments_json = json.dumps(dept_list)
    
    # Update all teachers and students
    Teacher.query.filter_by(department=old_name).update({"department": new_name})
    Student.query.filter_by(department=old_name).update({"department": new_name})
    
    db.session.commit()
    
    return jsonify({"ok": True, "departments": dept_list})

@departments_bp.route("/delete", methods=["POST"])
def delete_department():
    u = current_user()
    if not u or u.role != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    
    if not name:
        return jsonify({"error": "Department name is required"}), 400
        
    # Check if empty
    t_count = Teacher.query.filter_by(department=name).count()
    s_count = Student.query.filter_by(department=name).count()
    
    if t_count > 0 or s_count > 0:
        return jsonify({"error": f"Cannot delete '{name}'. It still has {t_count} teachers and {s_count} students. Please transfer them first."}), 400
        
    settings = CampusSettings.query.first()
    try:
        dept_list = json.loads(settings.departments_json or "[]")
    except:
        dept_list = []
        
    if name in dept_list:
        dept_list.remove(name)
        settings.departments_json = json.dumps(dept_list)
        db.session.commit()
        
    return jsonify({"ok": True, "departments": dept_list})

@departments_bp.route("/transfer", methods=["POST"])
def transfer_user():
    u = current_user()
    if not u or u.role != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.get_json() or {}
    user_type = data.get("type", "")  # 'student' or 'teacher'
    user_id = data.get("id")
    new_dept = data.get("new_dept", "").strip()
    
    if not user_type or not user_id or not new_dept:
        return jsonify({"error": "Missing required fields (type, id, new_dept)"}), 400
        
    if user_type == "student":
        student = Student.query.get(user_id)
        if not student:
            return jsonify({"error": "Student not found"}), 404
        student.department = new_dept
    elif user_type == "teacher":
        teacher = Teacher.query.get(user_id)
        if not teacher:
            return jsonify({"error": "Teacher not found"}), 404
        teacher.department = new_dept
    else:
        return jsonify({"error": "Invalid user type"}), 400
        
    db.session.commit()
    
    return jsonify({"ok": True, "message": f"Successfully transferred to {new_dept}"})
