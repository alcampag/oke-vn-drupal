#!/usr/bin/env python3
"""Create external Kubernetes Secrets without putting credentials in Helm values."""
import argparse
import getpass
import json
import os
from pathlib import Path
import secrets
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("--namespace", default="drupal-demo")
parser.add_argument("--database-host")
parser.add_argument("--initialize-mysql", action="store_true")
parser.add_argument("--apply-existing", action="store_true")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
local = root / ".local"
local.mkdir(mode=0o700, exist_ok=True)
path = local / "credentials.json"
if args.apply_existing:
    data = json.loads(path.read_text())
else:
    if path.exists():
        parser.error("Credentials already exist; use --apply-existing to reuse them.")
    if not args.database_host:
        parser.error("--database-host is required for initial configuration")
    data = {
        "drupal-database": {
            "DRUPAL_DB_HOST": args.database_host, "DRUPAL_DB_PORT": "3306",
            "DRUPAL_DB_NAME": input("Application database [drupal]: ").strip() or "drupal",
            "DRUPAL_DB_USER": input("Application DB user [drupal]: ").strip() or "drupal",
            "DRUPAL_DB_PASSWORD": getpass.getpass("Application DB password (blank generates one): ") or secrets.token_urlsafe(32),
            "DRUPAL_HASH_SALT": secrets.token_urlsafe(48),
        },
        "drupal-site-admin": {
            "DRUPAL_ADMIN_USER": input("Drupal administrator [admin]: ").strip() or "admin",
            "DRUPAL_ADMIN_PASSWORD": secrets.token_urlsafe(32),
            "DRUPAL_ADMIN_EMAIL": input("Administrator email [admin@example.invalid]: ").strip() or "admin@example.invalid",
        },
    }
    if args.initialize_mysql:
        data["drupal-mysql-admin"] = {
            "MYSQL_ADMIN_USER": input("Existing MySQL administrator username: ").strip(),
            "MYSQL_ADMIN_PASSWORD": getpass.getpass("Existing MySQL administrator password: "),
        }
        if not all(data["drupal-mysql-admin"].values()):
            parser.error("MySQL administrator credentials cannot be empty")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(data, stream, indent=2)
subprocess.run(["kubectl", "get", "namespace", args.namespace], check=True, stdout=subprocess.DEVNULL)
for name, values in data.items():
    manifest = {"apiVersion": "v1", "kind": "Secret", "metadata": {"name": name, "namespace": args.namespace}, "type": "Opaque", "stringData": values}
    # Server-side apply avoids a credential copy in last-applied-configuration.
    result = subprocess.run(["kubectl", "apply", "--server-side", "--field-manager=drupal-demo-setup", "-f", "-"],
                            input=json.dumps(manifest), text=True, capture_output=True)
    if result.returncode:
        raise SystemExit(f"Could not apply Secret {name}; check cluster access and existing field ownership. Credentials remain in {path}.")
    print(f"Secret {name}: applied")
print(f"Credentials saved privately to {path}; never commit or share this file.")
