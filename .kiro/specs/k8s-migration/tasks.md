# Implementation Plan: k8s-migration

## Overview

Migrate the inventory system from Docker Compose to Kubernetes across three phases: local manifest validation on k3d (Phase 1), OCI infrastructure provisioning and ARM64 image builds (Phase 2), and production deployment to the OCI k3s cluster (Phase 3). A documentation phase runs in parallel, covering archive, ADRs, runbooks, and updated architecture docs.

All implementation is ordered so that each step produces artefacts consumed by the next. No task produces orphaned code or files.

---

## Tasks

### Phase 1 — Local Kubernetes Manifests

- [x] 1. Create Kubernetes namespace manifest
  - Create `k8s/namespace.yaml` defining the `inventory` Namespace resource
  - Set `apiVersion: v1`, `kind: Namespace`, `metadata.name: inventory`
  - _Requirements: 1.1_

- [x] 2. Create PostgreSQL ConfigMap manifest
  - Create `k8s/configmap-postgres-init.yaml` defining ConfigMap `postgres-init-sql` in namespace `inventory`
  - Set `data["init.sql"]` to the verbatim byte-for-byte content of `db_init/init.sql` — no reformatting, no trimming
  - Use `|` (literal block scalar) to preserve the SQL exactly
  - _Requirements: 7.1, 7.4_

- [x] 3. Create PostgreSQL PVC manifest
  - Create `k8s/pvc-postgres.yaml` defining PersistentVolumeClaim `postgres-pvc` in namespace `inventory`
  - Set `spec.accessModes: [ReadWriteOnce]`, `spec.resources.requests.storage: 1Gi`
  - **Do NOT set `spec.storageClassName`** — omit the field entirely so the manifest binds to the cluster default in both k3d and k3s
  - _Requirements: 2.1, 2.6_

- [x] 4. Create PostgreSQL Deployment manifest
  - Create `k8s/deployment-postgres.yaml` defining Deployment `inventory-db` in namespace `inventory`
  - Image: `postgres:15-alpine`, replicas: 1
  - Mount `postgres-pvc` at `/var/lib/postgresql/data`
  - Mount ConfigMap `postgres-init-sql` at `/docker-entrypoint-initdb.d/init.sql` using `subPath: init.sql`
  - Inject `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` from Secret `inventory-secrets` via `secretKeyRef`; **no `value` field for these keys**
  - Readiness probe: exec `pg_isready`, `initialDelaySeconds: 10`, `periodSeconds: 5`, `timeoutSeconds: 5`, `failureThreshold: 5`, `successThreshold: 1`
  - Add node affinity block (commented-out placeholder) for OCI `kubernetes.io/hostname` pinning; operator fills it in Phase 3
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.7, 2.9, 7.3_

- [x] 5. Create PostgreSQL Service manifest
  - Create `k8s/service-postgres.yaml` defining ClusterIP Service `postgres` in namespace `inventory`
  - `spec.ports: [{port: 5432, targetPort: 5432}]`, selector targets `inventory-db` pods
  - _Requirements: 2.8_

- [x] 6. Create Redis Deployment manifest
  - Create `k8s/deployment-redis.yaml` defining Deployment `inventory-redis` in namespace `inventory`
  - Image: `redis:alpine`, replicas: 1
  - No volume mounts — cache data is ephemeral
  - Readiness probe: exec `redis-cli ping`, `periodSeconds: 5`, `timeoutSeconds: 3`, `failureThreshold: 3`
  - _Requirements: 3.1, 3.3, 3.4_

- [x] 7. Create Redis Service manifest
  - Create `k8s/service-redis.yaml` defining ClusterIP Service `redis` in namespace `inventory`
  - `spec.ports: [{port: 6379, targetPort: 6379}]`, selector targets `inventory-redis` pods
  - _Requirements: 3.2_

