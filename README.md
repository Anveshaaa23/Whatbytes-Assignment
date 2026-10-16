# Healthcare Backend

Django REST Framework backend for the healthcare assignment. Includes PostgreSQL storage, email/password registration, SimpleJWT authentication, patient and doctor CRUD, patient-doctor assignments, Django admin, migrations, and API integration tests.

## Run locally

Requires Python 3.12+ and PostgreSQL 17 running directly on Windows. Docker is not used.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
Copy-Item .env.example .env
```

Edit `.env`: use a long random `DJANGO_SECRET_KEY` and a database password. A private `.env` has already been generated for this workspace; do not overwrite it when using the existing setup. Never commit `.env`.

```powershell
.\.venv\Scripts\python.exe scripts/local_postgres.py start
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

The native helper downloads PostgreSQL on its first run, creates the database using `.env`, and reuses it thereafter. See `scripts/README.md` for stop/status commands. API base: `http://127.0.0.1:8000/api/`. PostgreSQL is the application's database; no SQLite fallback is used.

If using an existing PostgreSQL installation, skip the helper, create a database and user below, and set matching `POSTGRES_*` variables in `.env` (including your server's port):

```sql
CREATE USER healthcare WITH PASSWORD 'your-local-password' CREATEDB;
CREATE DATABASE healthcare OWNER healthcare;
```

`CREATEDB` is needed only for Django's test database creation. Use a less privileged database role for deployed applications.

## Authentication

Register with `POST /api/auth/register/`:

```json
{"name": "Alice", "email": "alice@example.com", "password": "A-strong-Healthcare-Password!42"}
```

Returns `201` with `id`, `name`, and `email`. Passwords are validated using Django's validators and stored as hashes. Email identity is case-insensitive, enforced by a database constraint.

Login with `POST /api/auth/login/`:

```json
{"email": "alice@example.com", "password": "A-strong-Healthcare-Password!42"}
```

Returns `200` with `access` and `refresh`. Send `Authorization: Bearer <access>` on every patient, doctor, and mapping request. Access tokens last 30 minutes, refresh tokens one day. `POST /api/auth/refresh/` with `{"refresh": "<refresh>"}` returns a fresh access token. Registration and login have basic per-IP throttling; the default cache is process-local.

## Endpoints

| Method | URL | Behavior |
| --- | --- | --- |
| POST | `/api/auth/register/` | Register name, email, password |
| POST | `/api/auth/login/` | Obtain JWT access and refresh tokens |
| POST | `/api/auth/refresh/` | Refresh access token |
| GET, POST | `/api/patients/` | List own patients / create patient |
| GET, PUT, PATCH, DELETE | `/api/patients/<id>/` | Retrieve / update / delete own patient |
| GET, POST | `/api/doctors/` | List / create doctors |
| GET, PUT, PATCH, DELETE | `/api/doctors/<id>/` | Retrieve / update / delete doctor |
| GET, POST | `/api/mappings/` | List own patients' assignments / assign doctor |
| GET | `/api/mappings/<patient_id>/` | List doctors assigned to an owned patient |
| DELETE | `/api/mappings/<id>/` | Delete an owned patient's mapping by mapping ID |

The assignment uses the same numeric mapping URL for two different identifiers: **GET takes a patient ID; DELETE takes a mapping ID**. The mapping creation response and mapping list include the mapping `id` to use for deletion. Lists are unpaginated JSON arrays.

### Patient payload

```json
{"name": "Anvesha Singh", "age": 21, "gender": "female", "email": "anvesha21@example.com", "phone": "+919876543210", "address": "Example Street", "medical_history": "No known allergies"}
```

`name` and `age` are required. Age must be 0-150. Gender is `female`, `male`, `other`, or `unspecified` (default). Contact information, address, and medical history are optional. The server sets `owner` from the authenticated user; clients cannot override ownership. Foreign patients return `404` for retrieval, update, deletion, and mapping lookup.

### Doctor payload

```json
{"name": "Dr. Smith", "specialization": "Cardiology", "email": "smith@example.com", "phone": "+919876543211", "experience_years": 10}
```

`name` and `specialization` are required. Experience defaults to zero and must be 0-80. Other fields are optional. Doctors form a shared directory: **any authenticated user can read, update, and delete any doctor**. This follows the assignment's all-doctors behavior; patients remain private.

### Mapping payload

```json
{"patient": 1, "doctor": 1}
```

Both IDs must exist, and the patient must belong to the caller. A patient may have multiple doctors and a doctor may serve multiple patients. Duplicate pairs return `400`, with a database uniqueness constraint protecting concurrent requests. Deleting a patient or doctor cascades to its mappings. Creating a mapping returns `201` with `id`, `patient`, `doctor`, nested `doctor_details`, and `created_at`. Patient and doctor responses also contain creation/update timestamps.

### Errors

Validation failures return `400` with field error arrays (or `non_field_errors` for duplicate assignments). Missing/foreign records return `404`; absent, invalid, expired, or inactive-user credentials return `401`; unsupported methods return `405`; throttled authentication requests return `429`. Successful deletes return `204` without a response body. PUT requires the model's required fields; PATCH supports partial updates.

## Verify

With PostgreSQL running:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test --verbosity 2
```

The DRF API client suite covers all required routes, real JWT requests, password hashing, malformed data, duplicate emails/mappings, missing records, cascading deletes, shared doctors, patient ownership, and cross-user mapping protection. Django creates and destroys a separate `test_healthcare` database; no application records are seeded by the tests.

Import `postman/Healthcare.postman_collection.json` into Postman and run it in order against the server. It saves the JWT and record IDs automatically and removes the patient, doctor, and mapping it creates. Change the collection's email before repeating a run because the registered account remains. The password is sample data, not an application credential.

Optional admin account: `.\.venv\Scripts\python.exe manage.py createsuperuser`, then visit `/admin/`.

## Project structure

- `config/`: environment settings, root URLs, WSGI entry point.
- `accounts/`: email-based user model, registration and JWT login.
- `healthcare/`: ORM models, serializers, CRUD views, ownership filters, tests.
- `accounts/migrations/`, `healthcare/migrations/`: committed database schema.
- `scripts/`: controls for this workspace's native PostgreSQL instance.
- `requirements.lock.txt`: exact dependency versions used for validation.

For deployment, set `DJANGO_DEBUG=False`, use an appropriate `DJANGO_ALLOWED_HOSTS`, provide secrets through the environment, and serve the application behind HTTPS with a production WSGI server. The included `runserver` command is for local development.
