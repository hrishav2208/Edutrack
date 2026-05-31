"""Session-based authentication and biometric demo endpoints."""

from flask import Blueprint, jsonify, request, session

from werkzeug.security import check_password_hash

from app.models import User, db

auth_bp = Blueprint("auth", __name__)


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.get(uid)


def require_login():
    u = current_user()
    if not u:
        return None, (jsonify({"error": "Unauthorized"}), 401)
    return u, None


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password"}), 401

    session["user_id"] = user.id
    session["biometric_verified"] = False
    return jsonify(
        {
            "ok": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "display_name": user.display_name,
                "teacher_id": user.teacher_id,
                "student_id": user.student_id,
                "parent_id": user.parent_id,
            },
        }
    )


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@auth_bp.route("/me", methods=["GET"])
def me():
    u = current_user()
    if not u:
        return jsonify({"user": None})
    return jsonify(
        {
            "user": {
                "id": u.id,
                "email": u.email,
                "role": u.role,
                "display_name": u.display_name,
                "teacher_id": u.teacher_id,
                "student_id": u.student_id,
                "parent_id": u.parent_id,
                "biometric_verified": session.get("biometric_verified", False),
            }
        }
    )


@auth_bp.route("/biometric/challenge", methods=["POST"])
def biometric_challenge():
    """Demo: returns a fake challenge; real WebAuthn would use py_webauthn."""
    u, err = require_login()
    if err:
        return err
    return jsonify({"challenge": "demo-challenge", "rpId": request.host.split(":")[0]})


@auth_bp.route("/biometric/verify", methods=["POST"])
def biometric_verify():
    """Demo biometric completion (device attestation would go here in production)."""
    u, err = require_login()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    # Accept explicit demo flag from trusted UI, or pretend success on any POST after login
    if data.get("demo") is True or data.get("credential"):
        session["biometric_verified"] = True
        return jsonify({"ok": True, "verified": True})
    session["biometric_verified"] = True
    return jsonify({"ok": True, "verified": True})


@auth_bp.route("/biometric/login", methods=["POST"])
def biometric_login():
    """Passwordless demo: email must match a user; sets session without password."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Unknown user"}), 404
    session["user_id"] = user.id
    session["biometric_verified"] = True
    return jsonify(
        {
            "ok": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "display_name": user.display_name,
                "teacher_id": user.teacher_id,
                "student_id": user.student_id,
                "parent_id": user.parent_id,
            },
        }
    )
