from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import re
import os
import tempfile
import shutil
import uuid
import json
import hashlib
import hmac
import time
import base64
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from ai_service import analyze_candidate_with_ai

# Module-level logger (used by helper functions outside route handlers)
_app_logger = logging.getLogger('hireengine.app')

# Optional libraries for PDF and DOCX parsing
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import docx
except ImportError:
    docx = None

app = Flask(__name__)
# Enable CORS for frontend integration
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ── JWT Auth Config ──────────────────────────────────────────────────────────
JWT_SECRET = os.environ.get('HIREENGINE_JWT_SECRET', 'hireengine-super-secret-jwt-key-2026')
JWT_EXPIRY_HOURS = 24
USERS_DB_PATH = os.path.join(os.path.dirname(__file__), 'users.json')

def _load_users():
    if not os.path.exists(USERS_DB_PATH):
        # Seed a default admin account on first launch
        default = [
            {
                'id': str(uuid.uuid4()),
                'email': 'admin@hireengine.ai',
                'password_hash': _hash_password('admin1234'),
                'name': 'System Administrator',
                'role': 'Admin',
                'tenant_id': 'admin-tenant'   # Fixed ID — matches DEFAULT in SQLite migrations
            }
        ]
        with open(USERS_DB_PATH, 'w') as f:
            json.dump(default, f, indent=2)
        return default
    with open(USERS_DB_PATH, 'r') as f:
        users = json.load(f)
    # ── Backfill: legacy accounts created before multi-tenancy ──────────────
    dirty = False
    for u in users:
        if not u.get('tenant_id'):
            # Admin gets the fixed anchor tenant; others get fresh isolated UUIDs
            u['tenant_id'] = 'admin-tenant' if u.get('role') == 'Admin' else str(uuid.uuid4())
            dirty = True
    if dirty:
        with open(USERS_DB_PATH, 'w') as f:
            json.dump(users, f, indent=2)
    return users

def _save_users(users):
    with open(USERS_DB_PATH, 'w') as f:
        json.dump(users, f, indent=2)

def _hash_password(password: str) -> str:
    """SHA-256 HMAC password hash (simple, no bcrypt dependency required)."""
    return hmac.new(JWT_SECRET.encode(), password.encode(), hashlib.sha256).hexdigest()

def _check_password(password: str, stored_hash: str) -> bool:
    return hmac.compare_digest(_hash_password(password), stored_hash)

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + '=' * (padding % 4))

def _create_jwt(payload: dict) -> str:
    header = _b64url_encode(json.dumps({'alg': 'HS256', 'typ': 'JWT'}).encode())
    payload_enc = _b64url_encode(json.dumps(payload).encode())
    sig_input = f'{header}.{payload_enc}'.encode()
    signature = hmac.new(JWT_SECRET.encode(), sig_input, hashlib.sha256).digest()
    return f'{header}.{payload_enc}.{_b64url_encode(signature)}'

def _verify_jwt(token: str) -> dict | None:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        header, payload_enc, sig_b64 = parts
        sig_input = f'{header}.{payload_enc}'.encode()
        expected_sig = hmac.new(JWT_SECRET.encode(), sig_input, hashlib.sha256).digest()
        if not hmac.compare_digest(_b64url_decode(sig_b64), expected_sig):
            return None
        payload = json.loads(_b64url_decode(payload_enc))
        if payload.get('exp', 0) < time.time():
            return None
        return payload
    except Exception:
        return None

@app.route('/api/v1/auth/login', methods=['POST'])
def auth_login():
    data = request.get_json(force=True, silent=True) or {}
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', ''))

    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

    users = _load_users()
    user = next((u for u in users if u['email'].lower() == email), None)
    if not user or not _check_password(password, user['password_hash']):
        return jsonify({'error': 'Invalid email or password.'}), 401

    exp = time.time() + JWT_EXPIRY_HOURS * 3600
    token = _create_jwt({
        'sub': user['id'],
        'email': user['email'],
        'tenant_id': user.get('tenant_id', ''),
        'exp': exp
    })
    return jsonify({
        'token': token,
        'user': {
            'name': user['name'],
            'role': user['role'],
            'email': user['email'],
            'tenant_id': user.get('tenant_id', ''),
            'is_super_admin': user.get('role') == 'Admin'
        }
    })

@app.route('/api/v1/auth/register', methods=['POST'])
def auth_register():
    data = request.get_json(force=True, silent=True) or {}
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', ''))
    name = str(data.get('name', '')).strip()
    role = str(data.get('role', 'Recruiter')).strip()

    if not email or not password or not name:
        return jsonify({'error': 'name, email and password are required.'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters.'}), 400

    users = _load_users()
    if any(u['email'].lower() == email for u in users):
        return jsonify({'error': 'An account with this email already exists.'}), 409

    new_user = {
        'id': str(uuid.uuid4()),
        'email': email,
        'password_hash': _hash_password(password),
        'name': name,
        'role': role,
        'tenant_id': str(uuid.uuid4())   # Auto-generated isolated tenant namespace
    }
    users.append(new_user)
    _save_users(users)

    exp = time.time() + JWT_EXPIRY_HOURS * 3600
    token = _create_jwt({
        'sub': new_user['id'],
        'email': new_user['email'],
        'tenant_id': new_user['tenant_id'],
        'exp': exp
    })
    return jsonify({
        'token': token,
        'user': {
            'name': name,
            'role': role,
            'email': email,
            'tenant_id': new_user['tenant_id'],
            'is_super_admin': role == 'Admin'
        }
    }), 201

@app.route('/api/v1/auth/verify', methods=['GET'])
def auth_verify():
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({'valid': False}), 401
    token = auth_header[7:]
    payload = _verify_jwt(token)
    if not payload:
        return jsonify({'valid': False, 'error': 'Token expired or invalid.'}), 401
    users = _load_users()
    user = next((u for u in users if u['id'] == payload.get('sub')), None)
    if not user:
        return jsonify({'valid': False}), 401
    return jsonify({
        'valid': True,
        'user': {
            'name': user['name'],
            'role': user['role'],
            'email': user['email'],
            'tenant_id': user.get('tenant_id', ''),
            'is_super_admin': user.get('role') == 'Admin'
        }
    })

def _require_user(req):
    """Helper: verify Bearer token and return the calling user, else None."""
    auth_header = req.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    payload = _verify_jwt(auth_header[7:])
    if not payload:
        return None
    users = _load_users()
    return next((u for u in users if u['id'] == payload.get('sub')), None)

def _require_admin(request):
    """Helper: verify Bearer token and return the calling user if they are Admin, else None."""
    caller = _require_user(request)
    if not caller or caller.get('role') != 'Admin':
        return None
    return caller

def _get_caller_tenant(req):
    """
    Resolve the tenant scope for the calling user.

    Returns:
      None   — caller is the System Admin (super-admin bypass, global access).
      str    — the caller's tenant_id UUID (normal tenant-scoped access).
      False  — unauthenticated; caller must be rejected upstream.
    """
    caller = _require_user(req)
    if not caller:
        return False                          # unauthenticated
    if caller.get('role') == 'Admin':
        return None                           # None signals "no tenant filter"
    return caller.get('tenant_id', '')        # normal scoped tenant

@app.route('/api/v1/auth/change-password', methods=['PUT'])
def auth_change_password():
    """Change logged-in user password."""
    caller = _require_user(request)
    if not caller:
        return jsonify({'error': 'Authentication required.'}), 401
    data = request.json or {}
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    if not old_password or not new_password:
        return jsonify({'error': 'Old and new password are required.'}), 400
    if not _check_password(old_password, caller['password_hash']):
        return jsonify({'error': 'Incorrect current password.'}), 400
    if len(new_password) < 6:
        return jsonify({'error': 'New password must be at least 6 characters.'}), 400
    users = _load_users()
    for u in users:
        if u['id'] == caller['id']:
            u['password_hash'] = _hash_password(new_password)
            break
    _save_users(users)
    return jsonify({'success': True, 'message': 'Password changed successfully.'})

@app.route('/api/v1/auth/users', methods=['GET'])
def auth_list_users():
    """List all system users — Admin only."""
    caller = _require_admin(request)
    if not caller:
        return jsonify({'error': 'Admin access required.'}), 403
    users = _load_users()
    safe = [{'id': u['id'], 'email': u['email'], 'name': u['name'], 'role': u['role']} for u in users]
    return jsonify({'users': safe})

@app.route('/api/v1/auth/users/<string:user_id>', methods=['DELETE'])
def auth_delete_user(user_id):
    """Delete a user account — Admin only, cannot delete self."""
    caller = _require_admin(request)
    if not caller:
        return jsonify({'error': 'Admin access required.'}), 403
    if caller['id'] == user_id:
        return jsonify({'error': 'You cannot delete your own account.'}), 400
    users = _load_users()
    target = next((u for u in users if u['id'] == user_id), None)
    if not target:
        return jsonify({'error': 'User not found.'}), 404
    users = [u for u in users if u['id'] != user_id]
    _save_users(users)
    return jsonify({'success': True, 'deleted': target['email']})
# ── SQLite Database Layer ──────────────────────────────────────────────────────
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), 'hireengine.db')

SEED_REQUISITIONS = [
    {'id': 101, 'job_title': 'Petroleum Pipeline Engineer',     'location': 'Riyadh, Saudi Arabia',  'target_domain': 'Oil & Gas',                   'job_description_text': 'Looking for a Senior Pipeline Engineer with experience in petroleum pipelines, drilling simulation, gas reservoirs, refining operations, offshore wellhead setups, and hydrocarbon transport. HSE certifications required.'},
    {'id': 102, 'job_title': 'Process Engineer — Petrochemical Plant', 'location': 'Jubail, Saudi Arabia',  'target_domain': 'Petrochemical',               'job_description_text': 'Seeking a process engineer with expertise in distillation operations, catalyst management, feedstock handling, chemical process optimization, and plant safety. HAZOP experience is a strong advantage.'},
    {'id': 103, 'job_title': 'MEP Site Engineer',               'location': 'Dubai, UAE',             'target_domain': 'Construction & Infrastructure', 'job_description_text': 'Hiring an MEP site engineer for large-scale infrastructure projects. Must have experience in mechanical, electrical, and plumbing systems, site management, AutoCAD, and Primavera P6 scheduling.'},
    {'id': 104, 'job_title': 'Marine Engineer — Vessel Operations', 'location': 'Abu Dhabi, UAE',        'target_domain': 'Maritime & Shipping',         'job_description_text': 'Recruiting a qualified marine engineer for vessel operations and maintenance. STCW certification required. Experience in cargo handling, port logistics, and maritime safety compliance is essential.'},
]

