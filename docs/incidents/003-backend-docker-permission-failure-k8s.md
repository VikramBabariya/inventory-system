# Incident Report: Backend Docker Permission Failure in Kubernetes

**Incident ID:** INC-001  
**Date:** 2026-08-13  
**Environment:** k3d validation cluster (Phase 1)  
**Severity:** Medium  
**Status:** Resolved  

## Summary

Backend pod crashed with permission errors during Phase 1 Kubernetes validation, preventing end-to-end testing completion. Root cause was Docker file permission configuration in production Dockerfile when running as non-root user.

## Timeline

| Time (UTC) | Event |
|------------|-------|
| 11:15 | Applied Kubernetes manifests to k3d cluster |
| 11:16 | Backend pod entered CrashLoopBackOff status |
| 11:20 | Identified `PermissionError` in pod logs |
| 11:25 | Root cause analysis revealed Docker file permission issue |
| 11:40 | Multiple solution paths identified and documented |
| 11:45 | Incident recorded and resolved |

## Impact Assessment

- **Environment**: Local k3d validation cluster (no production impact)
- **Duration**: 30 minutes of investigation and resolution
- **Affected Systems**: Backend pod deployment, dependent frontend pod
- **Users Affected**: 0 (pre-production environment)
- **Business Impact**: Phase 1 validation testing delayed but no customer impact

## Root Cause Analysis

### Problem Description
The production Dockerfile implements security hardening by running as non-root user, but file permissions were not properly configured:

```dockerfile
# Production Dockerfile sequence
RUN useradd -m appuser
USER appuser              # ← Sets default user for CMD/ENTRYPOINT  
COPY . .                  # ← But COPY still runs as Docker daemon (root)
CMD ["uvicorn", "main:app", ...]
```

### Technical Root Cause
1. **Source files** had `600` permissions (owner read/write only)
2. **Docker COPY** preserved permissions but set owner to `root`
3. **Container runtime** executed as `appuser` (UID 1000)
4. **Result**: `appuser` could not read `root`-owned `600` files

### File System Evidence
```bash
# Inside container:
ls -la /app/main.py
# -rw------- 1 root root 5492 Aug 13 main.py  ← Only root can read

whoami  
# appuser  ← Process runs as non-root user
```

### Error Details
```
PermissionError: [Errno 13] Permission denied: '/app/main.py'
  File "/opt/venv/lib/python3.12/importlib/__init__.py", line 90, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
```

## Environment Behavior Analysis

| Environment | User Context | File Access | Result |
|-------------|-------------|-------------|--------|
| **Docker Compose** | `root` (default) | Can read `600` files | ✅ Works |
| **Kubernetes** | `appuser` (security hardened) | Cannot read `600` files | ❌ Fails |

This explains why the same Docker image worked in Docker Compose but failed in Kubernetes deployment.

## Resolution

### Implemented Solution
Applied **Option 2: Source File Permission Fix**

```bash
# Made source files readable by all users
chmod 644 backend/*.py backend/requirements.txt

# Rebuilt image
docker build -t inventory-backend:local ./backend

# Reimported to k3d
k3d image import inventory-backend:local -c inventory-local
```

### Alternative Solutions Identified

**Option 1: Dockerfile Fix (Recommended for production)**
```dockerfile
COPY . .
RUN chown -R appuser:appuser /app
USER appuser
```

**Option 3: Development Dockerfile**
```bash
docker build -f backend/Dockerfile.dev -t inventory-backend:local ./backend
```

## Lessons Learned

### Technical Insights
1. **Docker COPY Behavior**: `COPY` operations run as Docker daemon (root) regardless of `USER` directive
2. **Permission Preservation**: Docker preserves source file permissions but changes ownership
3. **Security vs Functionality**: Security hardening requires explicit permission management
4. **Cross-Environment Testing**: Same artifact can behave differently in different execution contexts

### Process Insights
1. **Validation Value**: Phase 1 validation successfully caught deployment pipeline gap
2. **Multi-Environment Testing**: Need to test production Docker images with non-root users
3. **Documentation Gap**: Dockerfile security implications need better documentation

## Prevention Actions

### Immediate Actions (Completed)
- ✅ Source file permissions corrected
- ✅ Docker image rebuilt and tested
- ✅ Phase 1 validation unblocked

### Long-term Actions (Recommended)

| Action | Owner | Due Date | Priority |
|--------|-------|----------|----------|
| Add Docker image permission testing to CI/CD pipeline | DevOps | 2026-08-20 | High |
| Create production Docker image validation checklist | Platform | 2026-08-18 | Medium |
| Document file permission requirements in Dockerfile | Development | 2026-08-16 | Low |
| Implement automated non-root container testing | SRE | 2026-08-25 | Medium |

## Validation Success

This incident validates that the Phase 1 Kubernetes validation process works as intended:
- ✅ **Caught deployment issue** before production
- ✅ **Isolated environment** prevented customer impact  
- ✅ **Early detection** allowed proper root cause analysis
- ✅ **Multiple solutions** identified and documented

## References

- **Troubleshooting Log**: `/docs/logs/troubleshooting.md`
- **Production Dockerfile**: `/backend/Dockerfile`
- **Development Dockerfile**: `/backend/Dockerfile.dev`
- **Phase 1 Tasks**: `.kiro/specs/k8s-migration/tasks.md` (Task 13.5)

---

**Incident Closed:** 2026-08-13 11:45 UTC  
**Next Review Date:** 2026-08-20 (Action items follow-up)