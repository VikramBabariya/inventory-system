📄 Troubleshooting Log: Port Conflicts
Date: February 1, 2026 Issue: Bind for 0.0.0.0:xxxx failed: port is already allocated

🔴 The Symptom
When running docker-compose up, the build fails immediately with an error indicating that the port (e.g., 5173 or 8000) is already allocated, preventing the new container from starting.

🔍 The Root Cause
"Zombie Containers." We previously ran the frontend/backend using individual docker run commands. Even if we stopped the terminal, the container might still be running in the background (detached mode -d) or was stopped but not removed, effectively "parking" on that port.

    Docker Compose tried to park in spot 5173.

    Old Manual Container was already parked in spot 5173.

    Result: Collision.

✅ The Solution
Method 1: GUI (Docker Desktop)

1.Open Docker Desktop.

2.Navigate to the "Containers" tab.

3.Identify standalone containers (names like fervent_bose or backend that are NOT grouped under inventory-system).

4.Select and Delete (Trash icon) the conflicting containers.

Method 2: CLI (The "DevOps" Way) Run this command to find and force-remove the specific container hogging the port:

Bash
# 1. Find the Container ID using the port
docker ps --filter "publish=5173"

# 2. Force remove it (Stop + Delete in one go)
docker rm -f <CONTAINER_ID>

🛡️ Prevention
Always shut down your compose stack correctly to free up ports:

Bash
docker-compose down

down stops the containers AND removes them, freeing the ports immediately.


---------------------------------------------------------------------------------------------------------


📄 Troubleshooting Log: Connectivity Testing in Minimal Containers
Date: February 2, 2026 Issue: OCI runtime exec failed: ... executable file not found in $PATH

🔴 The Symptom
When trying to debug networking using standard Linux commands (ping, curl, telnet) inside a container, the command fails because the binary is missing.

🔍 The Root Cause
Modern Docker images (even "heavy" ones like python:3.12 or node:20) exclude administration tools to reduce image size and improve security (Attack Surface Reduction).

✅ The Solution
Do not install ping. Instead, use the runtime already present in the container (Python or Node) to test TCP connectivity.

For Python Containers (Backend):

Bash
python -c "import socket; socket.create_connection(('target_host', port))"

For Node.js Containers (Frontend):

Bash
node -e 'const net = require("net"); const client = net.createConnection({ port: 5432, host: "db" }, () => { console.log("Connected (BAD!)"); client.end(); }); client.on("error", (err) => { console.log("Connection Failed (GOOD!): " + err.message); });'