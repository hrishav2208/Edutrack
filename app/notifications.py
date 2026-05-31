from flask import Blueprint, jsonify, request
from app.auth import require_login
from app.models import Notification, db

notifications_bp = Blueprint("notifications", __name__)

@notifications_bp.route("/list", methods=["GET"])
def list_notifications():
    u, err = require_login()
    if err:
        return err
    notifs = Notification.query.filter_by(user_id=u.id).order_by(Notification.created_at.desc()).limit(20).all()
    out = []
    for n in notifs:
        out.append({
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat()
        })
    return jsonify(out)

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
