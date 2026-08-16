# Oracle Cloud Infrastructure Always Free Limits

**Source:** [Oracle Always Free Resources Documentation](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)  
**Date Extracted:** August 14, 2026  
**Home Region:** ap-mumbai-1 (Mumbai, India)

## ⚠️ CRITICAL: Idle Instance Reclamation Policy

### **Oracle's Reclamation Rules**
Oracle **WILL AUTOMATICALLY DELETE** your Always Free VM instances if they remain idle for **7 consecutive days**.

**An instance is considered "idle" if ALL of the following are true for 7 days:**
- **CPU utilization** for the 95th percentile is **< 20%**
- **Network utilization** is **< 20%**  
- **Memory utilization** is **< 20%** (applies to A1 ARM64 shapes only)

### **Impact on Inventory System**
- **Data Loss**: PostgreSQL database, uploaded files, configuration
- **Service Interruption**: Complete system shutdown
- **Recovery**: Manual rebuild required, no automatic restoration

## 🛡️ Prevention Strategies

### **1. Application-Level Solutions (Recommended)**

**A. Enable Health Check Monitoring**
```bash
# Add to your inventory system - backend health endpoint
curl http://your-vm-ip/api/health  # Every few minutes via cron
```

**B. Database Activity**
```python
# Add periodic background task in FastAPI
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

async def keep_alive_task():
    """Periodic database query to maintain activity"""
    async with get_db() as db:
        await db.execute("SELECT COUNT(*) FROM products")
        logger.info("Keep-alive query executed")

# Run every 30 minutes
scheduler = AsyncIOScheduler()
scheduler.add_job(keep_alive_task, 'interval', minutes=30)
```

**C. Synthetic Traffic Generation**
```bash
# Add to system cron (crontab -e)
# Query API every 10 minutes to maintain network activity
*/10 * * * * curl -s http://localhost:8000/api/products > /dev/null 2>&1
*/15 * * * * curl -s http://localhost:8000/api/categories > /dev/null 2>&1
*/12 * * * * curl -s http://localhost:8000/api/health > /dev/null 2>&1
```

### **2. System-Level Solutions**

**A. Memory Baseline Load**
```bash
# Add memory pressure to stay above 20%
# Use Redis as intentional memory consumer
redis-cli config set maxmemory 2gb
redis-cli config set maxmemory-policy allkeys-lru
```

**B. CPU Baseline Activity**  
```bash
# Light background CPU activity (add to crontab)
# Run every hour for 2 minutes to maintain CPU stats
0 * * * * timeout 120 yes > /dev/null 2>&1
```

**C. Network Baseline Traffic**
```bash
# Periodic external connectivity test
# Add to crontab - runs every 15 minutes
*/15 * * * * ping -c 4 8.8.8.8 > /dev/null 2>&1
*/20 * * * * curl -s https://httpbin.org/ip > /dev/null 2>&1
```

### **3. Monitoring Setup (Essential)**

**A. Install OCI Monitoring Agent**
```bash
# Install monitoring agent on your VM
curl -L https://objectstorage.us-ashburn-1.oraclecloud.com/n/oracle/b/oci-monitoring/o/unified_monitoring_agent/monitoring-agent-install.sh | bash
```

**B. Custom Metrics Collection**
```python
# Add to your FastAPI app - expose metrics endpoint
@app.get("/metrics")
async def metrics():
    return {
        "cpu_usage": psutil.cpu_percent(interval=1),
        "memory_usage": psutil.virtual_memory().percent,
        "active_connections": len(await db.execute("SELECT * FROM pg_stat_activity")),
        "timestamp": datetime.utcnow()
    }
```

## 📊 Always Free Resource Limits

### **VM.Standard.A1.Flex (ARM64) Allocation**
| Resource | Monthly Limit | 24/7 Equivalent | Our Usage |
|----------|---------------|-----------------|-----------|
| **OCPU Hours** | 1,500 hours | 2.08 OCPUs | 2 OCPUs ✅ |
| **Memory Hours** | 9,000 GB hours | 12.5 GB RAM | 12 GB RAM ✅ |
| **Boot Volume** | 200 GB total | 47 GB minimum | 47 GB ✅ |

**Result:** Our Terraform configuration uses **100% of Always Free allowance** (optimal).

### **Additional Always Free Resources**
| Service | Limit | Usage for Inventory System |
|---------|-------|----------------------------|
| **Block Volume** | 200 GB total | PostgreSQL data storage |
| **Volume Backups** | 5 backups | Database disaster recovery |
| **Object Storage** | 20 GB | Container image backups |
| **VCNs** | 2 maximum | 1 VCN (single network) |
| **Outbound Data** | 10 TB/month | API responses, image pulls |
| **Monitoring** | 500M data points | Resource utilization tracking |

## 🏠 Region Restrictions

**Critical Rule:** ALL Always Free resources must be created in your **home region only**.

**Your Home Region:** `ap-mumbai-1` (Mumbai, India)  
**Implication:** Cannot use Always Free resources in any other OCI region.

## 💡 Recommended Monitoring Approach

### **Phase 1: Basic Keep-Alive (Immediate)**
```bash
# Simple cron jobs to prevent idle classification
*/10 * * * * curl -s http://localhost:8000/api/health > /dev/null
*/30 * * * * docker exec inventory_db psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT NOW();" > /dev/null
```

### **Phase 2: Application Integration (Next Sprint)**  
- Add background tasks to FastAPI application
- Implement periodic database maintenance queries
- Create metrics endpoint for resource utilization

### **Phase 3: Advanced Monitoring (Future)**
- Install OCI Monitoring Agent  
- Set up custom dashboards
- Configure automated alerting

## 🚨 Emergency Recovery Plan

**If Instance Gets Reclaimed:**
1. **Immediate**: Create new VM with same Terraform configuration
2. **Restore Data**: From volume backups (if configured)  
3. **Redeploy**: Apply k8s manifests with same configuration
4. **DNS Update**: Point domain to new public IP (if using custom domain)

**Prevention is Better:** Implement keep-alive strategies immediately after Phase 2 deployment.

---

**Next Actions:**
1. ✅ Complete Phase 2 (Terraform + ARM64 images)  
2. ✅ Deploy to OCI (Phase 3)
3. 🔄 **PRIORITY**: Implement idle prevention (add to Phase 4 documentation)
4. 📊 Set up basic monitoring

**Documentation Updated:** August 14, 2026  
**Review Date:** Every 6 months or after OCI policy changes