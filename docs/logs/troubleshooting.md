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

```Bash
# 1. Find the Container ID using the port
docker ps --filter "publish=5173"

# 2. Force remove it (Stop + Delete in one go)
docker rm -f <CONTAINER_ID>
```

🛡️ Prevention
Always shut down your compose stack correctly to free up ports:

```Bash
docker-compose down
```

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

```Bash
python -c "import socket; socket.create_connection(('target_host', port))"
```

For Node.js Containers (Frontend):

```Bash
node -e 'const net = require("net"); const client = net.createConnection({ port: 5432, host: "db" }, () => { console.log("Connected (BAD!)"); client.end(); }); client.on("error", (err) => { console.log("Connection Failed (GOOD!): " + err.message); });'
```


---------------------------------------------------------------------------------------------------------


### 📄 Troubleshooting Log: Database Schema Not Loading (The "Volume Trap")

**Date:** February 3, 2026
**Issue:** `init.sql` script did not run; Tables `products`, `categories`, `stock_movements` are missing.

#### 🔴 The Symptom
After adding `init.sql` to the `docker-compose.yml` volumes and restarting the container, connecting to the database shows it is still empty (no tables found via `\dt`).

#### 🔍 The Root Cause
**"First Boot Rule" violation.**
The official PostgreSQL Docker image checks the data directory (`/var/lib/postgresql/data`) on startup.
* **If Empty:** It runs scripts in `/docker-entrypoint-initdb.d/`.
* **If Data Exists:** It assumes the DB is already set up and **skips** initialization.
* **Our Scenario:** We ran the DB *before* adding the script, so the volume already contained system files.

#### ✅ The Solution
We must trigger a "Fresh Install" by destroying the existing persistence volume.

**Command:**
```bash
# The -v flag is critical. It deletes the Named Volumes.
docker-compose down -v

# Rebuild and start
docker-compose up --build -d
```

🛡️ Prevention
* If you change the schema (init.sql) in development, you must run down -v to apply changes.
* In production, we never use init.sql for updates; we use Migration tools (like Alembic) instead.


---------------------------------------------------------------------------------------------------------


### 📄 Troubleshooting Log: Missing Python Libraries

**Date:** February 3, 2026
**Issue:** `ModuleNotFoundError: No module named 'sqlalchemy'` (or similar) in backend logs.

#### 🔴 The Symptom
The container starts, but the backend service crashes immediately.
Running `docker logs inventory_backend` reveals an import error for a library you just added to `requirements.txt`.

#### 🔍 The Root Cause
**Stale Docker Image.**
Docker images are built in layers. If you modify `requirements.txt`, Docker does not know it needs to re-run `pip install` unless you explicitly tell it to rebuild. It is reusing the old image which only has the old libraries.

#### ✅ The Solution
Force a rebuild of the container image to trigger the installation step.

**Command:**
```bash
docker-compose up --build
```