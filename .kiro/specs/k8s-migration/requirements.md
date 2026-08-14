# Requirements Document

## Introduction

This document covers the migration of the inventory management system from Docker Compose to Kubernetes. The migration is structured in three phases: (1) author and validate all Kubernetes manifests against a local k3d cluster, (2) provision Oracle Cloud Infrastructure (OCI) and build ARM64 images, and (3) deploy to the production k3s cluster on OCI. CI/CD, TLS, custom domains, and monitoring are explicitly out of scope for this phase.

The existing application stack (FastAPI backend, React/Nginx frontend, PostgreSQL 15, Redis) and all existing Dockerfiles remain unchanged. The migration targets a single-node k3s cluster on OCI Always Free Tier (VM.Standard.A1.Flex, ARM64).

---

## Glossary

- **Cluster**: The Kubernetes cluster — either the local k3d cluster (Phase 1) or the OCI k3s cluster (Phase 3).
- **k3d**: A tool that runs k3s clusters inside Docker containers for local development and manifest validation.
- **k3s**: A lightweight Kubernetes distribution used for the single-node OCI production cluster.
- **Manifest**: A Kubernetes YAML configuration file describing a desired resource state (Deployment, Service, ConfigMap, Secret, PersistentVolumeClaim, etc.).
- **Namespace**: A Kubernetes logical partition used to group and isolate resources. All application resources live in the `inventory` namespace.
- **Backend_Pod**: The Kubernetes Pod running the FastAPI/Uvicorn application container.
- **Frontend_Pod**: The Kubernetes Pod running the React build served by embedded Nginx.
- **DB_Pod**: The Kubernetes Pod running the PostgreSQL 15 database.
- **Redis_Pod**: The Kubernetes Pod running the Redis cache.
- **PVC**: PersistentVolumeClaim — a request for persistent storage used by the DB_Pod.
- **ConfigMap**: A Kubernetes resource that stores non-secret configuration data, used here to mount `init.sql`.
- **Secret**: A Kubernetes resource that stores sensitive credentials (database username/password, etc.).
- **NodePort**: A Kubernetes Service type that exposes a port on every cluster node's IP, used here to expose the frontend on port 80.
- **ClusterIP**: A Kubernetes Service type for internal-only cluster communication, used for backend, database, and Redis.
- **OCI**: Oracle Cloud Infrastructure — the target cloud platform.
- **VCN**: Virtual Cloud Network — OCI's virtual private network construct.
- **Terraform**: Infrastructure-as-code tool used to provision OCI resources (VM, VCN, Security Lists).
- **ghcr.io**: GitHub Container Registry, the image registry used for all container images.
- **git_SHA**: The full Git commit hash used as the image tag for traceability.
- **ARM64**: The CPU architecture of the OCI VM (VM.Standard.A1.Flex). Images built for OCI must target `linux/arm64`.
- **x86_64**: The CPU architecture used for local k3d manifest validation in Phase 1.
- **init.sql**: The existing SQL script in `db_init/init.sql` that initialises the PostgreSQL schema and seed data on first startup.
- **local-path-provisioner**: The built-in k3s storage class that provisions PVCs using local node storage.
- **Node_Affinity**: A Kubernetes scheduling constraint that pins a Pod to a specific node, ensuring the DB_Pod always binds to its PVC data on the single OCI node.
- **Runbook**: Operational documentation that records exact commands for setup, secrets bootstrapping, deployment, and debugging.
- **ADR**: Architecture Decision Record — a short document capturing a technical decision, its context, and consequences.

---

## Requirements

---

### Requirement 1: Kubernetes Namespace Isolation

**User Story:** As a cluster operator, I want all application resources grouped under a dedicated namespace, so that inventory system resources are isolated from any other workloads on the cluster.

#### Acceptance Criteria