- [x] 8. Create Backend Deployment manifest
  - Create `k8s/deployment-backend.yaml` defining Deployment `inventory-backend` in namespace `inventory`
  - Image: `ghcr.io/VikramBabariya/inventory-backend:<git_SHA>` (placeholder tag)
  - Inject `DATABASE_URL`, `REDIS_URL`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` from Secret `inventory-secrets` via `secretKeyRef`; **no `value` field for any of these**
  - Init container: `busybox` image, command polls `postgres:5432` TCP with 60-second timeout before exiting 0
    - Use: `until nc -z postgres 5432; do sleep 2; done`
  - Readiness probe: HTTP GET `/health` on port 8000, `initialDelaySeconds: 15`, `periodSeconds: 10`, `failureThreshold: 3`
  - Liveness probe: HTTP GET `/health` on port 8000, `initialDelaySeconds: 30`, `periodSeconds: 20`, `failureThreshold: 3`
  - No volume mounts
  - _Requirements: 4.1, 4.2, 4.3, 4.5, 4.6, 4.7_

- [x] 9. Create Backend Service manifest
  - Create `k8s/service-backend.yaml` defining ClusterIP Service `backend` in namespace `inventory`
  - `spec.ports: [{port: 8000, targetPort: 8000}]`, selector targets `inventory-backend` pods
  - _Requirements: 4.4_

- [x] 10. Create Frontend Deployment manifest
  - Create `k8s/deployment-frontend.yaml` defining Deployment `inventory-frontend` in namespace `inventory`
  - Image: `ghcr.io/VikramBabariya/inventory-frontend:<git_SHA>` (placeholder tag — Phase 1 uses x86_64 build)
  - No volume mounts — serves statically compiled files
  - Readiness probe: HTTP GET `/` on port 80
  - Document in a manifest comment: `VITE_API_URL` must be set at `docker buildx build` time; for Phase 1 use `http://backend.inventory.svc.cluster.local:8000`; for Phase 3 use `http://<OCI_PUBLIC_IP>:8000`
  - _Requirements: 5.1, 5.2, 5.5, 5.6_

- [x] 11. Create Frontend Service manifest
  - Create `k8s/service-frontend.yaml` defining NodePort Service `frontend` in namespace `inventory`
  - `spec.type: NodePort`, `spec.ports: [{port: 80, targetPort: 80}]`, selector targets `inventory-frontend` pods
  - _Requirements: 5.3_

- [x] 12. Write manifest property tests
  - Create `tests/test_k8s_manifests.py` using `pytest` + `PyYAML`
  - Add shared fixture: `load_all(filename)` reads and `yaml.safe_load_all` parses files from `k8s/`
  - Constant: `SECRET_KEYS = {"POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "DATABASE_URL", "REDIS_URL"}`

  - [x] 12.1 Write property test for all deployment probe field values
    - Parse `deployment-postgres.yaml`, `deployment-redis.yaml`, `deployment-backend.yaml`, `deployment-frontend.yaml`
    - Assert each probe's command/path, `initialDelaySeconds`, `periodSeconds`, `timeoutSeconds`, `failureThreshold`, `successThreshold` match the spec exactly (see Property 1 in design)
    - Tag comment: `# Feature: k8s-migration, Property 1: all deployment probe fields conform to specification`
    - _Requirements: 2.9, 3.3, 4.5, 4.6, 5.6_

  - [x] 12.2 Write property test for no plaintext credentials in any manifest
    - Walk every env var entry in every YAML file under `k8s/`
    - For any env entry whose `name` is in `SECRET_KEYS`, assert `valueFrom.secretKeyRef` is set and `value` field is absent
    - Tag comment: `# Feature: k8s-migration, Property 2: no plaintext credentials in any manifest`
    - _Requirements: 2.5, 4.2, 6.3_

  - [x] 12.3 Write property test for ConfigMap init.sql round-trip fidelity
    - Read `db_init/init.sql` as raw bytes
    - Parse `configmap-postgres-init.yaml`; extract `data["init.sql"]` as a string
    - Assert the string is byte-for-byte identical to the file contents
    - Tag comment: `# Feature: k8s-migration, Property 3: configmap init.sql round-trip fidelity`
    - _Requirements: 7.1, 7.4_

  - [x] 12.4 Write property test for all resources declaring the `inventory` namespace
    - Parse every YAML file in `k8s/`; skip Namespace kind itself
    - For each document of a namespaced Kind (Deployment, Service, PersistentVolumeClaim, ConfigMap), assert `metadata.namespace == "inventory"`
    - Tag comment: `# Feature: k8s-migration, Property 4: all kubernetes resources declare the inventory namespace`
    - _Requirements: 1.1, 1.4_

  - [x] 12.5 Write property test for PVC storageClassName absence
    - Parse `pvc-postgres.yaml`
    - Assert `spec` dict does not contain key `storageClassName`, OR the key is present with value `None`
    - Tag comment: `# Feature: k8s-migration, Property 6: pvc storageClassName is absent`
    - _Requirements: 2.6_

  - [x] 12.6 Write property-based test for Nginx API prefix stripping (hypothesis)
    - Import `hypothesis` and `hypothesis.strategies`
    - Define strategy `path_segment = st.from_regex(r"[a-zA-Z0-9/_\-\.]{1,64}", fullmatch=True)`
    - Parse `frontend/nginx.conf` as text; extract the `location /api/` block's `proxy_pass` directive
    - `@given(path_segment)` `@settings(max_examples=100)`: assert that the configured `proxy_pass` URL strips the `/api` prefix exactly — i.e., `proxy_pass http://backend:8000/` + segment, not `http://backend:8000/api/` + segment
    - Add deterministic examples: `/api/products`, `/api/products/1/movements`, `/api/health`
    - Assert that non-API paths (`/`, `/assets/main.js`) are NOT covered by the `/api/` block
    - Tag comment: `# Feature: k8s-migration, Property 5: nginx api prefix stripping`
    - _Requirements: 5.4_

