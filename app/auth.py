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

    # Send Email via SMTP
    sender_email = os.environ.get('MAIL_USERNAME')
    sender_password = os.environ.get('MAIL_PASSWORD')
    smtp_server = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('MAIL_PORT', 587))
    
    recipient_email = user.email

    if sender_email and sender_password and recipient_email:
        try:
            msg = MIMEMultipart()
            msg['From'] = f"EduTrack Support <{sender_email}>"
            msg['To'] = recipient_email
            msg['Subject'] = "Your EduTrack OTP Verification Code"

            body = f"""
            <html>
            <body>
                <h2>EduTrack Security Verification</h2>
                <p>Hello,</p>
                <p>You recently requested a Password Reset or OTP Login. Your 6-digit verification code is:</p>
                <h1 style="color: #2b6cb0; font-size: 32px; letter-spacing: 4px;">{otp}</h1>
                <p>This code will expire in 5 minutes.</p>
                <p>If you did not request this, please ignore this email or contact the administrator.</p>
                <br>
                <p>Regards,<br>EduTrack Team</p>
            </body>
            </html>
            """
            msg.attach(MIMEText(body, 'html'))

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
        except Exception as e:
            print(f"Failed to send email: {e}")
            return jsonify({"error": "Failed to send OTP email. Please contact support."}), 500
    else:
        print(f"\n\n[WARNING] SMTP not configured or user has no email! OTP for {identifier} is {otp}\n\n")

    return jsonify({"ok": True, "message": "OTP sent to registered email address"})

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
