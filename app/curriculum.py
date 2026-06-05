from flask import Blueprint, request, jsonify
import os
from werkzeug.utils import secure_filename
from app.auth import login_required

curriculum_bp = Blueprint("curriculum", __name__)

UPLOAD_FOLDER = os.path.join("instance", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@curriculum_bp.route("/upload", methods=["POST"])
@login_required
def upload_curriculum():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        return jsonify({"message": f"Successfully uploaded {filename}", "filename": filename}), 200
