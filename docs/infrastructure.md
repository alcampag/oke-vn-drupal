# Infrastructure prerequisites

Use resources in the intended region and VCN. Keep all actual resource
identifiers in ignored local files; every placeholder below must be replaced
locally.

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

Create and attach separate frontend LB, backend LB, pod, FSS, and database NSGs.
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
