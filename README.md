## 🛠️ Prerequisites
Before running this project, ensure you have the following installed:

| Tool | Required Version | Purpose | Installation Link |
| :--- | :--- | :--- | :--- |
| **WSL** | `v2.x` | Docker desktop requires this in windowes |  |
| **Node.js** | `v24.x` (LTS) | Backend Runtime | [Download](https://nodejs.org/en) |
| **Docker Desktop** | `v4.20+` (Ensure "Use Docker Compose V2" is enabled in settings) | Containerization | [Get Docker Desktop](https://www.docker.com/products/docker-desktop/) |
| **Make** | `v4.x` | Build Automation | Pre-installed on Mac/Linux (Use Chocolatey for Windows) |
| **AWS CLI** | `v2.x` | Cloud Deployment | [Install Guide](https://aws.amazon.com/cli/) |

### ✅ Check Installation
Run the following commands to verify your setup:

```bash
node --version   # Should be v24.x
npm --version    # Should be v11.x
docker --version # Should be v29.x or higher
```

## 🚀 Quick Start

### Option A: Development Mode (Hot Reload)
*Best for coding. Changes appear instantly.*

1.  **Clone & Setup:**
    ```bash
    git clone <your-repo-url>
    cd inventory-system
    cp .env.example .env
    ```
2.  **Run:**
    ```bash
    docker-compose up --build
    ```
3.  **Access:**
    * Frontend: `http://localhost:5173`
    * Backend Docs: `http://localhost:8000/docs`

### Option B: Production Mode (Optimized)
*Best for performance testing. Uses Nginx & Static Builds.*

1.  **Run:**
    ```bash
    docker-compose -f docker-compose.prod.yml up --build
    ```
2.  **Access:**
    * App: `http://localhost:5173` (Served via Nginx)

## 📊 Performance Benchmarks (Phase 4)

We utilize Multi-Stage Docker builds to minimize attack surface and storage costs.

* **Frontend:** Reduced by **95%** (1.84GB $\to$ 93MB).
* **Backend:** Reduced by **83%** (1.63GB $\to$ 271MB).
* **Security:** Production containers run as non-root users and contain no compilers.