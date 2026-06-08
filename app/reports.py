import io
import csv
from flask import Blueprint, jsonify, request, Response
from sqlalchemy import func
from app.auth import require_login
from app.models import db, Student, Teacher, AttendanceRecord, Mark, User, AcademicEvent, ExamScheduleItem, ClassSession, SessionCheckIn

reports_bp = Blueprint("reports", __name__)


# ===================================================================
#  ADMIN STATS (Global College Metrics)
# ===================================================================

@reports_bp.route("/admin-stats", methods=["GET"])
def admin_stats():
    """Returns global stats for the Admin Dashboard."""
    u, err = require_login()
    if err:
        return err
    if u.role != "admin":
        return jsonify({"error": "Forbidden"}), 403

    # Total Students
    total_students = Student.query.count()

    # Active Teachers
    active_teachers = Teacher.query.count()

    # Avg Attendance
    total_sessions = AttendanceRecord.query.count()
    if total_sessions > 0:
        present_sessions = AttendanceRecord.query.filter_by(present=True).count()
        avg_attendance = round((present_sessions / total_sessions) * 100.0, 1)
    else:
        avg_attendance = 100.0

    # Defaulters (Students with overall attendance < 75%)
    # For a large DB we'd do a complex group_by query, but for now we calculate
    att_data = db.session.query(
        AttendanceRecord.student_id,
        func.count(AttendanceRecord.id).label("total"),
        func.sum(func.cast(AttendanceRecord.present, db.Integer)).label("present")
    ).group_by(AttendanceRecord.student_id).all()

    defaulters = 0
    for row in att_data:
        if row.total > 0:
            pct = (row.present / row.total) * 100.0
            if pct < 75.0:
                defaulters += 1

    # Placement Rate
    placed_students = Student.query.filter_by(is_placed=True).count()
    if total_students > 0:
        placement_rate = round((placed_students / total_students) * 100.0, 1)
    else:
        placement_rate = 0.0

    return jsonify({
        "total_students": total_students,
        "active_teachers": active_teachers,
        "avg_attendance": avg_attendance,
        "defaulters": defaulters,
        "placement_rate": placement_rate
    })

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

    student_details = []

    for s in students:
        stats = student_stats.get(s.id)
        if not stats or stats["total"] == 0:
            student_details.append({
                "id": s.id,
                "roll_no": s.roll_no,
                "name": s.name,
                "department": s.department,
                "percent": 0.0,
                "status": "No Records",
                "row_class": "neutral",
                "present": 0,
                "total": 0
            })
            continue
            
        percent = (stats["present"] / stats["total"]) * 100.0
        total_att_percent += percent
        students_with_records += 1
        
        row_class = "good"
        status_text = "Good"
        
        if percent >= 90:
            excellent += 1
            status_text = "Excellent"
        elif percent >= 75:
            good += 1
        elif percent >= 60:
            warning += 1
            status_text = "Warning"
            row_class = "warning"
        else:
            defaulter += 1
            status_text = "Defaulter"
            row_class = "danger"
            
        student_details.append({
            "id": s.id,
            "roll_no": s.roll_no,
            "name": s.name,
            "department": s.department,
            "percent": round(percent, 1),
            "status": status_text,
            "row_class": row_class,
            "present": stats["present"],
            "total": stats["total"]
        })

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
        "average_exam_percent": round(average_exam_percent, 1),
        "students": student_details
    })

@reports_bp.route("/public-stats", methods=["GET"])
def public_stats():
    # Public route for landing page
    total_students = Student.query.count()
    total_teachers = Teacher.query.count()
    
    # Calculate simple average placement rate
    if total_students > 0:
        placed = Student.query.filter_by(is_placed=True).count()
        placement_rate = round((placed / total_students) * 100.0, 1)
    else:
        placement_rate = 0.0

    return jsonify({
        "students_enrolled": total_students,
        "active_faculty": total_teachers,
        "avg_placement": placement_rate
    })


@reports_bp.route("/academic-calendar", methods=["GET"])
def academic_calendar():
    events = AcademicEvent.query.order_by(AcademicEvent.date.asc()).all()
    return jsonify([{
        "id": e.id,
        "title": e.title,
        "date": e.date.isoformat(),
        "description": e.description,
        "type": e.type
    } for e in events])

@reports_bp.route("/exam-schedule", methods=["GET"])
def exam_schedule():
    exams = ExamScheduleItem.query.order_by(ExamScheduleItem.exam_date.asc()).all()
    return jsonify([{
        "id": e.id,
        "course_code": e.course_code,
        "exam_title": e.exam_title,
        "exam_date": e.exam_date.isoformat()
    } for e in exams])

