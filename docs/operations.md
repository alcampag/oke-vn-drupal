# Operations and troubleshooting

## Health checks versus application health

`/healthz.html` is static. It proves that Apache responds, not that Drupal can
reach MySQL or that editors can upload files. Check the homepage, authenticated
`/admin/content`, and an actual uploaded file as well.

Pods may be Ready while MySQL is stopped. A database timeout or access-denied
error in Drupal logs is an application dependency failure, not proof that the
LB is broken.

```sh
kubectl get deploy,pods,pvc,svc -n drupal-demo
kubectl get events -n drupal-demo --sort-by=.lastTimestamp
kubectl logs deployment/serverless-drupal -n drupal-demo --tail=100
kubectl logs job/serverless-drupal-setup -n drupal-demo --tail=100
```

The final command works only while the Job exists. Successful hooks are deleted.
Inspect both web pods individually when behavior differs between replicas.
Do not publish raw logs without reviewing them for sensitive data.

## Common failures

| Symptom | Check |
|---|---|
| Pod pending | Node architecture, virtual-node capacity, resource requests, PVC binding |
| Image pull failure | ARM64/AMD64 manifest, registry address, pull Secret, network access |
| PVC pending | Cluster IAM, correct region/AD, active mount target, FSS quotas |
| FSS mount failure | Pod and FSS NSGs, TCP 2051, subnet routing, export permissions |
| Static health works but Drupal fails | MySQL lifecycle, endpoint, user/password, grants |
| Login redirects to HTTP | Trusted LB subnet in `reverseProxyAddresses`, forwarded HTTPS headers |
| TLS certificate still has temporary name | Update the external Secret and increment `service.tls.revision` |
| Bootstrap refuses a nonempty DB | Investigate existing installation; do not force a reinstall |
| Admission warnings | The Apache demo uses port 80/root startup; policies may require a differently hardened image |

Do not rely on `kubectl exec` being available for virtual-node pods. Use logs and
a reviewed, resource-bounded Job for diagnostics when runtime exec is unavailable.

## Image updates

Drupal 11.4.7 is the baseline tested for this guide. Its
[release notes](https://www.drupal.org/project/drupal/releases/11.4.7) identify the
security fix. This does not mean that version will remain current indefinitely.

The Dockerfile pins an official PHP 8.4 image digest and installs the application
from `composer.lock`. The older Drupal version in the base tag is replaced by
Composer. Dependency auditing covers Composer packages, not the OS or PHP
runtime; review and update the base image separately.

To update reproducibly:

1. Select a supported Drupal security release and an appropriate official base.
2. Regenerate `image/composer.json` and `image/composer.lock` with Composer using
   that PHP runtime. Review the dependency diff; do not commit registry credentials.
3. Build with a **new immutable image tag** and run `composer audit --no-dev`.
4. Update local Helm image values, take database/FSS backups, then upgrade.
5. Verify the setup hook, login, homepage, and uploads.

The web container retains the official image startup command. The separate hook
Job runs schema updates and demo installation; it mounts the same PVC and runs
as the web user to avoid root-owned generated files.

## Local smoke test

Run `python3 scripts/smoke-test.py`. It builds the image, starts a disposable
MySQL container and Drupal on a private Docker network, generates throwaway
credentials in a temporary file, installs the site, and tests the homepage and
shared files. It removes only its own containers and volumes afterwards.
CI runs the same test. A real OKE deployment is still required to validate FSS
mounts, OCI IAM, NSGs, and the LB.

## State and upgrades

Drupal content, users, sessions, and configuration are in MySQL. Uploaded media
and generated public assets are on FSS. Back up both. A retained FSS volume alone
does not restore deleted database content or file metadata.

Sticky sessions are optional for Drupal when both replicas share the database
and files. The chart enables them to demonstrate OCI LB cookie persistence; they
are not the mechanism that shares uploads. FSS supplies that shared filesystem.

Secret changes do not restart containers automatically. After updating the
database Secret, roll the deployment through your normal deployment workflow.
Do not rotate the hash salt accidentally.

Keep the setup administrator Secret private. The routine setup hook does not
change an existing Drupal administrator password; after installation, password
changes belong in Drupal's account management workflow.

## Cleanup and retained storage

First record the PV and backing FSS resource identifiers privately, if you want
to recover files later:

```sh
kubectl get pvc serverless-drupal-files -n drupal-demo
kubectl get pv
helm uninstall serverless-drupal -n drupal-demo
```

This removes the chart resources and the LB Service. Wait for OCI to delete its
load balancer. The **Retain** policy keeps the backing FSS data; the mount target
was created outside Helm and remains too. MySQL and the OKE cluster also remain.

For a completely disposable demo, remove leftover hook Jobs and separately
created Secrets when no longer needed, then delete the namespace. Explicitly
review the retained filesystem/export/PV, mount target, MySQL DB System, and OKE
cluster before deleting any of them in OCI. Uninstalling Helm does not stop all
charges. Never delete shared infrastructure merely because it was used by this
demo.

If preserving data, do not blindly reinstall against the same PVC name after
uninstall: a newly provisioned PVC may create a different filesystem. Recover
the retained volume deliberately and restore the corresponding database.
