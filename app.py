from datetime import datetime
import json
import os
import secrets
import tempfile

from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=BASE_DIR, static_folder=BASE_DIR)
db_dir = tempfile.gettempdir() if os.environ.get('VERCEL') else BASE_DIR
db_path = os.path.join(db_dir, 'questions.db').replace('\\', '/')
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
            password_hash=generate_password_hash('admin123'),
            is_admin=True,
        ))
        db.session.commit()


def get_token():
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[7:]
    return None


def current_user():
    token = get_token()
    if not token:
        return None
    sess = UserSession.query.filter_by(token=token).first()
    if not sess:
        return None
    return db.session.get(User, sess.user_id)


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


def split_units(content):
    import re
    lines = content.splitlines()
    units = {}
    current = None
    for line in lines:
        match = re.match(r'^\s*UNIT\s*[-: ]?\s*([1-5IVX]+)\s*[:.-]?\s*(.*)$', line, re.I)
        if match:
            raw_unit = match.group(1).upper()
            roman = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5}
            current = roman.get(raw_unit, int(raw_unit) if raw_unit.isdigit() else None)
            if current:
                units[str(current)] = match.group(2).strip()
        elif current:
            units[str(current)] = (units.get(str(current), '') + '\n' + line).strip()
    return units or {'1': content}


