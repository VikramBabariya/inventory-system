## 🛠️ Prerequisites
Before running this project, ensure you have the following installed:

| Tool | Required Version | Purpose | Installation Link |
| :--- | :--- | :--- | :--- |
| **WSL** | `v2.x` | Docker desktop requires this in windowes |  |
| **Node.js** | `v24.x` (LTS) | Backend Runtime | [Download](https://nodejs.org/en) |
| **Docker** | `v24.0+` | Containerization | [Get Docker Desktop](https://www.docker.com/products/docker-desktop/) |
| **Make** | `v4.x` | Build Automation | Pre-installed on Mac/Linux (Use Chocolatey for Windows) |
| **AWS CLI** | `v2.x` | Cloud Deployment | [Install Guide](https://aws.amazon.com/cli/) |

### ✅ Check Installation
Run the following commands to verify your setup:

```bash
node --version   # Should be v24.x
npm --version    # Should be v11.x
docker --version # Should be v29.x or higher
```

### 🚀 Getting Started

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    ```

2.  **Setup Environment Variables:**
    Create a `.env` file in the root directory.
    ```bash
    cp .env.example .env
    ```

3.  **Start the Engine:**
    ```bash
    docker-compose up --build
    ```