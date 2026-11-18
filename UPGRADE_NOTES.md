# Upgrade notes — Student Management System

Based on the uploaded `EduManage_Pro(1).zip`.

## Changes in this package
- Rebranded visible application title, sidebar brand, workspace header and login subtitle to **Student Management System**.
- Fixed attendance update lookup so the selected subject is part of the record key (student + day + subject).
- Updated dashboard unpaid-invoice count to use each invoice's computed balance, which accounts for discount and late fine.
- Updated README with setup, data-safety guidance and known scope limitations.

## Preserved
- Existing Python/Flask architecture.
- Existing SQLAlchemy model definitions and table names.
- Existing route names and templates, apart from branding.
- SQLite as the default database.

## Verification performed
- ZIP source extracted successfully.
- All 4 Python source files passed Python syntax compilation.
- Full Flask runtime/database integration tests were not run because Flask dependencies are not installed in the build environment.
- The uploaded archive did not contain a SQLite database file, so no school records were migrated or altered.
