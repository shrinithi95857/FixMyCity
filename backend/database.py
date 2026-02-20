"""SQLite database setup and helpers for complaints."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime
import hashlib
import secrets

# Use resolved path so DB path is correct when run from project root
DB_PATH = Path(__file__).resolve().parent / "complaints.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


@contextmanager
def get_db():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create all tables if not exists."""
    with get_db() as conn:
        # Users table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('citizen', 'officer')),
                created_at TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # Complaints table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                area_name TEXT,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'unresolved',
                image_path TEXT,
                area_importance TEXT DEFAULT 'normal' CHECK (area_importance IN ('low', 'normal', 'high', 'critical'))
            )
        """)
        
        # User complaints mapping (track who submitted which complaint)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                complaint_id INTEGER NOT NULL,
                submitted_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (complaint_id) REFERENCES complaints (id),
                UNIQUE (user_id, complaint_id)
            )
        """)
        
        # Officer actions tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS officer_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                officer_id INTEGER NOT NULL,
                complaint_id INTEGER NOT NULL,
                action TEXT NOT NULL CHECK (action IN ('resolved', 'unresolved')),
                timestamp TEXT NOT NULL,
                notes TEXT,
                FOREIGN KEY (officer_id) REFERENCES users (id),
                FOREIGN KEY (complaint_id) REFERENCES complaints (id)
            )
        """)
        
        # Add image_path column if it doesn't exist (for existing databases)
        try:
            conn.execute("ALTER TABLE complaints ADD COLUMN image_path TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Add area_importance column if it doesn't exist
        try:
            conn.execute("ALTER TABLE complaints ADD COLUMN area_importance TEXT DEFAULT 'normal'")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Create indexes for better performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_complaints_category ON complaints (category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints (status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_complaints_timestamp ON complaints (timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user_complaints_user_id ON user_complaints (user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user_complaints_complaint_id ON user_complaints (complaint_id)")


def hash_password(password):
    """Hash password with salt."""
    salt = secrets.token_hex(16)
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return salt + pwdhash.hex()


def verify_password(stored_password, provided_password):
    """Verify a stored password against one provided by user."""
    salt = stored_password[:32]
    stored_hash = stored_password[32:]
    pwdhash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return pwdhash.hex() == stored_hash


def create_user(username, email, password, role):
    """Create a new user."""
    timestamp = datetime.utcnow().isoformat() + "Z"
    password_hash = hash_password(password)
    
    with get_db() as conn:
        try:
            cur = conn.execute(
                """INSERT INTO users (username, email, password_hash, role, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (username, email, password_hash, role, timestamp)
            )
            conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError as e:
            if "username" in str(e).lower():
                raise ValueError("Username already exists")
            elif "email" in str(e).lower():
                raise ValueError("Email already exists")
            else:
                raise e


def authenticate_user(username, password):
    """Authenticate user and return user data if valid."""
    with get_db() as conn:
        user = conn.execute(
            "SELECT id, username, email, password_hash, role, is_active FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        
        if user and user['is_active'] and verify_password(user['password_hash'], password):
            return {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'role': user['role']
            }
        return None


def get_user_by_id(user_id):
    """Get user by ID."""
    with get_db() as conn:
        user = conn.execute(
            "SELECT id, username, email, role, created_at FROM users WHERE id = ? AND is_active = 1",
            (user_id,)
        ).fetchone()
        return dict(user) if user else None


def track_complaint_submission(user_id, complaint_id):
    """Track which user submitted which complaint."""
    timestamp = datetime.utcnow().isoformat() + "Z"
    with get_db() as conn:
        conn.execute(
            """INSERT INTO user_complaints (user_id, complaint_id, submitted_at)
               VALUES (?, ?, ?)""",
            (user_id, complaint_id, timestamp)
        )
        conn.commit()


def get_user_complaints(user_id):
    """Get all complaints submitted by a user."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT c.* FROM complaints c
               JOIN user_complaints uc ON c.id = uc.complaint_id
               WHERE uc.user_id = ?
               ORDER BY c.timestamp DESC""",
            (user_id,)
        ).fetchall()
        return [dict(row) for row in rows]


def delete_user_complaint(user_id, complaint_id):
    """Delete a user's complaint (before submission - from temporary storage)."""
    with get_db() as conn:
        # First check if user owns this complaint
        ownership = conn.execute(
            "SELECT 1 FROM user_complaints WHERE user_id = ? AND complaint_id = ?",
            (user_id, complaint_id)
        ).fetchone()
        
        if ownership:
            # Delete the complaint
            conn.execute("DELETE FROM complaints WHERE id = ?", (complaint_id,))
            conn.execute("DELETE FROM user_complaints WHERE complaint_id = ?", (complaint_id,))
            conn.commit()
            return True
        return False


def log_officer_action(officer_id, complaint_id, action, notes=None):
    """Log officer actions on complaints."""
    timestamp = datetime.utcnow().isoformat() + "Z"
    with get_db() as conn:
        conn.execute(
            """INSERT INTO officer_actions (officer_id, complaint_id, action, timestamp, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (officer_id, complaint_id, action, timestamp, notes)
        )
        # Update complaint status
        conn.execute(
            "UPDATE complaints SET status = ? WHERE id = ?",
            (action, complaint_id)
        )
        conn.commit()


def get_officer_actions(officer_id=None):
    """Get officer actions, optionally filtered by officer."""
    with get_db() as conn:
        if officer_id:
            rows = conn.execute(
                """SELECT oa.*, c.category, c.description, u.username as officer_name
                   FROM officer_actions oa
                   JOIN complaints c ON oa.complaint_id = c.id
                   JOIN users u ON oa.officer_id = u.id
                   WHERE oa.officer_id = ?
                   ORDER BY oa.timestamp DESC""",
                (officer_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT oa.*, c.category, c.description, u.username as officer_name
                   FROM officer_actions oa
                   JOIN complaints c ON oa.complaint_id = c.id
                   JOIN users u ON oa.officer_id = u.id
                   ORDER BY oa.timestamp DESC""",
                ()
            ).fetchall()
        return [dict(row) for row in rows]