1. THE Cluster SHALL provide a namespace named `inventory`, created via a manifest, that contains all application resources (Deployments, Services, ConfigMaps, Secrets, PVCs).
2. IF a Manifest targeting the `inventory` namespace is applied without an explicit `namespace` field in its metadata, THEN THE Cluster SHALL reject the resource with a validation error indicating the missing namespace.
3. IF a Manifest explicitly specifies a namespace other than `inventory`, THEN THE Cluster SHALL reject that resource with a validation error at admission time.
4. THE Cluster SHALL enforce that Backend_Pod, Frontend_Pod, DB_Pod, and Redis_Pod are all scheduled within the `inventory` namespace, rejecting any pod spec that references a different namespace at admission time.

---

### Requirement 2: Database Deployment and Persistence

**User Story:** As a cluster operator, I want PostgreSQL to run as a StatefulSet-equivalent (single-replica Deployment with a PVC) with persistent storage, so that inventory data survives pod restarts and VM reboots.

#### Acceptance Criteria

1. WHEN the DB_Pod is scheduled, THE Cluster SHALL attach a PVC with a capacity of at least 1Gi and an access mode of ReadWriteOnce, mounted at `/var/lib/postgresql/data`, to provide persistent storage across restarts.
2. THE DB_Pod SHALL run the `postgres:15-alpine` image, matching the existing Docker Compose configuration.
3. WHEN the DB_Pod starts with an empty data directory, THE DB_Pod SHALL execute `init.sql` to initialise the schema and seed data, by mounting the ConfigMap at `/docker-entrypoint-initdb.d/init.sql`.
4. WHEN the DB_Pod starts with a non-empty data directory, THE DB_Pod SHALL skip execution of `init.sql`, preserving existing data.
5. THE DB_Pod SHALL read `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` exclusively from the `inventory-secrets` Kubernetes Secret mounted as environment variables.
6. IF the PVC does not have a `storageClassName` set, THEN THE Cluster SHALL bind the PVC to the default storage class (local-path on k3s, standard on k3d), ensuring manifest portability between environments.
7. WHERE the deployment target is the OCI k3s cluster, THE DB_Pod SHALL have a Node Affinity rule that pins it to the single cluster node using the `kubernetes.io/hostname` label key, so that it always finds its PVC data after VM reboots.
8. THE DB_Pod SHALL expose port 5432 on a ClusterIP Service named `postgres` within the `inventory` namespace.
9. THE Cluster SHALL configure the DB_Pod readiness probe to execute `pg_isready`, with an `initialDelaySeconds` of 10, a `periodSeconds` of 5, a `timeoutSeconds` of 5, a `failureThreshold` of 5, and a `successThreshold` of 1, marking the DB_Pod as ready only when the probe succeeds.

---

### Requirement 3: Redis Deployment

**User Story:** As a cluster operator, I want Redis to run as a stateless deployment within the cluster, so that the caching layer is available to the backend without external dependencies.

#### Acceptance Criteria

1. THE Redis_Pod SHALL run the `redis:alpine` image in the `inventory` namespace, matching the existing Docker Compose configuration.
2. THE Redis_Pod SHALL expose port 6379 on a ClusterIP Service named `redis` within the `inventory` namespace.
3. WHEN `redis-cli ping` returns `PONG`, THE Cluster SHALL mark the Redis_Pod as ready, using a readiness probe with a `periodSeconds` of 5, a `timeoutSeconds` of 3, and a `failureThreshold` of 3.
4. THE Redis_Pod SHALL use no PVC, as Redis cache data is ephemeral and does not require persistence across restarts.

---

### Requirement 4: Backend Deployment

**User Story:** As a cluster operator, I want the FastAPI backend to run as a Kubernetes Deployment, connected to PostgreSQL and Redis via ClusterIP Services, so that the API is available to the frontend within the cluster.

#### Acceptance Criteria