- [x] 13. Validate manifests on local k3d cluster
  - This task is the Phase 1 end-to-end validation. All manifests from tasks 1–11 must exist before starting.

  - [x] 13.1 Create local k3d cluster
    - Run: `k3d cluster create inventory-local --port "8080:80@loadbalancer"`
    - Verify cluster is ready: `kubectl cluster-info`
    - _Requirements: 8.1_

  - [x] 13.2 Build local x86_64 images
    - Build backend: `docker build -t inventory-backend:local ./backend`
    - Build frontend with local API URL: `docker build -t inventory-frontend:local ./frontend`
    - These are x86_64 images for local validation only — NOT the ARM64 images used in Phase 3
    - _Requirements: 8.4_

  - [x] 13.3 Load local images into k3d
    - Run: `k3d image import inventory-backend:local inventory-frontend:local -c inventory-local`
    - This avoids k3d trying to pull from ghcr.io (which would fail — placeholder tags don't exist yet)
    - Update image fields in `k8s/deployment-backend.yaml` and `k8s/deployment-frontend.yaml` temporarily to use `inventory-backend:local` and `inventory-frontend:local` with `imagePullPolicy: Never`
    - _Requirements: 8.4_

  - [x] 13.4 Bootstrap test secrets on k3d cluster
    - Run the secret bootstrap with test/dummy values (NOT production credentials):
      ```
      kubectl create secret generic inventory-secrets \
        --from-literal=POSTGRES_USER=testuser \
        --from-literal=POSTGRES_PASSWORD=testpassword \
        --from-literal=POSTGRES_DB=inventory \
        --from-literal=DATABASE_URL=postgresql://testuser:testpassword@postgres:5432/inventory \
        --from-literal=REDIS_URL=redis://redis:6379 \
        -n inventory
      ```
    - _Requirements: 6.1, 8.1_

  - [x] 13.5 Apply all manifests to k3d cluster
    - Apply in dependency order:
      ```
      kubectl apply -f k8s/namespace.yaml
      kubectl apply -f k8s/configmap-postgres-init.yaml
      kubectl apply -f k8s/pvc-postgres.yaml
      kubectl apply -f k8s/deployment-postgres.yaml
      kubectl apply -f k8s/service-postgres.yaml
      kubectl apply -f k8s/deployment-redis.yaml
      kubectl apply -f k8s/service-redis.yaml
      kubectl apply -f k8s/deployment-backend.yaml
      kubectl apply -f k8s/service-backend.yaml
      kubectl apply -f k8s/deployment-frontend.yaml
      kubectl apply -f k8s/service-frontend.yaml
      ```
    - _Requirements: 8.1, 8.2_

  - [x] 13.6 Wait for all pods to reach Running status
    - Run: `kubectl wait --for=condition=ready pod --all -n inventory --timeout=120s`
    - If timeout is hit, run triage commands:
      - `kubectl get pods -n inventory`
      - `kubectl describe pod <failing-pod> -n inventory`
      - `kubectl logs <failing-pod> -n inventory`
      - `kubectl get events -n inventory --sort-by=.lastTimestamp`
    - _Requirements: 8.2_

  - [x] 13.7 End-to-end smoke test
    - Test frontend is reachable: `curl -I http://localhost:8080` — expect HTTP 200
    - Test API health through Nginx proxy: `curl http://localhost:8080/api/health` — expect `{"status":"healthy","database":"connected","cache":"connected"}`
    - Test product list (exercises DB + Redis + backend): `curl http://localhost:8080/api/products`
    - _Requirements: 8.3_

  - [x] 13.8 Run manifest property tests
    - Run: `pytest tests/test_k8s_manifests.py -v`
    - All tests must pass before Phase 1 is considered complete
    - _Requirements: 8.2_

  - [x] 13.9 Restore manifest image tags and teardown k3d cluster
    - Revert `k8s/deployment-backend.yaml` and `k8s/deployment-frontend.yaml` back to placeholder ghcr.io tags (`ghcr.io/VikramBabariya/inventory-backend:<git_SHA>`) and remove `imagePullPolicy: Never`
    - Tear down the k3d cluster: `k3d cluster delete inventory-local`
    - _Requirements: 8.1_

---

### Phase 2 — OCI Infrastructure and ARM64 Images

- [ ] 14. Create Terraform variables file
  - Create `terraform/variables.tf` declaring five input variables:
    - `region` (string, required) — OCI region identifier
    - `instance_image_ocid` (string, required) — ARM64-compatible OS image OCID
    - `operator_cidr` (string, required) — CIDR allowed to reach k3s API on port 6443
    - `reserve_public_ip` (bool, default false) — whether to attach a reserved (persistent) public IP
    - `ssh_public_key` (string, required) — public key to inject into the VM
  - Each variable must include a `description` field
  - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [ ] 15. Create Terraform main configuration
  - Create `terraform/main.tf` with:
    - OCI provider block (region from variable)
    - VCN resource with CIDR `10.0.0.0/16`
    - Public subnet resource with CIDR `10.0.1.0/24`
    - `oci_core_instance` resource: shape `VM.Standard.A1.Flex`, 2 OCPUs, 12 GB RAM, image from `instance_image_ocid` variable, SSH key from `ssh_public_key` variable, placed in the public subnet
    - Conditional reserved public IP: `count = var.reserve_public_ip ? 1 : 0`
    - Public IP association resource (also conditional)
  - _Requirements: 9.1, 9.2, 9.4_

- [ ] 16. Create Terraform security configuration
  - Create `terraform/security.tf` with OCI VCN Security List ingress rules:
    - TCP port 22 from `0.0.0.0/0` (SSH)
    - TCP port 80 from `0.0.0.0/0` (HTTP / NodePort)
    - TCP port 6443 from `var.operator_cidr` (k3s API)
  - Egress: allow all traffic (stateless egress)
  - Associate the Security List with the subnet defined in `main.tf`
  - _Requirements: 9.3_

- [ ] 17. Create Terraform outputs file
  - Create `terraform/outputs.tf` with a single output `vm_public_ip`
  - Value: the VM instance's public IP; if `reserve_public_ip` is true, use the reserved IP resource; else use `oci_core_instance.public_ip`
  - _Requirements: 9.6_

- [ ] 18. Create Terraform example variables file
  - Create `terraform/terraform.tfvars.example` with all five variable stubs
  - Include inline comments on each line explaining the expected value format
  - Example stub format: `region = "# e.g. uk-london-1"`
  - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [ ] 19. Checkpoint — Terraform configuration complete
  - Run `terraform validate` inside `terraform/` and confirm zero errors
  - Run `terraform plan` (using stub/mock values or `-var` overrides) and confirm the plan is parseable
  - Ask the user if any infrastructure adjustments are needed before ARM64 image tasks.

---

### Phase 3 — Deploy to OCI k3s

- [ ] 20. Update deployment manifests with OCI node affinity
  - Edit `k8s/deployment-postgres.yaml`: uncomment or activate the node affinity block added in task 4
  - Set `requiredDuringSchedulingIgnoredDuringExecution.nodeSelectorTerms[0].matchExpressions` to match `kubernetes.io/hostname` = actual OCI VM hostname (document as a `TODO:` placeholder — operator fills in after `kubectl get nodes`)
  - _Requirements: 2.7_

- [ ] 21. Bootstrap inventory-secrets on the OCI k3s cluster
  - Document (in code comments within a helper script `scripts/bootstrap-secrets.sh`) the exact `kubectl create secret generic inventory-secrets` command with all five keys: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`, `REDIS_URL`
  - The script must validate that `kubectl config current-context` points to the OCI cluster before running
  - The script must check whether the secret already exists (`kubectl get secret inventory-secrets -n inventory`) and skip creation if present, printing a warning
  - _Requirements: 6.1, 6.3_

- [ ] 22. Apply manifests to OCI k3s and verify pod readiness
  - Document (as executable comments in `scripts/deploy-oci.sh`) the full apply sequence:
    1. Pre-flight: `docker manifest inspect` for both ARM64 images
    2. Pre-flight: `kubectl get secret inventory-secrets -n inventory` — all five keys present
    3. `kubectl apply -f k8s/` in dependency order
    4. `kubectl wait --for=condition=ready pod -l app=inventory-db -n inventory --timeout=180s` (repeat for each of the four apps)
  - Include the triage commands to run if any pod does not reach `Running` within 180s:
    - `kubectl describe pod <name> -n inventory`
    - `kubectl logs <name> -n inventory`
    - `kubectl get events -n inventory --sort-by=.lastTimestamp`
  - _Requirements: 11.1, 11.2, 11.3_

- [ ] 23. Checkpoint — OCI deployment complete
  - Ensure all four pods are `Running`: `kubectl get pods -n inventory`
  - Verify public IP access: `curl -I http://<OCI_PUBLIC_IP>:80` returns HTTP 200
  - Verify API health: `curl http://<OCI_PUBLIC_IP>:80/api/health` returns `{"status":"healthy","database":"connected","cache":"connected"}`
  - Ask the user if any deployment issues need resolution before proceeding to documentation tasks.

---

### Phase 4 — Documentation

- [ ] 24. Archive AWS-era documentation
  - Move `docs/runbooks/aws-manual-deployment.md` → `docs/archive/aws-manual-deployment.md`
  - Move `docs/architecture/lld/network-topology.md` → `docs/archive/network-topology.md`
  - Move `docs/architecture/lld/images/vpc-network-topology.png` → `docs/archive/vpc-network-topology.png`
  - File contents must remain unchanged — only paths change
  - _Requirements: 12.1, 12.3_

- [ ] 25. Create docs/archive/README.md
  - Create `docs/archive/README.md` with:
    - A statement that this directory contains documentation for the previous deployment era (AWS EC2 with Docker Compose on a VM)
    - The date range the AWS deployment was active
    - A note that these files are preserved for historical reference and no longer reflect the current deployment model
  - _Requirements: 12.2_

- [ ] 26. Create ADR 010 — NodePort + embedded Nginx ingress strategy
  - Create `docs/decisions/010-nodeport-nginx-ingress.md`
  - Sections: **Status** (Accepted), **Context**, **Decision**, **Consequences** (≥1 positive, ≥1 negative)
  - Context: single-node k3s on OCI Always Free Tier; no domain, no TLS, no Ingress controller needed in this phase; NodePort exposes the frontend on port 80 directly on the VM IP
  - _Requirements: 13.1, 13.2, 13.3_

- [ ] 27. Create ADR 011 — k3s local-path PVC persistence with node affinity
  - Create `docs/decisions/011-pvc-persistence-node-affinity.md`
  - Sections: **Status** (Accepted), **Context**, **Decision**, **Consequences**
  - Context: single-node cluster means PVC data lives on the node's local disk; node affinity ensures the DB pod always returns to the same node after VM reboots so it can bind its PVC
  - _Requirements: 13.1, 13.2, 13.3_

- [ ] 28. Create ADR 012 — manual kubectl secret bootstrapping
  - Create `docs/decisions/012-manual-secret-bootstrap.md`
  - Sections: **Status** (Accepted), **Context**, **Decision**, **Consequences**
  - Context: no CI/CD in this phase; storing secrets in manifests or `.env` committed to git is a security violation; `kubectl create secret generic` keeps credentials out of source control
  - _Requirements: 13.1, 13.2, 13.3_

- [ ] 29. Create ADR 013 — OCI dual-firewall networking
  - Create `docs/decisions/013-oci-dual-firewall.md`
  - Sections: **Status** (Accepted), **Context**, **Decision**, **Consequences**
  - Context: OCI has two independent firewall layers — VCN Security List (cloud-level, Terraform-managed) and OS iptables (VM-level, applied manually); both must allow a port for traffic to reach a pod
  - _Requirements: 13.1, 13.2, 13.3_

- [ ] 30. Create ADR 014 — init.sql ConfigMap mounting
  - Create `docs/decisions/014-init-sql-configmap.md`
  - Sections: **Status** (Accepted), **Context**, **Decision**, **Consequences**
  - Context: PostgreSQL's `docker-entrypoint-initdb.d` mechanism runs scripts on first boot only; mounting via ConfigMap subPath avoids modifying the existing `init.sql` script and keeps schema initialisation declarative
  - _Requirements: 13.1, 13.2, 13.3_

- [ ] 31. Create ADR 015 — unset storageClassName for portability
  - Create `docs/decisions/015-unset-storageclassname.md`
  - Sections: **Status** (Accepted), **Context**, **Decision**, **Consequences**
  - Context: k3d uses `standard` storage class; k3s uses `local-path`; omitting `storageClassName` causes the PVC to bind to the cluster default, making the manifest portable across both environments without modification
  - _Requirements: 13.1, 13.2, 13.3_

- [ ] 32. Create OCI Terraform setup runbook
  - Create `docs/runbooks/oci-terraform-setup.md`
  - Must cover (each command block preceded by a `#` comment line):
    - OCI account prerequisites: tenancy OCID, user OCID, API key fingerprint, private key path
    - Terraform variable configuration (`terraform.tfvars` setup from example)
    - `terraform init`, `terraform plan`, `terraform apply` steps
    - k3s installation command: `curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION=<pinned> sh -s - --write-kubeconfig-mode 644`
    - iptables commands to open TCP 22, 80, and 6443 on the OCI VM's OS firewall
  - _Requirements: 9.5, 9.7, 14.1_

- [ ] 33. Create Kubernetes operations runbook
  - Create `docs/runbooks/k8s-operations.md`
  - Must cover (each command block preceded by a `#` comment line):
    - Secret bootstrapping: the exact `kubectl create secret generic inventory-secrets` command with all five keys
    - Secret rotation: delete + re-create + restart pods
    - `kubectl apply -f k8s/` workflow
    - Pod status verification: `kubectl get pods -n inventory`
    - Log access: `kubectl logs <pod> -n inventory`
    - Debugging commands: `kubectl exec -it <pod> -n inventory -- <shell>`, `kubectl get endpoints -n inventory`, `kubectl get events -n inventory --sort-by=.lastTimestamp`
    - ARM64 pre-flight: `docker manifest inspect` commands for both images
  - _Requirements: 6.1, 6.4, 11.1, 14.2_

- [ ] 34. Create local k3d development runbook
  - Create `docs/runbooks/local-k3d-dev.md`
  - Must cover (each command block preceded by a `#` comment line):
    - k3d cluster creation command
    - Local image loading (for images built locally rather than pulled from registry)
    - Manifest application in dependency order
    - Port-forwarding to expose frontend at `localhost:8080`: `kubectl port-forward svc/frontend 8080:80 -n inventory`
    - Verification: `curl http://localhost:8080` must return HTTP 200
    - Cluster teardown: `k3d cluster delete`
    - Known gap: ARM64 images cannot be validated locally; Phase 2 is where ARM64 correctness is first confirmed
  - _Requirements: 8.1, 8.5, 14.3_

- [ ] 35. Update docs/architecture/hld/system-architecture.md
  - Add a new section "Kubernetes Network Topology" containing the Mermaid diagram from the design document (reproduced verbatim)
  - The diagram must show: `inventory` namespace, all four pods with ports, all four Services (three ClusterIP + one NodePort on port 80), and the external access path from the internet to the NodePort Service
  - _Requirements: 15.1_

- [ ] 36. Update docs/architecture/concepts/environments.md
  - Add a third environment column "Kubernetes/OCI" alongside the existing "Dev (Docker Compose)" and "Prod (Docker Compose)" columns
  - Cover all existing rows: runtime, image source, database persistence, secret management, network exposure, hot-reload behaviour
  - Fill in accurate values for the Kubernetes/OCI column for each row
  - _Requirements: 15.2_

- [ ] 37. Update docs/security.md
  - Add a new section "Kubernetes Secrets Model" documenting: manual bootstrap via `kubectl create secret generic`, `secretKeyRef` references in manifests, no credentials in committed files, secret rotation procedure
  - Add a new section "OCI Dual Firewall" documenting: the VCN Security List (Terraform-managed, opens TCP 22/80/6443) and the OS iptables rules (applied manually on the VM, opens TCP 80/6443); explain that both layers must allow a port for traffic to reach a pod
  - _Requirements: 15.3_

- [ ] 38. Update docs/cheatsheet.md
  - Add a "Kubernetes Quick Reference" section with at minimum the following `kubectl` operations, each with the exact command and a one-line description:
    - Apply manifests (`kubectl apply -f k8s/`)
    - Get pod status (`kubectl get pods -n inventory`)
    - View logs (`kubectl logs <pod> -n inventory`)
    - Exec into a pod (`kubectl exec -it <pod> -n inventory -- /bin/sh`)
    - Describe a resource (`kubectl describe pod <pod> -n inventory`)
    - Get events (`kubectl get events -n inventory --sort-by=.lastTimestamp`)
    - Delete a pod to force restart (`kubectl delete pod <pod> -n inventory`)
    - Port-forward a service (`kubectl port-forward svc/frontend 8080:80 -n inventory`)
  - _Requirements: 14.5_

- [ ] 39. Create docs/backlog.md
  - Create `docs/backlog.md` with all eleven out-of-scope future tasks organised under three priority tiers: **High**, **Medium**, **Low**
  - For each of the eleven tasks, include: a one-sentence description of what it involves and a one-sentence explanation of why it is deferred
  - The eleven tasks (all must be present): CI/CD (GitHub Actions), TLS/HTTPS (cert-manager + Let's Encrypt), Domain attachment, Alembic migrations, Traefik ingress, CORS hardening, Resource tuning, Vulnerability scanning, Prometheus + Grafana monitoring, Horizontal Pod Autoscaler, Multi-node k3s
  - High priority: CI/CD, TLS/HTTPS, Domain
  - Medium priority: Alembic migrations, Traefik ingress, CORS hardening, Resource tuning
  - Low priority: Vulnerability scanning, Monitoring, HPA, Multi-node k3s
  - _Requirements: 16.1, 16.2, 16.3_

- [ ] 40. Final checkpoint — all documentation complete
  - Verify all 11 entries are present in `docs/backlog.md`
  - Verify all six ADR files (010–015) exist in `docs/decisions/`
  - Verify all three runbook files exist in `docs/runbooks/`
  - Verify `docs/archive/` contains the three moved files plus `README.md`
  - Ask the user if any documentation corrections or additions are needed.

---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP; all other tasks are required
- Property test sub-tasks map 1:1 to the six Correctness Properties in the design document
- **Phase 1 validation flow**: write all manifests (1–11) → create k3d cluster (13.1) → build + load local x86_64 images (13.2–13.3) → bootstrap test secrets (13.4) → apply manifests (13.5) → wait for Running (13.6) → smoke test (13.7) → run property tests (13.8) → restore tags + teardown (13.9)
- **Image tag strategy**: manifests use placeholder `ghcr.io/VikramBabariya/...<git_SHA>` tags. For k3d validation (task 13), temporarily swap to local tags with `imagePullPolicy: Never`, then revert before Phase 2. For OCI deployment (Phase 3), update tags to the actual ARM64 git SHA.
- The `VITE_API_URL` build arg is the only difference between Phase 1 and Phase 3 frontend images — Phase 1 uses `http://localhost:8080`, Phase 3 uses `http://<OCI_PUBLIC_IP>:8000`
- `inventory-secrets` is never created from a manifest file; it is bootstrapped manually (with test values for k3d, production values for OCI)
- Phases 1–3 are ordered by dependency: manifests + k3d validation → Terraform → OCI deploy. Documentation tasks (24–40) are largely independent and can run in parallel with Phase 2 and Phase 3 tasks after Phase 1 is complete

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1", "14"] },
    { "id": 1, "tasks": ["2", "3", "15", "16", "17", "18"] },
    { "id": 2, "tasks": ["4", "6", "8", "10"] },
    { "id": 3, "tasks": ["5", "7", "9", "11"] },
    { "id": 4, "tasks": ["12.1", "12.3", "12.4", "12.5", "12.6"] },
    { "id": 5, "tasks": ["12.2", "13.1", "24", "26", "27", "28", "29", "30", "31"] },
    { "id": 6, "tasks": ["13.2", "13.3", "25", "32", "33", "34", "35", "36", "37", "38", "39"] },
    { "id": 7, "tasks": ["13.4"] },
    { "id": 8, "tasks": ["13.5"] },
    { "id": 9, "tasks": ["13.6"] },
    { "id": 10, "tasks": ["13.7", "13.8"] },
    { "id": 11, "tasks": ["13.9", "20"] },
    { "id": 12, "tasks": ["21"] },
    { "id": 13, "tasks": ["22"] }
  ]
}
```
