from flask import Blueprint, request, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
from app.auth import require_login

curriculum_bp = Blueprint("curriculum", __name__)

UPLOAD_FOLDER = os.path.join("instance", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@curriculum_bp.route("/upload", methods=["POST"])
def upload_curriculum():
    u, err = require_login()
    if err:
        return err

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

@curriculum_bp.route("/list", methods=["GET"])
def list_curriculums():
    u, err = require_login()
    if err:
        return err
    try:
        files = os.listdir(UPLOAD_FOLDER)
        files.sort(key=lambda x: os.path.getmtime(os.path.join(UPLOAD_FOLDER, x)), reverse=True)
        return jsonify([{"filename": f} for f in files]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@curriculum_bp.route("/download/<filename>", methods=["GET"])
def download_curriculum(filename):
    u, err = require_login()
    if err:
        return err
    return send_from_directory(os.path.abspath(UPLOAD_FOLDER), filename, as_attachment=True)
