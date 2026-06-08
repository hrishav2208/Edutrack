"""Notifications & in-app messaging API."""

from flask import Blueprint, jsonify, request
from app.auth import require_login
from app.models import Notification, Message, User, Student, Teacher, Parent, db
from datetime import datetime

notifications_bp = Blueprint("notifications", __name__)


# ─── Notifications ────────────────────────────────────────────────────────────

@notifications_bp.route("/list", methods=["GET"])
def list_notifications():
    u, err = require_login()
    if err:
        return err
    notifs = (
        Notification.query
        .filter_by(user_id=u.id)
        .order_by(Notification.created_at.desc())
        .limit(30)
        .all()
    )
    return jsonify([{
        "id": n.id,
        "title": n.title,
        "message": n.message,
        "type": n.type,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat()
    } for n in notifs])


@notifications_bp.route("/unread-count", methods=["GET"])
def unread_count():
    u, err = require_login()
    if err:
        return jsonify({"count": 0})
    count = Notification.query.filter_by(user_id=u.id, is_read=False).count()
    return jsonify({"count": count})


@notifications_bp.route("/mark-read", methods=["POST"])
def mark_read():
    u, err = require_login()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    notif_id = data.get("id")
    if notif_id:
        n = Notification.query.filter_by(id=notif_id, user_id=u.id).first()
        if n:
            n.is_read = True
            db.session.commit()
    else:
        Notification.query.filter_by(user_id=u.id).update({"is_read": True})
        db.session.commit()
    return jsonify({"ok": True})


# ─── Messages ─────────────────────────────────────────────────────────────────

def _msg_dict(msg, sender_name=None):
    return {
        "id": msg.id,
        "sender_id": msg.sender_id,
        "sender_name": sender_name or (msg.sender.display_name if msg.sender else "Unknown"),
        "recipient_id": msg.recipient_id,
        "recipient_role": msg.recipient_role,
        "recipient_dept": msg.recipient_dept,
        "subject": msg.subject,
        "body": msg.body,
        "is_read": msg.is_read,
        "sent_at": msg.sent_at.isoformat(),
    }


def _create_notification(user_id, title, message, notif_type="info"):
    """Helper to create a notification for a user."""
    db.session.add(Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notif_type,
    ))


@notifications_bp.route("/messages/send", methods=["POST"])
def send_message():
    """Send a message to an individual or group. Admin/Teacher only."""
    u, err = require_login()
    if err:
        return err
    if u.role not in ("admin", "teacher"):
        return jsonify({"error": "Only admins and teachers can send messages"}), 403

    data = request.get_json(silent=True) or {}
    subject = (data.get("subject") or "").strip()
    body = (data.get("body") or "").strip()
    target_type = data.get("target_type", "")  # 'user' | 'role' | 'dept'
    target_value = data.get("target_value", "")  # user_id | role string | dept string

    if not body:
        return jsonify({"error": "Message body is required"}), 400
    if not target_type or not target_value:
        return jsonify({"error": "Target is required"}), 400

    # Teacher restrictions: cannot message admin or other teachers
    if u.role == "teacher" and target_type == "role" and target_value in ("admin", "teacher"):
        return jsonify({"error": "Teachers cannot message admins or other teachers"}), 403

    recipients = []  # list of User objects who will receive this

    if target_type == "user":
        recipient_user = User.query.get(int(target_value))
        if not recipient_user:
            return jsonify({"error": "Recipient not found"}), 404
        # Teachers cannot message admins or other teachers
        if u.role == "teacher" and recipient_user.role in ("admin", "teacher"):
            return jsonify({"error": "Teachers cannot message admins or other teachers"}), 403

        msg = Message(
            sender_id=u.id,
            recipient_id=recipient_user.id,
            subject=subject,
            body=body,
        )
        db.session.add(msg)
        db.session.flush()
        recipients = [recipient_user]

    elif target_type == "role":
        role_filter = target_value  # 'student', 'teacher', 'parent', 'all'
        if role_filter == "all":
            users = User.query.filter(User.id != u.id).all()
        else:
            users = User.query.filter_by(role=role_filter).all()

        msg = Message(
            sender_id=u.id,
            recipient_role=role_filter,
            subject=subject,
            body=body,
        )
        db.session.add(msg)
        db.session.flush()
        recipients = users

    elif target_type == "dept":
        dept = target_value.strip().upper()
        # Find all students and teachers in that department
        student_users = (
            db.session.query(User)
            .join(Student, User.student_id == Student.id)
            .filter(Student.department == dept)
            .all()
        )
        teacher_users = (
            db.session.query(User)
            .join(Teacher, User.teacher_id == Teacher.id)
            .filter(Teacher.department == dept)
            .all()
        )
        users = list({usr.id: usr for usr in student_users + teacher_users}.values())

        msg = Message(
            sender_id=u.id,
            recipient_dept=dept,
            subject=subject,
            body=body,
        )
        db.session.add(msg)
        db.session.flush()
        recipients = users

    else:
        return jsonify({"error": "Invalid target_type"}), 400

    # Fan-out notifications to each recipient
    notif_title = f"📨 New message from {u.display_name}"
    notif_body = subject if subject else body[:80]
    for rec in recipients:
        _create_notification(rec.id, notif_title, notif_body, "info")

    db.session.commit()
    return jsonify({"ok": True, "recipients_count": len(recipients)})


