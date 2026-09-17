#!/usr/bin/env python3
"""Fail publication if tracked files contain resource IDs or credential material."""
import base64
import re
import subprocess
import sys

names = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
patterns = [
    re.compile(rb"ocid" + rb"1\.[A-Za-z0-9_.-]+"),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})"),
    re.compile(rb"(?:AKIA|ASIA)[A-Z0-9]{16}"),
]
forbidden_names = {".kubeconfig", "credentials.txt", "credentials.json", "admin.credentials.json", "values.local.yaml"}
failures = []
for name in filter(None, names):
    if name.split("/")[-1] in forbidden_names or name.startswith(".local/"):
        failures.append((name, "private file"))
    data = subprocess.check_output(["git", "show", ":" + name])
    # Inspect content and base64-encoded text tokens without printing matches.
    candidates = [data]
    for token in re.findall(rb"[A-Za-z0-9+/]{48,}={0,2}", data):
        try:
            candidates.append(base64.b64decode(token, validate=True))
        except ValueError:
            pass
    if any(pattern.search(blob) for pattern in patterns for blob in candidates):
        failures.append((name, "resource identifier or credential pattern"))
if failures:
    for name, reason in failures:
        print(f"BLOCKED: {name}: {reason}", file=sys.stderr)
    sys.exit(1)
print(f"Publication check passed for {len(list(filter(None, names)))} staged/tracked files.")
