"""Marks: teachers record scores; students/parents read."""

from datetime import datetime

from flask import Blueprint, jsonify, request

from app.auth import require_login
from app.models import Mark, Student, User, Notification, db

marks_bp = Blueprint("marks", __name__)


@marks_bp.route("/list", methods=["GET"])
def list_marks():
    u, err = require_login()
    if err:
        return err
    if u.role == "parent":
        return jsonify([])

    sid = request.args.get("student_id", type=int)
    if u.role == "student" and u.student_id:
        sid = u.student_id

    q = Mark.query
    if u.role == "teacher" and u.teacher_id:
        q = q.filter(Mark.teacher_id == u.teacher_id)
        if sid:
            q = q.filter_by(student_id=sid)
    elif u.role == "admin":
        if sid:
            q = q.filter_by(student_id=sid)
    else:
        if not sid:
            return jsonify({"error": "student_id required"}), 400
        q = q.filter_by(student_id=sid)

    rows = q.order_by(Mark.graded_at.desc()).limit(200).all()
    out = []
    for m in rows:
        st = Student.query.get(m.student_id)
        out.append(
            {
                "id": m.id,
                "student_id": m.student_id,
                "student_name": st.name if st else "",
                "course_code": m.course_code,
                "exam_title": m.exam_title,
                "score": m.score,
                "max_score": m.max_score,
                "graded_at": m.graded_at.isoformat() if m.graded_at else "",
            }
        )
    return jsonify(out)


@marks_bp.route("/add", methods=["POST"])
def add_mark():
    u, err = require_login()
    if err:
        return err
    if u.role not in ("admin", "teacher"):
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    student_id = int(data.get("student_id", 0))
    course_code = (data.get("course_code") or "CS101").strip()
    exam_title = (data.get("exam_title") or "").strip()
    score = float(data.get("score", 0))
    max_score = float(data.get("max_score") or 100)
    if not student_id or not exam_title:
        return jsonify({"error": "student_id and exam_title required"}), 400
    m = Mark(
        student_id=student_id,
        teacher_id=u.teacher_id,
        course_code=course_code,
        exam_title=exam_title,
        score=score,
        max_score=max_score,
        graded_at=datetime.utcnow(),
    )
    db.session.add(m)
    
    # Create notifications
    st = Student.query.get(student_id)
    if st:
        # Notify student
        stu_user = User.query.filter_by(student_id=st.id).first()
        if stu_user:
            db.session.add(Notification(
                user_id=stu_user.id,
                title="New Marks Added",
                message=f"Marks for {course_code} - {exam_title} have been added: {score}/{max_score}",
                type="success" if score >= max_score*0.5 else "warning"
            ))
        # Notify parent
        if st.parent_id:
            parent_user = User.query.filter_by(parent_id=st.parent_id).first()
            if parent_user:
                db.session.add(Notification(
                    user_id=parent_user.id,
                    title="Student Marks Update",
                    message=f"{st.name} received marks for {course_code} - {exam_title}: {score}/{max_score}",
                    type="info"
                ))

    db.session.commit()
    return jsonify({"ok": True, "id": m.id})
