1. Network Foundation Runbook

VPC Configuration: Document the custom IPv4 CIDR block you choose (e.g., 10.0.0.0/16).

Subnet Mapping: Note the specific availability zone (e.g., ap-south-1a) and the Public Subnet CIDR.

Routing: Log the creation of the Internet Gateway and the explicit Route Table association linking 0.0.0.0/0 to your public subnet.

2. Compute & Security Runbook

Firewall Rules: A strict ledger of your Security Group inbound rules (Port 80 from anywhere, Port 22 from your exact static IP only).

Instance Specs: Record the AMI ID used for Ubuntu 24.04 LTS and the instance type (t3.small).

Key Management: Document the command used to secure your downloaded SSH key (chmod 400 inventory-key.pem).

3. Deployment & Orchestration Runbook

Server Initialization: The exact bash commands used to update the Ubuntu package manager (sudo apt update) and install Docker.

Code Delivery: The git clone command to pull your frontend and backend code onto the server.

Secrets Injection: The method used to securely transfer your .env file (containing your PostgreSQL credentials) to the EC2 instance without using version control.

Execution: The final docker compose -f docker-compose.prod.yml up -d command.