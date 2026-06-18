from datetime import date, datetime
from flask import Blueprint, jsonify, request
from app.models import db, TimetableEntry, User, Student, Teacher, AttendanceRecord
from app.auth import require_login

timetable_bp = Blueprint("timetable", __name__)

@timetable_bp.route("/", methods=["GET"])
def get_timetable():
    current_user, err = require_login()
    if err:
        return err
    """
    Get timetable entries based on user role.
    Supports ?day=Monday filter or ?date=YYYY-MM-DD
    """
    day_filter = request.args.get("day")
    date_filter = request.args.get("date")

    query = TimetableEntry.query

    if current_user.role == "student":
        student = Student.query.get(current_user.student_id)
        if not student:
            return jsonify({"error": "Student profile not found"}), 404
        query = query.filter_by(department=student.department)
    elif current_user.role == "teacher":
        query = query.filter_by(teacher_id=current_user.teacher_id)
    # Admin gets all (can optionally filter via UI)

    if day_filter:
        query = query.filter_by(day_of_week=day_filter)

    entries = query.order_by(TimetableEntry.start_time).all()

    results = []
    for entry in entries:
        teacher = Teacher.query.get(entry.teacher_id)
        teacher_name = teacher.name if teacher else "Unknown"

        data = {
            "id": entry.id,
            "day_of_week": entry.day_of_week,
            "start_time": entry.start_time.strftime("%H:%M"),
            "end_time": entry.end_time.strftime("%H:%M"),
            "course_code": entry.course_code,
            "teacher_id": entry.teacher_id,
            "teacher_name": teacher_name,
            "department": entry.department,
            "room_name": entry.room_name,
            "is_temporary": entry.is_temporary,
            "temporary_date": entry.temporary_date.isoformat() if entry.temporary_date else None
        }

        # If student, attach attendance info if fetching for a specific date (or today)
        if current_user.role == "student":
            target_date = None
            if date_filter:
                try:
                    target_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
                except:
                    pass
            elif not day_filter or day_filter == date.today().strftime("%A"):
                # Default to today if no filter or today's day
                target_date = date.today()

            if target_date:
                # Check if there's an attendance record for this course code today
                att = AttendanceRecord.query.filter_by(
                    student_id=student.id,
                    course_code=entry.course_code,
                    session_date=target_date
                ).first()
                if att:
                    data["attendance_status"] = "Attended" if att.present else "Absent"
                else:
                    data["attendance_status"] = "Pending"

        results.append(data)

    return jsonify({"timetable": results}), 200


@timetable_bp.route("/", methods=["POST"])
def create_entry():
    current_user, err = require_login()
    if err:
        return err

    if current_user.role not in ["admin", "teacher"]:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    try:
        new_entry = TimetableEntry(
            day_of_week=data["day_of_week"],
            start_time=datetime.strptime(data["start_time"], "%H:%M").time(),
            end_time=datetime.strptime(data["end_time"], "%H:%M").time(),
            course_code=data["course_code"],
            teacher_id=data.get("teacher_id", current_user.teacher_id),
            department=data["department"],
            room_name=data.get("room_name", ""),
            is_temporary=data.get("is_temporary", False)
        )
        if new_entry.is_temporary and data.get("temporary_date"):
            new_entry.temporary_date = datetime.strptime(data["temporary_date"], "%Y-%m-%d").date()

        db.session.add(new_entry)
        db.session.commit()
        return jsonify({"message": "Timetable entry created", "id": new_entry.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


@timetable_bp.route("/<int:entry_id>", methods=["PUT"])
def update_entry(entry_id):
    current_user, err = require_login()
    if err:
        return err

    if current_user.role not in ["admin", "teacher"]:
        return jsonify({"error": "Unauthorized"}), 403

    entry = TimetableEntry.query.get_or_404(entry_id)
    
    # Teachers can only edit their own entries
    if current_user.role == "teacher" and entry.teacher_id != current_user.teacher_id:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    try:
        if "day_of_week" in data: entry.day_of_week = data["day_of_week"]
        if "start_time" in data: entry.start_time = datetime.strptime(data["start_time"], "%H:%M").time()
        if "end_time" in data: entry.end_time = datetime.strptime(data["end_time"], "%H:%M").time()
        if "course_code" in data: entry.course_code = data["course_code"]
        if "teacher_id" in data and current_user.role == "admin": 
            entry.teacher_id = data["teacher_id"]
        if "department" in data: entry.department = data["department"]
        if "room_name" in data: entry.room_name = data["room_name"]
        if "is_temporary" in data: entry.is_temporary = data["is_temporary"]
        if "temporary_date" in data: 
            entry.temporary_date = datetime.strptime(data["temporary_date"], "%Y-%m-%d").date() if data["temporary_date"] else None

        db.session.commit()
        return jsonify({"message": "Timetable entry updated"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


@timetable_bp.route("/<int:entry_id>", methods=["DELETE"])
def delete_entry(entry_id):
    current_user, err = require_login()
    if err:
        return err

    if current_user.role not in ["admin", "teacher"]:
        return jsonify({"error": "Unauthorized"}), 403

    entry = TimetableEntry.query.get_or_404(entry_id)
    
    if current_user.role == "teacher" and entry.teacher_id != current_user.teacher_id:
        return jsonify({"error": "Unauthorized"}), 403

    db.session.delete(entry)
    db.session.commit()
    return jsonify({"message": "Timetable entry deleted"}), 200