@notifications_bp.route("/messages/inbox", methods=["GET"])
def inbox():
    """Messages received by the current user."""
    u, err = require_login()
    if err:
        return err

    # Direct messages to this user
    direct = Message.query.filter_by(recipient_id=u.id).all()

    # Broadcast messages by role
    role_msgs = Message.query.filter(
        Message.recipient_id == None,
        Message.sender_id != u.id,
        db.or_(
            Message.recipient_role == u.role,
            Message.recipient_role == "all",
        )
    ).all()

    # Broadcast messages by department
    dept_msgs = []
    if u.role == "student" and u.student_id:
        stu = Student.query.get(u.student_id)
        if stu:
            dept_msgs = Message.query.filter(
                Message.recipient_id == None,
                Message.recipient_role == None,
                Message.recipient_dept == stu.department,
                Message.sender_id != u.id,
            ).all()
    elif u.role == "teacher" and u.teacher_id:
        tch = Teacher.query.get(u.teacher_id)
        if tch:
            dept_msgs = Message.query.filter(
                Message.recipient_id == None,
                Message.recipient_role == None,
                Message.recipient_dept == tch.department,
                Message.sender_id != u.id,
            ).all()

    # Deduplicate and sort
    seen = set()
    all_msgs = []
    for m in sorted(direct + role_msgs + dept_msgs, key=lambda x: x.sent_at, reverse=True):
        if m.id not in seen:
            seen.add(m.id)
            all_msgs.append(m)

    return jsonify([_msg_dict(m) for m in all_msgs])


@notifications_bp.route("/messages/sent", methods=["GET"])
def sent_messages():
    """Messages sent by the current user."""
    u, err = require_login()
    if err:
        return err
    msgs = (
        Message.query
        .filter_by(sender_id=u.id)
        .order_by(Message.sent_at.desc())
        .limit(50)
        .all()
    )
    return jsonify([_msg_dict(m) for m in msgs])


@notifications_bp.route("/messages/mark-read/<int:msg_id>", methods=["POST"])
def mark_message_read(msg_id):
    u, err = require_login()
    if err:
        return err
    msg = Message.query.filter_by(id=msg_id, recipient_id=u.id).first()
    if msg:
        msg.is_read = True
        db.session.commit()
    return jsonify({"ok": True})


@notifications_bp.route("/messages/recipients", methods=["GET"])
def get_recipients():
    """Return a list of users that the current user can message."""
    u, err = require_login()
    if err:
        return err
    if u.role == "admin":
        users = User.query.filter(User.id != u.id).order_by(User.display_name).all()
    elif u.role == "teacher":
        # Teachers can message students and parents only
        users = User.query.filter(
            User.id != u.id,
            User.role.in_(["student", "parent"])
        ).order_by(User.display_name).all()
    else:
        return jsonify([])

    return jsonify([{
        "id": usr.id,
        "display_name": usr.display_name,
        "role": usr.role,
        "email": usr.email,
        "uid": usr.uid,
    } for usr in users])