def get_db():
    """Return a SQLite connection with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    return conn

def init_db():
    """Create tables if missing and seed default requisitions on first launch."""
    with get_db() as conn:
        # ── Tenants registry (informational, lightweight) ──────────────────────
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tenants (
                id   TEXT PRIMARY KEY,
                name TEXT NOT NULL
            )
        ''')
        # Ensure the system admin's anchor tenant exists
        conn.execute(
            "INSERT OR IGNORE INTO tenants (id, name) VALUES (?, ?)",
            ('admin-tenant', 'System Administrator')
        )
        conn.execute('''
            CREATE TABLE IF NOT EXISTS requisitions (
                id                   INTEGER PRIMARY KEY,
                job_title            TEXT NOT NULL,
                location             TEXT NOT NULL DEFAULT "Not specified",
                target_domain        TEXT NOT NULL,
                job_description_text TEXT NOT NULL,
                screening_rules      TEXT,
                tenant_id            TEXT NOT NULL DEFAULT "admin-tenant",
                created_at           TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS candidates (
                id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                requisition_id           INTEGER NOT NULL REFERENCES requisitions(id) ON DELETE CASCADE,
                full_name                TEXT NOT NULL,
                email                    TEXT NOT NULL DEFAULT "",
                phone                    TEXT NOT NULL DEFAULT "",
                passport_number          TEXT,
                current_stage            TEXT NOT NULL DEFAULT "Screening",
                total_experience_years   REAL NOT NULL DEFAULT 0,
                relevant_experience_years REAL NOT NULL DEFAULT 0,
                match_score              INTEGER NOT NULL DEFAULT 0,
                skills_matrix            TEXT NOT NULL DEFAULT "[]",
                specialization_tags      TEXT NOT NULL DEFAULT "[]",
                industry_remarks         TEXT NOT NULL DEFAULT "",
                cv_file_name             TEXT,
                ai_analysis              TEXT,
                eligible                 INTEGER NOT NULL DEFAULT 1,
                veto_reason              TEXT,
                tenant_id                TEXT NOT NULL DEFAULT "admin-tenant",
                created_at               TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS candidate_notes (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
                author_email TEXT NOT NULL DEFAULT "Recruiter",
                note_text    TEXT NOT NULL,
                created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # ── Backward-compatible migrations for existing live databases ─────────
        for migration in [
            'ALTER TABLE requisitions ADD COLUMN screening_rules TEXT',
            'ALTER TABLE candidates ADD COLUMN eligible INTEGER NOT NULL DEFAULT 1',
            'ALTER TABLE candidates ADD COLUMN veto_reason TEXT',
            # Multi-tenancy migrations — idempotent (ignored if column exists)
            "ALTER TABLE requisitions ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'admin-tenant'",
            "ALTER TABLE candidates   ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'admin-tenant'",
        ]:
            try:
                conn.execute(migration)
            except Exception:
                pass  # Column already exists — safe to ignore
        # Seed default requisitions only on first launch
        count = conn.execute('SELECT COUNT(*) FROM requisitions').fetchone()[0]
        if count == 0:
            for r in SEED_REQUISITIONS:
                conn.execute(
                    'INSERT OR IGNORE INTO requisitions (id, job_title, location, target_domain, job_description_text) VALUES (?,?,?,?,?)',
                    (r['id'], r['job_title'], r['location'], r['target_domain'], r['job_description_text'])
                )
        conn.commit()

init_db()

def row_to_requisition(row):
    raw_rules = row['screening_rules'] if 'screening_rules' in row.keys() else None
    return {
        'id': row['id'],
        'job_title': row['job_title'],
        'location': row['location'],
        'target_domain': row['target_domain'],
        'job_description_text': row['job_description_text'],
        'screening_rules': json.loads(raw_rules) if raw_rules else None,
        'created_at': row['created_at'],
    }

def row_to_candidate(row):
    keys = row.keys()
    return {
        'id': row['id'],
        'requisition_id': row['requisition_id'],
        'full_name': row['full_name'],
        'email': row['email'],
        'phone': row['phone'],
        'passport_number': row['passport_number'],
        'current_stage': row['current_stage'],
        'total_experience_years': row['total_experience_years'],
        'relevant_experience_years': row['relevant_experience_years'],
        'match_score': row['match_score'],
        'skills_matrix': json.loads(row['skills_matrix'] or '[]'),
        'specialization_tags': json.loads(row['specialization_tags'] or '[]'),
        'industry_remarks': row['industry_remarks'],
        'cv_file_name': row['cv_file_name'],
        'ai_analysis': json.loads(row['ai_analysis']) if row['ai_analysis'] else None,
        'eligible': bool(row['eligible']) if 'eligible' in keys else True,
        'veto_reason': row['veto_reason'] if 'veto_reason' in keys else None,
        'created_at': row['created_at'],
    }

# ── Requisition Endpoints ──────────────────────────────────────────────────────

@app.route('/api/v1/requisitions', methods=['GET'])
def list_requisitions():
    tid = _get_caller_tenant(request)
    if tid is False:
        return jsonify({'error': 'Authentication required.'}), 401
    with get_db() as conn:
        if tid is None:   # Admin super-user: return all tenants
            rows = conn.execute('SELECT * FROM requisitions ORDER BY created_at DESC').fetchall()
        else:
            rows = conn.execute(
                'SELECT * FROM requisitions WHERE tenant_id=? ORDER BY created_at DESC', (tid,)
            ).fetchall()
    return jsonify([row_to_requisition(r) for r in rows])

@app.route('/api/v1/requisitions', methods=['POST'])
def create_requisition():
    tid = _get_caller_tenant(request)
    if tid is False:
        return jsonify({'error': 'Authentication required.'}), 401
    # Admin writes into admin-tenant by default (unless tenant_id overridden)
    effective_tid = tid if tid is not None else 'admin-tenant'
    data = request.get_json(force=True, silent=True) or {}
    title   = str(data.get('job_title', '')).strip()
    loc     = str(data.get('location', 'Not specified')).strip() or 'Not specified'
    domain  = str(data.get('target_domain', 'Engineering Services')).strip()
    jd_text = str(data.get('job_description_text', '')).strip()
    rules   = data.get('screening_rules')  # Optional dict or None
    if not title or not jd_text:
        return jsonify({'error': 'job_title and job_description_text are required.'}), 400
    rules_json = json.dumps(rules) if rules and isinstance(rules, dict) else None
    with get_db() as conn:
        cur = conn.execute(
            'INSERT INTO requisitions (job_title, location, target_domain, job_description_text, screening_rules, tenant_id) VALUES (?,?,?,?,?,?)',
            (title, loc, domain, jd_text, rules_json, effective_tid)
        )
        conn.commit()
        row = conn.execute('SELECT * FROM requisitions WHERE id=?', (cur.lastrowid,)).fetchone()
    return jsonify(row_to_requisition(row)), 201

@app.route('/api/v1/requisitions/<int:req_id>/screening-rules', methods=['PUT'])
def update_screening_rules(req_id):
    """Update (or clear) the screening rules for a requisition without recreating it."""
    tid = _get_caller_tenant(request)
    if tid is False:
        return jsonify({'error': 'Authentication required.'}), 401
    data = request.get_json(force=True, silent=True) or {}
    rules = data.get('screening_rules')  # None to clear, dict to set
    rules_json = json.dumps(rules) if rules and isinstance(rules, dict) else None
    with get_db() as conn:
        if tid is None:   # Admin: update without tenant filter
            conn.execute('UPDATE requisitions SET screening_rules=? WHERE id=?', (rules_json, req_id))
        else:
            conn.execute('UPDATE requisitions SET screening_rules=? WHERE id=? AND tenant_id=?', (rules_json, req_id, tid))
        conn.commit()
        row = conn.execute('SELECT * FROM requisitions WHERE id=?', (req_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Requisition not found.'}), 404
    return jsonify(row_to_requisition(row))

@app.route('/api/v1/requisitions/<int:req_id>', methods=['PUT'])
def update_requisition(req_id):
    """Update editable fields of a requisition."""
    tid = _get_caller_tenant(request)
    if tid is False:
        return jsonify({'error': 'Authentication required.'}), 401
    data = request.get_json(force=True, silent=True) or {}
    allowed = ('job_title', 'location', 'target_domain', 'job_description_text')
    updates = {k: str(v).strip() for k, v in data.items() if k in allowed and v is not None}
    if not updates:
        return jsonify({'error': 'No valid fields provided for update.'}), 400
    set_clause = ', '.join(f'{k}=?' for k in updates)
    with get_db() as conn:
        if tid is None:
            conn.execute(f'UPDATE requisitions SET {set_clause} WHERE id=?', list(updates.values()) + [req_id])
        else:
            conn.execute(f'UPDATE requisitions SET {set_clause} WHERE id=? AND tenant_id=?', list(updates.values()) + [req_id, tid])
        conn.commit()
        row = conn.execute('SELECT * FROM requisitions WHERE id=?', (req_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Requisition not found.'}), 404
    return jsonify(row_to_requisition(row))

@app.route('/api/v1/requisitions/<int:req_id>', methods=['DELETE'])
def delete_requisition(req_id):
    tid = _get_caller_tenant(request)
    if tid is False:
        return jsonify({'error': 'Authentication required.'}), 401
    with get_db() as conn:
        if tid is None:
            conn.execute('DELETE FROM candidates WHERE requisition_id=?', (req_id,))
            conn.execute('DELETE FROM requisitions WHERE id=?', (req_id,))
        else:
            conn.execute('DELETE FROM candidates WHERE requisition_id=? AND tenant_id=?', (req_id, tid))
            conn.execute('DELETE FROM requisitions WHERE id=? AND tenant_id=?', (req_id, tid))
        conn.commit()
    return jsonify({'success': True})

# ── Candidate Endpoints ────────────────────────────────────────────────────────

@app.route('/api/v1/candidates', methods=['GET'])
def list_candidates():
    tid = _get_caller_tenant(request)
    if tid is False:
        return jsonify({'error': 'Authentication required.'}), 401
    req_id = request.args.get('req_id', type=int)
    with get_db() as conn:
        if tid is None:   # Admin: global view
            if req_id:
                rows = conn.execute('SELECT * FROM candidates WHERE requisition_id=? ORDER BY match_score DESC, created_at DESC', (req_id,)).fetchall()
            else:
                rows = conn.execute('SELECT * FROM candidates ORDER BY match_score DESC, created_at DESC').fetchall()
        else:
            if req_id:
                rows = conn.execute('SELECT * FROM candidates WHERE requisition_id=? AND tenant_id=? ORDER BY match_score DESC, created_at DESC', (req_id, tid)).fetchall()
            else:
                rows = conn.execute('SELECT * FROM candidates WHERE tenant_id=? ORDER BY match_score DESC, created_at DESC', (tid,)).fetchall()
    return jsonify([row_to_candidate(r) for r in rows])

@app.route('/api/v1/candidates', methods=['POST'])
def upsert_candidate():
    """Create or update a candidate. Matches on full_name+requisition_id for deduplication."""
    tid = _get_caller_tenant(request)
    if tid is False:
        return jsonify({'error': 'Authentication required.'}), 401
    effective_tid = tid if tid is not None else 'admin-tenant'
    data = request.get_json(force=True, silent=True) or {}
    req_id    = data.get('requisition_id')
    full_name = str(data.get('full_name', '')).strip()
    if not req_id or not full_name:
        return jsonify({'error': 'requisition_id and full_name are required.'}), 400

    fields = {
        'requisition_id':           req_id,
        'full_name':                full_name,
        'email':                    str(data.get('email', '')),
        'phone':                    str(data.get('phone', '')),
        'passport_number':          data.get('passport_number'),
        'current_stage':            str(data.get('current_stage', 'Screening')),
        'total_experience_years':   float(data.get('total_experience_years', 0)),
        'relevant_experience_years':float(data.get('relevant_experience_years', 0)),
        'match_score':              int(data.get('match_score', 0)),
        'skills_matrix':            json.dumps(data.get('skills_matrix', [])),
        'specialization_tags':      json.dumps(data.get('specialization_tags', [])),
        'industry_remarks':         str(data.get('industry_remarks', '')),
        'ai_analysis':              json.dumps(data.get('ai_analysis')) if data.get('ai_analysis') else None,
        'eligible':                 1 if data.get('eligible', True) else 0,
        'veto_reason':              data.get('veto_reason'),
        'tenant_id':                effective_tid,
    }

    with get_db() as conn:
        # Check for existing candidate scoped to this tenant
        email_clean = str(data.get('email', '')).strip().lower()
        phone_clean = str(data.get('phone', '')).strip()
        passport_clean = str(data.get('passport_number', '')).strip() if data.get('passport_number') else ''

        query = '''
            SELECT id FROM candidates WHERE tenant_id=? AND (
            (LOWER(email) = ? AND ? != '') OR
            (phone = ? AND ? != '') OR
            (passport_number = ? AND ? != '') OR
            (requisition_id = ? AND LOWER(full_name) = LOWER(?))
            )
            LIMIT 1
        '''
        existing = conn.execute(
            query,
            (effective_tid, email_clean, email_clean, phone_clean, phone_clean, passport_clean, passport_clean, req_id, full_name)
        ).fetchone()

        if existing:
            set_clause = ', '.join(f'{k}=?' for k in fields if k not in ('requisition_id', 'full_name', 'tenant_id'))
            values = [v for k, v in fields.items() if k not in ('requisition_id', 'full_name', 'tenant_id')]
            conn.execute(f'UPDATE candidates SET {set_clause} WHERE id=?', values + [existing['id']])
            conn.commit()
            row = conn.execute('SELECT * FROM candidates WHERE id=?', (existing['id'],)).fetchone()
        else:
            cols = ', '.join(fields.keys())
            placeholders = ', '.join('?' for _ in fields)
            cur = conn.execute(f'INSERT INTO candidates ({cols}) VALUES ({placeholders})', list(fields.values()))
            conn.commit()
            row = conn.execute('SELECT * FROM candidates WHERE id=?', (cur.lastrowid,)).fetchone()

    return jsonify(row_to_candidate(row)), 201

@app.route('/api/v1/candidates/<int:cand_id>', methods=['PUT'])
def update_candidate(cand_id):
    tid = _get_caller_tenant(request)
    if tid is False:
        return jsonify({'error': 'Authentication required.'}), 401
    data = request.get_json(force=True, silent=True) or {}
    allowed = {'current_stage', 'email', 'phone', 'passport_number', 'match_score',
               'total_experience_years', 'relevant_experience_years',
               'skills_matrix', 'specialization_tags', 'industry_remarks', 'cv_file_name',
               'ai_analysis', 'eligible', 'veto_reason'}
    updates = {}
    for key in allowed:
        if key in data:
            if key in ('skills_matrix', 'specialization_tags'):
                updates[key] = json.dumps(data[key])
            elif key == 'ai_analysis':
                updates[key] = json.dumps(data[key]) if data[key] else None
            elif key == 'eligible':
                updates[key] = 1 if data[key] else 0
            else:
                updates[key] = data[key]
    if not updates:
        return jsonify({'error': 'No valid fields to update.'}), 400
    with get_db() as conn:
        set_clause = ', '.join(f'{k}=?' for k in updates)
        if tid is None:
            conn.execute(f'UPDATE candidates SET {set_clause} WHERE id=?', list(updates.values()) + [cand_id])
        else:
            conn.execute(f'UPDATE candidates SET {set_clause} WHERE id=? AND tenant_id=?', list(updates.values()) + [cand_id, tid])
        conn.commit()
        row = conn.execute('SELECT * FROM candidates WHERE id=?', (cand_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Candidate not found.'}), 404
    return jsonify(row_to_candidate(row))

@app.route('/api/v1/candidates/<int:cand_id>', methods=['DELETE'])
def delete_candidate(cand_id):
    tid = _get_caller_tenant(request)
    if tid is False:
        return jsonify({'error': 'Authentication required.'}), 401
    with get_db() as conn:
        if tid is None:
            conn.execute('DELETE FROM candidates WHERE id=?', (cand_id,))
        else:
            conn.execute('DELETE FROM candidates WHERE id=? AND tenant_id=?', (cand_id, tid))
        conn.commit()
    return jsonify({'success': True})

@app.route('/api/v1/candidates/clear', methods=['DELETE'])
def clear_candidates():
    tid = _get_caller_tenant(request)
    if tid is False:
        return jsonify({'error': 'Authentication required.'}), 401
    effective_tid = tid if tid is not None else 'admin-tenant'
    req_id = request.args.get('req_id', type=int)
    with get_db() as conn:
        if tid is None:   # Admin clears globally (or by req_id)
            if req_id:
                conn.execute('DELETE FROM candidates WHERE requisition_id=?', (req_id,))
            else:
                conn.execute('DELETE FROM candidates')
        else:
            if req_id:
                conn.execute('DELETE FROM candidates WHERE requisition_id=? AND tenant_id=?', (req_id, effective_tid))
            else:
                conn.execute('DELETE FROM candidates WHERE tenant_id=?', (effective_tid,))
        conn.commit()
    return jsonify({'success': True})


@app.route('/api/v1/candidates/<int:cand_id>/notes', methods=['GET'])
def get_candidate_notes(cand_id):
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM candidate_notes WHERE candidate_id = ? ORDER BY created_at DESC', (cand_id,)).fetchall()
        return jsonify([dict(r) for r in rows])

@app.route('/api/v1/candidates/<int:cand_id>/notes', methods=['POST'])
def add_candidate_note(cand_id):
    data = request.get_json(force=True, silent=True) or {}
    note_text = data.get('note_text', '').strip()
    author_email = data.get('author_email', 'Recruiter').strip()
    if not note_text:
        return jsonify({'error': 'Note text cannot be empty.'}), 400
    with get_db() as conn:
        cursor = conn.execute('INSERT INTO candidate_notes (candidate_id, author_email, note_text) VALUES (?, ?, ?)', (cand_id, author_email, note_text))
        conn.commit()
        note_id = cursor.lastrowid
        row = conn.execute('SELECT * FROM candidate_notes WHERE id = ?', (note_id,)).fetchone()
        return jsonify(dict(row)), 201

@app.route('/api/v1/candidates/<int:cand_id>/notes/<int:note_id>', methods=['DELETE'])
def delete_candidate_note(cand_id, note_id):
    with get_db() as conn:
        conn.execute('DELETE FROM candidate_notes WHERE id = ? AND candidate_id = ?', (note_id, cand_id))
        conn.commit()
        return jsonify({'success': True})

# ── Instant AI Summary Route ───────────────────────────────────────────────────

@app.route('/api/v1/candidates/<int:cand_id>/instant-summary', methods=['POST'])
def instant_summary(cand_id):
    """
    Generate a concise 3-bullet Gemini summary for a candidate.
    Reads their stored CV file for raw text, then calls the Gemini API.
    Returns: { bullets: [str, str, str] }
    """
    import logging
    from dotenv import load_dotenv
    load_dotenv()
    logger = logging.getLogger(__name__)

    # 1. Fetch candidate record
    with get_db() as conn:
        row = conn.execute('SELECT * FROM candidates WHERE id=?', (cand_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Candidate not found.'}), 404

    candidate = row_to_candidate(row)

    # 2. Try to get CV raw text from file
    cv_text = ''
    cv_file = candidate.get('cv_file_name')
    if cv_file:
        cv_path = os.path.join(UPLOAD_FOLDER, cv_file)
        if os.path.isfile(cv_path):
            try:
                cv_text = extract_text_from_file(cv_path)
            except Exception as e:
                logger.warning(f'Could not extract CV text for summary: {e}')

    # 3. Fall back to stored profile data if no CV file
    if not cv_text.strip():
        skills_str = ', '.join(candidate.get('skills_matrix', []))
        cv_text = (
            f"Name: {candidate['full_name']}\n"
            f"Experience: {candidate['total_experience_years']} years total, "
            f"{candidate['relevant_experience_years']} years relevant\n"
            f"Skills: {skills_str}\n"
            f"Remarks: {candidate.get('industry_remarks', '')}"
        )

    # 4. Call Gemini API
    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    if not api_key or api_key == 'YOUR_GEMINI_API_KEY_HERE':
        return jsonify({'error': 'GEMINI_API_KEY not configured on the server.'}), 503

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        prompt = (
            "You are an expert technical recruiter. Read the following candidate resume text carefully.\n\n"
            "Your task is to produce exactly 3 concise bullet points (each starting with the bullet character) "
            "that a recruiter should know at a glance:\n"
            "  1. Top 3 core technical skills or certifications this person holds\n"
            "  2. Total years of experience and the primary industry/domain they worked in\n"
            "  3. One standout project, achievement, or notable qualification\n\n"
            "Rules:\n"
            "- Each bullet must be a single crisp sentence, max 20 words.\n"
            "- Output ONLY the 3 bullet lines, no headers, no numbering, no markdown.\n"
            "- If information is missing, make a reasonable inference from context.\n\n"
            f"Resume Text:\n{cv_text[:10000]}"
        )

        models_to_try = [
            'gemini-2.5-flash-lite',
            'gemini-2.5-flash',
            'gemini-flash-latest',
            'gemini-2.5-pro',
        ]

        response_text = None
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.2),
                )
                if response.text:
                    response_text = response.text.strip()
                    break
            except Exception as e:
                err = str(e)
                if '429' in err or 'RESOURCE_EXHAUSTED' in err:
                    import time; time.sleep(5)
                elif '404' in err or 'not found' in err.lower():
                    continue
                else:
                    logger.warning(f'Gemini model {model_name} error: {err[:80]}')
                    continue

        if not response_text:
            return jsonify({'error': 'Gemini API did not return a response.'}), 502

        # Parse lines into clean bullet list
        raw_lines = [l.strip() for l in response_text.splitlines() if l.strip()]
        bullets = []
        for line in raw_lines:
            cleaned = line.lstrip('-*\u2022\u2013\u2014 0123456789.').strip()
            if cleaned:
                bullets.append('\u2022 ' + cleaned)
        bullets = bullets[:3]
        if not bullets:
            bullets = [response_text]

        return jsonify({'bullets': bullets})

    except Exception as e:
        logger.error(f'Instant summary error for candidate {cand_id}: {e}')
        return jsonify({'error': f'AI service error: {str(e)[:120]}'}), 500

# ── CV File Existence Check ────────────────────────────────────────────────────

@app.route('/api/v1/cv/<path:filename>/exists', methods=['GET'])
def cv_exists(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    return jsonify({'exists': os.path.isfile(path)})

# ─────────────────────────────────────────────────────────────────────────────

# Directory where uploaded CV files are permanently stored
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt'}

# 1. Domain Taxonomy — 7 Business Verticals
DOMAIN_TAXONOMY = {
    'Oil & Gas': [
        'mechanical engineering', 'chemical engineering', 'petroleum engineering',
        'instrumentation engineering', 'electrical engineering', 'civil engineering',
        'process engineering', 'industrial engineering', 'production engineering',
        'diploma mechanical', 'diploma electrical', 'diploma instrumentation',
        'diploma civil', 'process technology', 'commissioning engineer',
        'qa/qc engineer', 'pipeline engineer', 'welding inspector',
        'ndt inspector', 'safety officer', 'hse engineer', 'instrument engineer',
        'rotating equipment engineer', 'static equipment engineer',
        'maintenance engineer', 'shutdown engineer', 'oil', 'gas', 'petroleum'
    ],
    'Petrochemical': [
        'chemical engineering', 'mechanical engineering', 'instrumentation',
        'electrical', 'polymer engineering', 'process engineer', 'production engineer',
        'plant engineer', 'maintenance engineer', 'operations engineer',
        'process safety engineer', 'petrochemical', 'chemical plant',
        'distillation', 'cracking', 'feedstock'
    ],
    'Construction & Infrastructure': [
        'civil engineering', 'structural engineering', 'architecture',
        'mechanical', 'electrical', 'quantity surveying', 'rics', 'site engineer',
        'planning engineer', 'quantity surveyor', 'project engineer', 'project manager',
        'qa/qc engineer', 'construction manager', 'civil', 'mep', 'construction',
        'structural'
    ],
    'Energy': [
        'electrical engineering', 'mechanical engineering', 'renewable energy engineering',
        'power systems', 'electronics engineering', 'iec standards', 'solar pv design',
        'wind turbine maintenance', 'electrical engineer', 'grid engineer',
        'power systems engineer', 'protection engineer', 'solar engineer', 'wind engineer',
        'renewable', 'solar', 'wind', 'grid', 'energy'
    ],
    'Hospitality': [
        'hotel management', 'hospitality management', 'culinary arts', 'tourism',
        'business administration', 'ahlei', 'wset', 'barista certification',
        'hotel manager', 'front office manager', 'executive chef', 'sous chef',
        'housekeeping manager', 'restaurant manager', 'guest relations', 'hotel',
        'resort', 'barista', 'f&b', 'housekeeping', 'restaurant'
    ],
    'Facilities Management': [
        'mechanical engineering', 'electrical engineering', 'hvac', 'facility management',
        'civil engineering', 'ifma cfm', 'fmp', 'leed', 'bms', 'hvac certification',
        'facility manager', 'maintenance manager', 'hvac engineer', 'mep engineer',
        'building engineer', 'facilities', 'building maintenance', 'property management',
        'fm'
    ],
    'Maritime & Shipping': [
        'marine engineering', 'naval architecture', 'nautical science',
        'mechanical engineering', 'stcw', 'coc class i-iv', 'gmdss', 'dp operator',
        'ism', 'isps', 'marpol', 'tanker endorsement', 'marine engineer',
        'chief engineer', 'second engineer', 'deck officer', 'captain', 'port engineer',
        'technical superintendent', 'maritime', 'shipping', 'vessel', 'marine', 'port',
        'seafarer'
    ],
    'Power Plants': [
        'mechanical', 'electrical', 'instrumentation', 'chemical', 'power engineering',
        'boiler operator', 'turbine maintenance', 'shift engineer', 'operations engineer',
        'turbine engineer', 'boiler engineer', 'maintenance engineer', 'plant manager',
        'power plant', 'turbine', 'boiler', 'generator', 'dcs', 'commissioning'
    ],
    'Engineering Services': [
        'any engineering discipline', 'industrial engineering', 'mechatronics',
        'electronics', 'design engineer', 'project engineer', 'application engineer',
        'sales engineer', 'service engineer'
    ],
    'Manufacturing': [
        'mechanical', 'industrial', 'production', 'mechatronics', 'manufacturing engineering',
        'tpm', 'kaizen', 'cqe', 'cqa', 'production engineer', 'manufacturing engineer',
        'process engineer', 'quality engineer', 'plant manager', 'manufacturing',
        'six sigma', 'lean'
    ],
    'EPC': [
        'mechanical', 'civil', 'electrical', 'instrumentation', 'chemical',
        'epc engineer', 'project engineer', 'procurement engineer', 'construction engineer',
        'planning engineer', 'commissioning engineer', 'qa/qc engineer', 'epc',
        'procurement', 'engineering procurement'
    ]
}

# Specialization Tags
SPECIALIZATION_POOL = [
    'NEBOSH', 'IOSH', 'OSHA 10', 'OSHA 30', 'H2S Alive', 'BOSIET', 'HUET', 'OPITO',
    'CSWIP 3.1', 'CSWIP 3.2', 'AWS CWI', 'API 510', 'API 570', 'API 653',
    'ASNT Level II', 'NACE CIP', 'BGAS', 'PMP', 'Primavera P6', 'AutoCAD', 'PDMS',
    'SP3D', 'SmartPlant', 'ISO 9001 Lead Auditor', 'ISO 45001 Lead Auditor',
    'Six Sigma', 'Lean Manufacturing', 'HAZOP', 'SIL', 'Functional Safety',
    'STAAD Pro', 'ETABS', 'Revit', 'BIM', 'OSHA', 'Quantity Surveying', 'RICS',
    'ISO 9001', 'ETAP', 'SCADA', 'PLC', 'AutoCAD Electrical', 'IEC Standards',
    'Solar PV Design', 'Wind Turbine Maintenance', 'HACCP', 'Food Safety', 'ServSafe',
    'AHLEI', 'WSET', 'Barista Certification', 'IFMA CFM', 'FMP', 'LEED', 'BMS',
    'HVAC Certification', 'STCW', 'COC Class I-IV', 'GMDSS', 'DP Operator', 'ISM',
    'ISPS', 'MARPOL', 'Tanker Endorsement', 'Boiler Operator', 'Turbine Maintenance',
    'DCS', 'SolidWorks', 'CATIA', 'ANSYS', 'MATLAB', 'Six Sigma Green Belt',
    'Six Sigma Black Belt', 'TPM', 'Kaizen', 'CQE', 'CQA', 'AWS'
]

# Skills pool for CV extraction
SKILLS_POOL = [
    'PETROLEUM PIPING', 'DRILLING SIMULATION', 'HSE RISK MANAGEMENT',
    'WELL LOGGING', 'SEISMIC ANALYSIS', 'WELLHEAD OPERATIONS', 'PIPELINE INTEGRITY',
    'PROCESS ENGINEERING', 'CHEMICAL ANALYSIS', 'DISTILLATION OPERATIONS',
    'PLANT OPERATIONS', 'CATALYST MANAGEMENT', 'PROCESS SAFETY',
    'CIVIL ENGINEERING', 'MEP SYSTEMS', 'QUANTITY SURVEYING',
    'STRUCTURAL DESIGN', 'AUTOCAD', 'SITE MANAGEMENT', 'PRIMAVERA P6',
    'HVAC SYSTEMS', 'FACILITIES MANAGEMENT', 'BUILDING MAINTENANCE',
    'ENERGY AUDITING', 'PROPERTY MANAGEMENT', 'PREVENTIVE MAINTENANCE',
    'SHIP OPERATIONS', 'MARINE ENGINEERING', 'PORT LOGISTICS',
    'CARGO HANDLING', 'VESSEL MAINTENANCE', 'MARITIME SAFETY',
    'POWER GENERATION', 'TURBINE MAINTENANCE', 'DCS CONTROL',
    'INSTRUMENTATION', 'BOILER OPERATIONS', 'ELECTRICAL SYSTEMS',
    'CUSTOMER SERVICE', 'F&B OPERATIONS', 'BARISTA SKILLS',
    'HOTEL MANAGEMENT', 'HOUSEKEEPING', 'FOOD SAFETY', 'GUEST RELATIONS',
    'QUALITY ASSURANCE', 'QUALITY CONTROL', 'PROJECT MANAGEMENT', 'LNG OPERATIONS'
]

# Section-header words that are NOT candidate names — blocklist for name parser
NAME_BLOCKLIST = {
    'CONTACT ME', 'CONTACT', 'CONTACTS', 'RESUME', 'CV', 'CURRICULUM VITAE',
    'CURRICULUM', 'VITAE', 'PROFILE', 'PERSONAL DETAILS', 'PERSONAL INFORMATION',
    'PERSONAL PROFILE', 'ABOUT ME', 'OBJECTIVE', 'SUMMARY', 'CAREER SUMMARY',
    'CAREER OBJECTIVE', 'PROFESSIONAL SUMMARY', 'INTRODUCTION', 'BIO', 'BIOGRAPHY',
    'NAME', 'FULL NAME', 'CANDIDATE', 'APPLICANT'
}

# Job titles and placeholder template words that should never be extracted as a candidate's name
TITLE_GENERIC_KEYWORDS = {
    'ENGINEER', 'DEVELOPER', 'MANAGER', 'ANALYST', 'DESIGNER', 'OFFICER', 
    'TECHNICIAN', 'OPERATOR', 'DIRECTOR', 'SUPERVISOR', 'FOREMAN', 'INSPECTOR', 
    'SPECIALIST', 'CONSULTANT', 'CHIEF', 'ADMINISTRATOR', 'LEAD', 'COORDINATOR', 
    'ARCHITECT', 'SURNAME', 'FORENAME', 'FIRSTNAME', 'LASTNAME', 'MIDDLE',
    'RESUME', 'CV', 'CURRICULUM', 'VITAE', 'CONTACT', 'PROFILE', 'OBJECTIVE',
    'SUMMARY', 'EDUCATION', 'EXPERIENCE', 'SKILLS', 'PROJECTS', 'CERTIFICATIONS',
    'ADDITIONAL', 'INFORMATION', 'DETAILS', 'LANGUAGES', 'HOBBIES', 'INTERESTS',
    'PERSONAL', 'WORK', 'HISTORY', 'EMPLOYMENT', 'CAREER', 'QUALIFICATIONS',
    'TESTING', 'COMMISSIONING', 'SURVEYOR', 'EXECUTIVE', 'HEAD', 'ASSISTANT',
    'SENIOR', 'JUNIOR', 'INTERN', 'TRAINEE', 'ASSOCIATE', 'PROJECT', 'SAFETY',
    'QUALITY', 'CONTROL', 'ASSURANCE', 'QA', 'QC', 'HSE', 'EHS', 'NDT', 'PIPELINE',
    'MECHANICAL', 'ELECTRICAL', 'CIVIL', 'INSTRUMENTATION', 'PROCESS', 'INDUSTRIAL'
}

def clean_candidate_name(name, file_hint=''):
    if not name:
        name = "Unknown Candidate"
    name = str(name).strip()
    
    # 1. Remove common prefix labels
    name = re.sub(r'^(name|full\s*name|candidate\s*name|applicant\s*name|candidate|applicant|resume\s*of|cv\s*of|curriculum\s*vitae\s*of|application\s*of)\s*[:\-–—|]\s*', '', name, flags=re.IGNORECASE).strip()
    
    # 2. If the name string contains a delimiter (e.g. "John Doe - Senior Engineer" or "Jane Smith | Piping Manager"), split and check parts
    if re.search(r'\s*[-–—|:]\s*', name):
        parts = re.split(r'\s*[-–—|:]\s*', name)
        for part in parts:
            clean_part = part.strip()
            # Remove post-nominals from part
            clean_part = re.sub(r'(\s*[,|\-–—]\s*(MBA|PMP|PHD|B\.?TECH|B\.?E|M\.?TECH|M\.?S|B\.?S|BSC|MSC|LEED|NEBOSH|IOSH|OSHA|API\s*\d+|CSWIP|RICS|CFM|FMP|P\.?E|C\.?ENG).*)+$', '', clean_part, flags=re.IGNORECASE).strip()
            words = clean_part.split()
            words_cleaned = [re.sub(r'[^\w]', '', w.upper()) for w in words]
            if 1 <= len(words) <= 5 and not re.search(r'\d', clean_part) and not any(w in TITLE_GENERIC_KEYWORDS for w in words_cleaned):
                name = clean_part.title()
                break

    # 3. Remove trailing post-nominals if attached
    name = re.sub(r'(\s*[,|\-–—]\s*(MBA|PMP|PHD|B\.?TECH|B\.?E|M\.?TECH|M\.?S|B\.?S|BSC|MSC|LEED|NEBOSH|IOSH|OSHA|API\s*\d+|CSWIP|RICS|CFM|FMP|P\.?E|C\.?ENG).*)+$', '', name, flags=re.IGNORECASE).strip()
    words_cleaned = [re.sub(r'[^\w]', '', w.upper()) for w in name.split()]
    
    # 4. If the resulting name is still invalid or contains job titles, try fallback from file_hint
    if not name or name.upper() in ["UNKNOWN CANDIDATE", "UNKNOWN", "", "N/A", "NONE", "NULL", "NAME"] or any(w in TITLE_GENERIC_KEYWORDS for w in words_cleaned):
        if file_hint:
            stem = os.path.splitext(file_hint)[0]
            stem = re.sub(r'^[0-9a-f]{8}_', '', stem, flags=re.IGNORECASE)
            stem = re.sub(r'(?i)(_cv|_resume|_application|\d{4,}).*$', '', stem)
            if re.search(r'[-–—|,|_]', stem):
                parts = re.split(r'[-–—|,|_]', stem)
                for p in parts:
                    p_clean = p.strip()
                    p_words = p_clean.split()
                    p_words_upper = [re.sub(r'[^\w]', '', w.upper()) for w in p_words]
                    if 1 <= len(p_words) <= 5 and not re.search(r'\d', p_clean) and not any(w in TITLE_GENERIC_KEYWORDS for w in p_words_upper):
                        return p_clean.title()
            stem = re.sub(r'[_\-]+', ' ', stem).strip()
            stem_words = stem.split()
            stem_words_cleaned = [re.sub(r'[^\w]', '', w.upper()) for w in stem_words]
            if 1 <= len(stem_words) <= 5 and not re.search(r'\d', stem) and not any(w in TITLE_GENERIC_KEYWORDS for w in stem_words_cleaned):
                return stem.title()
        return "Unknown Candidate"
    return name.title() if name else "Unknown Candidate"

def extract_contacts(text, file_hint=''):
    """Scan and parse candidate basic info using regular expressions.
    
    file_hint: the original uploaded filename (without extension) used as a
               last-resort name fallback when the CV text does not yield a
               clean candidate name.
    """
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    phone_regex = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    
    email_match = re.search(email_regex, text)
    phone_match = re.search(phone_regex, text)
    
    email = email_match.group(0) if email_match else "N/A"
    phone = phone_match.group(0) if phone_match else "N/A"
    
    # Try to parse candidate name from the first 8 non-empty lines.
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    full_name = None
    for line in lines[:8]:
        line = re.sub(r'^(name|full\s*name|candidate\s*name|applicant\s*name|candidate|applicant|resume\s*of|cv\s*of|curriculum\s*vitae\s*of)\s*[:\-–—|]\s*', '', line, flags=re.IGNORECASE).strip()
        line = re.sub(r'^(NAME|Full Name|Candidate Name|Applicant Name|Name)\s*[:\-]\s*', '', line, flags=re.IGNORECASE).strip()
        if not line:
            continue
        # Check if line has a delimiter like John Doe - Engineer
        if re.search(r'\s*[-–—|:]\s*', line):
            parts = re.split(r'\s*[-–—|:]\s*', line)
            line = parts[0].strip()
        words = re.split(r'[\s._-]+', line)
        words = [w for w in words if w]
        if not (1 <= len(words) <= 5):
            continue
        if re.search(r'\d', line):
            continue
        if '@' in line:
            continue
        if re.fullmatch(r'[^\w\s]+', line):
            continue
        if line.upper().strip() in NAME_BLOCKLIST:
            continue
        words_cleaned = [re.sub(r'[^\w]', '', w.upper()) for w in words]
        if any(w in TITLE_GENERIC_KEYWORDS for w in words_cleaned):
            continue
        full_name = line
        break

    if full_name is None and file_hint:
        full_name = clean_candidate_name("", file_hint=file_hint)
            
    return clean_candidate_name(full_name, file_hint=file_hint), email, phone

def parse_experience_years(text):
    """Estimate total experience years from textual descriptions"""
    text_lower = text.lower()
    
    # 1. Search for explicit "total", "overall", or "work" experience patterns
    explicit_patterns = [
        r'(?:total|overall|work|professional|industry)\s+experience\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)',
        r'(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\s+(?:of\s+)?(?:total|overall|work|professional|industry)?\s*experience',
        r'experience\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)',
    ]
    for pattern in explicit_patterns:
        match = re.search(pattern, text_lower)
        if match:
            try:
                val = float(match.group(1))
                if 0 < val < 50:
                    return val
            except ValueError:
                pass

    # 2. Search for any pattern of "N years" or "N yrs"
    all_yr_matches = re.findall(r'\b(\d{1,2})\+?\s*(?:years?|yrs?)\b', text_lower)
    if all_yr_matches:
        try:
            vals = [float(x) for x in all_yr_matches]
            valid_vals = [v for v in vals if 0 < v < 50]
            if valid_vals:
                # The maximum years value usually represents total experience
                return max(valid_vals)
        except ValueError:
            pass

    # 3. Date-range heuristic (e.g. 2018 - present)
    years = re.findall(r'\b(20[0-2][0-9]|19[8-9][0-9])\b', text_lower)
    if years:
        try:
            year_vals = [int(y) for y in years]
            min_year = min(year_vals)
            max_year = max(year_vals)
            if "present" in text_lower or "current" in text_lower:
                max_year = max(max_year, 2026)
            diff = max_year - min_year
            if 0 < diff < 45:
                return float(diff)
        except Exception:
            pass
            
    # Default fallback
    return 7.0

# Domains considered "adjacent heavy industry" — these share significant
# skillset overlap with engineering-heavy targets (e.g. commissioning, testing,
# instrumentation) and should receive a PARTIAL match rather than a full penalty.
ADJACENT_DOMAIN_MAP = {
    # target_domain -> set of candidate domains treated as partial match
    'Oil & Gas':                  {'Power Plants', 'EPC', 'Petrochemical', 'Manufacturing', 'Energy', 'Engineering Services'},
    'Petrochemical':              {'Oil & Gas', 'Power Plants', 'EPC', 'Manufacturing', 'Energy'},
    'Power Plants':               {'Oil & Gas', 'EPC', 'Energy', 'Petrochemical', 'Manufacturing', 'Engineering Services'},
    'EPC':                        {'Oil & Gas', 'Power Plants', 'Petrochemical', 'Construction & Infrastructure', 'Manufacturing'},
    'Energy':                     {'Power Plants', 'Oil & Gas', 'EPC', 'Petrochemical', 'Facilities Management'},
    'Construction & Infrastructure': {'EPC', 'Facilities Management', 'Engineering Services', 'Manufacturing'},
    'Facilities Management':      {'Construction & Infrastructure', 'Energy', 'Engineering Services', 'Manufacturing'},
    'Manufacturing':              {'EPC', 'Engineering Services', 'Power Plants', 'Oil & Gas'},
    'Engineering Services':       {'Manufacturing', 'EPC', 'Power Plants', 'Construction & Infrastructure'},
    'Maritime & Shipping':        {'Engineering Services', 'Oil & Gas'},
}

def score_candidate_data(candidate_text, target_domain='', file_hint='', jd_text=''):
    """Screen a candidate CV against a job description and/or target domain.

    Parameters
    ----------
    candidate_text : str   Raw text extracted from the CV file.
    target_domain  : str   The hiring domain (optional — auto-detected when blank).
    file_hint      : str   Original uploaded filename used as name-parsing fallback.
    jd_text        : str   Full job description text (primary matching signal when provided).
    """
    # Extract candidate metadata
    full_name, email, phone = extract_contacts(candidate_text, file_hint=file_hint)
    total_exp = parse_experience_years(candidate_text)

    # Identify skills present in resume
    skills_matrix = []
    text_upper = candidate_text.upper()
    for skill in SKILLS_POOL:
        if skill in text_upper:
            skills_matrix.append(skill)

    # Extract specialization tags
    specialization_tags = []
    for spec in SPECIALIZATION_POOL:
        if spec.lower() in candidate_text.lower():
            specialization_tags.append(spec)

    # Analyze keyword density per industry domain
    text_lower = candidate_text.lower()
    domain_scores = {}
    for domain, keywords in DOMAIN_TAXONOMY.items():
        count = 0
        for kw in keywords:
            matches = re.findall(rf'\b{re.escape(kw)}\b', text_lower)
            count += len(matches)
        domain_scores[domain] = count

    # Determine candidate's primary domain by keyword frequency
    candidate_domain = max(domain_scores, key=domain_scores.get)
    max_count = domain_scores[candidate_domain]

    # Auto-detect target domain from JD or CV if not explicitly set
    if not target_domain:
        if jd_text:
            jd_lower = jd_text.lower()
            jd_domain_scores = {}
            for domain, keywords in DOMAIN_TAXONOMY.items():
                count = sum(len(re.findall(rf'\b{re.escape(kw)}\b', jd_lower)) for kw in keywords)
                jd_domain_scores[domain] = count
            target_domain = max(jd_domain_scores, key=jd_domain_scores.get)
        else:
            target_domain = candidate_domain  # fall back to CV-detected domain

    # ── JD Keyword Matching (primary signal when JD provided) ────────────────
    jd_match_score = 0
    jd_matched_keywords = []
    jd_keywords = []

    if jd_text:
        jd_lower = jd_text.lower()
        cv_lower = candidate_text.lower()

        # Extract all meaningful words from JD (4+ chars, not stopwords)
        stopwords = {'with', 'have', 'that', 'this', 'from', 'will', 'must', 'shall',
                     'should', 'would', 'their', 'been', 'able', 'work', 'team',
                     'strong', 'good', 'role', 'also', 'well', 'based', 'more'}
        raw_words = re.findall(r'\b[a-z][a-z0-9/&+\-]{3,}\b', jd_lower)
        jd_keywords = list(dict.fromkeys([w for w in raw_words if w not in stopwords]))  # deduplicated

        # Score each JD keyword found in CV (weighted by word length as proxy for specificity)
        total_weight = 0
        matched_weight = 0
        for kw in jd_keywords[:120]:  # cap at 120 most-frequent JD terms
            weight = min(3.0, 1.0 + len(kw) * 0.1)  # longer/specific terms worth more
            total_weight += weight
            if re.search(rf'\b{re.escape(kw)}\b', cv_lower):
                matched_weight += weight
                jd_matched_keywords.append(kw)

        # JD score: up to 60 points based on keyword coverage
        jd_match_score = int((matched_weight / total_weight) * 60) if total_weight > 0 else 0

    # ── Base score factors (skills, experience, specialization) ──────────────
    skill_factor = min(25, len(skills_matrix) * 5)
    exp_factor   = min(25, total_exp * 3)
    spec_factor  = min(10, len(specialization_tags) * 5)

    # ── Final Match Score ────────────────────────────────────────────────────
    relevant_exp = total_exp

    if jd_text and jd_keywords:
        # JD-based scoring: JD keyword match is the primary signal (60%), skills/exp/spec top it up (40%)
        match_score = jd_match_score + skill_factor + exp_factor + spec_factor
        match_score = max(10, min(100, match_score))

        jd_coverage = round((len(jd_matched_keywords) / max(1, len(jd_keywords[:120]))) * 100, 1)
        remarks = (
            f"JD Match: {jd_coverage}% of job description keywords found in CV "
            f"({len(jd_matched_keywords)} of {min(len(jd_keywords), 120)} terms). "
            f"Detected domain: {target_domain}. "
            f"Experience: {total_exp:.1f} years. "
            f"Matched CV skills: {', '.join(skills_matrix[:5]) if skills_matrix else 'General Technical'}."
        )

    else:
        # Domain-taxonomy fallback when no JD supplied
        adjacent_domains = ADJACENT_DOMAIN_MAP.get(target_domain, set())
        is_exact_match    = (candidate_domain == target_domain)
        is_adjacent_match = (not is_exact_match) and (candidate_domain in adjacent_domains)

        if is_exact_match or max_count < 2:
            match_score = int(skill_factor * 1.6 + exp_factor * 1.6 + spec_factor * 2)
            match_score = max(10, min(100, match_score))
            remarks = (
                f"Domain Match ({target_domain}). {total_exp:.1f} yrs experience. "
                f"Skills: {', '.join(skills_matrix[:4]) if skills_matrix else 'General Technical'}."
            )
        elif is_adjacent_match:
            relevant_exp = round(total_exp * 0.60, 1)
            match_score  = int(20 + skill_factor * 1.4 + exp_factor * 1.2 + spec_factor * 1.5)
            match_score  = max(42, min(80, match_score))
            remarks = (
                f"Adjacent Domain ({candidate_domain} → {target_domain}). "
                f"{relevant_exp:.1f} yrs transferable experience. "
                f"Skills: {', '.join(skills_matrix[:4]) if skills_matrix else 'General Technical'}."
            )
        else:
            relevant_exp = round(total_exp * 0.15, 1)
            match_score  = int(20 + min(18, total_exp * 2) + min(10, len(skills_matrix) * 2))
            match_score  = max(20, min(48, match_score))
            remarks = (
                f"Domain Mismatch. CV focused on {candidate_domain} "
                f"vs required {target_domain}. {total_exp:.1f} yrs total experience."
            )

    # 5. AI Precision ATS Parsing & Semantic Enrichment (Google Gemini)
    ai_result = analyze_candidate_with_ai(candidate_text, jd_text, target_domain, match_score)
    ai_analysis_payload = None
    eligible = True
    veto_reason = None

    if ai_result and isinstance(ai_result, dict):
        # 1. Enforce AI cleaned full_name (prevents headers like PERSONAL DETAILS or trailing MBA/PMP)
        ai_name = ai_result.get("full_name")
        if ai_name and str(ai_name).strip() not in ["Unknown Candidate", "UNKNOWN", ""]:
            full_name = str(ai_name).strip()
        
        # 2. Enforce AI extracted email and phone if found
        if ai_result.get("email") and str(ai_result.get("email")).strip():
            email = str(ai_result["email"]).strip()
        if ai_result.get("phone") and str(ai_result.get("phone")).strip():
            phone = str(ai_result["phone"]).strip()

        # 3. Use mathematically calculated timeline experience from AI
        if isinstance(ai_result.get("total_experience_years"), (int, float)):
            total_exp = round(float(ai_result["total_experience_years"]), 1)
        if isinstance(ai_result.get("relevant_experience_years"), (int, float)):
            relevant_exp = round(float(ai_result["relevant_experience_years"]), 1)

        # 4. Check eligibility from AI
        if "eligible" in ai_result:
            eligible = bool(ai_result["eligible"])
        if "justification" in ai_result:
            veto_reason = ai_result["justification"]

        # 5. Use precision AI match_score (blended 20% algorithmic + 80% AI semantic for maximum accuracy)
        if isinstance(ai_result.get("match_score"), (int, float)):
            match_score = int(round(0.2 * match_score + 0.8 * float(ai_result["match_score"])))
            match_score = max(0, min(100, match_score))

        # Hard stop rule: cap the score at 40% if the candidate lacks any mandatory requirement
        if not eligible:
            match_score = min(40, match_score)

        # 6. Merge or use AI skills matrix and specialization tags
        if isinstance(ai_result.get("skills_matrix"), list) and len(ai_result["skills_matrix"]) > 0:
            skills_matrix = [str(s).upper() for s in ai_result["skills_matrix"]]
        if isinstance(ai_result.get("specialization_tags"), list) and len(ai_result["specialization_tags"]) > 0:
            specialization_tags = [str(t) for t in ai_result["specialization_tags"]]

        # 7. Use AI industry remarks
        if ai_result.get("industry_remarks"):
            remarks = str(ai_result["industry_remarks"])

        # 8. Extract interview and summary report for frontend AI panel
        ai_analysis_payload = ai_result.get("ai_analysis")
        if not ai_analysis_payload or not isinstance(ai_analysis_payload, dict):
            ai_analysis_payload = {
                "summary": ai_result.get("industry_remarks", ""),
                "strengths": ai_result.get("strengths", []),
                "gaps": ai_result.get("gaps", []),
                "interview_questions": ai_result.get("interview_questions", [])
            }

    full_name = clean_candidate_name(full_name, file_hint=file_hint)

    return {
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "total_experience_years": total_exp,
        "relevant_experience_years": relevant_exp,
        "match_score": match_score,
        "skills_matrix": skills_matrix if skills_matrix else ["GENERAL TECHNICAL"],
        "specialization_tags": specialization_tags,
        "industry_remarks": remarks,
        "ai_analysis": ai_analysis_payload,
        "eligible": eligible,
        "veto_reason": veto_reason
    }

# ── Mandatory employer-keyword veto (Python-side safety net) ─────────────────
# These are the known mandatory employer/programme keywords for active job posts.
# The AI prompt is the primary enforcer; this block is an explicit Python
# fallback that runs AFTER the AI result is returned to guarantee correctness.
# All comparisons are normalised to lowercase so casing in the JD or CV never
# causes a missed match.
_MANDATORY_EMPLOYER_KEYWORDS = [
    "sec",               # Saudi Electricity Company
    "aramco",            # Saudi Aramco
    "national grid ksa", # National Grid SA
    "marafiq",           # Power & Water Utility
]

def _apply_mandatory_keyword_veto(scored: dict, candidate_text: str, jd_text: str) -> dict:
    """
    Python-side safety net for mandatory employer/programme requirements.

    • All string comparisons are normalised with .lower() so casing in the
      source documents never causes a false negative.
    • If the active JD contains at least one mandatory keyword AND the raw
      CV text contains none of those keywords, the candidate is forcibly vetoed:
        - eligible    -> False
        - match_score -> min(ai_score, 40)   # cap at 40, never raise below-40 AI scores
        - veto_reason -> descriptive message listing the missing requirement
    • If the JD does not mention any mandatory keyword, no veto fires so
      non-regulated job posts are completely unaffected.
    """
    # ── Normalise both texts once (case-insensitive, strip extra whitespace) ──
    jd_lower  = (jd_text  or "").lower()
    cv_lower  = (candidate_text or "").lower()

    # Which mandatory keywords appear in THIS job description?
    required_in_jd = [kw for kw in _MANDATORY_EMPLOYER_KEYWORDS if kw in jd_lower]

    if not required_in_jd:
        return scored  # No regulated requirement in this JD → skip

    # Does the CV mention at least one of the required employer/programme names?
    cv_has_required = any(kw in cv_lower for kw in required_in_jd)

    if not cv_has_required:
        missing = ", ".join(k.upper() for k in required_in_jd)
        original_score = scored.get("match_score", 0)
        capped_score   = min(original_score, 40)   # never raise a sub-40 AI score
        scored["eligible"]    = False
        scored["match_score"] = capped_score
        scored["veto_reason"] = (
            f"MANDATORY employer requirement not met. "
            f"This position requires experience with: {missing}. "
            f"No evidence of this was found in the candidate's CV."
        )
        _app_logger.info(
            "[VETO] Mandatory-keyword veto applied | missing=%s | score %d→%d",
            missing, original_score, capped_score,
        )

    return scored


@app.route('/api/v1/screen-candidate', methods=['POST'])
def screen_candidate():
    data = request.get_json()
    if not data or 'candidate_text' not in data:
        return jsonify({"error": "Missing parameter 'candidate_text'"}), 400

    candidate_text = data['candidate_text']
    target_domain  = data.get('target_domain', '')   # now optional
    jd_text        = data.get('job_description_text', '')
    file_hint      = data.get('file_hint', '')

    response_payload = score_candidate_data(candidate_text, target_domain, file_hint=file_hint, jd_text=jd_text)

    # Python-side mandatory keyword veto (safety net after AI scoring)
    response_payload = _apply_mandatory_keyword_veto(response_payload, candidate_text, jd_text)

    return jsonify(response_payload)


# -- Aliases for Magic Search query parsing --
SKILL_ALIASES = {
    'hse': 'HSE RISK MANAGEMENT', 'safety': 'HSE RISK MANAGEMENT', 'ehs': 'HSE RISK MANAGEMENT',
    'qaqc': 'QUALITY ASSURANCE', 'qa/qc': 'QUALITY ASSURANCE', 'qa': 'QUALITY ASSURANCE', 'qc': 'QUALITY CONTROL',
    'ndt': 'WELL LOGGING', 'non destructive testing': 'WELL LOGGING',
    'p6': 'PRIMAVERA P6', 'primavera': 'PRIMAVERA P6',
    'plc': 'DCS CONTROL', 'dcs': 'DCS CONTROL', 'programmable logic controller': 'DCS CONTROL', 'distributed control system': 'DCS CONTROL',
    'mep': 'MEP SYSTEMS', 'mechanical electrical plumbing': 'MEP SYSTEMS',
    'hvac': 'HVAC SYSTEMS', 'heating ventilation air conditioning': 'HVAC SYSTEMS',
    'pm': 'PROJECT MANAGEMENT', 'pmo': 'PROJECT MANAGEMENT', 'project management office': 'PROJECT MANAGEMENT',
    'epc': 'CIVIL ENGINEERING', 'engineering procurement construction': 'CIVIL ENGINEERING',
    'lng': 'LNG OPERATIONS', 'liquefied natural gas': 'LNG OPERATIONS', 'lpg': 'LNG OPERATIONS', 'cng': 'LNG OPERATIONS',
    'b.tech': 'CIVIL ENGINEERING', 'bachelor of technology': 'CIVIL ENGINEERING',
    'b.e.': 'CIVIL ENGINEERING', 'bachelor of engineering': 'CIVIL ENGINEERING',
    'diploma': 'CIVIL ENGINEERING', 'polytechnic diploma': 'CIVIL ENGINEERING',
    
    # Original aliases that are still useful
    'petroleum': 'PETROLEUM PIPING', 'pipeline': 'PETROLEUM PIPING', 'piping': 'PETROLEUM PIPING',
    'drilling': 'DRILLING SIMULATION',
    'wellhead': 'WELLHEAD OPERATIONS', 'pipeline integrity': 'PIPELINE INTEGRITY',
    'process engineering': 'PROCESS ENGINEERING', 'process engineer': 'PROCESS ENGINEERING',
    'chemical analysis': 'CHEMICAL ANALYSIS',
    'distillation': 'DISTILLATION OPERATIONS',
    'plant operations': 'PLANT OPERATIONS',
    'catalyst': 'CATALYST MANAGEMENT',
    'process safety': 'PROCESS SAFETY',
    'civil engineering': 'CIVIL ENGINEERING', 'structural': 'STRUCTURAL DESIGN',
    'quantity surveying': 'QUANTITY SURVEYING', 'qs': 'QUANTITY SURVEYING',
    'autocad': 'AUTOCAD', 'cad': 'AUTOCAD',
    'site management': 'SITE MANAGEMENT',
    'chiller': 'HVAC SYSTEMS',
    'facilities management': 'FACILITIES MANAGEMENT', 'fm': 'FACILITIES MANAGEMENT',
    'building maintenance': 'BUILDING MAINTENANCE',
    'energy auditing': 'ENERGY AUDITING',
    'property management': 'PROPERTY MANAGEMENT',
    'preventive maintenance': 'PREVENTIVE MAINTENANCE', 'ppm': 'PREVENTIVE MAINTENANCE',
    'ship operations': 'SHIP OPERATIONS',
    'marine engineering': 'MARINE ENGINEERING',
    'port logistics': 'PORT LOGISTICS',
    'cargo handling': 'CARGO HANDLING',
    'maritime safety': 'MARITIME SAFETY', 'stcw': 'MARITIME SAFETY',
    'power generation': 'POWER GENERATION', 'power plant': 'POWER GENERATION',
    'turbine': 'TURBINE MAINTENANCE', 'gas turbine': 'TURBINE MAINTENANCE',
    'scada': 'DCS CONTROL',
    'instrumentation': 'INSTRUMENTATION',
    'boiler': 'BOILER OPERATIONS',
    'customer service': 'CUSTOMER SERVICE',
    'food and beverage': 'F&B OPERATIONS', 'f&b': 'F&B OPERATIONS',
    'barista': 'BARISTA SKILLS', 'coffee': 'BARISTA SKILLS',
    'hotel management': 'HOTEL MANAGEMENT',
    'housekeeping': 'HOUSEKEEPING',
    'food safety': 'FOOD SAFETY',
    'guest relations': 'GUEST RELATIONS',
}

DOMAIN_ALIASES = {
    'oil': 'Oil & Gas', 'gas': 'Oil & Gas', 'petroleum': 'Oil & Gas',
    'offshore': 'Oil & Gas', 'refinery': 'Oil & Gas', 'hydrocarbon': 'Oil & Gas',
    'upstream': 'Oil & Gas', 'downstream': 'Oil & Gas', 'lng': 'Oil & Gas',
    'petrochemical': 'Petrochemical', 'chemical plant': 'Petrochemical',
    'cracking': 'Petrochemical', 'feedstock': 'Petrochemical',
    'construction': 'Construction & Infrastructure', 'civil': 'Construction & Infrastructure',
    'infrastructure': 'Construction & Infrastructure', 'mep': 'Construction & Infrastructure',
    'energy': 'Energy', 'renewable': 'Energy', 'solar': 'Energy', 'wind': 'Energy',
    'facilities': 'Facilities Management', 'hvac': 'Facilities Management',
    'building services': 'Facilities Management', 'fm': 'Facilities Management',
    'maritime': 'Maritime & Shipping', 'shipping': 'Maritime & Shipping',
    'marine': 'Maritime & Shipping', 'vessel': 'Maritime & Shipping',
    'port': 'Maritime & Shipping', 'seafarer': 'Maritime & Shipping',
    'power plant': 'Power Plants', 'turbine': 'Power Plants',
    'boiler': 'Power Plants', 'generator': 'Power Plants',
    'engineering services': 'Engineering Services', 'mechatronics': 'Engineering Services',
    'manufacturing': 'Manufacturing', 'production': 'Manufacturing', 'six sigma': 'Manufacturing',
    'epc': 'EPC', 'procurement': 'EPC',
    'hotel': 'Hospitality', 'resort': 'Hospitality', 'barista': 'Hospitality',
    'restaurant': 'Hospitality', 'catering': 'Hospitality', 'hospitality': 'Hospitality',
}

SPEC_ALIASES = {
    'hse certified': 'HSE Certified', 'hse': 'HSE Certified', 'ehs': 'HSE Certified',
    'nebosh': 'NEBOSH', 'opito': 'OPITO', 'osha': 'OSHA 30', 'osha 10': 'OSHA 10', 'osha 30': 'OSHA 30',
    'deepwater': 'Deepwater Drilling', 'deepwater drilling': 'Deepwater Drilling',
    'well logging': 'Well Logging',
    'process safety management': 'Process Safety Management', 'hazop': 'HAZOP',
    'mep engineer': 'MEP Engineer',
    'quantity surveyor': 'Quantity Surveying', 'qs': 'Quantity Surveying',
    'stcw': 'STCW', 'class 1 marine': 'COC Class I-IV',
    'deck officer': 'Deck Officer',
    'gas turbine': 'Turbine Maintenance',
    'dcs/scada': 'DCS', 'scada operator': 'SCADA',
    'power plant commissioning': 'Power Plant Commissioning',
    'hvac specialist': 'HVAC Certification',
    'facilities manager': 'IFMA CFM',
    'food safety certified': 'Food Safety',
    'hospitality management': 'Hospitality Management',
    'qaqc': 'CQE', 'qa/qc': 'CQE', 'qa': 'CQE', 'qc': 'CQA',
    'p6': 'Primavera P6', 'primavera': 'Primavera P6',
    'plc': 'PLC', 'dcs': 'DCS', 'mep': 'MEP Engineer',
    'hvac': 'HVAC Certification', 'pm': 'PMP', 'pmo': 'PMP',
    'iso 9001': 'ISO 9001', 'iso 45001': 'ISO 45001 Lead Auditor',
    'api 510': 'API 510', 'api 570': 'API 570', 'api 653': 'API 653',
    'six sigma': 'Six Sigma', 'lean': 'Lean Manufacturing',
    'bim': 'BIM', 'revit': 'Revit',
}


def parse_magic_query(query):
    """Extract intent signals from a natural-language recruiter query."""
    q = query.lower().strip()

    # Experience years
    exp_years = None
    exp_match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)', q)
    if exp_match:
        exp_years = float(exp_match.group(1))

    # Skill signals (check multi-word aliases first, then single-word)
    matched_skills = set()
    sorted_aliases = sorted(SKILL_ALIASES.keys(), key=len, reverse=True)
    for alias in sorted_aliases:
        if alias in q:
            matched_skills.add(SKILL_ALIASES[alias])
    for skill in SKILLS_POOL:
        if skill.lower() in q:
            matched_skills.add(skill)

    # Domain signals
    matched_domains = set()
    for alias, canonical in DOMAIN_ALIASES.items():
        if re.search(rf'\b{re.escape(alias)}\b', q):
            matched_domains.add(canonical)

    # Specialization signals
    matched_specs = set()
    for alias, canonical in SPEC_ALIASES.items():
        if alias in q:
            matched_specs.add(canonical)

    return {'exp_years': exp_years, 'skills': list(matched_skills),
            'domains': list(matched_domains), 'specs': list(matched_specs)}


def score_relevance(candidate, signals):
    """Score a candidate against parsed query signals. Returns (score, matched_signals)."""
    score = 0
    matched = []

    # Skill matches — 30 pts each
    cand_skills = [s.upper() for s in candidate.get('skills_matrix', [])]
    for skill in signals['skills']:
        if skill.upper() in cand_skills:
            score += 30
            matched.append(skill)

    # Domain match — 25 pts (once)
    remarks = candidate.get('industry_remarks', '').lower()
    for domain in signals['domains']:
        domain_kws = DOMAIN_TAXONOMY.get(domain, [])
        if any(kw in remarks for kw in domain_kws):
            score += 25
            matched.append(domain)
            break

    # Specialization tags — 20 pts each
    cand_specs = [s.lower() for s in candidate.get('specialization_tags', [])]
    for spec in signals['specs']:
        if spec.lower() in cand_specs:
            score += 20
            matched.append(spec)

    # Experience proximity — up to 15 pts
    if signals['exp_years'] is not None:
        cand_exp = float(candidate.get('total_experience_years', 0))
        diff = abs(cand_exp - signals['exp_years'])
        exp_label = f'~{cand_exp:.0f} yrs exp'
        if diff <= 1:
            score += 15
            matched.append(exp_label)
        elif diff <= 3:
            score += 8
            matched.append(exp_label)
        elif diff <= 5:
            score += 3

    # Tiebreaker: existing match_score (0–10 pts)
    score += int(candidate.get('match_score', 0) * 0.1)

    return score, matched


@app.route('/api/v1/semantic-search', methods=['POST'])
def semantic_search():
    """Magic Search: rank candidate list by natural-language query relevance."""
    data = request.get_json()
    if not data or 'query' not in data or 'candidates' not in data:
        return jsonify({'error': "Missing 'query' or 'candidates'"}), 400

    query = data['query'].strip()
    candidates_list = data['candidates']

    if not query:
        return jsonify({'results': candidates_list, 'signals': {}}), 200

    signals = parse_magic_query(query)

    scored = []
    for cand in candidates_list:
        rel_score, matched_signals = score_relevance(cand, signals)
        scored.append({**cand, 'relevance_score': rel_score, 'matched_signals': matched_signals})

    scored.sort(key=lambda c: (c['relevance_score'], c.get('match_score', 0)), reverse=True)

    return jsonify({'results': scored, 'signals': signals, 'total': len(scored)})


def extract_text_from_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    
    if ext == '.pdf':
        if fitz:
            try:
                doc = fitz.open(file_path)
                text = "\n".join([page.get_text() for page in doc])
            except Exception as e:
                text = f"[Error reading PDF with PyMuPDF: {str(e)}]"
        elif pypdf:
            try:
                reader = pypdf.PdfReader(file_path)
                text = "\n".join([page.extract_text() or "" for page in reader.pages])
            except Exception as e:
                text = f"[Error reading PDF with pypdf: {str(e)}]"
        else:
            text = "[PDF parser library (PyMuPDF or pypdf) not installed on server]"
            
    elif ext in ['.docx', '.doc']:
        if docx:
            try:
                doc = docx.Document(file_path)
                text = "\n".join([p.text for p in doc.paragraphs])
            except Exception as e:
                text = f"[Error reading Word document: {str(e)}]"
        else:
            text = "[Word document parser library python-docx not installed on server]"
            
    elif ext in ['.txt', '.rtf']:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        except Exception as e:
            text = f"[Error reading text file: {str(e)}]"
            
    return text

def get_mock_candidates_for_domain(target_domain):
    if target_domain == 'Oil & Gas':
        return [
            {
                "fileName": "Sarah_Jenkins_CV.pdf",
                "fileSize": 142300,
                "parsedData": {
                    "full_name": "Sarah Jenkins",
                    "email": "sarah.jenkins@petroleum-eng.com",
                    "phone": "+1 (555) 014-8821",
                    "total_experience_years": 10.0,
                    "relevant_experience_years": 10.0,
                    "match_score": 88,
                    "skills_matrix": ["PETROLEUM PIPING", "DRILLING SIMULATION", "HSE RISK MANAGEMENT", "PROJECT MANAGEMENT"],
                    "specialization_tags": ["Deepwater Drilling", "HSE Certified"],
                    "industry_remarks": "Strong Domain Match. Candidate possesses 10.0 years of experience in Oil & Gas with matching industry-specific skills (PETROLEUM PIPING, DRILLING SIMULATION)."
                }
            },
            {
                "fileName": "Michael_Chang_Resume.docx",
                "fileSize": 88400,
                "parsedData": {
                    "full_name": "Michael Chang",
                    "email": "m.chang@refineryops.org",
                    "phone": "+1 (555) 982-1430",
                    "total_experience_years": 4.0,
                    "relevant_experience_years": 4.0,
                    "match_score": 58,
                    "skills_matrix": ["PETROLEUM PIPING", "HSE RISK MANAGEMENT", "GIS MAINTENANCE"],
                    "specialization_tags": ["HSE Certified"],
                    "industry_remarks": "Strong Domain Match. Candidate possesses 4.0 years of experience in Oil & Gas with matching industry-specific skills (PETROLEUM PIPING)."
                }
            },
            {
                "fileName": "David_Miller_IT_CV.pdf",
                "fileSize": 105600,
                "parsedData": {
                    "full_name": "David Miller",
                    "email": "david.miller.dev@gmail.com",
                    "phone": "+1 (555) 321-4567",
                    "total_experience_years": 6.0,
                    "relevant_experience_years": 0.9,
                    "match_score": 26,
                    "skills_matrix": ["REACT", "TYPESCRIPT", "JAVASCRIPT", "PYTHON", "SQL", "GIT"],
                    "specialization_tags": [],
                    "industry_remarks": "Domain Mismatch Penalty. Candidate has 6.0 years of overall experience, but their footprint is heavily concentrated in the Information Technology industry (keyword density: 12). They lack the necessary specialized domain experience in Oil & Gas."
                }
            }
        ]
    elif target_domain == 'Railway':
        return [
            {
                "fileName": "Alistair_Vance_Resume.pdf",
                "fileSize": 151200,
                "parsedData": {
                    "full_name": "Alistair Vance",
                    "email": "a.vance@transitsystems.net",
                    "phone": "+44 20 7946 0192",
                    "total_experience_years": 9.0,
                    "relevant_experience_years": 9.0,
                    "match_score": 92,
                    "skills_matrix": ["SIGNALING SYSTEMS", "ROLLING STOCK MAINTENANCE", "SCADA CONTROL", "PROJECT MANAGEMENT"],
                    "specialization_tags": ["CBTC Systems", "PLC/SCADA Developer"],
                    "industry_remarks": "Strong Domain Match. Candidate possesses 9.0 years of experience in Railway with matching industry-specific skills (SIGNALING SYSTEMS, ROLLING STOCK MAINTENANCE)."
                }
            },
            {
                "fileName": "Elena_Rostova_CV.docx",
                "fileSize": 91200,
                "parsedData": {
                    "full_name": "Elena Rostova",
                    "email": "e.rostova@railwayinfra.com",
                    "phone": "+7 912 345 6789",
                    "total_experience_years": 3.0,
                    "relevant_experience_years": 3.0,
                    "match_score": 52,
                    "skills_matrix": ["ROLLING STOCK MAINTENANCE", "AUTOCAD", "PROJECT MANAGEMENT"],
                    "specialization_tags": [],
                    "industry_remarks": "Strong Domain Match. Candidate possesses 3.0 years of experience in Railway with matching industry-specific skills (ROLLING STOCK MAINTENANCE)."
                }
            },
            {
                "fileName": "David_Miller_IT_CV.pdf",
                "fileSize": 105600,
                "parsedData": {
                    "full_name": "David Miller",
                    "email": "david.miller.dev@gmail.com",
                    "phone": "+1 (555) 321-4567",
                    "total_experience_years": 6.0,
                    "relevant_experience_years": 0.9,
                    "match_score": 28,
                    "skills_matrix": ["REACT", "TYPESCRIPT", "JAVASCRIPT", "PYTHON", "SQL", "GIT"],
                    "specialization_tags": [],
                    "industry_remarks": "Domain Mismatch Penalty. Candidate has 6.0 years of overall experience, but their footprint is heavily concentrated in the Information Technology industry (keyword density: 12). They lack the necessary specialized domain experience in Railway."
                }
            }
        ]
    elif target_domain == 'Electrical/Testing':
        return [
            {
                "fileName": "Marcus_Vance_CV.pdf",
                "fileSize": 164000,
                "parsedData": {
                    "full_name": "Marcus Vance",
                    "email": "marcus.vance@powergrid.com",
                    "phone": "+1 (555) 234-5678",
                    "total_experience_years": 12.0,
                    "relevant_experience_years": 12.0,
                    "match_score": 95,
                    "skills_matrix": ["HIGH VOLTAGE RELAY", "GIS MAINTENANCE", "SWITCHGEAR TESTING", "SCADA CONTROL"],
                    "specialization_tags": ["380KV", "765KV", "ETAP Certified", "PLC/SCADA Developer"],
                    "industry_remarks": "Strong Domain Match. Candidate possesses 12.0 years of experience in Electrical/Testing with matching industry-specific skills (HIGH VOLTAGE RELAY, GIS MAINTENANCE)."
                }
            },
            {
                "fileName": "Ravi_Kumar_Resume.docx",
                "fileSize": 95000,
                "parsedData": {
                    "full_name": "Ravi Kumar",
                    "email": "ravi.kumar@testlabs.in",
                    "phone": "+91 98765 43210",
                    "total_experience_years": 4.0,
                    "relevant_experience_years": 4.0,
                    "match_score": 62,
                    "skills_matrix": ["SWITCHGEAR TESTING", "SCADA CONTROL", "AUTOCAD"],
                    "specialization_tags": ["ETAP Certified"],
                    "industry_remarks": "Strong Domain Match. Candidate possesses 4.0 years of experience in Electrical/Testing with matching industry-specific skills (SWITCHGEAR TESTING)."
                }
            },
            {
                "fileName": "David_Miller_IT_CV.pdf",
                "fileSize": 105600,
                "parsedData": {
                    "full_name": "David Miller",
                    "email": "david.miller.dev@gmail.com",
                    "phone": "+1 (555) 321-4567",
                    "total_experience_years": 6.0,
                    "relevant_experience_years": 0.9,
                    "match_score": 27,
                    "skills_matrix": ["REACT", "TYPESCRIPT", "JAVASCRIPT", "PYTHON", "SQL", "GIT"],
                    "specialization_tags": [],
                    "industry_remarks": "Domain Mismatch Penalty. Candidate has 6.0 years of overall experience, but their footprint is heavily concentrated in the Information Technology industry (keyword density: 12). They lack the necessary specialized domain experience in Electrical/Testing."
                }
            }
        ]
    elif target_domain == 'Healthcare':
        return [
            {
                "fileName": "Emily_Taylor_CV.pdf",
                "fileSize": 139000,
                "parsedData": {
                    "full_name": "Dr. Emily Taylor",
                    "email": "emily.taylor@clinicalresearch.org",
                    "phone": "+1 (555) 345-6789",
                    "total_experience_years": 11.0,
                    "relevant_experience_years": 11.0,
                    "match_score": 90,
                    "skills_matrix": ["CLINICAL TRIALS", "NURSING CARE", "PROJECT MANAGEMENT"],
                    "specialization_tags": ["HSE Certified"],
                    "industry_remarks": "Strong Domain Match. Candidate possesses 11.0 years of experience in Healthcare with matching industry-specific skills (CLINICAL TRIALS, NURSING CARE)."
                }
            },
            {
                "fileName": "James_Wilson_Resume.docx",
                "fileSize": 82000,
                "parsedData": {
                    "full_name": "James Wilson",
                    "email": "j.wilson@healthcare.net",
                    "phone": "+1 (555) 456-7890",
                    "total_experience_years": 5.0,
                    "relevant_experience_years": 5.0,
                    "match_score": 60,
                    "skills_matrix": ["NURSING CARE", "PROJECT MANAGEMENT"],
                    "specialization_tags": [],
                    "industry_remarks": "Strong Domain Match. Candidate possesses 5.0 years of experience in Healthcare with matching industry-specific skills (NURSING CARE)."
                }
            },
            {
                "fileName": "David_Miller_IT_CV.pdf",
                "fileSize": 105600,
                "parsedData": {
                    "full_name": "David Miller",
                    "email": "david.miller.dev@gmail.com",
                    "phone": "+1 (555) 321-4567",
                    "total_experience_years": 6.0,
                    "relevant_experience_years": 0.9,
                    "match_score": 25,
                    "skills_matrix": ["REACT", "TYPESCRIPT", "JAVASCRIPT", "PYTHON", "SQL", "GIT"],
                    "specialization_tags": [],
                    "industry_remarks": "Domain Mismatch Penalty. Candidate has 6.0 years of overall experience, but their footprint is heavily concentrated in the Information Technology industry (keyword density: 12). They lack the necessary specialized domain experience in Healthcare."
                }
            }
        ]
    else: # Information Technology
        return [
            {
                "fileName": "Alex_Rivera_CV.pdf",
                "fileSize": 112000,
                "parsedData": {
                    "full_name": "Alex Rivera",
                    "email": "alex.rivera@devopsmail.com",
                    "phone": "+1 (555) 789-0123",
                    "total_experience_years": 8.0,
                    "relevant_experience_years": 8.0,
                    "match_score": 94,
                    "skills_matrix": ["REACT", "TYPESCRIPT", "JAVASCRIPT", "PYTHON", "GIT", "DOCKER", "AWS"],
                    "specialization_tags": ["PLC/SCADA Developer"],
                    "industry_remarks": "Strong Domain Match. Candidate possesses 8.0 years of experience in Information Technology with matching industry-specific skills (REACT, TYPESCRIPT, JAVASCRIPT, PYTHON)."
                }
            },
            {
                "fileName": "Priyanka_Patel_Resume.docx",
                "fileSize": 85000,
                "parsedData": {
                    "full_name": "Priyanka Patel",
                    "email": "priyanka.p@codesolution.in",
                    "phone": "+91 99887 76655",
                    "total_experience_years": 4.0,
                    "relevant_experience_years": 4.0,
                    "match_score": 68,
                    "skills_matrix": ["PYTHON", "SQL", "GIT", "REACT"],
                    "specialization_tags": [],
                    "industry_remarks": "Strong Domain Match. Candidate possesses 4.0 years of experience in Information Technology with matching industry-specific skills (PYTHON, SQL)."
                }
            },
            {
                "fileName": "David_Miller_Oil_Gas_CV.pdf",
                "fileSize": 121000,
                "parsedData": {
                    "full_name": "David Miller",
                    "email": "david.miller.eng@gmail.com",
                    "phone": "+1 (555) 321-4567",
                    "total_experience_years": 10.0,
                    "relevant_experience_years": 1.5,
                    "match_score": 31,
                    "skills_matrix": ["PETROLEUM PIPING", "DRILLING SIMULATION", "HSE RISK MANAGEMENT", "PROJECT MANAGEMENT"],
                    "specialization_tags": ["Deepwater Drilling", "HSE Certified"],
                    "industry_remarks": "Domain Mismatch Penalty. Candidate has 10.0 years of overall experience, but their footprint is heavily concentrated in the Oil & Gas industry (keyword density: 10). They lack the necessary specialized domain experience in Information Technology."
                }
            }
        ]

@app.route('/api/v1/gdrive-import', methods=['POST'])
def gdrive_import():
    data = request.get_json()
    if not data or 'folder_url' not in data or 'target_domain' not in data or 'requisition_id' not in data:
        return jsonify({"error": "Missing parameters 'folder_url', 'target_domain', or 'requisition_id'"}), 400
        
    folder_url = data['folder_url'].strip()
    target_domain = data['target_domain']
    requisition_id = data['requisition_id']
    jd_text = data.get('job_description_text', '')
    
    # Check for dummy or test folder URLs/IDs
    is_dummy = (
        folder_url == "test" or 
        folder_url == "mock" or 
        "1_A2B3C4D5" in folder_url or 
        "1_A2B3C4D5E6F7G8H9I0J" in folder_url
    )
    if is_dummy:
        print(f"Intercepted dummy Google Drive folder URL. Returning high-fidelity mock candidates for domain: {target_domain}")
        mock_candidates = get_mock_candidates_for_domain(target_domain)
        return jsonify({
            "success": True,
            "count": len(mock_candidates),
            "candidates": mock_candidates
        })
        
    try:
        import gdown
    except ImportError:
        return jsonify({"error": "Google Drive download utility 'gdown' is not installed on the server. Please run: pip install gdown"}), 500
        
    temp_dir = tempfile.mkdtemp()
    try:
        print(f"Downloading Google Drive folder URL: {folder_url}")
        
        # Download public folder contents
        downloaded_paths = gdown.download_folder(url=folder_url, output=temp_dir, quiet=True, use_cookies=False)
        
        if not downloaded_paths:
            downloaded_paths = []
            for root, dirs, files in os.walk(temp_dir):
                for f in files:
                    downloaded_paths.append(os.path.join(root, f))
        
        supported_extensions = ['.pdf', '.docx', '.doc', '.txt']
        candidates = []
        
        files_found = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in supported_extensions:
                    files_found.append(os.path.join(root, file))
                    
        if not files_found:
            return jsonify({
                "error": "No supported files (.pdf, .docx, .doc, .txt) found in the Google Drive folder. Ensure the folder is public and contains resumes.",
                "details": f"Checked temp directory. Total files found: {len(downloaded_paths)}"
            }), 400
            
        def _process_gdrive_file(file_path):
            """Extract, score and veto a single downloaded Drive file."""
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            raw_text  = extract_text_from_file(file_path)
            scored    = score_candidate_data(raw_text, target_domain, file_hint=file_name, jd_text=jd_text)
            scored    = _apply_mandatory_keyword_veto(scored, raw_text, jd_text)
            return {"fileName": file_name, "fileSize": file_size, "parsedData": scored}

        # Process concurrently (max 8 threads; each call is I/O + API bound)
        candidates = []
        max_workers = min(8, len(files_found))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_process_gdrive_file, fp): fp for fp in files_found}
            for future in as_completed(futures):
                try:
                    candidates.append(future.result())
                except Exception as exc:
                    fp = futures[future]
                    _app_logger.error("GDrive file %s failed: %s", os.path.basename(fp), exc)

        return jsonify({
            "success": True,
            "count": len(candidates),
            "candidates": candidates
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to download or parse Google Drive folder: {str(e)}"}), 500
        
    finally:
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


@app.route('/api/v1/upload-cv', methods=['POST'])
def upload_cv():
    """Accept a single CV file upload, screen it, apply veto and return results."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files['file']
    target_domain = request.form.get('target_domain', 'Information Technology')

    if not file or file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return jsonify({"error": f"Unsupported file type '{ext}'. Accepted: .pdf, .docx, .doc, .txt"}), 400

    # Save with a unique name to avoid collisions
    safe_original = re.sub(r'[^\w\-. ]', '_', file.filename)
    unique_name   = f"{uuid.uuid4().hex[:8]}_{safe_original}"
    save_path     = os.path.join(UPLOAD_FOLDER, unique_name)
    file.save(save_path)

    # Extract text, score and apply Python veto
    raw_text = extract_text_from_file(save_path)
    jd_text  = request.form.get('job_description_text', '')
    scored   = score_candidate_data(raw_text, target_domain, file_hint=file.filename, jd_text=jd_text)
    scored   = _apply_mandatory_keyword_veto(scored, raw_text, jd_text)
    scored['cv_file_name'] = unique_name

    return jsonify(scored)


