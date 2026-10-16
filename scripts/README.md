# Native PostgreSQL on Windows

This workspace uses a portable PostgreSQL 17 instance, bound to loopback only. No Docker or Windows service is needed. Its binaries and persistent data are kept in the ignored `.local/` directory.

From the project root:

```powershell
.\.venv\Scripts\python.exe scripts/local_postgres.py start
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

The first start downloads the Windows binary archive from EDB, the Windows binary distributor linked by PostgreSQL's official website. It extracts only `bin`, `lib`, and `share`, initializes a cluster using the credentials in `.env`, and creates the configured database. It uses SCRAM password authentication and listens on `127.0.0.1`. Later starts reuse the existing database. The bootstrap user is a local database administrator; use a dedicated restricted role for deployments.

```powershell
.\.venv\Scripts\python.exe scripts/local_postgres.py status
.\.venv\Scripts\python.exe scripts/local_postgres.py stop
```

This workspace uses port `55432` in `.env` to avoid conflicts with installed database services. Set `POSTGRES_PORT=55432` when recreating its environment. Changing `.env` passwords after initialization does not change PostgreSQL role passwords; use SQL `ALTER ROLE` for an initialized cluster.

The helper and portable runtime are optional. You can use an existing PostgreSQL installation by pointing `.env` to that server and creating a database and role as documented in the main README.
