# Runbook: Local Development Setup

**Environment:** Local  
**Stack:** Docker, FastAPI, React, PostgreSQL  
**Last Updated:** 2026-06

---

## Prerequisites

| Tool | Version | Notes |
| :--- | :--- | :--- |
| Docker Desktop | v4.20+ | Enable "Use Docker Compose V2" in settings |
| WSL | v2.x | Required for Docker on Windows |
| Node.js | v24.x | Only needed for local frontend work outside Docker |

Verify your setup:

```bash
docker --version    # v29.x or higher
node --version      # v24.x
npm --version       # v11.x
```

---

## First-Time Setup

```bash
# 1. Clone the repository
git clone <repo-url>
cd inventory-system

# 2. Configure environment variables
cp .env.example .env
```

Edit `.env` with your values:

```bash
POSTGRES_USER=admin
POSTGRES_PASSWORD=your_password
POSTGRES_DB=inventory_db
DATABASE_URL=postgresql://admin:your_password@db:5432/inventory_db
```

> `.env` is git-ignored. Never commit it. Share credentials securely via a password manager.

---

## Running the Stack

### Development Mode (Hot Reload)

Best for active development. Code changes reflect instantly without rebuilding images.

```bash
docker-compose up --build
```

| Service | URL |
| :--- | :--- |
| Frontend (Vite) | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

### Production Mode (Optimized Build)

Best for testing the production-optimized build locally. Uses Nginx and multi-stage images.

```bash
docker-compose -f docker-compose.prod.yml up --build
```

| Service | URL |
| :--- | :--- |
| App (via Nginx) | http://localhost:5173 |
| Backend API | http://localhost:8000 |

### Stop All Services

```bash
docker-compose down
```

---

## Common Operations

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f db
```

### Access the Database Shell

```bash
docker exec -it inventory_db psql -U admin -d inventory_db
```

Useful queries:

```sql
\dt                          -- list all tables
SELECT * FROM products;      -- view products
SELECT * FROM stock_movements;  -- view ledger history
\q                           -- exit
```

### Access a Container Shell

```bash
# Backend
docker exec -it inventory_backend bash

# Frontend (Alpine — use sh, not bash)
docker exec -it inventory_frontend sh
```

### Verify Backend ↔ Database Connectivity

```bash
docker exec -it inventory_backend python -c \
  "import socket; print(socket.create_connection(('db', 5432)))"
```

### Check Optimized Image Sizes

```bash
docker images | grep inventory
```

---

## Rebuild Decision Matrix

| If you changed... | Run... | Why |
| :--- | :--- | :--- |
| Python / JS code | Nothing (just save) | Bind mounts + hot reload handle it |
| `requirements.txt` or `package.json` | `docker-compose up --build` | Libraries are installed inside the image |
| `.env` or `docker-compose.yml` | `docker-compose up` | Docker recreates container config |
| `db_init/init.sql` | `docker-compose down -v && docker-compose up --build` | Init SQL only runs on an empty volume |
| Testing prod build | `docker-compose -f docker-compose.prod.yml up --build` | Uses optimized images without bind mounts |

---

## Health Checks

```bash
# Backend health (tests DB connectivity)
curl http://localhost:8000/health

# Redis connectivity (once integrated)
docker exec -it inventory_redis redis-cli ping

# PostgreSQL readiness
docker exec -it inventory_db pg_isready -U admin
```

---

## Troubleshooting

**Services start in wrong order / DB not ready**  
The `backend` service uses `depends_on` with `condition: service_healthy`. If the DB health check is failing, check `docker-compose logs db` for init errors.

**Database schema changes not reflecting**  
`init.sql` only runs when the volume is empty. Run a full reset:
```bash
docker-compose down -v
docker-compose up --build
```

**`node_modules` conflicts on frontend**  
The frontend volume config excludes `node_modules` from the bind mount (`/app/node_modules` anonymous volume). If you see module errors, rebuild:
```bash
docker-compose up --build frontend
```

**Port already in use**  
Check for conflicting processes on ports `5173` or `8000` and stop them before starting the stack.
