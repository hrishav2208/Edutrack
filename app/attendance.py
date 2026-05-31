"""Attendance: manual entry, location check, optional face image verify."""

from datetime import date, datetime

from flask import Blueprint, jsonify, request

from app.auth import require_login
from app.face_recognition import haversine_m, verify_face_stub
from app.models import AttendanceRecord, CampusSettings, Student, User, Notification, db

attendance_bp = Blueprint("attendance", __name__)


def _campus():
    row = CampusSettings.query.get(1)
    if row:
        return row.lat, row.lng, row.radius_m
    from flask import current_app

    c = current_app.config
    return c["DEFAULT_CAMPUS_LAT"], c["DEFAULT_CAMPUS_LNG"], c["DEFAULT_CAMPUS_RADIUS_M"]


def _ensure_campus_row():
    if CampusSettings.query.get(1):
        return
    from flask import current_app

    c = current_app.config
    db.session.add(
        CampusSettings(
            id=1,
            lat=c["DEFAULT_CAMPUS_LAT"],
            lng=c["DEFAULT_CAMPUS_LNG"],
            radius_m=c["DEFAULT_CAMPUS_RADIUS_M"],
        )
    )
    db.session.commit()


@attendance_bp.route("/campus", methods=["GET"])
def get_campus():
    u, err = require_login()
    if err:
        return err
    _ensure_campus_row()
    row = CampusSettings.query.get(1)
    return jsonify({"lat": row.lat, "lng": row.lng, "radius_m": row.radius_m})


@attendance_bp.route("/campus", methods=["PUT"])
def put_campus():
    u, err = require_login()
    if err:
        return err
    if u.role != "admin":
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    _ensure_campus_row()
    row = CampusSettings.query.get(1)
    row.lat = float(data.get("lat", row.lat))
    row.lng = float(data.get("lng", row.lng))
    row.radius_m = float(data.get("radius_m", row.radius_m))
    row.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True, "lat": row.lat, "lng": row.lng, "radius_m": row.radius_m})


@attendance_bp.route("/verify-location", methods=["POST"])
def verify_location():
    u, err = require_login()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    lat = float(data.get("lat", 0))
    lng = float(data.get("lng", 0))
    clat, clng, radius = _campus()
    d = haversine_m(lat, lng, clat, clng)
    ok = d <= radius
    return jsonify(
        {
            "ok": ok,
            "distance_m": round(d, 1),
            "radius_m": radius,
            "campus": {"lat": clat, "lng": clng},
            "message": "Inside campus boundary" if ok else "Outside allowed radius — contact admin to update campus GPS.",
        }
    )


@attendance_bp.route("/manual", methods=["GET"])
def list_manual():
    u, err = require_login()
    if err:
        return err
    if u.role not in ("admin", "teacher"):
        return jsonify({"error": "Forbidden"}), 403
    course = request.args.get("course_code", "CS101")
    day = request.args.get("date")
    session_date = date.fromisoformat(day) if day else date.today()
    q = AttendanceRecord.query.filter_by(course_code=course, session_date=session_date)
    rows = q.all()
    present_map = {r.student_id: r.present for r in rows}
    students = Student.query.order_by(Student.roll_no).all()
    out = []
    for s in students:
        out.append(
            {
                "id": s.id,
                "roll_no": s.roll_no,
                "name": s.name,
                "department": s.department,
                "present": present_map.get(s.id, None),
            }
        )
    return jsonify({"course_code": course, "session_date": session_date.isoformat(), "students": out})


@attendance_bp.route("/manual", methods=["POST"])
def save_manual():
    u, err = require_login()
    if err:
        return err
    if u.role not in ("admin", "teacher"):
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    course_code = data.get("course_code", "CS101")
    day = data.get("date")
    session_date = date.fromisoformat(day) if day else date.today()
    entries = data.get("entries") or []  # [{ "student_id": 1, "present": true }, ...]

    for e in entries:
        sid = int(e["student_id"])
        present = bool(e.get("present", True))
        rec = AttendanceRecord.query.filter_by(
            student_id=sid, course_code=course_code, session_date=session_date
        ).first()
        if rec:
            rec.present = present
            rec.method = "manual"
        else:
            db.session.add(
                AttendanceRecord(
                    student_id=sid,
                    course_code=course_code,
                    session_date=session_date,
                    present=present,
                    method="manual",
                )
            )
            
        # Notifications for absent students
        if not present:
            st = Student.query.get(sid)
            if st:
                stu_user = User.query.filter_by(student_id=st.id).first()
                if stu_user:
                    db.session.add(Notification(
                        user_id=stu_user.id,
                        title="Attendance Alert",
                        message=f"You have been marked ABSENT for {course_code} on {session_date}",
                        type="danger"
                    ))
                if st.parent_id:
                    parent_user = User.query.filter_by(parent_id=st.parent_id).first()
                    if parent_user:
                        db.session.add(Notification(
                            user_id=parent_user.id,
                            title="Student Absent Alert",
                            message=f"{st.name} was marked ABSENT for {course_code} on {session_date}",
                            type="danger"
                        ))

    db.session.commit()
    return jsonify({"ok": True, "saved": len(entries)})


@attendance_bp.route("/mark-combined", methods=["POST"])
def mark_combined():
    """Student marks attendance with both GPS and Face recognition combined."""
    u, err = require_login()
    if err:
        return err
    if u.role != "student" or not u.student_id:
        return jsonify({"error": "Only students with linked profile"}), 403
        
    lat = float(request.form.get("lat", 0))
    lng = float(request.form.get("lng", 0))
    course_code = request.form.get("course_code", "CS101")
    
    # 1. Verify GPS Location
    clat, clng, radius = _campus()
    d = haversine_m(lat, lng, clat, clng)
    if d > radius:
        return jsonify({"ok": False, "reason": f"Outside campus radius ({round(d, 1)}m away)"}), 400
        
    # 2. Verify Face Image
    image = request.files.get("image")
    raw = image.read() if image else None
    ok, reason = verify_face_stub(raw)
    if not ok:
        return jsonify({"ok": False, "reason": f"Face verification failed: {reason}"}), 400
        
    # 3. Save Attendance
    session_date = date.today()
    rec = AttendanceRecord.query.filter_by(
        student_id=u.student_id, course_code=course_code, session_date=session_date
    ).first()
    if rec:
        rec.present = True
        rec.method = "gps_face"
    else:
        db.session.add(
            AttendanceRecord(
                student_id=u.student_id,
                course_code=course_code,
                session_date=session_date,
                present=True,
                method="gps_face",
            )
        )
        
    # Notification for successful self-attendance
    db.session.add(Notification(
        user_id=u.id,
        title="Attendance Marked",
        message=f"You successfully marked your attendance for {course_code} today.",
        type="success"
    ))
    db.session.commit()
    
    return jsonify({"ok": True, "distance_m": round(d, 1)})
