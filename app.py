#!/usr/bin/env python3
import os
import uuid
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, g, abort
from werkzeug.utils import secure_filename

# -----------------------
# Config
# -----------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")  # Changed to database.db
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  * 1024  # 5 GB

ALLOWED_EXTENSIONS = None  # Set to a set like {'png','jpg','pdf'} to restrict

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "change-me")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -----------------------
# Database helpers
# -----------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_name TEXT NOT NULL,
            stored_name TEXT NOT NULL UNIQUE,
            size_bytes INTEGER NOT NULL,
            mime_type TEXT,
            uploaded_at TEXT NOT NULL
        )
    """)
    db.commit()

# -----------------------
# Utility
# -----------------------
def is_allowed(filename: str) -> bool:
    if not filename:
        return False
    if ALLOWED_EXTENSIONS is None:
        return True
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in ALLOWED_EXTENSIONS

# -----------------------
# Routes
# -----------------------
@app.route("/")
def index():
    db = get_db()
    q = request.args.get("q", "").strip()
    if q:
        rows = db.execute(
            "SELECT * FROM files WHERE original_name LIKE ? ORDER BY uploaded_at DESC",
            (f"%{q}%",)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM files ORDER BY uploaded_at DESC").fetchall()
    return render_template("index.html", files=rows, q=q)

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        flash("No file part in the request", "error")
        return redirect(url_for("index"))
    files = request.files.getlist("file")
    saved = 0
    db = get_db()

    for f in files:
        if f.filename == "":
            continue
        filename = secure_filename(f.filename)
        if not is_allowed(filename):
            flash(f"File type not allowed: {filename}", "error")
            continue
        stored_name = f"{uuid.uuid4().hex}_{filename}"
        dest = os.path.join(app.config["UPLOAD_FOLDER"], stored_name)
        f.save(dest)
        size_bytes = os.path.getsize(dest)
        mime_type = f.mimetype
        db.execute(
            "INSERT INTO files (original_name, stored_name, size_bytes, mime_type, uploaded_at) VALUES (?, ?, ?, ?, ?)",
            (filename, stored_name, size_bytes, mime_type, datetime.utcnow().isoformat())
        )
        saved += 1

    db.commit()
    if saved:
        flash(f"Uploaded {saved} file(s) successfully.", "success")
    else:
        flash("No files uploaded.", "warning")
    return redirect(url_for("index"))

@app.route("/files/<int:file_id>/download")
def download(file_id: int):
    db = get_db()
    row = db.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
    if not row:
        abort(404)
    return send_from_directory(app.config["UPLOAD_FOLDER"], row["stored_name"], as_attachment=True, download_name=row["original_name"])

@app.route("/files/<int:file_id>/delete", methods=["POST"])
def delete(file_id: int):
    db = get_db()
    row = db.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
    if not row:
        flash("File not found.", "error")
        return redirect(url_for("index"))
    path = os.path.join(app.config["UPLOAD_FOLDER"], row["stored_name"])
    try:
        if os.path.exists(path):
            os.remove(path)
        db.execute("DELETE FROM files WHERE id = ?", (file_id,))
        db.commit()
        flash(f"Deleted {row['original_name']}.", "success")
    except Exception as e:
        flash(f"Error deleting file: {e}", "error")
    return redirect(url_for("index"))

@app.route("/files/<int:file_id>")
def details(file_id: int):
    db = get_db()
    row = db.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
    if not row:
        abort(404)
    return render_template("details.html", file=row)

# Health check
@app.route("/healthz")
def healthz():
    return {"status": "ok"}

if __name__ == "__main__":
    # Ensure DB exists before starting server
    if not os.path.exists(DB_PATH):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_name TEXT NOT NULL,
                    stored_name TEXT NOT NULL UNIQUE,
                    size_bytes INTEGER NOT NULL,
                    mime_type TEXT,
                    uploaded_at TEXT NOT NULL
                )
            """)
            conn.commit()
    app.run(host="0.0.0.0", port=5000, debug=True)
