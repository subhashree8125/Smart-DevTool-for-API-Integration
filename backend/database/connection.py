import os
import sqlite3
import json
from pathlib import Path

DB_PATH = os.getenv("DATABASE_URL", "sqlite:///backend/database/database.db")

def get_db_file_path() -> str:
    """Extracts local database file path from connection string."""
    if DB_PATH.startswith("sqlite:///"):
        path_str = DB_PATH.replace("sqlite:///", "")
    else:
        path_str = DB_PATH
    return str(Path(path_str).absolute())

def get_db_connection():
    """Establishes connection to the SQLite database with row factory."""
    db_file = get_db_file_path()
    # Ensure directory exists
    os.makedirs(os.path.dirname(db_file), exist_ok=True)
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes database schema creating required tables."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # APIS table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS apis (
        id TEXT PRIMARY KEY,
        url TEXT NOT NULL,
        use_case TEXT,
        name TEXT,
        version TEXT,
        base_url TEXT,
        doc_type TEXT,
        auth_type TEXT,
        summary TEXT,
        sdk_recommendation TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Endpoints table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS endpoints (
        id TEXT PRIMARY KEY,
        api_id TEXT NOT NULL,
        method TEXT NOT NULL,
        path TEXT NOT NULL,
        description TEXT,
        auth_required INTEGER DEFAULT 0,
        headers TEXT,
        query_params TEXT,
        path_params TEXT,
        request_body TEXT,
        response_body TEXT,
        status_codes TEXT,
        sample_request TEXT,
        sample_response TEXT,
        FOREIGN KEY (api_id) REFERENCES apis(id) ON DELETE CASCADE
    );
    """)

    # Projects table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        api_id TEXT NOT NULL,
        language TEXT NOT NULL,
        wrapper_code TEXT,
        readme_code TEXT,
        zip_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (api_id) REFERENCES apis(id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
