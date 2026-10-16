"""Start/stop this workspace's native PostgreSQL, without a system service."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
import urllib.request
import zipfile

from dotenv import dotenv_values
import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parent.parent
LOCAL = ROOT / ".local"
BIN = LOCAL / "pgsql" / "bin"
DATA = LOCAL / "pgdata"
DOWNLOAD = "https://get.enterprisedb.com/postgresql/postgresql-17.11-3-windows-x64-binaries.zip"


def run(name, *args, check=True):
    return subprocess.run([str(BIN / (name + ".exe")), *map(str, args)], check=check, cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "stop", "status"])
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("This helper is for Windows. Use your local PostgreSQL installation on other systems.")
    LOCAL.mkdir(exist_ok=True)
    if not BIN.exists():
        if args.action != "start":
            parser.error("No local PostgreSQL instance has been installed yet.")
        archive = ROOT / "tmp" / "postgresql.zip"
        archive.parent.mkdir(exist_ok=True)
        if not archive.exists() or not zipfile.is_zipfile(archive):
            print("Downloading PostgreSQL 17 Windows binaries from EDB (about 326 MB)...", flush=True)
            urllib.request.urlretrieve(DOWNLOAD, archive)
        print("Extracting native database runtime...", flush=True)
        with zipfile.ZipFile(archive) as package:
            for member in package.infolist():
                if member.filename.startswith(("pgsql/bin/", "pgsql/lib/", "pgsql/share/")):
                    package.extract(member, LOCAL)
    if args.action == "status":
        raise SystemExit(run("pg_ctl", "-D", DATA, "status", check=False).returncode)
    if args.action == "stop":
        run("pg_ctl", "-D", DATA, "-m", "fast", "-w", "stop")
        return
    env = {**dotenv_values(ROOT / ".env"), **os.environ}
    user = env.get("POSTGRES_USER", "healthcare")
    password = env.get("POSTGRES_PASSWORD", "")
    database = env.get("POSTGRES_DB", "healthcare")
    port = env.get("POSTGRES_PORT", "5432")
    if not password:
        parser.error("Set POSTGRES_PASSWORD in .env before starting PostgreSQL.")
    if not DATA.exists():
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, dir=LOCAL) as stream:
            stream.write(password)
            password_file = stream.name
        try:
            run("initdb", "-D", DATA, "-U", user, "--pwfile", password_file, "-A", "scram-sha-256", "-E", "UTF8", "--locale=C")
        finally:
            Path(password_file).unlink(missing_ok=True)
    # pg_ctl status returns 3 for a stopped instance.
    status = subprocess.run([str(BIN / "pg_ctl.exe"), "-D", str(DATA), "status"], capture_output=True)
    if status.returncode != 0:
        run("pg_ctl", "-D", DATA, "-l", LOCAL / "postgres.log", "-o", f"-h 127.0.0.1 -p {port}", "-w", "start")
    with psycopg.connect(host="127.0.0.1", port=port, user=user, password=password, dbname="postgres", autocommit=True, connect_timeout=5) as connection:
        if not connection.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,)).fetchone():
            connection.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(sql.Identifier(database), sql.Identifier(user)))
    print(f"PostgreSQL ready at 127.0.0.1:{port}; database: {database}")


if __name__ == "__main__":
    main()
