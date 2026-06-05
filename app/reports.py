from flask import Blueprint, jsonify, request
from sqlalchemy import func
from app.auth import require_login
from app.models import db, Student, AttendanceRecord, Mark, User

reports_bp = Blueprint("reports", __name__)

@reports_bp.route("/teacher/analytics", methods=["GET"])
def teacher_analytics():
    u, err = require_login()
    if err:
        return err
    if u.role != "teacher" or not u.teacher_id:
        return jsonify({"error": "Only teachers can view these reports"}), 403

    course_code = request.args.get("course_code", "CS101")

    # 1. Attendance analytics
    # Get all students for the course. For demo purposes, we fetch all students
    # and their attendance records for the given course.
    students = Student.query.all()
    total_students = len(students)
    
    if total_students == 0:
        return jsonify({
            "course_code": course_code,
            "total_students": 0,
            "overall_attendance_percent": 0.0,
            "attendance_breakdown": {"excellent": 0, "good": 0, "warning": 0, "defaulter": 0},
            "average_exam_percent": 0.0
        })

    # Group attendance by student
    attendance_data = db.session.query(
        AttendanceRecord.student_id,
        func.count(AttendanceRecord.id).label("total_sessions"),
        func.sum(func.cast(AttendanceRecord.present, db.Integer)).label("sessions_present")
    ).filter_by(course_code=course_code).group_by(AttendanceRecord.student_id).all()

    # Map student_id -> stats
    student_stats = {row.student_id: {"total": row.total_sessions, "present": row.sessions_present} for row in attendance_data}
    
    excellent = 0
    good = 0
    warning = 0
    defaulter = 0
    total_att_percent = 0.0
    students_with_records = 0

    for s in students:
        stats = student_stats.get(s.id)
        if not stats or stats["total"] == 0:
            # If no records, default them to 100% or 0% depending on policy.
            # Here we skip them for the average, but for categorization let's say they haven't attended.
            continue
            
        percent = (stats["present"] / stats["total"]) * 100.0
        total_att_percent += percent
        students_with_records += 1
        
        if percent >= 90:
            excellent += 1
        elif percent >= 75:
            good += 1
        elif percent >= 60:
            warning += 1
        else:
            defaulter += 1

    overall_attendance_percent = (total_att_percent / students_with_records) if students_with_records > 0 else 0.0

    # 2. Exam Analytics
    # Average score percentage for exams graded by this teacher
    marks_data = db.session.query(Mark).filter_by(teacher_id=u.teacher_id).all()
    total_marks_percent = 0.0
    if marks_data:
        for m in marks_data:
            if m.max_score > 0:
                total_marks_percent += (m.score / m.max_score) * 100.0
        average_exam_percent = total_marks_percent / len(marks_data)
    else:
        average_exam_percent = 0.0

    return jsonify({
        "course_code": course_code,
        "total_students": total_students,
        "overall_attendance_percent": round(overall_attendance_percent, 1),
        "attendance_breakdown": {
            "excellent": excellent,
            "good": good,
            "warning": warning,
            "defaulter": defaulter
        },
        "average_exam_percent": round(average_exam_percent, 1)
    })
