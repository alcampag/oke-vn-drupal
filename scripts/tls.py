#!/usr/bin/env python3
"""Generate a local demo certificate and update an external Kubernetes TLS Secret."""
import argparse
import base64
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess

p = argparse.ArgumentParser()
p.add_argument("--namespace", default="drupal-demo")
p.add_argument("--name", default="drupal-tls")
p.add_argument("--hostname", default="drupal.invalid")
p.add_argument("--ip")
a = p.parse_args()
identity = str(ipaddress.ip_address(a.ip)) if a.ip else a.hostname
if not a.ip and not re.fullmatch(r"[A-Za-z0-9.-]+", identity):
    p.error("Invalid DNS name")
local = Path(__file__).resolve().parents[1] / ".local" / "tls"
local.mkdir(parents=True, mode=0o700, exist_ok=True)
os.umask(0o077)
key, cert = local / "tls.key", local / "tls.crt"
subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "365",
                "-keyout", str(key), "-out", str(cert), "-subj", f"/CN={identity}",
                "-addext", f"subjectAltName={'IP' if a.ip else 'DNS'}:{identity}"],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
manifest = {"apiVersion": "v1", "kind": "Secret", "metadata": {"name": a.name, "namespace": a.namespace},
            "type": "kubernetes.io/tls", "data": {"tls.crt": base64.b64encode(cert.read_bytes()).decode(), "tls.key": base64.b64encode(key.read_bytes()).decode()}}
result = subprocess.run(["kubectl", "apply", "--server-side", "--field-manager=drupal-demo-tls", "-f", "-"],
                        input=json.dumps(manifest), text=True, capture_output=True)
if result.returncode:
    raise SystemExit("Could not apply TLS Secret; check cluster access and field ownership.")
print(f"Updated TLS Secret {a.name} for {identity}. Local key is under .local/tls/.")
