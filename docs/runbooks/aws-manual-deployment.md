# Network Foundation Runbook

## Execution Log: Network Foundation

| Component | Resource Name / Tag | Configuration Details | Status |
| :--- | :--- | :--- | :--- |
| **VPC** | `inventory-vpc` | CIDR: `10.0.0.0/16` | Provisioned |
| **Subnet** | `inventory-public-subnet-1a` | CIDR: `10.0.1.0/24`, AZ: `ap-south-1a`, Auto-assign Public IP: Enabled | Provisioned |
| **Internet Gateway** | `inventory-igw` | Attached to `inventory-vpc` | Provisioned |
| **Route Table** | (Default VPC Route Table) | Route Added: `0.0.0.0/0` -> `inventory-igw`. Explicitly associated with `inventory-public-subnet-1a`. | Configured |

# Compute & Security Runbook

## Execution Log: Security Boundaries 

| Firewall | Attached To | Inbound Rules | Outbound Rules | Status |
| :--- | :--- | :--- | :--- | :--- |
| `inventory-web-sg` | EC2 ENI (Pending) | HTTP (80) from `0.0.0.0/0`<br>SSH (22) from `<YOUR_IP>/32` | All Traffic to `0.0.0.0/0` | Provisioned |

## Execution Log: Compute Provisioning

| Component | Configuration | Architectural Justification | Status |
| :--- | :--- | :--- | :--- |
| **EC2 Instance** | `t3.small` (Ubuntu 24.04 LTS) | 2GB RAM prevents OOM errors during Vite/React build processes. | Provisioned |
| **Network Location** | `inventory-public-subnet-1a` | Assigned a Public IP for direct administration. Protected by `inventory-web-sg`. | Configured |
| **Storage (EBS)** | 15 GiB gp3 (Encrypted via KMS) | Increased capacity for Docker. **Security:** Data at rest encryption enforced. | Provisioned |
| **Authentication** | `inventory-key.pem` (RSA) | Key securely stored locally. Will enforce `chmod 400` before SSH attempt. | Generated |

Firewall Rules: A strict ledger of your Security Group inbound rules (Port 80 from anywhere, Port 22 from your exact static IP only).

Instance Specs: Record the AMI ID used for Ubuntu 24.04 LTS and the instance type (t3.small).

Key Management: Document the command used to secure your downloaded SSH key (chmod 400 inventory-key.pem).

# Deployment & Orchestration Runbook

Server Initialization: The exact bash commands used to update the Ubuntu package manager (sudo apt update) and install Docker.

Code Delivery: The git clone command to pull your frontend and backend code onto the server.

Secrets Injection: The method used to securely transfer your .env file (containing your PostgreSQL credentials) to the EC2 instance without using version control.

Execution: The final docker compose -f docker-compose.prod.yml up -d command.