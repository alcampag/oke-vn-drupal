#!/usr/bin/env python3
"""Fresh local install with generated disposable credentials; cleanup is automatic."""
import argparse
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import urllib.request

p = argparse.ArgumentParser()
p.add_argument("--skip-build", action="store_true")
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
os.chdir(root)
if not a.skip_build:
    subprocess.run(["docker", "build", "-t", "drupal-demo:test", "image"], check=True)
project = "drupal-demo-test-" + secrets.token_hex(4)
password = secrets.token_urlsafe(32)
root_password = secrets.token_urlsafe(32)
with tempfile.NamedTemporaryFile(mode="w", suffix=".env") as file:
    file.write("\n".join([
        "MYSQL_ROOT_PASSWORD=" + root_password,
        "MYSQL_ADMIN_USER=root", "MYSQL_ADMIN_PASSWORD=" + root_password,
        "DRUPAL_DB_HOST=mysql", "DRUPAL_DB_PORT=3306", "DRUPAL_DB_NAME=drupal",
        "DRUPAL_DB_USER=drupal", "DRUPAL_DB_PASSWORD=" + password,
        "DRUPAL_HASH_SALT=" + secrets.token_urlsafe(48),
        "DRUPAL_ADMIN_USER=admin", "DRUPAL_ADMIN_PASSWORD=" + secrets.token_urlsafe(32),
        "DRUPAL_ADMIN_EMAIL=admin@example.invalid", "INSTALL_IF_EMPTY=true", "DRUPAL_SITE_NAME=Nexus Research",
    ]) + "\n")
    file.flush()
    env = dict(os.environ, DEMO_TEST_ENV=file.name)
    compose = ["docker", "compose", "-p", project, "-f", "compose.test.yaml"]
    def run(*args, capture=False):
        return subprocess.run(compose + list(args), env=env, check=True, text=True,
                              stdout=subprocess.PIPE if capture else None)
    def drush(*args):
        return run("exec", "-T", "--user", "www-data", "drupal", "vendor/bin/drush", *args)
    try:
        run("up", "-d", "--wait")
        run("exec", "-T", "--user", "www-data", "drupal", "sh", "/setup/bootstrap.sh")
        run("exec", "-T", "--user", "www-data", "drupal", "sh", "/setup/bootstrap.sh")
        refusal = subprocess.run(compose + ["exec", "-T", "--user", "www-data", "drupal", "php", "/setup/database.php", "--require-empty"], env=env, capture_output=True)
        assert refusal.returncode != 0 and b"nonempty database" in refusal.stderr
        drush("status", "--fields=drupal-version,bootstrap,db-status")
        run("exec", "-T", "--user", "www-data", "drupal", "php", "-r",
            'if (file_put_contents("web/sites/default/files/smoke.txt", "shared-file-ok") === false) { exit(1); }')
        address = run("port", "drupal", "80", capture=True).stdout.strip()
        with urllib.request.urlopen("http://" + address + "/", timeout=30) as response:
            assert response.status == 200 and b"Nexus" in response.read()
        with urllib.request.urlopen("http://" + address + "/sites/default/files/smoke.txt", timeout=30) as response:
            assert response.read() == b"shared-file-ok"
        print("Fresh Drupal install, repeat module enablement, homepage, and shared-file checks: OK")
    finally:
        subprocess.run(compose + ["down", "--volumes", "--remove-orphans"], env=env, check=True)
