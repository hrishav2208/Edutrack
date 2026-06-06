"""Session-based authentication and biometric demo endpoints."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
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


import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

@auth_bp.route("/request-otp", methods=["POST"])
def request_otp():
    data = request.get_json(silent=True) or {}
    identifier = (data.get("identifier") or "").strip().lower()
    
    if not identifier:
        return jsonify({"error": "Identifier required"}), 400

    user = User.query.filter(
        db.or_(
            db.func.lower(User.uid) == identifier,
            User.email == identifier,
        )
    ).first()

    if not user:
        # Prevent user enumeration by acting like it sent
        return jsonify({"ok": True, "simulated": True})

    # Generate 6 digit OTP
    otp = str(random.randint(100000, 999999))
    user.current_otp = otp
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=5)
    db.session.commit()

    # Send Email via EmailJS API (Bypasses SMTP Blocks)
    emailjs_service_id = os.environ.get('EMAILJS_SERVICE_ID')
    emailjs_template_id = os.environ.get('EMAILJS_TEMPLATE_ID')
    emailjs_public_key = os.environ.get('EMAILJS_PUBLIC_KEY')
    recipient_email = user.email

    if emailjs_service_id and emailjs_template_id and emailjs_public_key and recipient_email:
        import urllib.request
        import urllib.error
        import json
        try:
            payload = {
                "service_id": emailjs_service_id,
                "template_id": emailjs_template_id,
                "user_id": emailjs_public_key,
                "template_params": {
                    "to_email": recipient_email,
                    "otp_code": otp
                }
            }
            req = urllib.request.Request(
                'https://api.emailjs.com/api/v1.0/email/send',
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                print(f"EmailJS Response: {response.status}")
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode('utf-8')
            print(f"EmailJS HTTP Error: {err_msg}")
            return jsonify({"error": f"EmailJS API Error: {err_msg}"}), 500
        except Exception as e:
            print(f"Failed to send email via EmailJS: {e}")
            return jsonify({"error": f"Failed to send OTP email: {e}"}), 500
    else:
        print(f"\n\n[WARNING] EmailJS keys missing or user has no email. Falling back to Admin Outbox. OTP for {identifier} is {otp}\n\n")

    return jsonify({"ok": True, "message": "OTP sent securely. Check your email or the Admin System Outbox."})

@auth_bp.route("/verify-otp-login", methods=["POST"])
def verify_otp_login():
    data = request.get_json(silent=True) or {}
    identifier = (data.get("identifier") or "").strip().lower()
    otp = (data.get("otp") or "").strip()

    if not identifier or not otp:
        return jsonify({"error": "Missing info"}), 400

    user = User.query.filter(
        db.or_(
            db.func.lower(User.uid) == identifier,
            User.email == identifier,
        )
    ).first()

    if not user or user.current_otp != otp:
        return jsonify({"error": "Invalid or expired OTP"}), 401

    if user.otp_expiry and datetime.utcnow() > user.otp_expiry:
        return jsonify({"error": "OTP has expired"}), 401

    # Valid OTP, log them in
    user.current_otp = None
    user.otp_expiry = None
    db.session.commit()

    session["user_id"] = user.id
    session["biometric_verified"] = False
    return jsonify({"ok": True, "user": _user_dict(user)})

@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json(silent=True) or {}
    identifier = (data.get("identifier") or "").strip().lower()
    otp = (data.get("otp") or "").strip()
    new_password = (data.get("new_password") or "").strip()

    if not identifier or not otp or not new_password:
        return jsonify({"error": "Missing info"}), 400

    user = User.query.filter(
        db.or_(
            db.func.lower(User.uid) == identifier,
            User.email == identifier,
        )
    ).first()

    if not user or user.current_otp != otp:
        return jsonify({"error": "Invalid or expired OTP"}), 401

    if user.otp_expiry and datetime.utcnow() > user.otp_expiry:
        return jsonify({"error": "OTP has expired"}), 401

    # Valid OTP, reset password
    user.password_hash = generate_password_hash(new_password)
    user.current_otp = None
    user.otp_expiry = None
    db.session.commit()

    return jsonify({"ok": True, "message": "Password updated successfully"})


@auth_bp.route("/admin/otp-logs", methods=["GET"])
def get_otp_logs():
    # Only allow admins to view OTP logs
    u = current_user()
    if not u or u.role != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
        
    try:
        now = datetime.utcnow()
        # Find all users with an active OTP
        users_with_otp = User.query.filter(User.current_otp.isnot(None), User.otp_expiry > now).all()
        
        logs = []
        for u in users_with_otp:
            logs.append({
                "identifier": u.uid or u.email,
                "role": u.role,
                "otp": u.current_otp,
                "expiry": u.otp_expiry.isoformat()
            })
            
        return jsonify({"logs": logs})
    except Exception as e:
        print(f"Error fetching OTP logs: {e}")
        return jsonify({"error": "Failed to fetch OTP logs"}), 500

