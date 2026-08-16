# OCI Manual Infrastructure Setup Runbook

## Overview

This runbook covers the manual provisioning of Oracle Cloud Infrastructure (OCI) resources required to host the inventory system's single-node k3s cluster. It is structured as a sequential execution guide — complete each section in order before proceeding to the next.

**Target VM**: `VM.Standard.A1.Flex` — OCI Always Free Tier, ARM64 architecture  
**Network**: VCN `10.0.0.0/16` with public subnet `10.0.1.0/24`

> **Note**: k3s installation steps are covered separately. This runbook ends after the VM is reachable via SSH and its public IP is known.

---

## Execution Log

| Resource | Name / Tag | Configuration | Status |
| :--- | :--- | :--- | :--- |
| **VCN** | `inventory-vcn` | CIDR: `10.0.0.0/16` | Pending |
| **Public Subnet** | `inventory-public-subnet` | CIDR: `10.0.1.0/24` | Pending |
| **Internet Gateway** | `inventory-igw` | Attached to `inventory-vcn` | Pending |
| **Security List** | `inventory-security-list` | TCP 22, 80 from `0.0.0.0/0`; TCP 6443 from operator IP | Pending |
| **SSH Key Pair** | `oci_inventory_key` | RSA 4096, uploaded to OCI | Pending |
| **VM Instance** | `inventory-k3s-node` | `VM.Standard.A1.Flex`, 2 OCPUs, 12 GB RAM, Ubuntu 22.04 ARM64 | Pending |
| **Reserved Public IP** | `inventory-public-ip` | Optional; persists across reboots | Pending |

---

## Section 1: Prerequisites — OCI Account Identifiers

Before provisioning any resources, collect these identifiers from the OCI Console. They are required in subsequent steps.

### 1.1 Locate Tenancy OCID

