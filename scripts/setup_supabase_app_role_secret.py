from __future__ import annotations

import argparse
import secrets
import string
import subprocess
import urllib.parse
from pathlib import Path


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, **kwargs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Supabase app role and store its DB URL in GCP Secret Manager.")
    parser.add_argument("--project", default="maliyet-analizi-yazilimi")
    parser.add_argument("--secret", default="bomaksan-database-url")
    parser.add_argument("--role", default="bomaksan_app")
    parser.add_argument("--project-ref", default="hmdwblkemxasxlgipxtz")
    parser.add_argument("--host", default="aws-1-ap-northeast-1.pooler.supabase.com")
    parser.add_argument("--port", default="5432")
    parser.add_argument("--database", default="postgres")
    parser.add_argument("--gcloud", default=r"C:\Users\burak\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd")
    args = parser.parse_args()

    alphabet = string.ascii_letters + string.digits + "-_"
    password = "".join(secrets.choice(alphabet) for _ in range(48))
    escaped_password = password.replace("'", "''")

    sql = f"""
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{args.role}') THEN
    CREATE ROLE {args.role} LOGIN PASSWORD '{escaped_password}';
  ELSE
    ALTER ROLE {args.role} WITH LOGIN PASSWORD '{escaped_password}';
  END IF;
END $$;
GRANT USAGE ON SCHEMA public TO {args.role};
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {args.role};
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO {args.role};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {args.role};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {args.role};
"""

    root = Path.cwd()
    sql_path = root / ".codex-create-supabase-role.sql"
    secret_path = root / ".codex-db-url.tmp"

    try:
        sql_path.write_text(sql, encoding="utf-8")
        run(["supabase.cmd", "db", "query", "--linked", "--file", str(sql_path)])

        encoded_password = urllib.parse.quote(password, safe="")
        pooler_user = f"{args.role}.{args.project_ref}"
        db_url = (
            f"postgresql://{pooler_user}:{encoded_password}@{args.host}:{args.port}/"
            f"{args.database}?sslmode=require"
        )

        import psycopg

        with psycopg.connect(db_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM public.urunler")
                product_count = int(cursor.fetchone()[0])

        secret_path.write_text(db_url, encoding="ascii")
        describe = subprocess.run(
            [args.gcloud, "secrets", "describe", args.secret, "--project", args.project],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if describe.returncode == 0:
            run([args.gcloud, "secrets", "versions", "add", args.secret, "--data-file", str(secret_path), "--project", args.project])
        else:
            run(
                [
                    args.gcloud,
                    "secrets",
                    "create",
                    args.secret,
                    "--replication-policy=automatic",
                    "--data-file",
                    str(secret_path),
                    "--project",
                    args.project,
                ]
            )
    finally:
        sql_path.unlink(missing_ok=True)
        secret_path.unlink(missing_ok=True)

    print("created_role_and_secret")
    print(f"urunler_count={product_count}")


if __name__ == "__main__":
    main()
