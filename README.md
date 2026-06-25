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
