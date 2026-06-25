# Inventory System

> Containerized inventory platform built with a production-grade, security-first architecture. Demonstrates multi-tier Docker network isolation, an immutable ledger pattern for audit-safe stock tracking, and multi-stage builds that reduced deployment artifacts by 90%.

---

## Overview

A full-stack inventory system designed to track products, categories, and stock movements across a warehouse operation. The project prioritizes architectural correctness over feature breadth — every infrastructure decision is documented, justified, and built to production standards.

The core engineering challenge: how do you track inventory changes safely, audit every movement, and deploy a secure, minimal-footprint system? This project addresses all three.

---

## Key Technical Highlights

### Immutable Ledger Architecture
Stock is never overwritten. Every change (sale, restock, return, damage) is recorded as a signed delta (`+10`, `-5`) in an append-only `stock_movements` table. The `current_stock` field on the `products` table is a denormalized snapshot maintained for read performance. This mirrors the double-entry bookkeeping pattern used in financial systems — history is always preserved and fully auditable.

### Multi-Tier Network Isolation
Two Docker bridge networks enforce strict service boundaries:

- `frontend_tier` — React frontend and FastAPI backend
- `backend_tier` — FastAPI backend, PostgreSQL, and Redis (planned)

The database has **no IP route** to the frontend container. A compromised frontend cannot reach the database — not by configuration, but by network topology. The FastAPI backend is the sole authorized gateway to data.

### Multi-Stage Docker Builds
Production images are built in two stages: a builder stage that compiles dependencies (including C-extensions via `gcc`), and a minimal runtime stage that copies only the final artifacts. Compilers, build tools, and intermediate files are discarded entirely.

| Service | Dev Image | Prod Image | Reduction |
| :--- | :--- | :--- | :--- |
| Frontend | `node:20` — 1.84 GB | `nginx:alpine` — ~93 MB | **~95%** |
| Backend | `python:3.12` — 1.63 GB | `python:3.12-slim` — ~271 MB | **~83%** |
| **Total** | **~3.5 GB** | **~364 MB** | **~90%** |

### Container Security Hardening
- Non-root user (`appuser`, UID 1000) in all production containers — prevents container breakout from escalating to host privileges
- No compilers in production images — attackers cannot compile exploits or cryptominers inside a compromised container
- No shell tools (`curl`, `wget`, `git`) in production runtime — limits lateral movement
- Secrets injected at runtime via environment variables, never written to the filesystem

### Dual-Environment Orchestration
Two separate Docker Compose files with explicitly different contracts:

| Feature | `docker-compose.yml` (Dev) | `docker-compose.prod.yml` (Prod) |
| :--- | :--- | :--- |
| Code Source | Bind-mounted from host | Baked into image (`COPY`) |
| Frontend Server | Vite dev server (HMR) | Nginx (static file serving) |
| Restart Policy | Off | `always` (self-healing) |
| Security | Loose (debug, open ports) | Strict (minimal ports, non-root) |
| Image Type | `Dockerfile.dev` | `Dockerfile` (multi-stage) |

### Nginx as Reverse Proxy
A single public entry point on port 80. Nginx routes traffic to the correct container by URL path (`/api/` → FastAPI, `/` → React SPA), solves CORS automatically, and handles the SPA fallback (`try_files $uri /index.html`) for client-side routing. Application servers (Uvicorn) are never exposed to the public directly.

### ACID-Compliant Data Store
PostgreSQL was selected over NoSQL alternatives specifically for its transaction guarantees. A stock deduction and a ledger entry must either both succeed or both fail — eventual consistency is not acceptable for inventory. Foreign key constraints (`stock_movements.product_id → products.id`) are enforced at the engine level.


---

## Tech Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend** | Python 3.12, FastAPI | Async REST API, auto-generated OpenAPI docs |
| **ORM** | SQLAlchemy | Database session management, model definitions |
| **Database** | PostgreSQL 15 (Alpine) | ACID-compliant relational data store |
| **Frontend** | React 19, Vite | SPA with component-based UI |
| **Web Server** | Nginx (Alpine) | Static file serving, reverse proxy (production) |
| **Containerization** | Docker, Docker Compose | Multi-service orchestration |
| **DB Driver** | psycopg2-binary | PostgreSQL ↔ Python connector |
| **Config** | python-dotenv | Environment variable management |

