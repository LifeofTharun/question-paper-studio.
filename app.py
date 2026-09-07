from datetime import datetime
import json
import os
import secrets
import tempfile

from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from werkzeug.security import check_password_hash, generate_password_hash

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=BASE_DIR, static_folder=BASE_DIR)
app.secret_key = os.environ.get('SECRET_KEY', 'kmg-question-paper-studio-secret-key-2026')
serializer = URLSafeTimedSerializer(app.secret_key)

if os.environ.get('VERCEL'):
    db_dir = tempfile.gettempdir()
    db_path = os.path.join(db_dir, 'questions.db').replace('\\', '/')
    orig_db = os.path.join(BASE_DIR, 'questions.db')
    if not os.path.exists(db_path) and os.path.exists(orig_db):
        import shutil
        try:
            shutil.copyfile(orig_db, db_path)
        except Exception:
            pass
    orig_backup = os.path.join(BASE_DIR, 'users_backup.json')
    backup_path = os.path.join(db_dir, 'users_backup.json')
    if not os.path.exists(backup_path) and os.path.exists(orig_backup):
        import shutil
        try:
            shutil.copyfile(orig_backup, backup_path)
        except Exception:
            pass
    BACKUP_FILE = backup_path
else:
    db_dir = BASE_DIR
    db_path = os.path.join(db_dir, 'questions.db').replace('\\', '/')
    BACKUP_FILE = os.path.join(BASE_DIR, 'users_backup.json')

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    warning_msg = db.Column(db.Text, nullable=True)
    warning_seen = db.Column(db.Boolean, default=False, nullable=False)
    warning_reply = db.Column(db.Text, nullable=True)
    warning_status = db.Column(db.String(20), default='open', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Syllabus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    subject_code = db.Column(db.String(40), nullable=False, default='AUCAI11')
    content = db.Column(db.Text, nullable=False)
    unit_names = db.Column(db.Text, default='{}', nullable=False)
    unit_content = db.Column(db.Text, default='{}', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    action = db.Column(db.String(80), nullable=False)
    details = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class GeneratedPaper(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    syllabus_id = db.Column(db.Integer, db.ForeignKey('syllabus.id'), nullable=True)
    subject_code = db.Column(db.String(40), nullable=False, default='AUCAI11')
    selections = db.Column(db.Text, nullable=False)
    paper_json = db.Column(db.Text, nullable=False)
    submitted = db.Column(db.Boolean, default=False, nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=True)
    submit_subject = db.Column(db.String(160), nullable=True)
    submit_dept = db.Column(db.String(160), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class UserSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unit = db.Column(db.Integer, nullable=False)
    k_level = db.Column(db.String(2), nullable=False)
    text = db.Column(db.String(500), nullable=False)
    marks = db.Column(db.Integer, nullable=False)
    co = db.Column(db.String(10), nullable=False, default='CO1')
    correct_answer = db.Column(db.Text, nullable=True)
    difficulty = db.Column(db.String(20), nullable=False, default='Medium')


with app.app_context():
    db.create_all()

    def add_col(table, col, definition):
        result = db.session.execute(text(f"PRAGMA table_info('{table}')")).fetchall()
        existing = {row[1] for row in result}
        if col not in existing:
            db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN {col} {definition}'))
            db.session.commit()

    add_col('user', 'is_active', 'BOOLEAN NOT NULL DEFAULT 1')
    add_col('user', 'warning_msg', 'TEXT')
    add_col('user', 'warning_seen', 'BOOLEAN NOT NULL DEFAULT 0')
    add_col('user', 'warning_reply', 'TEXT')
    add_col('user', 'warning_status', "VARCHAR(20) NOT NULL DEFAULT 'open'")
    add_col('syllabus', 'subject_code', "VARCHAR(40) NOT NULL DEFAULT 'AUCAI11'")
    add_col('syllabus', 'unit_content', "TEXT NOT NULL DEFAULT '{}' ")
    add_col('question', 'co', "VARCHAR(10) NOT NULL DEFAULT 'CO1'")
    add_col('question', 'correct_answer', 'TEXT')
    add_col('question', 'difficulty', "VARCHAR(20) NOT NULL DEFAULT 'Medium'")
    add_col('generated_paper', 'submitted', 'BOOLEAN NOT NULL DEFAULT 0')
    add_col('generated_paper', 'submitted_at', 'DATETIME')
    add_col('generated_paper', 'submit_subject', 'VARCHAR(160)')
    add_col('generated_paper', 'submit_dept', 'VARCHAR(160)')

    if not User.query.filter_by(email='admin@questionpaper.local').first():
        db.session.add(User(
            name='Administrator',
            email='admin@questionpaper.local',
            password_hash=generate_password_hash('Admin@Kmg#2026$Secure!'),
            is_admin=True,
        ))
        db.session.commit()


@app.after_request
def add_security_headers(response):
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response


def generate_token(user):
    if isinstance(user, int):
        u = db.session.get(User, user)
        if u:
            user = u
        else:
            return serializer.dumps({'user_id': user})
    return serializer.dumps({
        'user_id': user.id,
        'email': user.email,
        'name': user.name,
        'is_admin': user.is_admin
    })


def get_token():
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[7:]
    return None


def current_user():
    token = get_token()
    if not token:
        return None
    try:
        data = serializer.loads(token, max_age=86400 * 30)
        user_id = data.get('user_id')
        email = data.get('email')
        name = data.get('name')
        is_admin = data.get('is_admin', False)

        user = None
        if user_id:
            user = db.session.get(User, user_id)
        if not user and email:
            user = User.query.filter(db.func.lower(User.email) == email.lower()).first()

        # Self-healing: If DB reset or serverless container cold start, restore User record
        if not user and email and name:
            user = User(
                name=name,
                email=email,
                password_hash=generate_password_hash('RestoredUser123!'),
                is_admin=is_admin,
                is_active=True
            )
            db.session.add(user)
            db.session.commit()

        if user and user.is_active:
            return user
    except Exception:
        sess = UserSession.query.filter_by(token=token).first()
        if sess:
            u = db.session.get(User, sess.user_id)
            if u and u.is_active:
                return u
    return None


def log_activity(action, details, user_id=None):
    if user_id is None:
        u = current_user()
        user_id = u.id if u else None
    db.session.add(ActivityLog(user_id=user_id, action=action, details=details))
    db.session.commit()


def require_login():
    user = current_user()
    if not user:
        return None, (jsonify({'error': 'Please login first.'}), 401)
    return user, None


def require_admin():
    user = current_user()
    if not user:
        return None, (jsonify({'error': 'Please login first.'}), 401)
    if not user.is_admin:
        return None, (jsonify({'error': 'Admin access only.'}), 403)
    return user, None


def split_units(content, target_units=None):
    import re
    if not content or not content.strip():
        return {}
    lines = content.splitlines()
    units = {}
    current = None
    roman = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'ONE': 1, 'TWO': 2, 'THREE': 3, 'FOUR': 4, 'FIVE': 5}
    unit_pat = re.compile(
        r'^\s*(?:UNIT|MODULE|CHAPTER|PART|SECTION|BLOCK)\s*[-:–—._ ]*\s*([0-9]+|[IVX]+|ONE|TWO|THREE|FOUR|FIVE)\b\s*[:–—._-]?\s*(.*)$',
        re.I
    )
    for line in lines:
        sline = line.strip()
        if not sline:
            continue
        m = unit_pat.match(sline)
        if m:
            raw = m.group(1).upper()
            num = int(raw) if raw.isdigit() else roman.get(raw)
            if num and 1 <= num <= 5:
                current = str(num)
                rest = m.group(2).strip()
                units[current] = rest
                continue
        if current:
            units[current] = (units.get(current, '') + '\n' + sline).strip()

    active = [str(u) for u in (target_units or [1, 2, 3, 4, 5])]
    if len(units) < len(active):
        if not units:
            chunks = [c.strip() for c in re.split(r'\n\s*\n+', content.strip()) if c.strip()]
            if len(chunks) >= len(active):
                for i, u in enumerate(active):
                    units[u] = chunks[i]
            else:
                for u in active:
                    units[u] = content
        else:
            first_val = next(iter(units.values()))
            for u in active:
                if u not in units:
                    units[u] = first_val
    return units or {'1': content}



from markupsafe import escape
from datetime import timedelta

def load_user_backup():
    if os.path.exists(BACKUP_FILE):
        try:
            with open(BACKUP_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    orig_backup = os.path.join(BASE_DIR, 'users_backup.json')
    if orig_backup != BACKUP_FILE and os.path.exists(orig_backup):
        try:
            with open(orig_backup, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_user_backup(email, name, password_hash, is_admin=False, is_active=True):
    data = load_user_backup()
    data[email.lower()] = {
        'name': name,
        'email': email.lower(),
        'password_hash': password_hash,
        'is_admin': is_admin,
        'is_active': is_active
    }
    try:
        with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass
    local_backup = os.path.join(BASE_DIR, 'users_backup.json')
    if local_backup != BACKUP_FILE:
        try:
            with open(local_backup, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

def sync_users_from_backup():
    data = load_user_backup()
    if not data:
        return
    changed = False
    for email, uinfo in data.items():
        existing = User.query.filter(db.func.lower(User.email) == email.lower()).first()
        if not existing:
            user = User(
                name=uinfo['name'],
                email=uinfo['email'],
                password_hash=uinfo['password_hash'],
                is_admin=uinfo.get('is_admin', False),
                is_active=uinfo.get('is_active', True)
            )
            db.session.add(user)
            changed = True
        else:
            if existing.password_hash != uinfo['password_hash']:
                existing.password_hash = uinfo['password_hash']
                changed = True
    if changed:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

SYLLABUS_BACKUP_FILE = os.path.join(db_dir, 'syllabus_backup.json')

def load_syllabus_backup():
    orig_backup = os.path.join(BASE_DIR, 'syllabus_backup.json')
    data = []
    if os.path.exists(orig_backup):
        try:
            with open(orig_backup, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            pass
    if os.path.exists(SYLLABUS_BACKUP_FILE) and SYLLABUS_BACKUP_FILE != orig_backup:
        try:
            with open(SYLLABUS_BACKUP_FILE, 'r', encoding='utf-8') as f:
                file_data = json.load(f)
                if len(file_data) >= len(data):
                    data = file_data
        except Exception:
            pass
    return data

def save_all_syllabus_backup():
    try:
        all_s = Syllabus.query.all()
        data = []
        for s in all_s:
            u = db.session.get(User, s.user_id) if s.user_id else None
            data.append({
                'id': s.id,
                'user_id': s.user_id,
                'user_email': u.email if u else 'admin@questionpaper.local',
                'title': s.title,
                'subject_code': s.subject_code,
                'content': s.content,
                'unit_names': s.unit_names,
                'unit_content': s.unit_content,
                'created_at': s.created_at.isoformat()
            })
        if SYLLABUS_BACKUP_FILE:
            with open(SYLLABUS_BACKUP_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        local_backup = os.path.join(BASE_DIR, 'syllabus_backup.json')
        if local_backup != SYLLABUS_BACKUP_FILE:
            try:
                with open(local_backup, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
            except Exception:
                pass
    except Exception:
        pass

def sync_syllabus_from_backup():
    data = load_syllabus_backup()
    if not data:
        return
    for item in data:
        user_email = item.get('user_email', '')
        user = User.query.filter(db.func.lower(User.email) == user_email.lower()).first()
        uid = user.id if user else 1
        existing = Syllabus.query.filter_by(id=item.get('id')).first()
        if not existing:
            s = Syllabus(
                id=item.get('id'),
                user_id=uid,
                title=item.get('title', 'Syllabus'),
                subject_code=item.get('subject_code', 'AUCAI11'),
                content=item.get('content', ''),
                unit_names=item.get('unit_names', '{}'),
                unit_content=item.get('unit_content', '{}'),
                created_at=datetime.fromisoformat(item['created_at']) if item.get('created_at') else datetime.utcnow()
            )
            db.session.add(s)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

with app.app_context():
    sync_users_from_backup()
    sync_syllabus_from_backup()

# Security & Rate Limiting state
failed_logins = {}  # key: ip_email, val: (count, timestamp)

def is_rate_limited(key):
    now = datetime.utcnow()
    if key in failed_logins:
        count, first_time = failed_logins[key]
        if now - first_time > timedelta(minutes=15):
            failed_logins[key] = (0, now)
            return False
        return count >= 5
    return False

function_record_failure = lambda key: failed_logins.update({
    key: (failed_logins.get(key, (0, datetime.utcnow()))[0] + 1, failed_logins.get(key, (0, datetime.utcnow()))[1])
})

def record_login_success(key):
    if key in failed_logins:
        del failed_logins[key]

def sanitize(text):
    if isinstance(text, str):
        return str(escape(text.strip()))
    return text


@app.after_request
def apply_security_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com https://fonts.googleapis.com https://fonts.gstatic.com; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "object-src 'none'; frame-ancestors 'none';"
    )
    return response


@app.errorhandler(500)
def handle_500(e):
    return jsonify({'error': 'An internal security error occurred. Request was safely blocked.'}), 500


@app.errorhandler(404)
def handle_404(e):
    return jsonify({'error': 'Resource not found.'}), 404


@app.route('/')
def index():
    index_path = os.path.join(BASE_DIR, 'index.html')
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            return f.read(), 200, {'Content-Type': 'text/html; charset=utf-8'}
    return render_template('index.html')


@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.get_json(silent=True) or {}
    name = str(data.get('name', '')).strip()
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', '')).strip()
    if not name or '@' not in email or len(password) < 6:
        return jsonify({'error': 'Name, valid email, and a password of at least 6 characters are required.'}), 400
    
    sync_users_from_backup()
    existing = User.query.filter(db.func.lower(User.email) == email).first()
    
    if existing:
        # Update existing user details/password hash (allows self password reset)
        existing.name = name
        existing.password_hash = generate_password_hash(password)
        user = existing
    else:
        user = User(name=name, email=email, password_hash=generate_password_hash(password), is_admin=False, is_active=True)
        db.session.add(user)

    db.session.commit()
    save_user_backup(email, name, user.password_hash, is_admin=user.is_admin, is_active=user.is_active)

    token = generate_token(user)
    db.session.add(UserSession(user_id=user.id, token=token))
    db.session.commit()
    log_activity('signup', 'Account registered or updated.', user.id)
    return jsonify({'token': token, 'user': {'id': user.id, 'name': user.name, 'email': user.email, 'is_admin': user.is_admin,
                                              'warning': None, 'warning_msg': None, 'warning_seen': True,
                                              'warning_reply': None, 'warning_status': 'resolved'}}), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', '')).strip()
    client_ip = request.remote_addr or 'unknown'
    rate_key = f"{client_ip}:{email}"

    if is_rate_limited(rate_key):
        return jsonify({'error': 'Too many failed login attempts. Account protected. Please try again in 3 minutes.'}), 429

    if not email or '@' not in email or len(password) < 6:
        return jsonify({'error': 'Invalid email or password.'}), 401

    ADMIN_EMAIL = 'admin@questionpaper.local'
    ADMIN_PASS = 'Admin@Kmg#2026$Secure!'

    if email == ADMIN_EMAIL and password == ADMIN_PASS:
        user = User.query.filter(db.func.lower(User.email) == ADMIN_EMAIL).first()
        if not user:
            user = User(
                name='Administrator',
                email=ADMIN_EMAIL,
                password_hash=generate_password_hash(ADMIN_PASS),
                is_admin=True,
                is_active=True
            )
            db.session.add(user)
            db.session.commit()
        else:
            if not user.is_admin or not check_password_hash(user.password_hash, ADMIN_PASS):
                user.password_hash = generate_password_hash(ADMIN_PASS)
                user.is_admin = True
                user.is_active = True
                db.session.commit()
        save_user_backup(user.email, user.name, user.password_hash, is_admin=True, is_active=True)
        record_login_success(rate_key)
        UserSession.query.filter_by(user_id=user.id).delete()
        token = generate_token(user)
        db.session.add(UserSession(user_id=user.id, token=token))
        db.session.commit()
        log_activity('login', 'Admin logged in.', user.id)
        return jsonify({'token': token, 'user': {'id': user.id, 'name': user.name, 'email': user.email, 'is_admin': True,
                                                  'warning': None, 'warning_msg': None,
                                                  'warning_seen': True,
                                                  'warning_reply': None,
                                                  'warning_status': 'resolved'}})

    sync_users_from_backup()
    user = User.query.filter(db.func.lower(User.email) == email).first()

    # Backup store fallback check
    if not user:
        backup_data = load_user_backup()
        if email in backup_data:
            uinfo = backup_data[email]
            user = User(
                name=uinfo['name'],
                email=uinfo['email'],
                password_hash=uinfo['password_hash'],
                is_admin=uinfo.get('is_admin', False),
                is_active=uinfo.get('is_active', True)
            )
            db.session.add(user)
            db.session.commit()

    if not user or not check_password_hash(user.password_hash, password):
        function_record_failure(rate_key)
        return jsonify({'error': 'Invalid email or password.'}), 401

    if not user.is_active:
        return jsonify({'error': 'Your account has been deactivated. Please contact the administrator.'}), 403

    record_login_success(rate_key)
    
    # Save/ensure backup is current
    save_user_backup(user.email, user.name, user.password_hash, is_admin=user.is_admin, is_active=user.is_active)

    # Clear previous active sessions for clean user state
    UserSession.query.filter_by(user_id=user.id).delete()
    
    token = generate_token(user)
    db.session.add(UserSession(user_id=user.id, token=token))
    db.session.commit()
    log_activity('login', 'User logged in.', user.id)
    warning = user.warning_msg if (user.warning_msg and not user.warning_seen) else None
    return jsonify({'token': token, 'user': {'id': user.id, 'name': user.name, 'email': user.email, 'is_admin': user.is_admin,
                                              'warning': warning, 'warning_msg': user.warning_msg,
                                              'warning_seen': user.warning_seen,
                                              'warning_reply': user.warning_reply,
                                              'warning_status': user.warning_status}})


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    token = get_token()
    user = current_user()
    if user:
        log_activity('logout', 'User logged out.', user.id)
    if token:
        UserSession.query.filter_by(token=token).delete()
        db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/auth/change-password', methods=['POST'])
def change_password():
    user, error = require_login()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    current_password = str(data.get('current_password', '')).strip()
    new_password = str(data.get('new_password', '')).strip()

    if not current_password or not new_password:
        return jsonify({'error': 'Current password and new password are required.'}), 400

    if len(new_password) < 6:
        return jsonify({'error': 'New password must be at least 6 characters long.'}), 400

    if not check_password_hash(user.password_hash, current_password):
        return jsonify({'error': 'Current password is incorrect.'}), 400

    if current_password == new_password:
        return jsonify({'error': 'New password cannot be the same as current password.'}), 400

    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    save_user_backup(user.email, user.name, user.password_hash, is_admin=user.is_admin, is_active=user.is_active)
    log_activity('change_password', 'Password updated successfully.', user.id)
    return jsonify({'message': 'Password changed successfully!'}), 200


@app.route('/api/me')
def me():
    user = current_user()
    if not user:
        return jsonify({'user': None})
    warning = user.warning_msg if (user.warning_msg and not user.warning_seen) else None
    return jsonify({'user': {'name': user.name, 'email': user.email, 'is_admin': user.is_admin,
                              'warning': warning, 'warning_msg': user.warning_msg,
                              'warning_seen': user.warning_seen,
                              'warning_reply': user.warning_reply,
                              'warning_status': user.warning_status}})


@app.route('/api/syllabus', methods=['GET', 'POST'])
def syllabus_api():
    user, error = require_login()
    if error:
        return error
    if request.method == 'GET':
        sync_syllabus_from_backup()
        records = Syllabus.query.filter_by(user_id=user.id).order_by(Syllabus.created_at.desc()).all()
        if not records:
            records = Syllabus.query.order_by(Syllabus.created_at.desc()).all()
        return jsonify({'syllabuses': [
            {'id': r.id, 'title': r.title, 'content': r.content,
             'subject_code': r.subject_code, 'unit_names': json.loads(r.unit_names or '{}'),
             'unit_content': json.loads(r.unit_content or '{}'), 'created_at': r.created_at.isoformat()}
            for r in records
        ]})
    data = request.get_json(silent=True) or {}
    title = str(data.get('title', '')).strip() or 'My Syllabus'
    subject_code = str(data.get('subject_code', '')).strip() or 'AUCAI11'
    content = str(data.get('content', '')).strip()
    if not content:
        return jsonify({'error': 'Please enter syllabus text before saving.'}), 400
    
    # Allow saving unlimited syllabuses without restriction
    syllabus_id = data.get('id')
    existing = None
    if syllabus_id:
        existing = Syllabus.query.filter_by(id=syllabus_id, user_id=user.id).first()
    
    if existing:
        existing.title = title
        existing.subject_code = subject_code
        existing.content = content
        existing.unit_names = json.dumps(data.get('unit_names', {}))
        existing.unit_content = json.dumps(split_units(content))
        db.session.commit()
        save_all_syllabus_backup()
        log_activity('syllabus_updated', f'Updated syllabus: {title}')
        return jsonify({'id': existing.id, 'message': 'Syllabus updated successfully.'}), 200

    record = Syllabus(user_id=user.id, title=title, subject_code=subject_code,
                      content=content, unit_names=json.dumps(data.get('unit_names', {})),
                      unit_content=json.dumps(split_units(content)))
    db.session.add(record)
    db.session.commit()
    save_all_syllabus_backup()
    log_activity('syllabus_saved', f'Saved syllabus: {title}')
    return jsonify({'id': record.id, 'message': 'Syllabus saved successfully.'}), 201


@app.route('/api/syllabus/<int:syllabus_id>', methods=['PUT', 'DELETE'])
def syllabus_detail(syllabus_id):
    user, error = require_login()
    if error:
        return error
    record = Syllabus.query.filter_by(id=syllabus_id, user_id=user.id).first()
    if not record:
        record = Syllabus.query.filter_by(id=syllabus_id).first()
    if not record:
        return jsonify({'error': 'Syllabus not found.'}), 404
    if request.method == 'DELETE':
        db.session.delete(record)
        db.session.commit()
        save_all_syllabus_backup()
        log_activity('syllabus_deleted', f'Deleted syllabus: {record.title}')
        return jsonify({'message': 'Deleted successfully.'})
    data = request.get_json(silent=True) or {}
    title = str(data.get('title', '')).strip() or record.title
    subject_code = str(data.get('subject_code', '')).strip() or record.subject_code
    content = str(data.get('content', '')).strip()
    if not content:
        return jsonify({'error': 'Content cannot be empty.'}), 400
    record.title = title
    record.subject_code = subject_code
    record.content = content
    record.unit_names = json.dumps(data.get('unit_names', json.loads(record.unit_names or '{}')))
    record.unit_content = json.dumps(split_units(content))
    db.session.commit()
    save_all_syllabus_backup()
    log_activity('syllabus_updated', f'Updated syllabus: {title}')
    return jsonify({'id': record.id, 'message': 'Syllabus updated successfully.'})


@app.route('/api/history')
def history():
    user, error = require_login()
    if error:
        return error
    records = ActivityLog.query.filter_by(user_id=user.id).order_by(ActivityLog.created_at.desc()).limit(50).all()
    papers = GeneratedPaper.query.filter_by(user_id=user.id).order_by(GeneratedPaper.created_at.desc()).limit(30).all()
    return jsonify({'history': [
        {'action': r.action, 'details': r.details, 'created_at': r.created_at.isoformat()}
        for r in records
    ], 'papers': [
        {'id': p.id, 'subject_code': p.subject_code,
         'paper': json.loads(p.paper_json),
         'submitted': p.submitted,
         'submit_subject': p.submit_subject,
         'submit_dept': p.submit_dept,
         'submitted_at': p.submitted_at.isoformat() if p.submitted_at else None,
         'created_at': p.created_at.isoformat()}
        for p in papers
    ]})


@app.route('/api/paper/submit/<int:paper_id>', methods=['POST'])
def submit_paper(paper_id):
    user, error = require_login()
    if error:
        return error
    paper = GeneratedPaper.query.filter_by(id=paper_id, user_id=user.id).first()
    if not paper:
        return jsonify({'error': 'Paper not found.'}), 404
    if paper.submitted:
        return jsonify({'error': 'This paper has already been submitted.'}), 409
    data = request.get_json(silent=True) or {}
    paper.submitted = True
    paper.submitted_at = datetime.utcnow()
    paper.submit_subject = str(data.get('subject', '')).strip() or paper.subject_code
    paper.submit_dept = str(data.get('department', '')).strip() or 'Not specified'
    db.session.commit()
    log_activity('paper_submitted', f'Submitted paper {paper_id} ({paper.subject_code}) — {paper.submit_dept}')
    return jsonify({'message': 'Paper submitted to admin successfully.'})


@app.route('/api/admin/overview')
def admin_overview():
    user, error = require_admin()
    if error:
        return error
    sync_users_from_backup()
    users = User.query.order_by(User.created_at.desc()).all()
    submitted = (
        db.session.query(GeneratedPaper, User)
        .join(User, GeneratedPaper.user_id == User.id)
        .filter(GeneratedPaper.submitted == True)
        .order_by(GeneratedPaper.submitted_at.desc())
        .all()
    )
    return jsonify({
        'stats': {
            'total_users': len(users),
            'total_submitted': len(submitted),
            'total_questions': Question.query.count(),
            'total_papers': GeneratedPaper.query.count(),
        },
        'users': [{
            'id': u.id,
            'name': u.name,
            'email': u.email,
            'is_admin': u.is_admin,
            'is_active': u.is_active,
            'warning_msg': u.warning_msg,
            'warning_reply': u.warning_reply,
            'warning_status': u.warning_status,
            'created_at': u.created_at.isoformat(),
            'syllabuses': [{
                'id': s.id, 'title': s.title, 'subject_code': s.subject_code,
                'content': s.content, 'created_at': s.created_at.isoformat(),
            } for s in Syllabus.query.filter_by(user_id=u.id).all()],
            'papers': [{
                'id': p.id, 'subject_code': p.subject_code,
                'paper': json.loads(p.paper_json),
                'submitted': p.submitted,
                'created_at': p.created_at.isoformat(),
            } for p in GeneratedPaper.query.filter_by(user_id=u.id).order_by(GeneratedPaper.created_at.desc()).all()],
        } for u in users],
        'submitted_papers': [{
            'paper_id': p.id,
            'subject_code': p.subject_code,
            'submit_subject': p.submit_subject or p.subject_code,
            'submit_dept': p.submit_dept or 'Not specified',
            'paper': json.loads(p.paper_json),
            'submitted_at': p.submitted_at.isoformat() if p.submitted_at else None,
            'user_name': u.name,
            'user_email': u.email,
        } for p, u in submitted],
    })


@app.route('/api/questions', methods=['GET', 'POST'])
def questions_api():
    user, error = require_login()
    if error:
        return error
    if request.method == 'GET':
        unit = request.args.get('unit', type=int)
        k_level = request.args.get('k_level', '').strip().upper()
        co = request.args.get('co', '').strip().upper()
        marks = request.args.get('marks', type=int)
        q_search = request.args.get('q', '').strip()
        
        query = Question.query
        if unit:
            query = query.filter_by(unit=unit)
        if k_level:
            query = query.filter_by(k_level=k_level)
        if co:
            query = query.filter_by(co=co)
        if marks:
            query = query.filter_by(marks=marks)
        if q_search:
            query = query.filter(Question.text.ilike(f'%{q_search}%'))
            
        questions = query.order_by(Question.unit.asc(), Question.marks.asc(), Question.id.desc()).all()
        return jsonify({'questions': [
            {'id': q.id, 'unit': q.unit, 'k_level': q.k_level, 'co': q.co, 'text': q.text,
             'marks': q.marks, 'difficulty': q.difficulty, 'correct_answer': q.correct_answer}
            for q in questions
        ]})

    # POST: Add new question
    data = request.get_json(silent=True) or {}
    text_content = str(data.get('text', '')).strip()
    unit = data.get('unit', 1)
    k_level = str(data.get('k_level', 'K1')).upper()
    co = str(data.get('co', 'CO1')).upper()
    marks = data.get('marks', 2)
    difficulty = str(data.get('difficulty', 'Medium')).strip()
    correct_answer = str(data.get('correct_answer', '')).strip()

    if not text_content:
        return jsonify({'error': 'Question text cannot be empty.'}), 400
    if not isinstance(unit, int) or not (1 <= unit <= 5):
        return jsonify({'error': 'Unit must be between 1 and 5.'}), 400
    if k_level not in {f'K{i}' for i in range(1, 7)}:
        return jsonify({'error': 'Invalid K-level (K1-K6 allowed).'}), 400
    if marks not in {2, 5, 10}:
        return jsonify({'error': 'Marks must be 2, 5, or 10.'}), 400

    q = Question(unit=unit, k_level=k_level, co=co, text=text_content, marks=marks,
                 difficulty=difficulty, correct_answer=correct_answer)
    db.session.add(q)
    db.session.commit()
    log_activity('question_added', f'Added {marks}M question for Unit {unit} ({k_level}, {co})')
    return jsonify({'message': 'Question added to question bank.', 'question': {
        'id': q.id, 'unit': q.unit, 'k_level': q.k_level, 'co': q.co, 'text': q.text,
        'marks': q.marks, 'difficulty': q.difficulty, 'correct_answer': q.correct_answer
    }}), 201


@app.route('/api/questions/<int:question_id>', methods=['DELETE'])
def delete_question(question_id):
    user, error = require_login()
    if error:
        return error
    q = db.session.get(Question, question_id)
    if not q:
        return jsonify({'error': 'Question not found.'}), 404
    db.session.delete(q)
    db.session.commit()
    log_activity('question_deleted', f'Deleted question ID {question_id}')
    return jsonify({'message': 'Question removed successfully.'})


@app.route('/api/templates')
def get_templates():
    return jsonify({'templates': [
        {
            'title': 'R Programming',
            'subject_code': 'AUCAI41',
            'content': """UNIT 1: Introduction to R & Data Types
Introduction to R, features of R, RStudio interface, basic mathematical operations, R data types: vectors, matrices, arrays, lists, factors, data frames. Variable assignment and data type inspection.

UNIT 2: Control Structures & Functions
Decision making: if, if-else, switch; Loop structures: for, while, repeat, break, next. Writing user-defined functions, arguments, return values, recursion.

UNIT 3: Data Manipulation & Data Frames
Data frames creation, indexing, subsetting, slicing, adding and deleting columns and rows. Handling missing data: is.na, na.omit. Merging and reshaping data frames.

UNIT 4: Mathematical, Statistical Functions & Distributions
Mathematical functions: abs, sqrt, log, exp; Statistical distribution functions: dnorm, pnorm, qnorm, rnorm, binomial, Poisson distributions. Descriptive statistics: mean, median, mode, variance, standard deviation.

UNIT 5: Object-Oriented Programming & Visualization
S3 and S4 classes, object-oriented concepts, polymorphism and inheritance. Data visualization using base R graphics: plot, barplot, hist, pie chart, boxplot. Statistical analysis and simulation."""
        },
        {
            'title': 'Problem Solving & Python Programming',
            'subject_code': 'AUCPY101',
            'content': """UNIT 1: Computational Thinking & Fundamentals
Algorithms, building blocks of algorithms (statements, state, control flow, functions), notation (pseudo code, flow chart, programming language), Python interpreter and interactive mode, values and types: int, float, boolean, string, and list; variables, expressions, statements, tuple assignment, precedence of operators.

UNIT 2: Control Flow & Functions
Conditionals: Boolean values and operators, conditional (if), alternative (if-else), chained conditional (if-elif-else); Iteration: state, while, for, break, continue, pass; Fruitful functions: return values, parameters, local and global scope, function composition, recursion.

UNIT 3: Compound Data - Lists, Tuples, Dictionaries
Strings: string slices, immutability, string functions and methods, string module; Lists: list operations, list slices, list methods, list loop, mutability, aliasing, cloning lists, list parameters; Tuples: tuple assignment, tuple as return value; Dictionaries: operations and methods.

UNIT 4: Searching & Sorting Algorithms
Linear search, binary search, bubble sort, selection sort, insertion sort, merge sort; Hash tables and hash functions; String sorting and pattern matching algorithms.

UNIT 5: Files, Modules & Packages
Files and exception: text files, reading and writing files, format operator; command line arguments, errors and exceptions, handling exceptions, modules, packages; Illustrative programs: word count, copy file."""
        },
        {
            'title': 'Data Structures & Algorithms',
            'subject_code': 'AUCDS201',
            'content': """UNIT 1: Linear Data Structures - Stacks and Queues
Abstract Data Types (ADTs) – List ADT – array-based implementation – linked list implementation – singly linked lists – circularly linked lists – doubly-linked lists – applications of lists – Polynomial Manipulation – Stack ADT – Operations – Applications – Queue ADT – Operations – Circular Queue.

UNIT 2: Tree Data Structures
Tree ADT – tree traversals – Binary Tree ADT – expression trees – applications of trees – binary search tree ADT – Threaded Binary Trees – AVL Trees – B-Tree – B+ Tree – Heap – Applications of Heap.

UNIT 3: Set & Graph Structures
Set ADT – disjoint set operations – Union-Find – Graph ADT – Representation of Graphs – Breadth First Search (BFS) – Depth First Search (DFS) – Topological Sort – Bi-connectivity – Cut vertices.

UNIT 4: Advanced Graph Algorithms & Minimum Spanning Trees
Shortest Path Algorithms – Dijkstra's algorithm – Bellman-Ford algorithm – All Pairs Shortest Path – Floyd-Warshall algorithm – Minimum Spanning Tree – Prim's algorithm – Kruskal's algorithm – Network Flow Problem.

UNIT 5: Algorithm Design Techniques & Dynamic Programming
Greedy Strategy – Fractional Knapsack Problem – Huffman Coding – Divide and Conquer Strategy – Merge Sort – Quick Sort – Dynamic Programming – Matrix Chain Multiplication – Longest Common Subsequence – Backtracking – 8-Queens Problem – Branch and Bound."""
        },
        {
            'title': 'Artificial Intelligence & Machine Learning',
            'subject_code': 'AUCAI301',
            'content': """UNIT 1: Introduction to AI & Search Techniques
Foundations of AI – Intelligent Agents – Structure of Agents – Problem Solving by Searching – Uninformed Search Strategies: BFS, DFS, Uniform Cost Search – Informed Search Strategies: Greedy Best First Search, A* Search – Heuristic Functions – Adversarial Search: Minimax Algorithm, Alpha-Beta Pruning.

UNIT 2: Knowledge Representation & Logic
Knowledge-Based Agents – Propositional Logic – First-Order Logic – Inference in First-Order Logic – Forward Chaining – Backward Chaining – Resolution – Knowledge Representation Issues – Ontological Engineering – Categories and Objects – Reasoning Systems for Categories.

UNIT 3: Supervised Machine Learning Algorithms
Introduction to Machine Learning – Types of Learning – Supervised Learning – Linear Regression – Logistic Regression – Decision Trees – ID3 Algorithm – Naive Bayes Classifier – k-Nearest Neighbors (k-NN) – Support Vector Machines (SVM) – Model Evaluation and Metrics: Precision, Recall, F1-Score, ROC-AUC.

UNIT 4: Unsupervised & Ensemble Learning
Unsupervised Learning – Clustering – k-Means Clustering – Hierarchical Clustering – Dimensionality Reduction – Principal Component Analysis (PCA) – Ensemble Learning – Bagging – Random Forests – Boosting – AdaBoost – Gradient Boosting.

UNIT 5: Neural Networks & Deep Learning Basics
Perceptron Learning Model – Multilayer Perceptron – Backpropagation Algorithm – Activation Functions – Loss Functions – Introduction to Deep Learning – Convolutional Neural Networks (CNNs) for Image Recognition – Recurrent Neural Networks (RNNs) for Sequence Modeling – Ethical AI and Bias."""
        }
    ]})



@app.route('/api/admin/warn/<int:user_id>', methods=['POST'])
def warn_user(user_id):
    admin, error = require_admin()
    if error:
        return error
    user = db.session.get(User, user_id)
    if not user or user.is_admin:
        return jsonify({'error': 'User not found or cannot warn an admin.'}), 404
    data = request.get_json(silent=True) or {}
    msg = str(data.get('message', '')).strip()
    if not msg:
        return jsonify({'error': 'Warning message cannot be empty.'}), 400
    user.warning_msg = msg
    user.warning_reply = None
    user.warning_status = 'open'
    user.warning_seen = False
    db.session.commit()
    log_activity('user_warned', f'Warning sent to {user.email}: {msg}', admin.id)
    return jsonify({'message': f'Warning sent to {user.name}.'})


@app.route('/api/auth/reply-warning', methods=['POST'])
def reply_warning():
    user, error = require_login()
    if error:
        return error
    if not user.warning_msg:
        return jsonify({'error': 'There is no active warning to reply to.'}), 404
    data = request.get_json(silent=True) or {}
    reply = str(data.get('reply', '')).strip()
    if not reply:
        return jsonify({'error': 'Reply cannot be empty.'}), 400
    user.warning_reply = reply
    user.warning_seen = True
    db.session.commit()
    log_activity('warning_replied', f'User replied to warning: {reply}')
    return jsonify({'message': 'Your reply was sent to the admin.'})


@app.route('/api/admin/warning-status/<int:user_id>', methods=['POST'])
def update_warning_status(user_id):
    admin, error = require_admin()
    if error:
        return error
    user = db.session.get(User, user_id)
    if not user or user.is_admin or not user.warning_msg:
        return jsonify({'error': 'Warning not found.'}), 404
    data = request.get_json(silent=True) or {}
    status = str(data.get('status', '')).strip().lower()
    if status not in {'open', 'resolved'}:
        return jsonify({'error': 'Status must be open or resolved.'}), 400
    user.warning_status = status
    if status == 'resolved':
        user.warning_seen = True
    db.session.commit()
    log_activity('warning_status_changed', f'Warning for {user.email} marked {status}.', admin.id)
    return jsonify({'message': f'Warning for {user.name} marked {status.upper()}.', 'status': status})


@app.route('/api/auth/acknowledge-warning', methods=['POST'])
def acknowledge_warning():
    user = current_user()
    if not user:
        return jsonify({'error': 'Not logged in.'}), 401
    user.warning_seen = True
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/admin/remove/<int:user_id>', methods=['DELETE'])
def remove_user(user_id):
    admin, error = require_admin()
    if error:
        return error
    user = db.session.get(User, user_id)
    if not user or user.is_admin:
        return jsonify({'error': 'User not found or cannot remove an admin.'}), 404
    # Delete related records first
    ActivityLog.query.filter_by(user_id=user.id).delete()
    GeneratedPaper.query.filter_by(user_id=user.id).delete()
    Syllabus.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    log_activity('user_removed', f'Removed user: {user.email}', admin.id)
    return jsonify({'message': f'User {user.name} removed successfully.'})


@app.route('/api/admin/toggle-active/<int:user_id>', methods=['POST'])
def toggle_active(user_id):
    admin, error = require_admin()
    if error:
        return error
    user = db.session.get(User, user_id)
    if not user or user.is_admin:
        return jsonify({'error': 'User not found or cannot deactivate an admin.'}), 404
    user.is_active = not user.is_active
    db.session.commit()
    status = 'activated' if user.is_active else 'deactivated'
    log_activity('user_status_changed', f'User {user.email} {status}', admin.id)
    return jsonify({'message': f'{user.name} {status}.', 'is_active': user.is_active})


QUESTION_TEMPLATES = {
    2: {
        'K1': [
            "Define {topic} and state its primary purpose.",
            "What is {topic}? State its key characteristics.",
            "List any two essential features of {topic}.",
            "State the basic role of {topic} in computer systems.",
            "Mention two practical applications of {topic}.",
            "Recall the fundamental concepts behind {topic}.",
            "List the advantages of using {topic}.",
            "Identify the main components associated with {topic}.",
            "Name the standard types or categories of {topic}.",
            "What are the primary functions performed by {topic}?"
        ],
        'K2': [
            "Explain {topic} in brief with a simple example.",
            "Briefly describe the working principle of {topic}.",
            "Differentiate between {topic} and {other_topic}.",
            "Illustrate how {topic} operates in standard environments.",
            "Distinguish between the purpose and practical functioning of {topic}.",
            "Clarify the importance of {topic} with a suitable use case.",
            "Summarize the key benefits and limitations of {topic}.",
            "Give two practical examples demonstrating {topic}.",
            "Briefly explain the role and significance of {topic}.",
            "Compare the characteristics of {topic} and {other_topic}."
        ],
        'K3': [
            "Demonstrate how {topic} is initialized, configured, or used.",
            "Apply the concept of {topic} to execute a basic task.",
            "Show how {topic} can be utilized effectively with an example.",
            "Construct a simple outline or syntax demonstrating {topic}."
        ],
        'K4': [
            "Analyze the operational bottlenecks or errors associated with {topic}.",
            "Compare the performance aspects of {topic} with {other_topic}.",
            "Examine the primary advantages and constraints of {topic}."
        ],
        'K5': [
            "Assess the necessity of {topic} in modern software/computing environments.",
            "Justify why {topic} is preferred in standard system implementations."
        ],
        'K6': [
            "Formulate a minimal schematic or structure representing {topic}.",
            "Design a basic procedure demonstrating the application of {topic}."
        ]
    },
    5: {
        'K1': [
            "State the core principles, types, and structural organization of {topic} in detail.",
            "Describe the major components, classifications, and primary features of {topic}."
        ],
        'K2': [
            "Explain the working mechanism and operational principles of {topic} with neat illustrations.",
            "Describe {topic} with an architectural/schematic diagram and explain its features.",
            "Differentiate {topic} and {other_topic} with detailed comparison metrics.",
            "Discuss the characteristics, advantages, and real-world applications of {topic}.",
            "Explain the step-by-step workflow of {topic} with an illustrative diagram.",
            "Summarize the major techniques, tools, and procedures associated with {topic}."
        ],
        'K3': [
            "Demonstrate the practical implementation and execution of {topic} with a comprehensive example.",
            "Apply {topic} to solve a practical scenario, explaining each step clearly.",
            "Illustrate the complete workflow and lifecycle of {topic} with a flowchart or diagram.",
            "Construct a functional solution demonstrating the capabilities of {topic}."
        ],
        'K4': [
            "Analyze {topic} critically and examine its performance, scalability, and operational trade-offs.",
            "Investigate the primary differences and similarities between {topic} and {other_topic}.",
            "Deconstruct the architecture of {topic} and evaluate each sub-component's role."
        ],
        'K5': [
            "Evaluate the criteria for selecting {topic} in enterprise systems and justify your choice.",
            "Critically appraise the advantages, limitations, and future scope of {topic}."
        ],
        'K6': [
            "Design and develop an architectural solution implementing {topic} with suitable diagrams.",
            "Formulate a robust structural model or procedure based on {topic} for an application scenario."
        ]
    },
    10: {
        'K2': [
            "Explain in comprehensive detail the architecture, working principles, and complete workflow of {topic} with clear diagrams.",
            "(a) Explain the fundamental concepts, structures, and types of {topic} (5 Marks)\n(b) Discuss the working principles and practical applications of {other_topic} with diagrams (5 Marks)"
        ],
        'K3': [
            "Demonstrate the end-to-end design and implementation of {topic} using real-world case studies and illustrative examples.",
            "(a) Apply {topic} to formulate a step-by-step practical implementation (5 Marks)\n(b) Explain the working and optimization of {other_topic} with neat illustrations (5 Marks)"
        ],
        'K4': [
            "Provide an in-depth analytical review of {topic}. Examine its theoretical foundations, structural complexity, and comparative performance benchmarks.",
            "Critically analyze the design challenges, architectural bottlenecks, and optimization strategies in {topic}."
        ],
        'K5': [
            "Evaluate the structural organization and deployment strategies of {topic}. Formulate a detailed appraisal of its efficiency and fault tolerance.",
            "Assess the integration of {topic} and {other_topic} in modern computing environments with relevant illustrations."
        ],
        'K6': [
            "Design a complete high-performance system leveraging {topic}. Formulate its architectural blueprints, operational workflows, and evaluate its reliability.",
            "Formulate an optimal end-to-end framework utilizing {topic} to address complex real-world requirements, supported by comprehensive diagrams."
        ]
    }
}


def _clean_topic_str(t):
    import re as _re
    t = _re.sub(r'^\s*(?:introductory\s+concepts|introduction\s+to|overview\s+of|the\s+concept\s+of|features\s+of|understanding|basics\s+of|concept\s+of)\s*[:–—\- ]*', '', t, flags=_re.I)
    t = _re.sub(r'[\&\|\+]+its\s+features', '', t, flags=_re.I)
    t = _re.sub(r'^[0-9\.\-\*\•\(\) ]+', '', t)
    t = _re.sub(r'\s*\(.*?\)\s*', ' ', t)
    t = _re.sub(r'\s+\b(?:of|in|to|for|with|on|and|by|the|a|an|from|at)\s*$', '', t, flags=_re.I)
    t = _re.sub(r'^\s*\b(?:of|in|to|for|with|on|and|by|the|a|an|from|at)\s+', '', t, flags=_re.I)
    t = t.strip(' .-_:;()[]{}*•\t\r\n')
    return t


def _extract_unit_topics(block):
    import re as _re
    parts = _re.split(r'[\n;•\*]+|(?<=[a-zA-Z0-9])\s*[–—]\s*|(?<=[a-zA-Z0-9])\s*-\s*(?=[a-zA-Z0-9])|,\s*|\.\s+(?=[A-Z])|:\s+', block)
    topics = []
    seen = set()
    for raw in parts:
        c = _clean_topic_str(raw)
        c_lower = c.lower()
        if len(c) >= 3 and len(c) <= 60 and not c.isdigit() and c_lower not in seen:
            if c_lower not in {'and', 'or', 'etc', 'etc.', 'the', 'an', 'unit', 'features', 'options'}:
                seen.add(c_lower)
                topics.append(c)
    return topics


def _make_answer_key(topic, marks):
    if marks == 2:
        return f"{topic}: Core concept defining foundational operations, syntax, and characteristics. Essential for standard execution and modular handling."
    elif marks == 5:
        return f"Comprehensive explanation of {topic}: Involves structural design, operational workflow, component interactions, and practical applications with illustrative diagrams."
    else:
        return f"In-depth analysis and implementation of {topic}: Covers architectural framework, end-to-end processing lifecycle, performance optimization, and real-world deployment."


@app.route('/api/generate', methods=['POST'])
def generate_paper():
    user, error = require_login()
    if error:
        return error
    if user.is_admin:
        return jsonify({'error': 'Admin account cannot generate question papers.'}), 403

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Request body must be valid JSON.'}), 400

    selected_units = data.get('units', [])
    selected_k_levels = data.get('k_levels', [])
    selected_cos = data.get('cos', [])
    syllabus = str(data.get('syllabus', '')).strip()
    subject_code = str(data.get('subject_code', 'AUCAI11')).strip() or 'AUCAI11'
    subject_title = str(data.get('subject_title', '')).strip() or str(data.get('title', '')).strip() or 'Question Paper'
    mode = str(data.get('mode', 'full')).lower()

    if not isinstance(selected_units, list) or not all(
        isinstance(u, int) and not isinstance(u, bool) and 1 <= u <= 5 for u in selected_units
    ):
        return jsonify({'error': 'Units must be a list containing values from 1 to 5.'}), 400
    allowed_k = {f'K{i}' for i in range(1, 7)}
    if not isinstance(selected_k_levels, list) or not all(
        isinstance(k, str) and k in allowed_k for k in selected_k_levels
    ):
        return jsonify({'error': 'K-levels must be selected from K1 to K6.'}), 400
    if not isinstance(selected_cos, list) or not all(isinstance(c, str) and c.startswith('CO') for c in selected_cos):
        return jsonify({'error': 'Choose valid course outcomes.'}), 400
    if not selected_units or not selected_k_levels:
        return jsonify({'error': 'Please select at least one unit and K-level!'}), 400
    if mode not in {'full', '2', '5', '10'}:
        return jsonify({'error': 'Choose Full Paper, 2 Marks, 5 Marks, or 10 Marks.'}), 400

    import random as _random

    # Extract recent papers to prevent repetitive questions across multiple generations
    recent_history_texts = set()
    recent_history_topics = set()
    try:
        past_papers = GeneratedPaper.query.filter_by(user_id=user.id).order_by(GeneratedPaper.id.desc()).limit(6).all()
        for pp in past_papers:
            p_data = json.loads(pp.paper_json)
            for sec in ['part_a', 'part_b', 'part_c']:
                for q_item in p_data.get(sec, []):
                    txt = str(q_item.get('text', '')).strip().lower()
                    if txt:
                        recent_history_texts.add(txt)
                    tpc = str(q_item.get('topic', '')).strip().lower()
                    if tpc:
                        recent_history_topics.add(tpc)
    except Exception:
        pass

    part_a = []
    part_b = []
    part_c = []
    used_texts = set()
    used_topic_k_pairs = set()

    # PRIMARY PATH: Generate directly from provided syllabus
    if syllabus and len(syllabus) > 10:
        unit_blocks = split_units(syllabus, selected_units)
        unit_topics = {}
        for u in selected_units:
            blk = unit_blocks.get(str(u), '')
            topics = _extract_unit_topics(blk)
            if not topics:
                topics = [f"Unit {u} Core Concept", f"Unit {u} Principles", f"Unit {u} Architecture", f"Unit {u} Applications"]
            unit_topics[u] = topics

        def get_syllabus_question(u, marks, target_k):
            pool = unit_topics.get(u, [])
            candidates = []
            for t in pool:
                pair = (t.lower(), marks, target_k)
                penalty = 0
                if t.lower() in recent_history_topics:
                    penalty += 10
                if pair in used_topic_k_pairs:
                    penalty += 30
                candidates.append((penalty, t))
            candidates.sort(key=lambda x: (x[0], _random.random()))
            chosen_topic = candidates[0][1]
            other_candidates = [t for t in pool if t.lower() != chosen_topic.lower()]
            other_topic = _random.choice(other_candidates) if other_candidates else f"{chosen_topic} techniques"

            templates_pool = QUESTION_TEMPLATES.get(marks, {}).get(target_k, [])
            if not templates_pool:
                templates_pool = QUESTION_TEMPLATES.get(marks, {}).get('K2', ["Explain the concepts and importance of {topic} with an illustrative example."])

            shuffled_templates = list(templates_pool)
            _random.shuffle(shuffled_templates)

            chosen_text = None
            for tmpl in shuffled_templates:
                text_cand = tmpl.format(topic=chosen_topic, other_topic=other_topic)
                t_lower = text_cand.strip().lower()
                if t_lower not in used_texts and t_lower not in recent_history_texts:
                    chosen_text = text_cand
                    break
            if not chosen_text:
                for tmpl in shuffled_templates:
                    text_cand = tmpl.format(topic=chosen_topic, other_topic=other_topic)
                    t_lower = text_cand.strip().lower()
                    if t_lower not in used_texts:
                        chosen_text = text_cand
                        break
            if not chosen_text:
                chosen_text = f"Explain the fundamental mechanisms and significance of {chosen_topic} with an illustrative diagram."

            used_texts.add(chosen_text.strip().lower())
            used_topic_k_pairs.add((chosen_topic.lower(), marks, target_k))
            
            # Map CO: CO1 for Unit 1, CO2 for Unit 2, or user selected CO matching unit
            co_assigned = f'CO{u}'
            if selected_cos:
                matched_cos = [c for c in selected_cos if c.endswith(str(u))]
                if matched_cos:
                    co_assigned = matched_cos[0]
                else:
                    co_assigned = selected_cos[0]

            return {
                'id': None,
                'text': chosen_text,
                'k_level': target_k,
                'unit': u,
                'co': co_assigned,
                'marks': marks,
                'topic': chosen_topic,
                'correct_answer': _make_answer_key(chosen_topic, marks)
            }

        # SECTION A (2 Marks, 10 Questions total in Full mode)
        if mode in {'full', '2'}:
            k_pool = [k for k in selected_k_levels if k in ['K1', 'K2', 'K3']] or selected_k_levels or ['K1', 'K2']
            target_per_unit = max(1, 10 // len(selected_units))
            for u in selected_units:
                for _ in range(target_per_unit):
                    if len(part_a) < 10:
                        k = _random.choice(k_pool)
                        part_a.append(get_syllabus_question(u, 2, k))
            # If still less than 10, fill from selected units
            while len(part_a) < 10:
                u = _random.choice(selected_units)
                k = _random.choice(k_pool)
                part_a.append(get_syllabus_question(u, 2, k))

        # SECTION B (5 Marks, 10 Questions = 5 pairs either/or in Full mode)
        if mode in {'full', '5'}:
            k_pool = [k for k in selected_k_levels if k in ['K2', 'K3', 'K4']] or selected_k_levels or ['K2', 'K3']
            target_per_unit = max(1, 10 // len(selected_units))
            for u in selected_units:
                for _ in range(target_per_unit):
                    if len(part_b) < 10:
                        k = _random.choice(k_pool)
                        part_b.append(get_syllabus_question(u, 5, k))
            while len(part_b) < 10:
                u = _random.choice(selected_units)
                k = _random.choice(k_pool)
                part_b.append(get_syllabus_question(u, 5, k))

        # SECTION C (10 Marks, 5 Questions in Full mode)
        if mode in {'full', '10'}:
            k_pool = [k for k in selected_k_levels if k in ['K3', 'K4', 'K5', 'K6']] or selected_k_levels or ['K3', 'K4']
            target_per_unit = max(1, 5 // len(selected_units))
            for u in selected_units:
                for _ in range(target_per_unit):
                    if len(part_c) < 5:
                        k = _random.choice(k_pool)
                        part_c.append(get_syllabus_question(u, 10, k))
            while len(part_c) < 5:
                u = _random.choice(selected_units)
                k = _random.choice(k_pool)
                part_c.append(get_syllabus_question(u, 10, k))

    # FALLBACK PATH: Question Bank (Only when syllabus is empty)
    else:
        base_filter = [Question.unit.in_(selected_units), Question.k_level.in_(selected_k_levels)]
        question_filter = list(base_filter)
        if selected_cos:
            question_filter.append(Question.co.in_(selected_cos))

        def questions_for_db(marks, needed):
            res = []
            per_unit = max(1, needed // len(selected_units)) if selected_units else 1
            for u in selected_units:
                unit_qs = Question.query.filter(*question_filter, Question.unit == u, Question.marks == marks).order_by(db.func.random()).all()
                if not unit_qs and selected_cos:
                    unit_qs = Question.query.filter(*base_filter, Question.unit == u, Question.marks == marks).order_by(db.func.random()).all()
                count = 0
                for q in unit_qs:
                    if count >= per_unit or len(res) >= needed:
                        break
                    key = q.text.strip().lower()
                    if key not in used_texts:
                        used_texts.add(key)
                        res.append({'id': q.id, 'text': q.text, 'k_level': q.k_level, 'unit': q.unit, 'co': q.co or f'CO{q.unit}',
                                    'marks': q.marks, 'correct_answer': q.correct_answer or _make_answer_key(q.text[:30], marks)})
                        count += 1
            if len(res) < needed:
                qs = Question.query.filter(*question_filter, Question.marks == marks).order_by(Question.unit.asc(), db.func.random()).all()
                if not qs and selected_cos:
                    qs = Question.query.filter(*base_filter, Question.marks == marks).order_by(Question.unit.asc(), db.func.random()).all()
                for q in qs:
                    if len(res) >= needed:
                        break
                    key = q.text.strip().lower()
                    if key not in used_texts:
                        used_texts.add(key)
                        res.append({'id': q.id, 'text': q.text, 'k_level': q.k_level, 'unit': q.unit, 'co': q.co or f'CO{q.unit}',
                                    'marks': q.marks, 'correct_answer': q.correct_answer or _make_answer_key(q.text[:30], marks)})
            res.sort(key=lambda x: int(x.get('unit') or 1))
            return res[:needed]

        part_a = questions_for_db(2, 10) if mode in {'full', '2'} else []
        part_b = questions_for_db(5, 10) if mode in {'full', '5'} else []
        part_c = questions_for_db(10, 5) if mode in {'full', '10'} else []

    paper = {'part_a': part_a, 'part_b': part_b, 'part_c': part_c}
    counts = {'part_a': len(part_a), 'part_b': len(part_b), 'part_c': len(part_c)}
    warnings = []

    generated = GeneratedPaper(
        user_id=user.id,
        subject_code=subject_code,
        submit_subject=subject_title,
        selections=json.dumps({'units': selected_units, 'k_levels': selected_k_levels, 'cos': selected_cos}),
        paper_json=json.dumps({**paper, 'counts': counts, 'subject_title': subject_title, 'subject_code': subject_code}),
    )
    db.session.add(generated)
    db.session.commit()
    log_activity('paper_generated', f'Generated {subject_code} ({subject_title}): {len(part_a)}A {len(part_b)}B {len(part_c)}C.')
    return jsonify({**paper, 'counts': counts, 'warnings': warnings, 'paper_id': generated.id,
                    'mode': mode, 'subject_code': subject_code, 'subject_title': subject_title})



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
