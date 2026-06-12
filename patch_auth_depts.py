def patch_auth():
    with open('app/auth.py', 'r', encoding='utf-8') as f:
        code = f.read()

    # Import CampusSettings
    import_str = "from app.models import User, db"
    new_import_str = "from app.models import User, db, CampusSettings\\nimport json"
    if import_str in code and "CampusSettings" not in code:
        code = code.replace(import_str, new_import_str)

    # Append routes
    new_routes = """

@auth_bp.route("/admin/departments", methods=["GET"])
def get_departments():
    u = current_user()
    if not u or u.role != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
        
    settings = CampusSettings.query.first()
    if not settings or not settings.departments_json:
        return jsonify({"departments": ["CSE", "ECE", "ME", "CE", "EEE"]})
        
    try:
        dept_list = json.loads(settings.departments_json)
        return jsonify({"departments": dept_list})
    except:
        return jsonify({"departments": ["CSE", "ECE", "ME", "CE", "EEE"]})

@auth_bp.route("/admin/departments", methods=["POST"])
def update_departments():
    u = current_user()
    if not u or u.role != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.get_json() or {}
    departments = data.get("departments")
    if not isinstance(departments, list):
        return jsonify({"error": "departments must be a list"}), 400
        
    settings = CampusSettings.query.first()
    if not settings:
        settings = CampusSettings(lat=0, lng=0)
        db.session.add(settings)
        
    settings.departments_json = json.dumps(departments)
    db.session.commit()
    
    return jsonify({"ok": True, "departments": departments})
"""
    if "get_departments" not in code:
        code += new_routes

    with open('app/auth.py', 'w', encoding='utf-8') as f:
        f.write(code)

if __name__ == '__main__':
    patch_auth()
