# Incident Reports

This directory contains formal incident reports for the inventory management system. Each incident is documented in a separate numbered file following the naming convention: `{number}-{brief-description}.md`

## Incident Index

| ID | Date | Title | Severity | Status | Environment |
|----|------|-------|----------|--------|-------------|
| [001](./001-backend-docker-permission-failure-k8s.md) | 2026-08-13 | Backend Docker Permission Failure in Kubernetes | Medium | Resolved | k3d validation |
| [002](./002-database-schema-initialization-failure.md) | 2026-02-03 | Database Schema Initialization Failure | Medium | Resolved | Development |
| [003](./003-cache-invalidation-data-inconsistency.md) | 2026-08-11 | Cache Invalidation Data Inconsistency | Medium | Resolved | Development |

## Incident Severity Levels

- **Critical (P1)**: Complete service outage, major functionality unavailable
- **High (P2)**: Major functionality degraded, significant user impact
- **Medium (P3)**: Minor functionality affected, limited user impact  
- **Low (P4)**: Cosmetic issues, documentation gaps, no user impact

## Incident Lifecycle

```
Detected → Investigating → Mitigating → Resolved → Closed
```

## File Naming Convention

Format: `{number}-{brief-description}-{component}.md`

Examples:
- `001-backend-docker-permission-failure-k8s.md`
- `002-database-connection-pool-exhaustion.md`
- `003-frontend-build-failure-ci-cd.md`

## Report Template

Each incident report should include:

1. **Header**: ID, date, environment, severity, status
2. **Summary**: Brief description of the incident
3. **Timeline**: Chronological sequence of events
4. **Impact Assessment**: Affected systems, users, business impact
5. **Root Cause Analysis**: Technical details and investigation findings
6. **Resolution**: Steps taken to resolve the incident
7. **Lessons Learned**: Key insights and technical learnings
8. **Prevention Actions**: Steps to prevent similar incidents
9. **References**: Links to related documentation

## Integration with Other Documentation

- **Troubleshooting Log** (`/docs/logs/troubleshooting.md`): Informal development issues and solutions
- **Decision Records** (`/docs/decisions/`): Architecture decisions and their rationale
- **Runbooks** (`/docs/runbooks/`): Operational procedures and deployment guides

## Contributing

When creating new incident reports:

1. Use the next sequential number (002, 003, etc.)
2. Follow the established naming convention
3. Include all required sections from the template
4. Update this README index with the new incident
5. Cross-reference related documentation where appropriate

## Archive Policy

- Incidents remain in active directory for ongoing reference
- No automatic archival - all incidents provide long-term value
- Historical incidents help identify patterns and recurring issues
- Resolved incidents serve as troubleshooting references for similar future issues