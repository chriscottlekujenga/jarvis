import json
import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "jarvis_memory.db")
SKILLS_DIR = os.path.join(BASE_DIR, "skills")


def now():
    return datetime.now().isoformat(timespec="seconds")


def get_db():
    return sqlite3.connect(DB_FILE)


def init_db():
    os.makedirs(SKILLS_DIR, exist_ok=True)

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        raw_text TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER NOT NULL,
        step_number INTEGER NOT NULL,
        step_text TEXT NOT NULL,
        command TEXT,
        status TEXT,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        request_text TEXT NOT NULL,
        command TEXT NOT NULL,
        status TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS file_edits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        file_path TEXT NOT NULL,
        instruction TEXT NOT NULL,
        status TEXT NOT NULL,
        backup_path TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS project_state (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def save_plan(raw_text):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO plans (created_at, raw_text) VALUES (?, ?)",
        (now(), raw_text)
    )
    plan_id = cur.lastrowid
    conn.commit()
    conn.close()
    return plan_id


def save_step(plan_id, step_number, step_text, command="", status="parsed"):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO steps (plan_id, step_number, step_text, command, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (plan_id, step_number, step_text, command, status, now()))
    conn.commit()
    conn.close()


def update_step(plan_id, step_number, command, status):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE steps
        SET command = ?, status = ?
        WHERE plan_id = ? AND step_number = ?
    """, (command, status, plan_id, step_number))
    conn.commit()
    conn.close()


def save_command(request_text, command, status):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO commands (created_at, request_text, command, status)
        VALUES (?, ?, ?, ?)
    """, (now(), request_text, command, status))
    conn.commit()
    conn.close()


def save_file_edit(file_path, instruction, status, backup_path=""):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO file_edits (created_at, file_path, instruction, status, backup_path)
        VALUES (?, ?, ?, ?, ?)
    """, (now(), file_path, instruction, status, backup_path))
    conn.commit()
    conn.close()


def get_recent_commands(limit=20):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT created_at, request_text, command, status
        FROM commands
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_recent_plans(limit=10):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, created_at, raw_text
        FROM plans
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_plan_steps(plan_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT step_number, step_text, command, status
        FROM steps
        WHERE plan_id = ?
        ORDER BY step_number
    """, (plan_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_recent_file_edits(limit=20):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT created_at, file_path, instruction, status, backup_path
        FROM file_edits
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows


def set_project_state(key, value):
    stored = json.dumps(value)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO project_state (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = excluded.updated_at
    """, (key, stored, now()))
    conn.commit()
    conn.close()


def get_project_state(key, default=None):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT value
        FROM project_state
        WHERE key = ?
    """, (key,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return default

    try:
        return json.loads(row[0])
    except Exception:
        return default


def get_all_project_state():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT key, value, updated_at
        FROM project_state
        ORDER BY key ASC
    """)
    rows = cur.fetchall()
    conn.close()

    result = []
    for key, value, updated_at in rows:
        try:
            parsed = json.loads(value)
        except Exception:
            parsed = value
        result.append((key, parsed, updated_at))
    return result


def clear_project_state():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM project_state")
    conn.commit()
    conn.close()
