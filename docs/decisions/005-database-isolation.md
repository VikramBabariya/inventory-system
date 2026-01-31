ADR 005: Network Segmentation Strategy (The "Private Tier" Decision)

Status: Accepted Context: The Frontend container is public-facing and inherently risky (exposed to XSS, user input). The Database contains our most critical asset (data). We need to ensure that a compromise of the Frontend does not automatically grant access to the Database.

Decision: Implement Strict Network Segmentation using Docker Bridge Networks.

Network A (frontend-tier): Contains Nginx + React. (Accessible from Host).

Network B (backend-tier): Contains Backend + Database + Redis. (NOT Accessible from Host or Frontend).

Justification:

Prevention of Lateral Movement: If an attacker compromises the Frontend container (e.g., via a dependency vulnerability), they gain shell access to that container. If the DB were on the same network, they could simply run psql -h db_container and steal all data.

No Route Exists: By placing the DB on a separate backend-tier network, there is literally no IP route from the Frontend to the Database. A ping command from Frontend to DB will fail with Destination Host Unreachable.

The "Bastion" Principle: The Python Backend acts as the only authorized "Gatekeeper." It is the only service allowed to talk to the DB. It sanitizes inputs and enforces logic, whereas a direct network connection would bypass these checks.

Consequences:

We must explicitly define networks: in our docker-compose.yml.

The Backend container must be attached to both networks (or the Nginx proxy strategy must be strictly followed) to bridge the gap.