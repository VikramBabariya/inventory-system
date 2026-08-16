# OCI Idle Prevention - Quick Reference

> **🚨 CRITICAL**: Oracle deletes idle Always Free VMs after 7 days if usage < 20% on CPU, Memory, and Network.

## Immediate Actions After VM Deployment

### 1. Add Basic Keep-Alive Cron Jobs
```bash
# SSH into your OCI VM and run:
crontab -e

# Add these lines:
*/10 * * * * curl -s http://localhost:8000/api/health > /dev/null 2>&1
*/15 * * * * kubectl get pods -n inventory > /dev/null 2>&1  
*/20 * * * * ping -c 2 8.8.8.8 > /dev/null 2>&1
0 * * * * timeout 60 yes > /dev/null 2>&1
```

### 2. Verify Activity Levels
```bash
# Check current utilization (should be >20% each)
top                    # CPU usage
free -h               # Memory usage  
iftop                 # Network usage (install: sudo yum install iftop)
```

### 3. Monitor Resource Usage
```bash
# Weekly check - ensure none drop below 20% for 7 days
oci monitoring metric-data summarize-metrics-data \
  --compartment-id <your-tenancy-ocid> \
  --resource-group <your-vm-ocid>
```

## Quick Keep-Alive Solutions

### Application Level (Best)
- Health check endpoints every 5-10 minutes
- Background database queries every 30 minutes
- Redis cache warming every hour

### System Level (Backup)
- Light CPU activity: `yes` command for 1 minute every hour
- Network pings to external services every 15 minutes
- Memory pressure via Redis maxmemory setting

### Kubernetes Level (Automatic)
- Pod readiness/liveness probes (already configured)
- Service mesh traffic (future enhancement)
- Log shipping and metrics collection

---
**⚠️ Remember**: Prevention is critical - there's no recovery from reclamation, only complete rebuild.