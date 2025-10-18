import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
from datetime import datetime

# --- Configuration ---
UPLOAD_FOLDER = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "uploads")

DB_PATH = "database.db"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
CORS(app)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# --- Database setup ---


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author TEXT NOT NULL,
            description TEXT,
            filename TEXT NOT NULL,
            is_video BOOLEAN NOT NULL,
            created_at DATETIME NOT NULL
        )
    """)
    conn.commit()
    conn.close()


init_db()

# --- Routes ---


@app.route("/api/uploads", methods=["GET"])
def get_uploads():
    conn = get_db_connection()
    uploads = conn.execute(
        "SELECT * FROM uploads ORDER BY created_at DESC").fetchall()
    conn.close()

    result = []
    for u in uploads:
        result.append({
            "id": u["id"],
            "author": u["author"],
            "description": u["description"],
            "filename": u["filename"],
            "previewUrl": f"http://localhost:5000/uploads/{u['filename']}",
            "isVideo": bool(u["is_video"]),
            "createdAt": u["created_at"]
        })
    return jsonify(result)


@app.route("/api/uploads", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    author = request.form.get("author")
    description = request.form.get("description", "")
    is_video = file.content_type.startswith("video/")

    filename = f"{int(datetime.now().timestamp())}_{file.filename}"
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(file_path)

    conn = get_db_connection()
    cursor = conn.cursor()
    created_at = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO uploads (author, description, filename, is_video, created_at) VALUES (?, ?, ?, ?, ?)",
        (author, description, filename, is_video, created_at)
    )
    conn.commit()
    upload_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "id": upload_id,
        "author": author,
        "description": description,
        "filename": filename,
        "previewUrl": f"http://localhost:5000/uploads/{filename}",
        "isVideo": is_video,
        "createdAt": created_at
    })


@app.route("/api/uploads/<int:upload_id>", methods=["DELETE"])
def delete_upload(upload_id):
    conn = get_db_connection()
    upload = conn.execute(
        "SELECT * FROM uploads WHERE id = ?", (upload_id,)).fetchone()
    if not upload:
        conn.close()
        return jsonify({"error": "Upload not found"}), 404

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], upload["filename"])
    if os.path.exists(file_path):
        os.remove(file_path)

    conn.execute("DELETE FROM uploads WHERE id = ?", (upload_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Upload deleted"}), 200


@app.route("/uploads/<path:filename>")
def serve_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


if __name__ == "__main__":
    app.run(debug=True)
