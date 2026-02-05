# ADR-004: Dual-Environment Docker Configuration Strategy

* **Status:** Accepted
* **Date:** 2026-02-05
* **Context:** Phase 4 (Optimization) & Deployment Strategy

## Context
A single `docker-compose.yml` file cannot efficiently serve the opposing needs of Development (Agility) and Production (Stability).
* **Development** requires hot-reloading, volume mounting of source code, and loose security.
* **Production** requires immutable images, strict restart policies, and optimized web servers (Nginx).

## Decision
We decided to split the infrastructure configuration into two distinct files and workflows.

### 1. Development (`docker-compose.yml`)
* **Focus:** Developer Experience (DX).
* **Key Features:**
    * Uses `Dockerfile.dev`.
    * **Volumes:** Maps host source code to container (`- ./backend:/app`) for hot-reloading.
    * **Command:** Overrides default CMD to run dev servers (`npm run dev`, `uvicorn --reload`).

### 2. Production (`docker-compose.prod.yml`)
* **Focus:** Reliability & Security.
* **Key Features:**
    * Uses optimized `Dockerfile` (Multi-stage).
    * **No Volumes:** Code is baked into the image (Immutability).
    * **Restart Policy:** `restart: always` enabled for self-healing.
    * **Ordering:** Explicit `depends_on` ensures Nginx starts only after Backend is ready.

## Consequences

### Positive
* **Clean Separation of Concerns:** Production config is not cluttered with dev-specific overrides.
* **Immutability:** Production deployments are consistent and do not depend on the state of the host file system.
* **Safety:** Prevents accidental "debug mode" deployments in production.

### Negative
* **Maintenance Overhead:** Adding a new service (e.g., Redis) requires updating both files to ensure environments remain architecturally consistent.
* **Drift Risk:** Developers must be disciplined to keep version numbers and service names synchronized across both files.