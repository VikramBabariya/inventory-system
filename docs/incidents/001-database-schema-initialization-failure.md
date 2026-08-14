# Incident Report: Database Schema Initialization Failure

**Incident ID:** INC-002  
**Date:** 2026-02-03  
**Environment:** Development (Docker Compose)  
**Severity:** Medium  
**Status:** Resolved  

## Summary

Database schema initialization script (`init.sql`) failed to execute after being added to docker-compose configuration, resulting in missing tables and preventing application functionality. Root cause was PostgreSQL Docker image "first boot rule" interaction with persistent volumes.

## Timeline

| Time | Event |
|------|-------|
| Day 1 | Initial docker-compose setup completed successfully |
| Day 2 | Added `init.sql` script to project |
| Day 2 | Modified docker-compose.yml to mount init.sql |
| Day 2 | Restarted containers with `docker-compose up` |
| Day 2 | Discovered database still empty - no tables created |
| Day 2 | Investigation revealed PostgreSQL initialization behavior |
| Day 2 | Resolution applied with volume reset |

## Impact Assessment

- **Environment**: Development environment (all developers affected)
- **Duration**: Multiple hours of investigation across team
- **Affected Functionality**: Complete application failure - no database tables
- **Developer Productivity**: Blocked all feature development
- **Learning Impact**: Revealed critical Docker + PostgreSQL knowledge gap

## Root Cause Analysis

### Problem Description
PostgreSQL Docker container follows a "first boot rule" for initialization:

```bash
# PostgreSQL Docker entrypoint logic:
if [ -z "$(ls -A /var/lib/postgresql/data)" ]; then
    # Empty data directory - run initialization scripts
    run_init_scripts
else  
    # Data exists - skip initialization entirely
    start_postgres_only
fi
```

### Technical Root Cause
1. **Initial Setup**: Database container started without init.sql → created empty PostgreSQL data
2. **Volume Persistence**: Docker named volume preserved this "initialized" state
3. **Script Addition**: Added init.sql and restarted container
4. **Initialization Skip**: PostgreSQL saw existing data directory → skipped init.sql execution
5. **Result**: Empty database with no application schema

### Developer Mental Model Gap
```
Expected Behavior: Add script → Restart → Script runs
Actual Behavior:   Add script → Restart → Script ignored (data exists)
```

### Evidence
```bash
# Container logs showed:
PostgreSQL Database directory appears to contain a database; Skipping initialization

# Database inspection revealed:
psql> \dt
# No relations found. (Empty database)

# Volume inspection confirmed persistent data:
docker volume inspect inventory-system_postgres_data
```

## Resolution

### Implemented Solution
```bash
# Force volume destruction to trigger fresh initialization
docker-compose down -v    # ← Critical: -v flag removes volumes
docker-compose up --build -d
```

### Validation
```bash
# Confirmed init.sql execution in logs:
CREATE TABLE
CREATE TABLE  
CREATE TABLE
INSERT 0 2
INSERT 0 2

# Verified database schema:
psql> \dt
# products | categories | stock_movements ✓
```

## Environment Behavior Analysis

| Scenario | Data Directory | PostgreSQL Behavior | init.sql Execution |
|----------|---------------|--------------------|--------------------|
| **Fresh Install** | Empty | Full initialization | ✅ Executed |
| **Restart (same volume)** | Contains data | Skip initialization | ❌ Ignored |
| **Volume Reset** | Destroyed → Empty | Full initialization | ✅ Executed |

## Lessons Learned

### Technical Insights
1. **PostgreSQL Initialization**: One-time only on empty data directory
2. **Docker Volume Persistence**: Named volumes survive container destruction
3. **Development Workflow**: Schema changes require volume reset in development
4. **Production Implications**: Never use init.sql for schema updates in production

### Process Insights  
1. **Mental Model Gap**: Docker + database persistence behavior not obvious
2. **Documentation Need**: Clear guidance on development database workflows
3. **Onboarding Risk**: Every new developer will encounter this pattern
4. **Tool Selection**: Production systems need proper migration tools (Alembic)

## Prevention Actions

### Immediate Actions (Completed)
- ✅ Documented volume reset procedure for schema changes
- ✅ Added prevention guidance to troubleshooting log
- ✅ Team education on PostgreSQL Docker behavior

### Long-term Actions (Recommended)

| Action | Owner | Due Date | Priority |
|--------|-------|----------|----------|
| Create development workflow documentation | Development | 2026-02-10 | High |
| Add docker-compose.dev.yml with ephemeral volumes | DevOps | 2026-02-15 | Medium |
| Implement Alembic migrations for schema changes | Backend | 2026-02-20 | Medium |
| Add pre-commit hooks for schema change detection | Platform | 2026-02-25 | Low |

## Broader Implications

### Development Workflow Impact
- **Schema Changes**: Must use `docker-compose down -v` in development
- **Data Persistence**: Named volumes vs development convenience trade-off
- **Team Onboarding**: Critical concept for new Docker developers

### Production Considerations
- **Migration Strategy**: Alembic/Flyway required for production schema changes
- **Backup Procedures**: Volume management becomes critical
- **Deployment Process**: Clear separation of initialization vs migration

## References

- **PostgreSQL Docker Documentation**: Official initialization behavior
- **Docker Compose Volumes**: Named volume persistence documentation
- **Troubleshooting Entry**: Port conflicts and volume management
- **Future Migration Tool**: Alembic implementation planning

---

**Incident Closed:** 2026-02-03  
**Next Review Date:** 2026-02-10 (Development workflow documentation)