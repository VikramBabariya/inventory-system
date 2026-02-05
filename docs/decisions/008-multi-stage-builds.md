# ADR-008: Adoption of Multi-Stage Docker Builds

* **Status:** Accepted
* **Date:** 2026-02-05
* **Context:** Phase 4 (Optimization)

## Context
Initial Docker images for the application were based on "fat" images (`node:20`, `python:3.12`).
These images contained full operating system tools, build chains (GCC, Make), and source code.
* **Problem 1 (Size):** Images were >1GB, leading to slow deployment times and high storage costs.
* **Problem 2 (Security):** Production containers included compilers (`gcc`), which increases the attack surface (e.g., attackers compiling exploits inside the container).

## Decision
We decided to implement **Multi-Stage Builds** for both Frontend and Backend services.

### Frontend Strategy
* **Stage 1 (Builder):** Uses `node:20-alpine` to install dependencies and run `npm run build`.
* **Stage 2 (Runner):** Uses `nginx:alpine` to serve the static artifacts generated in Stage 1.

### Backend Strategy
* **Stage 1 (Builder):** Uses `python:3.12-slim` + `gcc` to compile C-extensions (e.g., `psycopg2`). Creates a virtual environment.
* **Stage 2 (Runner):** Uses `python:3.12-slim` (runtime only). Copies the virtual environment from Stage 1.

## Consequences

### Positive
* **Drastic Size Reduction:** Frontend reduced by ~96% (1.2GB $\to$ 40MB). Backend reduced by ~80% (900MB $\to$ 150MB).
* **Enhanced Security:** Build tools (compilers, headers) are strictly absent from the final production image.
* **Cost Efficiency:** Lower bandwidth and storage requirements for registry and nodes.

### Negative
* **Build Complexity:** Dockerfiles are slightly more complex to read and debug.
* **Build Time:** Initial build time may be slightly longer due to the copying of artifacts between stages (though caching mitigates this).