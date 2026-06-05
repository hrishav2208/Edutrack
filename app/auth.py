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


def _user_dict(user):
    """Serialize a User object for API responses."""
    return {
        "id": user.id,
        "email": user.email,
        "uid": user.uid,
        "role": user.role,
        "display_name": user.display_name,
        "teacher_id": user.teacher_id,
        "student_id": user.student_id,
        "parent_id": user.parent_id,
    }


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    # Accept 'identifier' (uid or email) or legacy 'email' field
    identifier = (data.get("identifier") or data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not identifier:
        return jsonify({"error": "Identifier (UID or email) is required"}), 400

    # Try uid first, then fall back to email
    user = User.query.filter(
        db.or_(
            db.func.lower(User.uid) == identifier,
            User.email == identifier,
        )
    ).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid credentials"}), 401

    session["user_id"] = user.id
    session["biometric_verified"] = False
    return jsonify({"ok": True, "user": _user_dict(user)})


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@auth_bp.route("/me", methods=["GET"])
def me():
    u = current_user()
    if not u:
        return jsonify({"user": None})
    d = _user_dict(u)
    d["biometric_verified"] = session.get("biometric_verified", False)
    return jsonify({"user": d})


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
    if data.get("demo") is True or data.get("credential"):
        session["biometric_verified"] = True
        return jsonify({"ok": True, "verified": True})
    session["biometric_verified"] = True
    return jsonify({"ok": True, "verified": True})


@auth_bp.route("/biometric/login", methods=["POST"])
def biometric_login():
    """Passwordless demo: identifier (uid or email) must match a user."""
    data = request.get_json(silent=True) or {}
    identifier = (data.get("identifier") or data.get("email") or "").strip().lower()
    user = User.query.filter(
        db.or_(
            db.func.lower(User.uid) == identifier,
            User.email == identifier,
        )
    ).first()
    if not user:
        return jsonify({"error": "Unknown user"}), 404
    session["user_id"] = user.id
    session["biometric_verified"] = True
    return jsonify({"ok": True, "user": _user_dict(user)})