from markupsafe import escape
from datetime import timedelta

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
        "default-src 'self' https://cdn.tailwindcss.com https://fonts.googleapis.com https://fonts.gstatic.com; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
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
    name = sanitize(data.get('name', ''))
    email = sanitize(data.get('email', '')).lower()
    password = str(data.get('password', ''))
    if not name or '@' not in email or len(password) < 6:
        return jsonify({'error': 'Name, valid email, and a password of at least 6 characters are required.'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'This email is already registered.'}), 409
    user = User(name=name, email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    token = secrets.token_hex(32)
    db.session.add(UserSession(user_id=user.id, token=token))
    db.session.commit()
    log_activity('signup', 'New account created.', user.id)
    return jsonify({'token': token, 'user': {'name': user.name, 'email': user.email, 'is_admin': False}}), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get('email', '')).strip().lower()
    client_ip = request.remote_addr or 'unknown'
    rate_key = f"{client_ip}:{email}"

    if is_rate_limited(rate_key):
        return jsonify({'error': 'Too many failed login attempts. Account protected. Please try again in 3 minutes.'}), 429

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, str(data.get('password', ''))):
        function_record_failure(rate_key)
        return jsonify({'error': 'Invalid email or password.'}), 401
    if not user.is_active:
        return jsonify({'error': 'Your account has been deactivated. Please contact the administrator.'}), 403

    record_login_success(rate_key)
    
    # Clear previous active sessions for clean user state
    UserSession.query.filter_by(user_id=user.id).delete()
    
    token = secrets.token_hex(32)
    db.session.add(UserSession(user_id=user.id, token=token))
    db.session.commit()
    log_activity('login', 'User logged in.', user.id)
    warning = user.warning_msg if (user.warning_msg and not user.warning_seen) else None
    return jsonify({'token': token, 'user': {'name': user.name, 'email': user.email, 'is_admin': user.is_admin,
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
        records = Syllabus.query.filter_by(user_id=user.id).order_by(Syllabus.created_at.desc()).all()
        return jsonify({'syllabuses': [
            {'id': r.id, 'title': r.title, 'content': r.content,
             'subject_code': r.subject_code, 'unit_names': json.loads(r.unit_names),
             'unit_content': json.loads(r.unit_content), 'created_at': r.created_at.isoformat()}
            for r in records
        ]})
    data = request.get_json(silent=True) or {}
    title = str(data.get('title', '')).strip() or 'My Syllabus'
    subject_code = str(data.get('subject_code', 'AUCAI11')).strip() or 'AUCAI11'
    content = str(data.get('content', '')).strip()
    if not content:
        return jsonify({'error': 'Please enter syllabus text before saving.'}), 400
    existing = Syllabus.query.filter_by(user_id=user.id, subject_code=subject_code).first()
    if existing:
        existing.title = title
        existing.content = content
        existing.unit_names = json.dumps(data.get('unit_names', {}))
        existing.unit_content = json.dumps(split_units(content))
        db.session.commit()
        log_activity('syllabus_updated', f'Updated syllabus: {title}')
        return jsonify({'id': existing.id, 'message': 'Syllabus updated successfully.'}), 200
    record = Syllabus(user_id=user.id, title=title, subject_code=subject_code,
                      content=content, unit_names=json.dumps(data.get('unit_names', {})),
                      unit_content=json.dumps(split_units(content)))
    db.session.add(record)
    db.session.commit()
    log_activity('syllabus_saved', f'Saved syllabus: {title}')
    return jsonify({'id': record.id, 'message': 'Syllabus saved successfully.'}), 201


@app.route('/api/syllabus/<int:syllabus_id>', methods=['PUT', 'DELETE'])
def syllabus_detail(syllabus_id):
    user, error = require_login()
    if error:
        return error
    record = Syllabus.query.filter_by(id=syllabus_id, user_id=user.id).first()
    if not record:
        return jsonify({'error': 'Syllabus not found.'}), 404
    if request.method == 'DELETE':
        db.session.delete(record)
        db.session.commit()
        log_activity('syllabus_deleted', f'Deleted syllabus: {record.title}')
        return jsonify({'message': 'Deleted successfully.'})
    data = request.get_json(silent=True) or {}
    title = str(data.get('title', '')).strip() or record.title
    subject_code = str(data.get('subject_code', '')).strip() or record.subject_code
    content = str(data.get('content', '')).strip()
    if not content:
        return jsonify({'error': 'Content cannot be empty.'}), 400
    conflict = Syllabus.query.filter_by(user_id=user.id, subject_code=subject_code).first()
    if conflict and conflict.id != syllabus_id:
        return jsonify({'error': f'Subject code {subject_code} already exists in another syllabus.'}), 409
    record.title = title
    record.subject_code = subject_code
    record.content = content
    record.unit_names = json.dumps(data.get('unit_names', json.loads(record.unit_names)))
    record.unit_content = json.dumps(split_units(content))
    db.session.commit()
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
    syllabus = data.get('syllabus', '')
    subject_code = str(data.get('subject_code', 'AUCAI11')).strip() or 'AUCAI11'
    mode = str(data.get('mode', 'full')).lower()

    if not isinstance(syllabus, str):
        return jsonify({'error': 'Syllabus must be provided as text.'}), 400
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

    import re as _re, random as _random

    base_filter = [Question.unit.in_(selected_units), Question.k_level.in_(selected_k_levels)]
    question_filter = list(base_filter)
    if selected_cos:
        question_filter.append(Question.co.in_(selected_cos))

    fallback_sections = []
    used_texts = set()

    def extract_topics(text, units):
        blocks = split_units(text)
        topics = []
        for u in units:
            block = blocks.get(str(u), '')
            for t in _re.split(r'[,\n;]+', block):
                t = t.strip().strip('-').strip()
                if len(t) > 8:
                    topics.append((u, t))
        return topics

    def make_topic_questions(topics, marks, needed):
        verbs = {'K1': 'Define', 'K2': 'Explain', 'K3': 'Apply', 'K4': 'Analyze', 'K5': 'Evaluate', 'K6': 'Design'}
        suffix = {2: 'with a brief example.', 5: 'with a suitable example and explanation.', 10: 'in detail with a complete example program or diagram.'}
        _random.shuffle(topics)
        results = []
        for unit, topic in topics:
            if len(results) >= needed:
                break
            k = _random.choice(selected_k_levels) if selected_k_levels else 'K1'
            co = _random.choice(selected_cos) if selected_cos else f'CO{unit}'
            results.append({'id': None, 'text': f"{verbs.get(k, 'Explain')} {topic} {suffix.get(marks, '.')}", 'k_level': k, 'unit': unit, 'co': co})
        return results

    def questions_for(marks, section, needed):
        qs = Question.query.filter(*question_filter, Question.marks == marks).order_by(db.func.random()).all()
        if not qs and selected_cos:
            qs = Question.query.filter(*base_filter, Question.marks == marks).order_by(db.func.random()).all()
            if qs:
                fallback_sections.append(section)
        result = []
        for q in qs:
            key = q.text.strip().lower()
            if key not in used_texts:
                used_texts.add(key)
                result.append({'id': q.id, 'text': q.text, 'k_level': q.k_level, 'unit': q.unit, 'co': q.co})
        if len(result) < needed and syllabus:
            topics = [(u, t) for u, t in extract_topics(syllabus, selected_units) if t.strip().lower() not in used_texts]
            for item in make_topic_questions(topics, marks, needed - len(result)):
                key = item['text'].strip().lower()
                if key not in used_texts:
                    used_texts.add(key)
                    result.append(item)
        return result[:needed]

    part_a = questions_for(2, 'Part A', 10) if mode in {'full', '2'} else []
    part_b = questions_for(5, 'Part B', 10) if mode in {'full', '5'} else []
    part_c = questions_for(10, 'Part C', 5) if mode in {'full', '10'} else []

    paper = {'part_a': part_a, 'part_b': part_b, 'part_c': part_c}
    counts = {'part_a': len(part_a), 'part_b': len(part_b), 'part_c': len(part_c)}
    warnings = []
    required = {'Part A': 10, 'Part B': 10, 'Part C': 5}
    active = {'2': ['Part A'], '5': ['Part B'], '10': ['Part C'], 'full': ['Part A', 'Part B', 'Part C']}[mode]
    for sec in active:
        actual = counts[sec.lower().replace(' ', '_')]
        if actual < required[sec]:
            warnings.append(f'{sec}: need {required[sec]}, found {actual}.')
    if fallback_sections:
        warnings.append('CO match unavailable for: ' + ', '.join(fallback_sections) + '. Used Unit/K-level pool instead.')

    generated = GeneratedPaper(
        user_id=user.id,
        subject_code=subject_code,
        selections=json.dumps({'units': selected_units, 'k_levels': selected_k_levels, 'cos': selected_cos}),
        paper_json=json.dumps({**paper, 'counts': counts}),
    )
    db.session.add(generated)
    db.session.commit()
    log_activity('paper_generated', f'Generated {subject_code}: {len(part_a)}A {len(part_b)}B {len(part_c)}C.')
    return jsonify({**paper, 'counts': counts, 'warnings': warnings, 'paper_id': generated.id,
                    'mode': mode, 'subject_code': subject_code})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