@reports_bp.route("/placement-stats", methods=["GET"])
def placement_stats():
    # Public or admin, let's keep it open or require login?
    # Simple implementation:
    total = Student.query.count()
    placed = Student.query.filter_by(is_placed=True).count()
    unplaced = total - placed
    rate = round((placed / total * 100.0) if total > 0 else 0, 1)
    
    return jsonify({
        "total_eligible": total,
        "placed": placed,
        "unplaced": unplaced,
        "placement_rate": rate
    })


# ===================================================================
#  ATTENDANCE CSV EXPORT
# ===================================================================

@reports_bp.route("/attendance/export-csv", methods=["GET"])
def export_attendance_csv():
    """Download attendance records as a CSV file. Teachers and admins only."""
    u, err = require_login()
    if err:
        return err
    if u.role not in ("admin", "teacher"):
        return jsonify({"error": "Forbidden"}), 403

    course_code = request.args.get("course_code", "CS101")
    date_from = request.args.get("from")  # optional YYYY-MM-DD
    date_to = request.args.get("to")      # optional YYYY-MM-DD

    query = (
        db.session.query(AttendanceRecord, Student)
        .join(Student, AttendanceRecord.student_id == Student.id)
        .filter(AttendanceRecord.course_code == course_code)
        .order_by(AttendanceRecord.session_date.asc(), Student.roll_no.asc())
    )
    if date_from:
        from datetime import date as dt_date
        query = query.filter(AttendanceRecord.session_date >= dt_date.fromisoformat(date_from))
    if date_to:
        from datetime import date as dt_date
        query = query.filter(AttendanceRecord.session_date <= dt_date.fromisoformat(date_to))

    rows = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Roll No", "Student Name", "Department", "Status", "Method"])
    for rec, stu in rows:
        writer.writerow([
            rec.session_date.isoformat(),
            stu.roll_no,
            stu.name,
            stu.department,
            "Present" if rec.present else "Absent",
            rec.method or "manual"
        ])

    csv_data = output.getvalue()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=attendance_{course_code}.csv"}
    )


# ===================================================================
#  SESSION HISTORY (past GPS class sessions)
# ===================================================================

@reports_bp.route("/session-history", methods=["GET"])
def session_history():
    """Get past completed sessions for the logged-in teacher, or all sessions for admin."""
    u, err = require_login()
    if err:
        return err
    if u.role not in ("admin", "teacher"):
        return jsonify({"error": "Forbidden"}), 403

    query = ClassSession.query.filter_by(is_active=False).order_by(ClassSession.started_at.desc())
    if u.role == "teacher" and u.teacher_id:
        query = query.filter_by(teacher_id=u.teacher_id)

    sessions = query.limit(50).all()
    result = []
    for s in sessions:
        teacher = Teacher.query.get(s.teacher_id)
        checkin_count = (
            db.session.query(SessionCheckIn.student_id)
            .filter_by(session_id=s.id, inside_radius=True)
            .distinct()
            .count()
        )
        duration_min = 0
        if s.ended_at and s.started_at:
            duration_min = round((s.ended_at - s.started_at).total_seconds() / 60, 1)

        result.append({
            "id": s.id,
            "course_code": s.course_code,
            "room_name": s.room_name,
            "teacher_name": teacher.name if teacher else "Unknown",
            "started_at": s.started_at.isoformat() + "Z",
            "ended_at": s.ended_at.isoformat() + "Z" if s.ended_at else None,
            "duration_minutes": duration_min,
            "checkin_count": checkin_count,
            "total_checkins": s.total_checkins or 0,
        })

    return jsonify(result)


# ===================================================================
#  STUDENT ATTENDANCE SUMMARY (real data per course)
# ===================================================================

@reports_bp.route("/student/attendance-summary", methods=["GET"])
def student_attendance_summary():
    """Get the logged-in student's attendance percentage per course."""
    u, err = require_login()
    if err:
        return err
    if u.role != "student" or not u.student_id:
        return jsonify({"error": "Only students can view their own summary"}), 403

    # Group attendance by course_code
    att_data = (
        db.session.query(
            AttendanceRecord.course_code,
            func.count(AttendanceRecord.id).label("total"),
            func.sum(func.cast(AttendanceRecord.present, db.Integer)).label("present")
        )
        .filter_by(student_id=u.student_id)
        .group_by(AttendanceRecord.course_code)
        .all()
    )

    courses = []
    overall_total = 0
    overall_present = 0
    for row in att_data:
        pct = round((row.present / row.total) * 100.0, 1) if row.total > 0 else 0.0
        courses.append({
            "course_code": row.course_code,
            "total_sessions": row.total,
            "present": row.present,
            "percentage": pct,
        })
        overall_total += row.total
        overall_present += row.present

    overall_pct = round((overall_present / overall_total) * 100.0, 1) if overall_total > 0 else 0.0

    return jsonify({
        "overall_percentage": overall_pct,
        "overall_total": overall_total,
        "overall_present": overall_present,
        "courses": courses,
    })
