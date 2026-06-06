def append_route():
    new_route = """

@auth_bp.route("/api/admin/otp-logs", methods=["GET"])
def get_otp_logs():
    # Only allow admins to view OTP logs
    if "user_id" not in session or session.get("role") != "admin":
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
    with open('app/auth.py', 'a', encoding='utf-8') as f:
        f.write(new_route)

if __name__ == '__main__':
    append_route()