1. THE Backend_Pod SHALL run the container image `ghcr.io/VikramBabariya/inventory-backend:<git_SHA>`.
2. THE Backend_Pod SHALL read all environment variables (`DATABASE_URL`, `REDIS_URL`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`) exclusively from the `inventory-secrets` Kubernetes Secret using `secretKeyRef`.
3. WHEN the Backend_Pod starts, THE Cluster SHALL not mark it as ready until the DB_Pod readiness probe passes; this SHALL be enforced via an init container that polls the `postgres` ClusterIP Service on TCP port 5432 with a timeout of 60 seconds before the main container starts.
4. THE Backend_Pod SHALL expose port 8000 on a ClusterIP Service named `backend` with `targetPort: 8000` within the `inventory` namespace.
5. WHEN `GET /health` returns HTTP 200, THE Cluster SHALL mark the Backend_Pod as ready, using a readiness probe with an `initialDelaySeconds` of 15, a `periodSeconds` of 10, and a `failureThreshold` of 3.
6. WHEN `GET /health` returns a non-200 status for 3 consecutive liveness probe attempts (with a `periodSeconds` of 20 and an `initialDelaySeconds` of 30), THE Cluster SHALL restart the Backend_Pod automatically.
7. THE Backend_Pod SHALL use zero PVCs, as all persistent state is delegated to the DB_Pod and Redis_Pod.

---

### Requirement 5: Frontend Deployment and External Access

**User Story:** As a cluster operator, I want the React/Nginx frontend to be accessible from outside the cluster on port 80, so that end users can reach the application via the cluster node's IP address.

#### Acceptance Criteria

1. THE Frontend_Pod SHALL run the container image `ghcr.io/VikramBabariya/inventory-frontend:<git_SHA>`, built from the existing `frontend/Dockerfile` with zero modifications.
2. THE Frontend_Pod SHALL receive `VITE_API_URL` as a build-time argument set to the in-cluster DNS name of the backend service (`http://backend.inventory.svc.cluster.local:8000`); the compiled static assets SHALL embed this value so that API requests resolve within the cluster.
3. THE Cluster SHALL expose the Frontend_Pod on a NodePort Service with `port: 80` and `targetPort: 80`, making the application reachable at `http://<NODE_IP>:80`.
4. WHEN a browser sends `GET /api/*`, THE Frontend_Pod's embedded Nginx SHALL proxy the request to the `backend` ClusterIP Service on port 8000, stripping the `/api` prefix.
5. THE Frontend_Pod SHALL use zero PVCs, as it serves only statically compiled files.
6. WHEN the Frontend_Pod's Nginx returns HTTP 200 to a readiness probe at path `/`, THE Cluster SHALL mark the Frontend_Pod as ready.

---

### Requirement 6: Secret Bootstrapping

**User Story:** As a cluster operator, I want all sensitive credentials stored in a Kubernetes Secret, so that secrets are never embedded in Manifest files or committed to source control.

#### Acceptance Criteria

1. THE Runbook SHALL document the exact `kubectl create secret generic inventory-secrets` command, listing all five required keys: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`, and `REDIS_URL`, to bootstrap the Secret in the `inventory` namespace on initial cluster setup.
2. IF the `inventory-secrets` Secret does not exist in the `inventory` namespace, THEN THE Backend_Pod and DB_Pod SHALL fail to start with a `CreateContainerConfigError` visible in `kubectl describe pod` output.
3. THE Manifest files SHALL contain no plaintext credentials; all credential references SHALL use `secretKeyRef` pointing to `inventory-secrets` for each of the five required keys.
4. THE Runbook SHALL specify that the Secret is created once manually during initial cluster setup; to rotate a secret, the operator SHALL delete the existing Secret and re-run the bootstrap command with the updated values, then restart the affected pods.

---

### Requirement 7: init.sql ConfigMap

**User Story:** As a cluster operator, I want the existing `init.sql` script mounted into the DB_Pod via a ConfigMap, so that the database schema and seed data are initialised on first startup without modifying the existing script.

#### Acceptance Criteria

1. THE Manifest SHALL define a ConfigMap named `postgres-init-sql` in the `inventory` namespace with a data key named `init.sql`, containing the full verbatim contents of `db_init/init.sql`.
2. WHEN the ConfigMap is updated and reapplied while the PostgreSQL data directory at `/var/lib/postgresql/data/PG_VERSION` already exists, THE DB_Pod SHALL not re-execute `init.sql`, preserving the idempotency guarantee of the PostgreSQL `docker-entrypoint-initdb.d` mechanism.
3. THE `postgres-init-sql` ConfigMap SHALL be volume-mounted into the DB_Pod at `/docker-entrypoint-initdb.d/init.sql` using a `subPath` mount targeting the `init.sql` key.
4. THE `init.sql` script SHALL not be modified as part of this migration; the ConfigMap SHALL reference the script contents verbatim.

---

### Requirement 8: Phase 1 — Local Manifest Validation with k3d

**User Story:** As a developer, I want to validate all Kubernetes manifests against a local k3d cluster before provisioning any cloud infrastructure, so that manifest errors are caught early at zero cloud cost.

#### Acceptance Criteria

1. THE Runbook SHALL document the exact commands to create a k3d cluster, apply all Manifests, verify that all four pods reach `Running` status, and tear down the cluster when validation is complete.
2. WHEN all Manifests are applied to the k3d cluster, THE Cluster SHALL bring all four pods (`inventory-backend`, `inventory-frontend`, `inventory-db`, `inventory-redis`) to `Running` status within 120 seconds.
3. WHILE the k3d cluster is running and all four pods are in `Running` status, THE Frontend_Pod SHALL return HTTP 200 when accessed at `http://localhost:80` (or the port-forwarded equivalent), confirming end-to-end connectivity.
4. THE Manifests used for Phase 1 SHALL use `x86_64` image variants (not ARM64), as k3d runs on the local x86_64 machine.
5. THE Runbook SHALL document the known gap: ARM64 images cannot be validated locally; Phase 2 is where ARM64 correctness is first confirmed.
6. IF any of the four pods do not reach `Running` status within 120 seconds, THE Runbook SHALL document the triage commands to execute: `kubectl describe pod <name> -n inventory`, `kubectl logs <name> -n inventory`, and `kubectl get events -n inventory --sort-by=.lastTimestamp`.

---

### Requirement 9: Phase 2 — OCI Infrastructure Provisioning with Terraform

**User Story:** As an infrastructure engineer, I want Terraform to provision all required OCI resources, so that the production environment is reproducible and version-controlled.

#### Acceptance Criteria

1. THE Terraform configuration SHALL provision a VCN with CIDR `10.0.0.0/16` and a public subnet with CIDR `10.0.1.0/24`, configured via a required input variable `region`.
2. THE Terraform configuration SHALL provision a VM instance of shape `VM.Standard.A1.Flex` with 2 OCPUs and 12 GB RAM, using an OS image specified via a required input variable `instance_image_ocid` (must be ARM64-compatible).
3. THE Terraform configuration SHALL configure OCI VCN Security List ingress rules to allow TCP traffic on port 22 (SSH) and port 80 (HTTP/NodePort) from `0.0.0.0/0`, and port 6443 (k3s API) restricted to the CIDR specified via a required input variable `operator_cidr`.
4. WHERE the operator sets the `reserve_public_ip` input variable to `true`, THE Terraform configuration SHALL attach a reserved public IP to the VM instance so the IP persists across VM reboots.
5. THE Runbook SHALL document the exact `iptables` commands to open ports 80 and 6443 on the OCI VM's OS firewall, as a complement to the Terraform-managed VCN Security List.
6. THE Terraform configuration SHALL output the VM's public IP address as `vm_public_ip` so it can be used in subsequent deployment steps.
7. THE Runbook SHALL document the k3s single-node installation command (pinned to a specific version using the `INSTALL_K3S_VERSION` environment variable, with `--write-kubeconfig-mode 644`) to be run on the provisioned VM after Terraform completes.
8. WHEN Terraform is applied a second time with no variable changes, THE Terraform configuration SHALL produce a plan with zero additions, zero changes, and zero destructions.

---

### Requirement 10: Phase 2 — ARM64 Image Build and Push

**User Story:** As a developer, I want to build and push linux/arm64 container images to ghcr.io, so that the OCI k3s cluster can pull the correct architecture images.

#### Acceptance Criteria

1. WHEN building images for OCI deployment, THE Developer SHALL use `docker buildx build --platform linux/arm64` for both the backend and frontend images.
2. WHEN the build completes, THE resulting images SHALL be tagged as `ghcr.io/VikramBabariya/inventory-backend:<git_SHA>` and `ghcr.io/VikramBabariya/inventory-frontend:<git_SHA>`, where `<git_SHA>` is the output of `git rev-parse HEAD`.
3. THE Runbook SHALL document the exact `docker buildx` and `docker push` commands for both images, including the `--platform linux/arm64` flag.
4. THE Runbook SHALL state that ARM64 image correctness is deferred to Phase 3, when the images are first pulled and run on the OCI k3s cluster.
5. WHEN the images are pushed to ghcr.io, THE repository visibility SHALL be set to public, or the k3s node SHALL be pre-authenticated with ghcr.io using a Personal Access Token with `read:packages` scope.
6. THE Runbook SHALL document the prerequisite step of authenticating to ghcr.io with `docker login ghcr.io` using a Personal Access Token before executing any `docker push` command.
7. THE Runbook SHALL document the `docker push` commands for both images, confirming that the push succeeded by verifying the digest returned by the registry.

---

### Requirement 11: Phase 3 — Deploy to OCI k3s

**User Story:** As a cluster operator, I want to apply the validated Kubernetes manifests to the OCI k3s cluster, so that the inventory system is reachable on the OCI public IP.

#### Acceptance Criteria

1. THE Runbook SHALL provide a pre-flight checklist that requires the operator to confirm all of the following before applying manifests: (a) `docker manifest inspect ghcr.io/VikramBabariya/inventory-backend:<git_SHA>` returns an ARM64 manifest, (b) `docker manifest inspect ghcr.io/VikramBabariya/inventory-frontend:<git_SHA>` returns an ARM64 manifest, (c) `kubectl get secret inventory-secrets -n inventory` returns all five expected keys, and (d) `VITE_API_URL` in the frontend image build was set to the OCI public IP.
2. THE only required adjustments when applying Phase 1 Manifests to the OCI k3s cluster SHALL be: updating both image tags to the ARM64-built `<git_SHA>` values, and confirming `VITE_API_URL` was set to the OCI public IP at image build time.
3. WHEN all Manifests are applied, THE Cluster SHALL bring all four pods (`inventory-backend`, `inventory-frontend`, `inventory-db`, `inventory-redis`) to `Running` status within 180 seconds; IF any pod does not reach `Running` within this window, the operator SHALL consult the triage commands documented in the k8s-operations runbook.
4. WHEN all four pods are in `Running` status, THE Frontend_Pod SHALL return HTTP 200 with a non-empty HTML response body when accessed at `http://<OCI_PUBLIC_IP>:80`.
5. WHEN `curl http://<OCI_PUBLIC_IP>:80/api/health` is executed, THE Backend_Pod SHALL return HTTP 200 with `{"status": "healthy", "database": "connected", "cache": "connected"}`.

---

### Requirement 12: Documentation — Archive AWS Docs

**User Story:** As a developer onboarding to the project, I want historical AWS-specific documentation archived rather than deleted, so that the deployment history is preserved and the current docs reflect only the Kubernetes deployment model.

#### Acceptance Criteria

1. WHEN the migration is executed, THE following files SHALL be moved to `docs/archive/`: `docs/runbooks/aws-manual-deployment.md`, `docs/architecture/lld/network-topology.md`, and `docs/architecture/lld/images/vpc-network-topology.png`.
2. THE `docs/archive/README.md` SHALL be created as a new file containing: (a) a statement that this directory contains documentation for the previous deployment era (AWS EC2 with Docker Compose on a VM), (b) the date range it was active, and (c) a note that these files are preserved for historical reference and no longer reflect the current deployment model.
3. WHEN a file is moved to `docs/archive/`, THE file contents SHALL remain unchanged; only the file path changes.

---

### Requirement 13: Documentation — Architecture Decision Records

**User Story:** As a developer reviewing the project, I want each deployment decision captured as an ADR, so that the rationale for each choice is recorded and future changes are informed by context.

#### Acceptance Criteria

1. THE migration SHALL produce exactly six ADR files numbered 010 through 015, placed in `docs/decisions/`, one ADR per decision from the Decisions Already Made section of the project brief.
2. EACH ADR SHALL contain the following sections with non-empty content: **Status** (value: "Accepted"), **Context** (describing the problem and the phase/deployment context that drove the decision), **Decision** (stating what was decided), and **Consequences** (listing at least one positive consequence and at least one negative consequence or trade-off).
3. THE six ADRs SHALL map to decisions as follows: ADR 010 → NodePort + embedded Nginx ingress strategy; ADR 011 → k3s local-path PVC persistence with node affinity; ADR 012 → manual `kubectl` secret bootstrapping; ADR 013 → OCI dual-firewall networking (VCN Security List + OS iptables); ADR 014 → `init.sql` ConfigMap mounting; ADR 015 → unset `storageClassName` for portability.

---

### Requirement 14: Documentation — Runbooks

**User Story:** As an operator deploying the system, I want step-by-step runbooks for OCI setup, Kubernetes operations, and local k3d development, so that each deployment phase can be executed without tribal knowledge.

#### Acceptance Criteria

1. THE migration SHALL produce a runbook at `docs/runbooks/oci-terraform-setup.md` covering: OCI account prerequisites (tenancy OCID, user OCID, API key fingerprint, private key path), Terraform variable configuration, `terraform init` / `plan` / `apply` steps, k3s installation via the official install script (`https://get.k3s.io`) pinned to a specific version, and `iptables` commands to open TCP ports 22, 80, and 6443 on the OCI VM's OS firewall.
2. THE migration SHALL produce a runbook at `docs/runbooks/k8s-operations.md` covering: secret bootstrapping commands, `kubectl apply` workflow, pod status verification, log access, and at minimum the following debugging commands: `kubectl exec -it <pod> -n inventory -- <shell>`, `kubectl get endpoints -n inventory`, and `kubectl get events -n inventory --sort-by=.lastTimestamp`.
3. THE migration SHALL produce a runbook at `docs/runbooks/local-k3d-dev.md` covering: k3d cluster creation, local image loading, manifest application, port-forwarding to expose the frontend at `localhost:8080` (verified by `curl http://localhost:8080` returning HTTP 200), and cluster teardown.
4. EACH runbook SHALL format every command block with a preceding `#` comment line explaining the purpose of the command.
5. THE `docs/cheatsheet.md` SHALL be updated to include a Kubernetes section containing at minimum the following `kubectl` operations: apply manifests, get pod status, view logs, exec into a pod, describe a resource, get events, delete a pod to force restart, and port-forward a service.

---

### Requirement 15: Documentation — Updated Architecture Docs

**User Story:** As a developer reading the project documentation, I want the HLD, environments concept, and security docs updated to reflect the Kubernetes deployment model, so that the documentation accurately describes the current system.

#### Acceptance Criteria

1. THE `docs/architecture/hld/system-architecture.md` SHALL be updated to include a Kubernetes network topology diagram showing: the `inventory` namespace containing the `inventory-backend` pod (port 8000), `inventory-frontend` pod (port 80), `inventory-db` pod (port 5432), and `inventory-redis` pod (port 6379); the four corresponding Services (`backend` ClusterIP, `postgres` ClusterIP, `redis` ClusterIP, and `frontend` NodePort on port 80); and the external access path from the internet to the NodePort Service.
2. THE `docs/architecture/concepts/environments.md` SHALL be updated to add a third environment column "Kubernetes/OCI" alongside the existing "Dev (Docker Compose)" and "Prod (Docker Compose)" columns, covering all existing rows: runtime, image source, database persistence, secret management, network exposure, and hot-reload behaviour.
3. THE `docs/security.md` SHALL be updated to document: (a) the Kubernetes secrets model — manual bootstrap via `kubectl create secret`, `secretKeyRef` references in manifests, no credentials in committed files; and (b) the dual OCI firewall layers — the VCN Security List (managed by Terraform, opening ports 22, 80, and 6443) and the OS iptables rules (applied manually on the VM, opening ports 80 and 6443).

---

### Requirement 16: Future Tasks Backlog

**User Story:** As a project planner, I want all out-of-scope items formally recorded, so that nothing is lost and prioritisation can happen in future phases.

#### Acceptance Criteria

1. THE migration SHALL produce a file at `docs/backlog.md` listing all out-of-scope future tasks under three priority tiers — High, Medium, and Low — covering: CI/CD (GitHub Actions), TLS/HTTPS (cert-manager + Let's Encrypt), domain attachment, Alembic migrations, Traefik ingress, CORS hardening, resource tuning, vulnerability scanning, Prometheus + Grafana monitoring, Horizontal Pod Autoscaler, and multi-node k3s.
2. THE `docs/backlog.md` file SHALL include for each task: a one-sentence description of what it involves and a one-sentence explanation of why it is deferred (scope, dependency, or complexity).
3. THE `docs/backlog.md` file SHALL contain entries for all eleven tasks listed in criterion 1; a tester can verify completeness by confirming all eleven task names are present.

---

## Future Tasks Backlog (Out of Scope for This Phase)

### High Priority

| Task | Description | Reason Deferred |
|---|---|---|
| CI/CD (GitHub Actions) | Automate ARM64 image build, push to ghcr.io on merge to main, and `kubectl apply` via self-hosted runner on the OCI VM. | Requires kubeconfig access strategy; manual deploy is sufficient for Phase 1–3. |
| TLS/HTTPS | cert-manager + Let's Encrypt once a domain is attached; switch ingress from NodePort to Traefik. | No domain in this phase; raw public IP access is sufficient. |
| Domain | Attach a domain to the OCI reserved public IP (free on Always Free Tier). | Out of scope for initial Kubernetes migration. |

### Medium Priority

| Task | Description | Reason Deferred |
|---|---|---|
| Alembic migrations | Replace `init.sql` with proper schema migrations, run as a Kubernetes Job before the backend rolls out. | Schema is stable; `init.sql` approach is equivalent in behaviour. |
| Traefik ingress | Migrate from NodePort once domain + TLS are in place. | Requires domain and TLS; not relevant without HTTPS. |
| CORS hardening | Update FastAPI `allow_origins` from `"*"` to the actual frontend origin once a domain is set. | No domain in this phase. |
| Resource tuning | Adjust pod resource requests/limits based on observed usage on the OCI VM. | Requires baseline metrics from running the system. |

### Low Priority

| Task | Description | Reason Deferred |
|---|---|---|
| Vulnerability scanning | Trivy or Snyk image scanning in the CI/CD pipeline. | Depends on CI/CD being in place first. |
| Monitoring | Prometheus + Grafana; only worthwhile once the app has real traffic. | Out of scope for this phase per explicit constraint. |
| Horizontal Pod Autoscaler | Once metrics-server is confirmed active on k3s. | Single-node cluster; HPA is not meaningful yet. |
| Multi-node k3s | Add k3s agent nodes if workload grows. | Single-node Always Free Tier is sufficient for current load. |

---

## Production Database Storage Strategy (Future Decision Required)

The current setup runs PostgreSQL as a single-replica Deployment with a `local-path` PVC, suitable for the single-node OCI Always Free Tier. This approach does **not** survive node loss and is not appropriate for production workloads with real data. Before scaling to a multi-node cluster or hardening for production, one of the following strategies must be chosen.

### Option 1 — StatefulSet + Network-Attached Storage (Recommended for self-hosted)

Migrate the PostgreSQL Deployment to a `StatefulSet` and back the PVC with a network-attached block storage driver (CSI). The PVC is no longer tied to a specific node's disk, so the Pod can reschedule to any node and remount its data.

| Cloud | Storage Class / CSI Driver | Notes |
|---|---|---|
| OCI | `oci-bv` (Block Volume CSI) | OCI Block Volumes support `ReadWriteOnce`; persistent across VM reboots |
| AWS | `aws-ebs-csi-driver` (gp3) | Per-AZ; use topology-aware scheduling |
| GCP | `pd-csi-driver` (pd-ssd) | Regional PDs available for cross-zone resilience |
| Azure | `disk.csi.azure.com` | Azure Managed Disks; or Azure Files for `ReadWriteMany` |
| Self-hosted | Longhorn or Rook-Ceph | Longhorn is simpler; Ceph is more feature-rich |

**Node affinity becomes unnecessary** with network-attached storage — the volume follows the Pod.

**Deferred because**: Current single-node OCI setup uses `local-path` provisioner which is sufficient. OCI Block Volume CSI requires additional Terraform resources and OCI IAM policies not in scope for this phase.

### Option 2 — PostgreSQL Operator (Recommended for production HA)

Replace the hand-authored Deployment/StatefulSet with a Kubernetes Operator that manages the full PostgreSQL lifecycle: primary/replica streaming replication, automated failover, scheduled backups to object storage, and point-in-time recovery.

| Operator | Notes |
|---|---|
| **CloudNativePG** | Most actively maintained; CNCF sandbox project; simple CRD-based API |
| **Zalando Postgres Operator** | Battle-tested at Zalando scale; supports Patroni-based HA |
| **CrunchyData PGO** | Enterprise-grade; includes pgBackRest for S3 backups |

Example CloudNativePG cluster CRD:
```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: inventory-db
  namespace: inventory
spec:
  instances: 3
  storage:
    size: 10Gi
  backup:
    barmanObjectStore:
      destinationPath: s3://my-bucket/inventory-db
```

**Deferred because**: Requires multi-node cluster, network storage, and a backup target (S3/OCI Object Storage). Operator CRDs add significant complexity beyond the scope of the initial Kubernetes migration.

### Option 3 — Managed Database Service (Recommended for teams wanting minimal ops)

Remove PostgreSQL from Kubernetes entirely and use a cloud-managed database. The application Pod receives a `DATABASE_URL` secret pointing to the managed endpoint. Storage, failover, patching, and backups are fully outsourced.

| Provider | Service | Notes |
|---|---|---|
| OCI | Autonomous Database or DB System | Free tier available; supports PostgreSQL-compatible endpoint |
| AWS | RDS PostgreSQL / Aurora Serverless v2 | Aurora offers serverless scaling; RDS is simpler |
| GCP | Cloud SQL for PostgreSQL | Easy private IP connection via Cloud SQL Auth Proxy |
| Azure | Azure Database for PostgreSQL Flexible Server | Zone-redundant HA available |
| Any | Supabase, Neon, Railway | Fully managed; suitable for small workloads |

**Deferred because**: Moves infrastructure outside the Kubernetes cluster, which contradicts the goal of a fully self-contained k8s deployment on OCI Always Free Tier. Introduces cloud provider lock-in and cost.

### Recommended Migration Path

```
Current (Phase 1–3)       →  Next step               →  Production-ready
──────────────────────────────────────────────────────────────────────────
Deployment + local-path      StatefulSet + OCI Block      CloudNativePG operator
single-node, no HA           Volume CSI, single-node      multi-node, HA, backups
```

**Decision criterion**: Choose Option 3 (managed DB) if operational simplicity is the priority. Choose Option 2 (operator) if full Kubernetes-native control and portability matter. Option 1 (StatefulSet + network storage) is the minimum viable step before any of the above.
