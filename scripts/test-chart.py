#!/usr/bin/env python3
"""Structural checks on Helm's rendered YAML; requires PyYAML."""
import subprocess
import yaml

def render(*args):
    output = subprocess.check_output(["helm", "template", "demo", "charts/serverless-drupal",
                                      "-f", "examples/values.ci.yaml", *args], text=True)
    return [doc for doc in yaml.safe_load_all(output) if doc]

docs = render()
assert not any(d["kind"] in ("Secret", "HorizontalPodAutoscaler") for d in docs)
deployment = next(d for d in docs if d["kind"] == "Deployment")
assert deployment["spec"]["replicas"] == 2
container = deployment["spec"]["template"]["spec"]["containers"][0]
assert "command" not in container and "args" not in container
assert container["resources"]["requests"] == container["resources"]["limits"]
service = next(d for d in docs if d["kind"] == "Service")
assert service["spec"]["allocateLoadBalancerNodePorts"] is False
assert [x["port"] for x in service["spec"]["ports"]] == [443]
sc = next(d for d in docs if d["kind"] == "StorageClass")
assert sc["parameters"]["encryptInTransit"] == "true"
assert sc["reclaimPolicy"] == "Retain"
pvc = next(d for d in docs if d["kind"] == "PersistentVolumeClaim")
assert pvc["spec"]["accessModes"] == ["ReadWriteMany"]
job = next(d for d in docs if d["kind"] == "Job")
assert job["spec"]["template"]["spec"]["securityContext"]["runAsUser"] == 33
assert not any(d["kind"] == "Job" for d in render("--set", "bootstrap.enabled=false"))
assert not any(d["kind"] in ("StorageClass", "PersistentVolumeClaim") for d in render("--set", "storage.enabled=false"))
print("Helm invariants and optional-resource rendering: OK")
