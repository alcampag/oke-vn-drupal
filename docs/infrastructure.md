# Infrastructure prerequisites

Use resources in the intended region and VCN. Keep all actual resource
identifiers in ignored local files; every placeholder below must be replaced
locally.

## Resource Manager stack prerequisite

Use the Oracle DevRel
[OKE Resource Manager Quickstart](https://github.com/oracle-devrel/technology-engineering/tree/main/oci-and-db/cloud-native/devops-and-containers/oke/oke-rm)
as the infrastructure prerequisite. This is the upstream solution used to create
the demo cluster, not infrastructure managed by the Drupal Helm release.
The instructions below were checked against the upstream source on 2026-09-17.
Use the deployment buttons in its README and record the selected release locally
so you can reproduce the infrastructure version as well as the chart version.

### 1. Apply the infrastructure stack

Select VCN-native pod networking. Create a dedicated demo VCN, or supply a
compatible existing VCN and review its subnets, routes, and CIDRs. In existing-VCN
mode, do not assume every subnet is created automatically.

- Keep FSS networking enabled (`create_fss = true`). This prepares networking;
  the FSS mount target is still created separately in the main walkthrough.
- For a new database network, enable `create_db_subnet` and
  `create_database_nsgs`, and include `mysql` in `db_service_list`. These options
  provision database **networking**, not a MySQL DB System.
- Retain a public external-LB subnet and private pod, FSS, and database subnets.
  A private Kubernetes API endpoint needs a private access path from your client.
- Review the upstream
  [network-rules report](https://github.com/oracle-devrel/technology-engineering/blob/main/oci-and-db/cloud-native/devops-and-containers/oke/oke-rm/files/infra/network-rules-report.md)
  and compare it with the application flows below. Do not assume its defaults
  implement this demo's HTTPS-only frontend or encrypted FSS access.

Plan and apply the infrastructure stack before creating the OKE stack. Keep its
outputs private: they contain account-specific resource identifiers.

### 2. Apply the OKE stack and enable virtual nodes

Pass the infrastructure outputs into the OKE stack's matching VCN, subnet, and
NSG inputs. Select an enhanced cluster with VCN-native pod networking.
The upstream worker examples are all disabled initially: edit the OKE stack's
`oke.tf`, enable only the `oke-virtual` pool with `create = true`, then plan and
apply. Leave managed/system pools disabled for a fully virtual-node demo.

The upstream virtual-pool example uses an x86 pod shape. For this walkthrough,
select an available ARM-compatible virtual-node pod shape in your region before
applying; otherwise build the amd64 image and change the chart's architecture
selector as described in the README. Verify the resulting node architecture.

The example also defines a `virtual-node-workload=true:NoSchedule` taint.
Remove that example taint from this dedicated demo pool's Terraform configuration
before applying: the chart does not define a matching toleration. Ensure CoreDNS
is healthy on virtual nodes before installing Drupal. Do not install Karpenter,
Cluster Autoscaler, or metrics-server for this fixed-replica demo.

IAM creation is opt-in through **Enable policies**. Review **Policy dry-run** and
the upstream [policy guide](https://github.com/oracle-devrel/technology-engineering/blob/main/oci-and-db/cloud-native/devops-and-containers/oke/oke-rm/files/oke/POLICIES.md).
The generated infrastructure policies do not replace the application-specific
FSS permission review below.

### 3. Hand off resources to the Drupal walkthrough

Keep all actual values under ignored `.local/`; never commit stack outputs,
Terraform state, plans, or downloaded environment-specific stack configurations.

| Stack resource/output | Use in this demo |
|---|---|
| Created OKE cluster | Local `CLUSTER_ID` and kubeconfig |
| `pod_subnet_id`, `pod_nsg_id` | Virtual-node pod networking and application network rules |
| `external_lb_subnet_id` | Public LB placement; its subnet CIDR becomes `drupal.reverseProxyAddresses` |
| `lb_nsg_id` | Review for the LB backend role; supply it alongside a dedicated frontend NSG in local Service annotations |
| `fss_nsg_id` and created FSS subnet | Local `FSS_NSG_ID` / `FSS_SUBNET_ID` for mount-target creation |
| `db_subnet_id`, `database_nsg_ids` | Private MySQL DB System placement and database-side rules |
| `database_client_nsg_ids` (when enabled) | Attach the MySQL client NSG to the pod network as required by the generated rules |

The stack has one general LB NSG output, not separate frontend/backend outputs.
Reuse its appropriate backend rules and create/configure the additional frontend
NSG for TCP 443. Verify the actual FSS subnet in OCI; do not invent an output name
if the selected release does not export it.

Create the MySQL DB System separately, then continue with the README's IAM/network
checks and mount-target creation. The chart dynamically provisions the filesystem
and deploys Drupal; it does not provision the DB System, cluster, or mount target.
Keep stack-owned network changes in the infrastructure configuration so a later
Resource Manager apply does not undo them.

## OKE and IAM

Use an enhanced OKE cluster with VCN-native pod networking and a virtual-node
pool. Match the image architecture to the virtual-node pod shape. CoreDNS must
be ready. This chart does not require metrics-server or autoscaling.

The provisioning principal needs FSS and networking permissions. An administrator
can adapt these policies to the demo compartment and cluster:

```text
Allow any-user to manage file-family in compartment <COMPARTMENT_NAME> where all {request.principal.type = 'cluster', request.principal.id = '<CLUSTER_ID>'}
Allow any-user to use virtual-network-family in compartment <COMPARTMENT_NAME> where all {request.principal.type = 'cluster', request.principal.id = '<CLUSTER_ID>'}
```

The normal OKE policies for cluster, load-balancer, and registry operations are
also required. Cross-compartment resources need policies at the appropriate
scope. See Oracle's [FSS provisioning guide](https://docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/contengcreatingpersistentvolumeclaim_Provisioning_PVCs_on_FSS.htm)
for current permission requirements.

## Network rules

Reuse the stack-created NSGs where appropriate and add the demo-specific rules
and frontend LB NSG. Attach the frontend LB, backend LB, pod, FSS, and database NSGs
to their respective resources; do not create duplicate NSGs unnecessarily.
The mount target belongs in the FSS subnet with the FSS NSG attached. The MySQL
DB System belongs in a private database subnet with its database NSG attached.
The virtual-node pool must attach the pod NSG to its pods.

For this encrypted demo, the application flows are:

| Source | Destination | Protocol / destination port | Purpose |
|---|---|---|---|
| Demo clients | LB frontend | TCP 443 | HTTPS |
| LB backend NSG | Pod NSG | TCP 80 | HTTP requests and static health checks |
| Pod NSG | Database NSG | TCP 3306 | Drupal content and sessions |
| Pod NSG | FSS NSG | TCP 2051 | FSS encryption in transit |
| Pods | DNS resolver/CoreDNS | UDP/TCP 53 as required by OKE | Name resolution |
| Pods/platform image-pull path | Required registries and OCI services | TCP 443 | Image pulls and service access |

Use stateful rules and allow both the initiating source's egress and the
destination's ingress. Stateful rules cover return traffic. If existing
stateless rules overlap, explicitly account for return traffic and ephemeral
ports; do not assume a new stateful rule fixes an overlapping stateless path.
Keep OKE's required control-plane and pod-network rules intact.

Expose only TCP 443 on the public frontend. Backend TCP 80 stays private.
The Service sets security-rule management to `None`, so the controller does not
manage the NSG rules. Supply both LB NSG identifiers through local annotations.

OCI routing, gateways, security lists, and NSGs must all permit the intended
flows. Private subnets need the appropriate service/NAT path for their required
outbound traffic. Network setup depends on the existing VCN design.

## FSS and virtual-node behavior

Create an **active mount target** in advance so its subnet and NSGs are explicit.
The chart supplies that target to the FSS provisioner; the PVC triggers creation
of a new filesystem/export/PV. The mount target can outlive the Helm release.

The chart uses RWX, `encryptInTransit: "true"`, and pod `fsGroup: 33` with
`OnRootMismatch`. Virtual-node storage integration handles the ownership
behavior. The filesystem's requested 50 GiB is a PVC capacity declaration, not
a guaranteed hard per-filesystem storage quota.

StorageClass parameters are immutable. Do not attempt to migrate an existing
filesystem by changing mount-target or encryption parameters in place.
See [operations](operations.md) before changing storage configuration.

Oracle references:

- [FSS PVCs and virtual-node support](https://docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/contengcreatingpersistentvolumeclaim_Provisioning_PVCs_on_FSS.htm)
- [Virtual-node resource allocation](https://docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/contengvirtualnodepodresourceallocation.htm)
- [OCI LB annotations and session persistence](https://docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/contengconfiguringloadbalancersnetworkloadbalancers-subtopic.htm)
- [FSS in-transit encryption](https://docs.oracle.com/en-us/iaas/Content/File/Tasks/intransitencryption.htm)