@app.route('/api/v1/batch-upload-cv', methods=['POST'])
def batch_upload_cv():
    """
    High-throughput batch endpoint — accepts up to 1,000 CV files in a single
    multipart/form-data POST.  Files are processed concurrently using a
    ThreadPoolExecutor so the browser never waits for sequential AI calls.

    Each processed file is immediately written to the database via upsert so
    results are durable even if the client disconnects mid-response.

    Form fields:
        files[]          – one or more CV files (PDF / DOCX / DOC / TXT)
        target_domain    – requisition domain string
        requisition_id   – integer requisition ID (required for DB insert)
        job_description_text – full JD text used for AI scoring + veto check

    Returns:
        { success, count, candidates: [ { fileName, fileSize, parsedData } ] }
    """
    tid = _get_caller_tenant(request)
    if tid is False:
        return jsonify({'error': 'Authentication required.'}), 401
    effective_tid = tid if tid is not None else 'admin-tenant'

    files         = request.files.getlist('files[]') or request.files.getlist('file')
    target_domain = request.form.get('target_domain', 'Information Technology')
    req_id        = request.form.get('requisition_id', type=int)
    jd_text       = request.form.get('job_description_text', '')

    if not files:
        return jsonify({"error": "No files provided. Use field name 'files[]'."}), 400
    if not req_id:
        return jsonify({"error": "requisition_id is required for batch upload."}), 400
    if len(files) > 1000:
        return jsonify({"error": "Maximum 1,000 files per batch request."}), 400

    # ── Save all files to disk first (fast, no AI yet) ──────────────────────
    pending = []  # list of (save_path, unique_name, original_filename)
    for f in files:
        if not f or f.filename == '':
            continue
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue
        safe_original = re.sub(r'[^\w\-. ]', '_', f.filename)
        unique_name   = f"{uuid.uuid4().hex[:8]}_{safe_original}"
        save_path     = os.path.join(UPLOAD_FOLDER, unique_name)
        f.save(save_path)
        pending.append((save_path, unique_name, f.filename))

    if not pending:
        return jsonify({"error": "No supported files found in request (accepted: .pdf, .docx, .doc, .txt)."}), 400

    # ── Process each saved file concurrently ─────────────────────────────────
    def _screen_one(args):
        save_path, unique_name, orig_name = args
        try:
            raw_text = extract_text_from_file(save_path)
            scored   = score_candidate_data(raw_text, target_domain, file_hint=orig_name, jd_text=jd_text)
            scored   = _apply_mandatory_keyword_veto(scored, raw_text, jd_text)
            scored['cv_file_name'] = unique_name
            file_size = os.path.getsize(save_path)

            # ── Immediately upsert into DB so record survives client disconnect ──
            candidate_payload = {
                'requisition_id':            req_id,
                'full_name':                 scored.get('full_name', orig_name),
                'email':                     scored.get('email', ''),
                'phone':                     scored.get('phone', ''),
                'passport_number':           scored.get('passport_number'),
                'current_stage':             'Screening',
                'total_experience_years':    float(scored.get('total_experience_years', 0)),
                'relevant_experience_years': float(scored.get('relevant_experience_years', 0)),
                'match_score':               int(scored.get('match_score', 0)),
                'skills_matrix':             json.dumps(scored.get('skills_matrix', [])),
                'specialization_tags':       json.dumps(scored.get('specialization_tags', [])),
                'industry_remarks':          scored.get('industry_remarks', ''),
                'ai_analysis':               json.dumps(scored.get('ai_analysis')) if scored.get('ai_analysis') else None,
                'eligible':                  1 if scored.get('eligible', True) else 0,
                'veto_reason':               scored.get('veto_reason'),
                'cv_file_name':              unique_name,
                'tenant_id':                 effective_tid,
            }
            full_name   = candidate_payload['full_name']
            email_clean = (candidate_payload['email'] or '').strip().lower()
            phone_clean = (candidate_payload['phone'] or '').strip()

            with get_db() as conn:
                existing = conn.execute(
                    '''
                    SELECT id FROM candidates WHERE tenant_id=? AND (
                        (LOWER(email) = ? AND ? != '') OR
                        (phone = ? AND ? != '') OR
                        (requisition_id = ? AND LOWER(full_name) = LOWER(?))
                    )
                    LIMIT 1
                    ''',
                    (effective_tid, email_clean, email_clean, phone_clean, phone_clean, req_id, full_name)
                ).fetchone()

                update_fields = {k: v for k, v in candidate_payload.items()
                                 if k not in ('requisition_id', 'full_name', 'tenant_id')}

                if existing:
                    set_clause = ', '.join(f'{k}=?' for k in update_fields)
                    conn.execute(
                        f'UPDATE candidates SET {set_clause} WHERE id=?',
                        list(update_fields.values()) + [existing['id']]
                    )
                    conn.commit()
                    row = conn.execute('SELECT * FROM candidates WHERE id=?', (existing['id'],)).fetchone()
                else:
                    all_fields = {**candidate_payload}
                    cols  = ', '.join(all_fields.keys())
                    placeholders = ', '.join('?' for _ in all_fields)
                    cur = conn.execute(
                        f'INSERT INTO candidates ({cols}) VALUES ({placeholders})',
                        list(all_fields.values())
                    )
                    conn.commit()
                    row = conn.execute('SELECT * FROM candidates WHERE id=?', (cur.lastrowid,)).fetchone()

            return {
                'fileName':   unique_name,
                'fileSize':   file_size,
                'parsedData': {**scored, **row_to_candidate(row)},
            }
        except Exception as exc:
            _app_logger.error("batch_upload_cv: error processing %s: %s", orig_name, exc, exc_info=True)
            return {
                'fileName':   unique_name,
                'fileSize':   0,
                'error':      str(exc),
                'parsedData': {'full_name': orig_name, 'match_score': 0, 'eligible': False,
                               'veto_reason': f'Processing error: {exc}'},
            }

    max_workers = min(10, len(pending))  # cap at 10 simultaneous AI calls
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_screen_one, args): args for args in pending}
        for future in as_completed(futures):
            results.append(future.result())

    return jsonify({
        'success':    True,
        'count':      len(results),
        'candidates': results,
    })


@app.route('/api/v1/cv/<path:filename>', methods=['GET'])
def serve_cv(filename):
    """Serve a stored CV file for download."""
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)


if __name__ == '__main__':
    # Run server locally on standard port 5000
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

