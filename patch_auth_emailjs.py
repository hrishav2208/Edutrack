import os

def patch_auth_api():
    with open('app/auth.py', 'r', encoding='utf-8') as f:
        auth_code = f.read()

    old_smtp_logic = """    # Send Email via SMTP
    sender_email = os.environ.get('MAIL_USERNAME')
    sender_password = os.environ.get('MAIL_PASSWORD')
    smtp_server = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('MAIL_PORT', 587))
    
    recipient_email = user.email
    if sender_email and sender_password and recipient_email:
        try:
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient_email
            msg['Subject'] = "Your EduTrack OTP Verification Code"

            html = f\"\"\"
            <html>
                <body style="font-family: Arial, sans-serif; background-color: #f4f7f6; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <h2 style="color: #2c3e50; text-align: center;">EduTrack Secure Login</h2>
                        <p style="color: #34495e; font-size: 16px;">Hello,</p>
                        <p style="color: #34495e; font-size: 16px;">You have requested to login or reset your password. Please use the following One-Time Password (OTP):</p>
                        <div style="text-align: center; margin: 30px 0;">
                            <span style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #3498db; background-color: #ecf0f1; padding: 15px 30px; border-radius: 8px;">{otp}</span>
                        </div>
                        <p style="color: #7f8c8d; font-size: 14px;">This code is valid for 10 minutes. If you did not request this code, please ignore this email.</p>
                        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                        <p style="color: #95a5a6; font-size: 12px; text-align: center;">&copy; EduTrack College Management System</p>
                    </div>
                </body>
            </html>
            \"\"\"
            msg.attach(MIMEText(html, 'html'))

            # Use SSL on port 465 for Gmail (more reliable than STARTTLS on 587)
            if smtp_port == 587:
                smtp_port = 465 # Force 465 for SSL

            import socket
            orig_getaddrinfo = socket.getaddrinfo
            def getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
                return orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
            
            socket.getaddrinfo = getaddrinfo_ipv4
            try:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)
                server.login(sender_email, sender_password)
                server.send_message(msg)
                server.quit()
            finally:
                socket.getaddrinfo = orig_getaddrinfo
        except smtplib.SMTPAuthenticationError as e:
            print(f"SMTP Auth Error: {e}")
            return jsonify({"error": "Configuration Error: Please ensure MAIL_USERNAME and MAIL_PASSWORD (16-letter App Password) are exactly correct in Render Environment Variables."}), 500
        except Exception as e:
            print(f"Failed to send email: {e}")
            return jsonify({"error": f"Failed to send OTP email: {e}"}), 500
    else:
        print(f"\\n\\n[WARNING] SMTP not configured or user has no email! OTP for {identifier} is {otp}\\n\\n")"""

    new_emailjs_logic = """    # Send Email via EmailJS API (Bypasses SMTP Blocks)
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
        print(f"\\n\\n[WARNING] EmailJS keys missing or user has no email. Falling back to Admin Outbox. OTP for {identifier} is {otp}\\n\\n")"""

    if old_smtp_logic in auth_code:
        auth_code = auth_code.replace(old_smtp_logic, new_emailjs_logic)
        print("Replaced SMTP with EmailJS logic!")
    else:
        print("Could not find old SMTP logic")

    # Now add the new admin OTP logs route
    new_route = """

@auth_bp.route('/admin/otp-logs', methods=['GET'])
def get_otp_logs():
    # Only allow admins to view OTP logs
    if 'user_id' not in session or session.get('role') != 'admin':
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
"""
    if "def get_otp_logs" not in auth_code:
        auth_code += new_route
        print("Added get_otp_logs route!")

    with open('app/auth.py', 'w', encoding='utf-8') as f:
        f.write(auth_code)

if __name__ == '__main__':
    patch_auth_api()