---

## Architecture Decision Records

All major technical choices are documented as ADRs in [`/docs/decisions`](./docs/decisions/).

| ADR | Decision | Status |
| :--- | :--- | :--- |
| [001](./docs/decisions/001-backend-framework.md) | FastAPI over Flask/Django | Accepted |
| [002](./docs/decisions/002-frontend-framework.md) | React + Vite over CRA | Accepted |
| [003](./docs/decisions/003-reverse-proxy.md) | Nginx as reverse proxy | Accepted |
| [004](./docs/decisions/004-database-strategy.md) | PostgreSQL over NoSQL | Accepted |
| [005](./docs/decisions/005-database-isolation.md) | Docker network segmentation | Accepted |
| [006](./docs/decisions/006-caching-stratagy.md) | Redis Cache-Aside pattern | Accepted |
| [007](./docs/decisions/007-ledger-pattern-vs-snapshot-updates.md) | Ledger pattern over snapshot updates | Accepted |
| [008](./docs/decisions/008-multi-stage-builds.md) | Multi-stage Docker builds | Accepted |
| [009](./docs/decisions/009-dual-environment-config.md) | Dual-environment Compose config | Accepted |

---

## Security Overview

| Control | Implementation |
| :--- | :--- |
| Network isolation | Database unreachable from frontend tier by network topology |
| Non-root containers | `appuser` (UID 1000) in all production images |
| Minimal attack surface | No compilers, no shell tools in production runtime |
| Secret management | `.env` git-ignored; runtime injection only |
| Reverse proxy | Nginx terminates public traffic; app servers not directly exposed |
| Immutable images | No bind mounts in production; code baked into image |

---


## Getting Started

See the full setup and operations guide: [`docs/runbooks/local-development.md`](./docs/runbooks/local-development.md)

**Quick start:**

```bash
git clone <repo-url>
cd inventory-system
cp .env.example .env
docker-compose up --build
```

| Service | URL |
| :--- | :--- |
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

---

## Roadmap

The current state of the project is a fully operational local development environment with a production-grade infrastructure foundation. Planned epics are sequenced below.

### Phase 3 — Caching Layer 
- [ ] Integrate Redis with Python `redis-py` client
- [ ] Implement Cache-Aside pattern on stock read endpoints
- [ ] Add cache invalidation on write operations
- [ ] Expose `REDIS_URL` as configurable environment variable

### Phase 4 — API Completion
- [ ] `POST /products` — create product
- [ ] `POST /stock/movement` — record a stock change (sale, restock, return)
- [ ] `GET /stock/{sku}` — get current stock with cache-first lookup
- [ ] Pydantic request/response schemas with input validation

### Phase 5 — Frontend Dashboard
- [ ] Product listing with live stock levels
- [ ] Stock movement form (sale / restock / return)
- [ ] Movement history table per product
- [ ] Category filter and SKU search

### Phase 6 — AWS Deployment 
- [ ] Provision custom VPC (`10.0.0.0/16`) in `ap-south-1`
- [ ] Deploy to EC2 `t3.small` (Ubuntu 24.04 LTS)
- [ ] Security Group: port 80 open, port 22 restricted to admin IP (`/32`)
- [ ] Push production images to Amazon ECR
- [ ] Inject secrets via AWS Systems Manager Parameter Store
- [ ] Add HTTPS via Let's Encrypt / Certbot on Nginx

### Phase 7 — Observability & Hardening
- [ ] Structured JSON logging across backend services
- [ ] Docker health check coverage for all services
- [ ] Vulnerability scanning with Trivy in CI pipeline
- [ ] Rate limiting via Nginx configuration
- [ ] CI/CD pipeline (GitHub Actions → ECR → EC2)
  
