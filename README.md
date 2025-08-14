# Flask File Manager (SQLite)

A minimal, production-ready starter for uploading, listing, downloading, and deleting files using Flask and SQLite.

## Features
- Multiple file upload
- SQLite database (`filemanager.db`) to track file metadata
- Download and delete endpoints
- Simple search by filename
- Bootstrap UI

## Quickstart

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Visit http://127.0.0.1:5000

## Configuration
- `UPLOAD_FOLDER`: `uploads/` by default.
- `MAX_CONTENT_LENGTH`: 50 MB (adjust in `app.py`).
- Set `FLASK_SECRET_KEY` env var for a strong session key in production.

## DB Reset
Delete `filemanager.db` to recreate an empty DB automatically on next run.
