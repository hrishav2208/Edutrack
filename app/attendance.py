"""Attendance: manual entry, location check, optional face image verify, and live session management."""

from datetime import date, datetime

from flask import Blueprint, jsonify, request

from app.auth import require_login
from app.face_recognition import haversine_m, verify_face_stub
from app.models import (
    AttendanceRecord,
    CampusSettings,
    ClassSession,
    SessionCheckIn,
    Student,
    User,
    Notification,
    db,
)

attendance_bp = Blueprint("attendance", __name__)


def _campus():
    row = CampusSettings.query.get(1)
    if row:
        return row.lat, row.lng, row.radius_m
    from flask import current_app

    c = current_app.config
    return (
        c["DEFAULT_CAMPUS_LAT"],
        c["DEFAULT_CAMPUS_LNG"],
        c["DEFAULT_CAMPUS_RADIUS_M"],
    )


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
    return jsonify(
        {"ok": True, "lat": row.lat, "lng": row.lng, "radius_m": row.radius_m}
    )


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
            "message": (
                "Inside campus boundary"
                if ok
                else "Outside allowed radius — contact admin to update campus GPS."
            ),
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
    q = AttendanceRecord.query.filter_by(
        course_code=course, session_date=session_date
    )
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
    return jsonify(
        {
            "course_code": course,
            "session_date": session_date.isoformat(),
            "students": out,
        }
    )


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
    entries = (
        data.get("entries") or []
    )  # [{ "student_id": 1, "present": true }, ...]

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
                    db.session.add(
                        Notification(
                            user_id=stu_user.id,
                            title="Attendance Alert",
                            message=f"You have been marked ABSENT for {course_code} on {session_date}",
                            type="danger",
                        )
                    )
                if st.parent_id:
                    parent_user = User.query.filter_by(
                        parent_id=st.parent_id
                    ).first()
                    if parent_user:
                        db.session.add(
                            Notification(
                                user_id=parent_user.id,
                                title="Student Absent Alert",
                                message=f"{st.name} was marked ABSENT for {course_code} on {session_date}",
                                type="danger",
                            )
                        )

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
        return (
            jsonify(
                {
                    "ok": False,
                    "reason": f"Outside campus radius ({round(d, 1)}m away)",
                }
            ),
            400,
        )

    # 2. Verify Face Image
    image = request.files.get("image")
    raw = image.read() if image else None
    ok, reason = verify_face_stub(raw)
    if not ok:
        return (
            jsonify(
                {"ok": False, "reason": f"Face verification failed: {reason}"}
            ),
            400,
        )

    # 3. Save Attendance
    session_date = date.today()
    rec = AttendanceRecord.query.filter_by(
        student_id=u.student_id,
        course_code=course_code,
        session_date=session_date,
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
    db.session.add(
        Notification(
            user_id=u.id,
            title="Attendance Marked",
            message=f"You successfully marked your attendance for {course_code} today.",
            type="success",
        )
    )
    db.session.commit()

    return jsonify({"ok": True, "distance_m": round(d, 1)})


# ===================================================================
#  LIVE SESSION MANAGEMENT — GPS Classroom Geofencing
# ===================================================================


@attendance_bp.route("/session/start", methods=["POST"])
def session_start():
    """Teacher starts a live class session. Creates a GPS geofence around the classroom."""
    u, err = require_login()
    if err:
        return err
    if u.role != "teacher" or not u.teacher_id:
        return jsonify({"error": "Only teachers can start sessions"}), 403

    data = request.get_json(silent=True) or {}
    lat = float(data.get("lat", 0))
    lng = float(data.get("lng", 0))
    course_code = data.get("course_code", "CS101")
    room_name = data.get("room_name", "Classroom")
    radius_m = float(data.get("radius_m", 20.0))

    if lat == 0 and lng == 0:
        return (
            jsonify(
                {"error": "GPS coordinates required. Allow location access."}
            ),
            400,
        )

    # End any existing active session for this teacher
    existing = ClassSession.query.filter_by(
        teacher_id=u.teacher_id, is_active=True
    ).all()
    for s in existing:
        s.is_active = False
        s.ended_at = datetime.utcnow()

    # Create the new session
    session = ClassSession(
        teacher_id=u.teacher_id,
        course_code=course_code,
        room_name=room_name,
        lat=lat,
        lng=lng,
        radius_m=radius_m,
    )
    db.session.add(session)
    db.session.flush()  # get session.id

    # Notify all students that class has begun
    students = Student.query.all()
    for st in students:
        stu_user = User.query.filter_by(student_id=st.id).first()
        if stu_user:
            db.session.add(
                Notification(
                    user_id=stu_user.id,
                    title="Class Started",
                    message=f"{course_code} has begun in {room_name}. Open EduTrack to mark your attendance.",
                    type="info",
                )
            )

    db.session.commit()

    return jsonify(
        {
            "ok": True,
            "session_id": session.id,
            "course_code": course_code,
            "room_name": room_name,
            "lat": lat,
            "lng": lng,
            "radius_m": radius_m,
        }
    )


@attendance_bp.route("/session/end", methods=["POST"])
def session_end():
    """Teacher ends the active class session."""
    u, err = require_login()
    if err:
        return err
    if u.role not in ("teacher", "admin"):
        return jsonify({"error": "Only teachers or admins can end sessions"}), 403

    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")

    if session_id:
        session = ClassSession.query.get(session_id)
    elif u.teacher_id:
        session = ClassSession.query.filter_by(
            teacher_id=u.teacher_id, is_active=True
        ).first()
    else:
        # Admin without teacher_id — try to find any active session
        session = ClassSession.query.filter_by(is_active=True).first()

    if not session:
        return jsonify({"error": "No active session found"}), 404

    if not session.is_active:
        return jsonify({"error": "Session already ended"}), 400

    session.is_active = False
    session.ended_at = datetime.utcnow()

    # Count unique students who checked in
    unique_students = (
        db.session.query(SessionCheckIn.student_id)
        .filter_by(session_id=session.id)
        .distinct()
        .count()
    )
    session.total_checkins = unique_students

    # Also mark attendance records for students who checked in
    checked_student_ids = [
        r[0]
        for r in db.session.query(SessionCheckIn.student_id)
        .filter_by(session_id=session.id, inside_radius=True)
        .distinct()
        .all()
    ]

    for sid in checked_student_ids:
        rec = AttendanceRecord.query.filter_by(
            student_id=sid,
            course_code=session.course_code,
            session_date=date.today(),
        ).first()
        if not rec:
            db.session.add(
                AttendanceRecord(
                    student_id=sid,
                    course_code=session.course_code,
                    session_date=date.today(),
                    present=True,
                    method="gps_session",
                )
            )

    db.session.commit()

    return jsonify(
        {
            "ok": True,
            "session_id": session.id,
            "total_checkins": unique_students,
            "duration_minutes": round(
                (session.ended_at - session.started_at).total_seconds() / 60, 1
            ),
        }
    )


@attendance_bp.route("/session/active", methods=["GET"])
def session_active():
    """Get currently active session(s). Students use this to know if a class is running."""
    u, err = require_login()
    if err:
        return err

    sessions = (
        ClassSession.query.filter_by(is_active=True)
        .order_by(ClassSession.started_at.desc())
        .all()
    )

    if not sessions:
        return jsonify({"active": False, "sessions": []})

    result = []
    for s in sessions:
        # Count students checked in so far
        checked_in = (
            db.session.query(SessionCheckIn.student_id)
            .filter_by(session_id=s.id)
            .distinct()
            .count()
        )

        # Check if current student already checked in
        already_checked = False
        if u.student_id:
            already_checked = (
                SessionCheckIn.query.filter_by(
                    session_id=s.id,
                    student_id=u.student_id,
                    check_type="initial",
                ).first()
                is not None
            )

        recent_checkins = []
        if u.role in ("teacher", "admin"):
            checkins_db = (
                db.session.query(SessionCheckIn, Student.roll_no, Student.name)
                .join(Student, SessionCheckIn.student_id == Student.id)
                .filter(SessionCheckIn.session_id == s.id)
                .order_by(SessionCheckIn.checked_at.desc())
                .all()
            )
            student_attempts = {}
            for ci, roll_no, name in checkins_db:
                if ci.student_id not in student_attempts:
                    student_attempts[ci.student_id] = {
                        "roll_no": roll_no,
                        "name": name,
                        "inside_radius": ci.inside_radius,
                        "distance_m": ci.distance_m,
                        "checked_at": ci.checked_at.isoformat() + "Z"
                    }
            recent_checkins = list(student_attempts.values())

        result.append(
            {
                "session_id": s.id,
                "course_code": s.course_code,
                "room_name": s.room_name,
                "lat": s.lat,
                "lng": s.lng,
                "radius_m": s.radius_m,
                "started_at": s.started_at.isoformat(),
                "checked_in_count": checked_in,
                "already_checked_in": already_checked,
                "recent_checkins": recent_checkins,
            }
        )

    return jsonify({"active": True, "sessions": result})


@attendance_bp.route("/session/checkin", methods=["POST"])
def session_checkin():
    """Student initial check-in: GPS + selfie photo verification."""
    u, err = require_login()
    if err:
        return err
    if u.role != "student" or not u.student_id:
        return jsonify({"error": "Only students can check in"}), 403

    lat = float(request.form.get("lat", 0))
    lng = float(request.form.get("lng", 0))
    session_id = int(request.form.get("session_id", 0))

    session = ClassSession.query.get(session_id)
    if not session or not session.is_active:
        return jsonify({"ok": False, "reason": "No active session found"}), 400

    # 1. Check GPS distance from classroom center
    d = haversine_m(lat, lng, session.lat, session.lng)
    inside = d <= session.radius_m

    if not inside:
        # Log the failed attempt so teachers can see who tried
        db.session.add(
            SessionCheckIn(
                session_id=session.id,
                student_id=u.student_id,
                lat=lat,
                lng=lng,
                inside_radius=False,
                distance_m=round(d, 1),
                check_type="initial",
            )
        )
        db.session.commit()
        return (
            jsonify(
                {
                    "ok": False,
                    "reason": f"You are {round(d, 1)}m away from the classroom. Required: within {session.radius_m}m.",
                }
            ),
            400,
        )

    # 2. Verify selfie (face present)
    image = request.files.get("image")
    raw = image.read() if image else None
    ok, reason = verify_face_stub(raw)
    if not ok:
        return (
            jsonify(
                {"ok": False, "reason": f"Face verification failed: {reason}"}
            ),
            400,
        )

    # 3. Log the check-in
    db.session.add(
        SessionCheckIn(
            session_id=session.id,
            student_id=u.student_id,
            lat=lat,
            lng=lng,
            inside_radius=True,
            distance_m=round(d, 1),
            check_type="initial",
        )
    )

    # 4. Notification to student
    db.session.add(
        Notification(
            user_id=u.id,
            title="Attendance Confirmed",
            message=f"You checked in to {session.course_code} ({session.room_name}). Distance: {round(d, 1)}m.",
            type="success",
        )
    )

    db.session.commit()

    return jsonify(
        {
            "ok": True,
            "session_id": session.id,
            "distance_m": round(d, 1),
            "message": "Attendance marked successfully. Background checks will verify your presence.",
        }
    )


@attendance_bp.route("/session/ping", methods=["POST"])
def session_ping():
    """Background random GPS ping from student. No photo required — battery efficient."""
    u, err = require_login()
    if err:
        return err
    if u.role != "student" or not u.student_id:
        return jsonify({"error": "Only students can ping"}), 403

    data = request.get_json(silent=True) or {}
    lat = float(data.get("lat", 0))
    lng = float(data.get("lng", 0))
    session_id = int(data.get("session_id", 0))

    session = ClassSession.query.get(session_id)
    if not session or not session.is_active:
        return jsonify(
            {"ok": False, "active": False, "reason": "Session ended"}
        )

    d = haversine_m(lat, lng, session.lat, session.lng)
    inside = d <= session.radius_m

    # Log the ping
    db.session.add(
        SessionCheckIn(
            session_id=session.id,
            student_id=u.student_id,
            lat=lat,
            lng=lng,
            inside_radius=inside,
            distance_m=round(d, 1),
            check_type="ping",
        )
    )

    # If student is outside the radius, notify the teacher
    if not inside:
        student = Student.query.get(u.student_id)
        teacher_user = User.query.filter_by(
            teacher_id=session.teacher_id
        ).first()
        if teacher_user and student:
            db.session.add(
                Notification(
                    user_id=teacher_user.id,
                    title="Student Left Classroom",
                    message=f"{student.name} ({student.roll_no}) may have left {session.room_name}. Distance: {round(d, 1)}m.",
                    type="warning",
                )
            )

    db.session.commit()

    return jsonify(
        {
            "ok": True,
            "active": session.is_active,
            "inside": inside,
            "distance_m": round(d, 1),
        }
    )
