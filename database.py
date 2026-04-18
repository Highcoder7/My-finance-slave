import sqlite3
from datetime import datetime, timedelta
import pytz

ALMATY_TZ = pytz.timezone("Asia/Almaty")


def get_connection():
    conn = sqlite3.connect("finance.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def add_transaction(user_id, type_, amount, category, description):
    conn = get_connection()
    now = datetime.now(ALMATY_TZ).isoformat()
    conn.execute(
        "INSERT INTO transactions (user_id, type, amount, category, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, type_, amount, category, description, now)
    )
    conn.commit()
    conn.close()


def undo_last_transaction(user_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM transactions WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,)
    ).fetchone()
    if row:
        conn.execute("DELETE FROM transactions WHERE id = ?", (row["id"],))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False


def get_today_transactions(user_id):
    conn = get_connection()
    today = datetime.now(ALMATY_TZ).date().isoformat()
    rows = conn.execute(
        "SELECT * FROM transactions WHERE user_id = ? AND DATE(created_at) = ?",
        (user_id, today)
    ).fetchall()
    conn.close()
    return rows


def get_week_transactions(user_id):
    conn = get_connection()
    week_ago = (datetime.now(ALMATY_TZ) - timedelta(days=7)).date().isoformat()
    rows = conn.execute(
        "SELECT * FROM transactions WHERE user_id = ? AND DATE(created_at) >= ?",
        (user_id, week_ago)
    ).fetchall()
    conn.close()
    return rows


def get_month_transactions(user_id, year=None, month=None):
    conn = get_connection()
    now = datetime.now(ALMATY_TZ)
    year = year or now.year
    month = month or now.month
    rows = conn.execute(
        "SELECT * FROM transactions WHERE user_id = ? AND strftime('%Y', created_at) = ? AND strftime('%m', created_at) = ?",
        (user_id, str(year), f"{month:02d}")
    ).fetchall()
    conn.close()
    return rows


def get_all_user_ids():
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT user_id FROM transactions").fetchall()
    conn.close()
    return [r["user_id"] for r in rows]
