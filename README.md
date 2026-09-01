# QP Studio — KMG College Question Paper Generator

An intelligent, secure, and modern Question Paper Studio web application designed for KMG College of Arts and Science.

## Features
- **Syllabus Parsing & Custom Templates**: Upload syllabuses or pick predefined templates (Python, Data Structures, AI & ML).
- **Bloom's K-Level & CO Alignment**: Automatic blueprint analytics calculating K1-K6 Bloom's Taxonomy distribution and CO coverage.
- **KMG College Printable Format**: Exam papers formatted to official college examination standards.
- **Direct PDF Export**: 1-click standalone `.pdf` file download with clean page breaks and zero header/footer URLs.
- **Question Bank Explorer**: Filter, search, and manage custom questions with answer keys.
- **Security Hardening**: Anti-DevTools inspection guards, XSS sanitization, HTTP security headers, and single-session concurrent login enforcement.
- **Dedicated Admin Console**: Faculty account management, warning issuer & resolution manager, and submitted paper repository.

## Tech Stack
- **Backend**: Python, Flask, Flask-SQLAlchemy, SQLite, Gunicorn
- **Frontend**: HTML5, Vanilla JavaScript, Tailwind CSS (Dark/Light mode)

## Quick Start
```bash
pip install -r requirements.txt
python app.py
```
App runs locally on `http://127.0.0.1:5000`.
