# Student Management System

A Flask-based school management web application with a dashboard and modules for core academic and administrative workflows. The project uses SQLite by default and keeps the existing interface and application modules.

## Technology stack

- Python 3.10+
- Flask, Flask-Login, Flask-WTF
- Flask-SQLAlchemy / SQLAlchemy
- SQLite (default; PostgreSQL driver is included in requirements)
- HTML, CSS, Bootstrap, Jinja2
- Werkzeug password hashing

## Features

- Dashboard
- Student records and admissions
- Teacher records
- Academic sessions, classes, sections, subjects and enrollments
- Attendance
- Fee invoices, partial payments and printable receipts
- Exams and results
- Timetable and announcements
- Library book issue and return
- Transport routes and student assignments
- Payroll
- Reports and activity logs

## Run locally (Windows PowerShell)

1. Install Python 3.10 or newer.
2. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Create your local environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

5. Open `.env` and replace `SECRET_KEY` with a unique random value. You can generate one with:

   ```powershell
   py -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

   Paste the generated value after `SECRET_KEY=` in `.env`. Never commit `.env`.

6. For a fresh database, set `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `.env`. Use an email you control and a unique password with at least 12 characters. `ADMIN_NAME` is optional. The first administrator is created only when both values are supplied and the database has no administrator account. Existing accounts are not overwritten.

7. Start the app:

   ```powershell
   python app.py
   ```

8. Open http://127.0.0.1:5000 in your browser and sign in with the administrator credentials you configured in `.env`.

## Security notes

- No default administrator email/password is included in the source.
- A strong `SECRET_KEY` is required at startup.
- `.env`, database files, virtual environments and Python cache files are excluded by `.gitignore`.
- Do not upload real student, parent, teacher, payment or other private records to a public repository. Use dummy/demo data only.
- Before deploying publicly, review authentication, authorization, input validation, backups, HTTPS, logging and database migrations.

## Database notes

SQLite is the default database. The database is created in Flask's instance directory. This source package intentionally does not include a database file. The application currently uses `db.create_all()` and additive SQLite schema updates; it does not yet use a full Alembic/Flask-Migrate migration workflow. Back up any existing database and test upgrades on a copy first.

## Current scope and future improvements

This is a portfolio/student project and is not presented as a certified production-ready school ERP. Potential future work includes automated tests, formal database migrations, parent/student portals, advanced report-card PDF generation, email/SMS notifications, online payments, inventory management and multi-campus support.

## Project structure

```text
Student_Management_System/
├── app.py
├── config.py
├── extensions.py
├── models.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── static/
└── templates/
```