1. Sign in to the [OCI Console](https://cloud.oracle.com).
2. Click the **Profile** icon (top-right) → **Tenancy: `<your-tenancy-name>`**.
3. On the Tenancy details page, copy the **OCID** field.

Record it:

```
# Tenancy OCID — identifies your OCI account root; used in CLI config and IAM policies
TENANCY_OCID="ocid1.tenancy.oc1..aaaa..."
```

### 1.2 Locate User OCID

1. Click the **Profile** icon → **My Profile**.
2. Copy the **OCID** field from the User details page.

Record it:

```
# User OCID — identifies the IAM user making API/CLI calls
USER_OCID="ocid1.user.oc1..aaaa..."
```

### 1.3 Confirm or Create a Compartment

OCI resources are organized in compartments. You can use the root compartment or create a dedicated one.

**Option A — Use root compartment**: The Compartment OCID equals your Tenancy OCID from step 1.1.

**Option B — Create a dedicated compartment** (recommended for isolation):

1. In the OCI Console, navigate to **Identity & Security** → **Compartments**.
2. Click **Create Compartment**.
3. Name: `inventory`, Description: `Inventory system production resources`.
4. Click **Create Compartment** and copy the resulting OCID.

Record it:

```
# Compartment OCID — all inventory resources will be created inside this compartment
COMPARTMENT_OCID="ocid1.compartment.oc1..aaaa..."
```

### 1.4 Note Your Home Region

1. Check the region selector in the top-right of the OCI Console (e.g., `ap-melbourne-1`, `us-ashburn-1`).
2. Always Free Tier VMs must be provisioned in your **home region**.

```
# Home region identifier — Always Free resources are only available in the home region
HOME_REGION="ap-melbourne-1"
```

---

## Section 2: SSH Key Generation and Upload

A dedicated SSH key pair provides secure, password-free access to the VM. The public key is uploaded to OCI during VM creation; the private key stays on your local machine.

### 2.1 Generate an RSA 4096-bit SSH Key Pair

```bash
# Generate a 4096-bit RSA key pair named oci_inventory_key in ~/.ssh/
ssh-keygen -t rsa -b 4096 -C "oci-inventory-k3s" -f ~/.ssh/oci_inventory_key
```

When prompted for a passphrase, enter a strong passphrase and store it in a password manager. The command produces two files:

- `~/.ssh/oci_inventory_key` — private key (never share or commit this)
- `~/.ssh/oci_inventory_key.pub` — public key (uploaded to OCI)

### 2.2 Set Correct Permissions on the Private Key

```bash
# Restrict private key to owner-read-only — SSH will refuse to use keys with open permissions
chmod 400 ~/.ssh/oci_inventory_key
```

### 2.3 View the Public Key for Upload

```bash
# Print the public key — copy this entire output for pasting into OCI during VM creation
cat ~/.ssh/oci_inventory_key.pub
```

Copy the full output (starts with `ssh-rsa`, ends with `oci-inventory-k3s`). You will paste this into the OCI Console in Section 5 when creating the VM.

> **Security note**: The private key (`oci_inventory_key`) must never be committed to source control, uploaded to any cloud storage, or shared. Treat it as a root credential for the server.

---

## Section 3: Virtual Cloud Network (VCN) Creation

The VCN is OCI's virtual private network. It provides the IP address space and routing for all resources.

### 3.1 Create the VCN

1. In the OCI Console, navigate to **Networking** → **Virtual Cloud Networks**.
2. Confirm the correct compartment is selected in the left panel.
3. Click **Create VCN**.
4. Fill in the form:
   - **Name**: `inventory-vcn`
   - **IPv4 CIDR Block**: `10.0.0.0/16`
   - Leave all other fields at defaults.
5. Click **Create VCN**.

Record the VCN OCID:

```
# VCN OCID — required when creating subnets and security lists
VCN_OCID="ocid1.vcn.oc1..aaaa..."
```

### 3.2 Create an Internet Gateway

An Internet Gateway allows the VCN to route traffic to and from the public internet.

1. Inside the newly created `inventory-vcn`, click **Internet Gateways** in the left Resources panel.
2. Click **Create Internet Gateway**.
3. Fill in:
   - **Name**: `inventory-igw`
   - **Enabled**: Yes (default)
4. Click **Create Internet Gateway**.

### 3.3 Update the Default Route Table

The default route table must include a route that directs outbound traffic through the Internet Gateway.

1. Inside `inventory-vcn`, click **Route Tables** in the Resources panel.
2. Click the **Default Route Table for inventory-vcn**.
3. Click **Add Route Rules**.
4. Fill in:
   - **Target Type**: Internet Gateway
   - **Destination CIDR Block**: `0.0.0.0/0`
   - **Target Internet Gateway**: `inventory-igw`
5. Click **Add Route Rules**.

---

## Section 4: Public Subnet and Security List Configuration

### 4.1 Configure the Security List Ingress Rules

The default Security List controls which inbound traffic reaches instances on the subnet. You must add ingress rules before associating the Security List with the subnet.

1. Inside `inventory-vcn`, click **Security Lists** in the Resources panel.
2. Click the **Default Security List for inventory-vcn**.
3. Under **Ingress Rules**, click **Add Ingress Rules** and add each rule below separately:

**Rule 1 — SSH access (required for remote management)**

```
# Allow SSH from any IP — narrow this to your static IP (<YOUR_IP>/32) in production if possible
Stateless: False
Source CIDR:    0.0.0.0/0
IP Protocol:    TCP
Source Port:    All
Destination Port: 22
Description:    SSH access
```

**Rule 2 — HTTP / NodePort (application traffic)**

```
# Allow HTTP on port 80 from anywhere — this is the NodePort that exposes the frontend
Stateless: False
Source CIDR:    0.0.0.0/0
IP Protocol:    TCP
Source Port:    All
Destination Port: 80
Description:    HTTP application access (NodePort frontend)
```

**Rule 3 — k3s API server (restricted to operator IP)**

```
# Allow k3s API on port 6443 — RESTRICT this to your operator IP only; it controls the cluster
Stateless: False
Source CIDR:    <YOUR_OPERATOR_IP>/32
IP Protocol:    TCP
Source Port:    All
Destination Port: 6443
Description:    k3s API server (operator access only)
```

> **Security note**: Replace `<YOUR_OPERATOR_IP>` with your actual public IP address. You can find it by running `curl -s https://checkip.amazonaws.com` in your terminal. Never open port 6443 to `0.0.0.0/0` — this port controls the entire Kubernetes cluster.

4. Click **Add Ingress Rules** after entering all three rules.

Verify the Egress Rules section already contains a rule allowing all outbound traffic (`0.0.0.0/0`). If not, add it:

```
# Allow all outbound traffic — required for package installs, image pulls, and health checks
Destination CIDR: 0.0.0.0/0
IP Protocol:      All
Description:      Allow all outbound traffic
```

### 4.2 Create the Public Subnet

1. Inside `inventory-vcn`, click **Subnets** in the Resources panel.
2. Click **Create Subnet**.
3. Fill in the form:
   - **Name**: `inventory-public-subnet`
   - **Subnet Type**: Regional
   - **IPv4 CIDR Block**: `10.0.1.0/24`
   - **Route Table**: Default Route Table for inventory-vcn
   - **Subnet Access**: Public Subnet
   - **Security List**: Default Security List for inventory-vcn
4. Click **Create Subnet**.

Record the Subnet OCID:

```
# Subnet OCID — required during VM instance creation
SUBNET_OCID="ocid1.subnet.oc1..aaaa..."
```

---

## Section 5: VM Instance Creation

### 5.1 Launch a Compute Instance

1. Navigate to **Compute** → **Instances**.
2. Confirm the correct compartment is selected.
3. Click **Create Instance**.

### 5.2 Configure the Instance

Fill in each section of the creation form:

**Name and placement**

```
# Instance name — used to identify the node in the OCI Console and in kubectl get nodes
Name: inventory-k3s-node
```

Leave the **Availability Domain** at the default (OCI selects one with Always Free capacity).

**Image and shape**

1. Under **Image**, click **Change Image**.
2. Select **Canonical Ubuntu** → **Ubuntu 22.04** → tick the **Minimal** or standard variant.
   - Confirm the **Build** column shows `aarch64` (ARM64). If it shows `x86_64`, select the correct ARM64 image.
3. Click **Select Image**.
4. Under **Shape**, click **Change Shape**.
5. Select **Ampere** → **VM.Standard.A1.Flex**.
6. Set:
   - **Number of OCPUs**: `2`
   - **Amount of Memory (GB)**: `12`
7. Click **Select Shape**.

> **Why these values?** The Always Free Tier provides 4 OCPUs and 24 GB RAM total across all A1 instances in a tenancy. Allocating 2 OCPUs and 12 GB leaves headroom for a second free instance if needed later.

**Networking**

```
# Place the instance in the public subnet created in Section 4
Primary Network:   inventory-vcn
Subnet:            inventory-public-subnet
Public IP Address: Assign a public IPv4 address (ephemeral)
```

> If you plan to use a reserved public IP (Section 7), you can select **No public IP** here and attach the reserved IP after creation. However, assigning the ephemeral IP now is simpler — you can replace it later.

**Add SSH keys**

1. Select **Paste public keys**.
2. Paste the full contents of `~/.ssh/oci_inventory_key.pub` (from Section 2.3).

```
# The SSH public key allows key-based authentication — no password is set on the VM
Paste the output of: cat ~/.ssh/oci_inventory_key.pub
```

**Boot volume**

Leave the boot volume at the default size (50 GB is sufficient for k3s + Docker images on the Always Free Tier).

### 5.3 Create the Instance

Click **Create** at the bottom of the form. The instance will enter **Provisioning** state for 1–2 minutes, then transition to **Running**.

---

## Section 6: Obtain the VM Public IP Address

The public IP is required for all subsequent steps — SSH access, kubectl configuration, and frontend image builds.

### 6.1 Find the Public IP in the OCI Console

1. Navigate to **Compute** → **Instances**.
2. Click **inventory-k3s-node**.
3. In the **Instance Information** tab, locate the **Primary VNIC** section.
4. Copy the **Public IPv4 address**.

```
# Record the public IP — replace <OCI_PUBLIC_IP> with this value in all subsequent commands
OCI_PUBLIC_IP="<your-instance-public-ip>"
```

### 6.2 Alternatively, Find the IP via OCI CLI

If you have the OCI CLI installed and configured:

```bash
# List running instances in the compartment and extract their public IPs
oci compute instance list \
  --compartment-id "$COMPARTMENT_OCID" \
  --display-name "inventory-k3s-node" \
  --query 'data[0]."id"' \
  --raw-output
```

```bash
# Retrieve the VNIC attachment to get the public IP for a known instance OCID
oci compute instance list-vnics \
  --instance-id "$INSTANCE_OCID" \
  --query 'data[0]."public-ip"' \
  --raw-output
```

### 6.3 Verify SSH Connectivity

Once the instance is in **Running** state, confirm you can reach it:

```bash
# Test SSH access using the generated key — expect a shell prompt on the OCI VM
ssh -i ~/.ssh/oci_inventory_key ubuntu@$OCI_PUBLIC_IP
```

> **Note**: The default username for Ubuntu 22.04 on OCI is `ubuntu`. For Oracle Linux 8 it is `opc`.

A successful connection confirms:
- The Security List rule for port 22 is active.
- The SSH key pair is correctly configured.
- The VM's network interface is up.

Type `exit` to close the SSH session before proceeding.

---

## Section 7: Optional — Reserved Public IP

By default, OCI assigns an **ephemeral** public IP that is released when the VM is stopped or terminated. A **reserved** public IP persists independently of the VM, so the application URL stays stable across VM reboots, stops, and even instance recreation.

> This step is recommended. The Always Free Tier includes one reserved public IP at no cost.

### 7.1 Create a Reserved Public IP

1. Navigate to **Networking** → **IP Management** → **Reserved Public IPs**.
2. Confirm the correct compartment is selected.
3. Click **Reserve Public IP Address**.
4. Fill in:
   - **Name**: `inventory-public-ip`
   - **IP Address Source**: Oracle (OCI assigns the address)
5. Click **Reserve Public IP Address**.

Record the reserved IP:

```
# Reserved public IP — this value is stable and should be used for all config from this point on
RESERVED_PUBLIC_IP="<your-reserved-ip>"
```

### 7.2 Detach the Ephemeral IP from the Instance

Before attaching the reserved IP, the ephemeral IP must be removed from the VNIC.

1. Navigate to **Compute** → **Instances** → **inventory-k3s-node**.
2. Click the **Attached VNICs** tab → click the primary VNIC name.
3. Under **IPv4 Addresses**, click the three-dot menu next to the ephemeral public IP.
4. Select **Edit** → set **Public IP Type** to **No public IP** → click **Update**.

### 7.3 Attach the Reserved IP to the Instance

1. On the same **IPv4 Addresses** list, click the three-dot menu on the private IP row.
2. Select **Edit** → set **Public IP Type** to **Reserved public IP**.
3. Select `inventory-public-ip` from the dropdown.
4. Click **Update**.

### 7.4 Verify the Reserved IP is Active

```bash
# Confirm SSH still works using the reserved IP — the connection should succeed as before
ssh -i ~/.ssh/oci_inventory_key ubuntu@$RESERVED_PUBLIC_IP
```

Update the `OCI_PUBLIC_IP` variable to use the reserved IP for all subsequent steps:

```bash
# Update the working variable — use the reserved IP from this point forward
OCI_PUBLIC_IP="$RESERVED_PUBLIC_IP"
```

---

## Summary Checklist

Before proceeding to k3s installation (covered in the next section of this runbook), verify all items below:

| # | Check | Expected Result |
|---|---|---|
| 1 | Tenancy OCID, User OCID, Compartment OCID recorded | All three OCIDs noted |
| 2 | SSH key pair generated at `~/.ssh/oci_inventory_key` | Both files present; `.pub` file copied |
| 3 | Private key permissions set | `ls -la ~/.ssh/oci_inventory_key` shows `-r--------` |
| 4 | VCN `inventory-vcn` created with CIDR `10.0.0.0/16` | Visible in OCI Console → Networking → VCNs |
| 5 | Internet Gateway attached and default route `0.0.0.0/0` configured | Route Table shows IGW route |
| 6 | Security List has TCP 22, 80 from `0.0.0.0/0` and TCP 6443 from operator IP | Three ingress rules visible |
| 7 | Subnet `inventory-public-subnet` created with CIDR `10.0.1.0/24` | Visible under VCN subnets |
| 8 | VM `inventory-k3s-node` is **Running** with `VM.Standard.A1.Flex`, 2 OCPUs, 12 GB RAM, Ubuntu 22.04 ARM64 | Compute → Instances shows Running |
| 9 | Public IP recorded in `OCI_PUBLIC_IP` | IP reachable via `ping $OCI_PUBLIC_IP` |
| 10 | SSH connection verified | `ssh -i ~/.ssh/oci_inventory_key ubuntu@$OCI_PUBLIC_IP` opens a shell |
| 11 | (Optional) Reserved IP attached | `OCI_PUBLIC_IP` updated to reserved address |

---

*Next step: k3s installation — see the k3s installation section of this runbook (task 15).*
