from flask import Blueprint, send_from_directory

static_bp = Blueprint('static', __name__)

UPLOAD_FOLDER = '../uploads'

@static_bp.route('/uploads/<filename>')
def serve_uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)