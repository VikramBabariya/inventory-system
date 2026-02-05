# 🌍 Environments & Lifecycle Concepts

## 1. The Dual-Environment Strategy

Our project relies on two distinct environments that serve opposing goals. Understanding the difference between **Development** and **Production** is key to understanding our Docker configuration.

| Feature | Development (`dev`) | Production (`prod`) |
| :--- | :--- | :--- |
| **Primary Goal** | **Agility** (Speed of Coding) | **Stability** (Reliability & Security) |
| **Code Source** | Local Files (Volumes) | Baked Image (`COPY`) |
| **Server** | Dev Server (Vite / Uvicorn w/ Reload) | Web Server (Nginx / Uvicorn) |
| **Performance** | Slower (Overhead of watchers) | Maximum (Compiled & Optimized) |
| **Security** | Loose (Open ports, debug mode) | Strict (Minimal ports, non-root) |

---

## 2. The Core Shifts

When we move from `docker-compose.yml` to `docker-compose.prod.yml`, three major architectural shifts occur.

### Shift 1: The "Magic Window" vs. The "Baked Cake" (Volumes)

**Development (The Magic Window):**
We use **Bind Mounts** (Volumes).
* **Concept:** We cut a "window" in the container that looks directly at your laptop's hard drive.
* **Mechanism:** `volumes: - ./frontend:/app`
* **Result:** When you save a file in VS Code, the container sees it immediately. If you delete the file on your laptop, the container breaks.

**Production (The Baked Cake):**
We use the **COPY Instruction**.
* **Concept:** We take a snapshot of your code and seal it inside the container image.
* **Mechanism:** `COPY . .` inside the Dockerfile.
* **Result:** The container is **Immutable**. It doesn't care if you delete the code on your laptop; it has its own copy inside. You can deploy this image to 100 servers, and they will all be identical.

### Shift 2: The Factory vs. The Showroom (Frontend Serving)

**Development (Node.js + Vite):**
* **The Tool:** We run a Node.js process (`npm run dev`).
* **The Job:** It acts as a Just-In-Time compiler. It watches files, recompiles changed modules, and pushes updates to the browser via WebSockets (HMR).
* **Cost:** High CPU and Memory usage.

**Production (Nginx):**
* **The Tool:** We run Nginx (`nginx -g daemon off`).
* **The Job:** It simply hands out pre-made files.
* **Process:**
    1.  **Build Stage:** Node.js runs once to compile React code into static HTML/CSS/JS files (`npm run build`).
    2.  **Run Stage:** We throw Node.js away. Nginx takes the static files and serves them.
* **Benefit:** Nginx is 10x faster and uses 95% less memory than Node.js.

### Shift 3: The "Fail Fast" Dependency (Service Orchestration)

**Development:**
We rely on "Eventual Consistency." If the DB isn't ready, the Backend throws an error, but the developer just waits 5 seconds and tries again.

**Production:**
We rely on **Strict Ordering**.
* **Nginx** (Frontend) is brittle; it crashes immediately if it cannot resolve the Backend hostname.
* **Solution:** We use `depends_on` and `healthchecks` to ensure the Backend is fully alive before Nginx even attempts to start.

---

## 3. Environment Variable Strategy

We treat configuration (Secrets, URLs) as an external dependency.

* **Implicit Loading:** Docker Compose automatically loads `.env` files from the root directory.
* **The Golden Rule:** Code should never know *where* it is running. It just asks for `os.getenv("DB_PASSWORD")`.
    * In **Dev**, this comes from your local `.env` file.
    * In **Prod (AWS)**, this comes from the Cloud Provider's Secret Manager, injected at runtime.