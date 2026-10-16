# Validation results

Validated on 16 October 2026 with Python 3.12.10, Django 5.2.18, Django REST Framework 3.16.1, SimpleJWT 5.5.1, and native PostgreSQL 17.11 on Windows. Docker was not used for the database or validation.

| Check | Result |
| --- | --- |
| `manage.py migrate --noinput` | All migrations applied to PostgreSQL |
| `manage.py test --verbosity 2 --noinput` | 17 tests passed in 53.861 seconds |
| `manage.py makemigrations --check --dry-run` | No changes detected |
| `manage.py check` | No issues |
| `python -m pip check` | No broken requirements |
| Python compilation | Passed for accounts, healthcare, config, scripts |
| Live HTTP GET `/api/patients/` without token | 401 as expected |
| Live HTTP POST `/api/auth/register/` with empty JSON | 400 as expected |

The tests use DRF's API client with actual JWT authorization headers and an independent PostgreSQL test database. The test database was destroyed after the successful run. The Postman collection is supplied with response status assertions and automatic token/ID capture; it was not executed in the Postman application.

The workspace's application database is migrated and contains no sample users, patients, or doctors. The native PostgreSQL server listens on `127.0.0.1:55432`; the development API was started at `http://127.0.0.1:8000/api/`.

The submission ZIP contains source code, migrations, dependency specifications, environment template, documentation, helper scripts, and the Postman collection. Local secrets, virtual environment, database files, downloaded binaries, logs, and the original assignment PDF are excluded. Follow README.md to set up a fresh copy.
