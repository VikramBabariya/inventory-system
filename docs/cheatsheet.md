# ⚡ Developer Cheatsheet & Commands

## 🐳 Docker Operations

### 🚀 Start Development Server
```bash
docker-compose up
# Add '-d' to run in background (detached mode)
docker-compose up -d
```

### 🔄 Full Reset (Nuclear Option)
*Use this if DB schema changes or things get stuck.*
```bash
docker-compose down -v
docker-compose up --build
```

### 🛑 Stop Everything (Cleanly)
```bash
docker-compose down
```

### 🗄️ Database (Postgres)

#### 🐚 Access SQL Shell (PSQL)*
Log into the database container to run queries manually.
```bash
# Development
docker exec -it inventory-system-db-1 psql -U admin -d inventory_db

# Production
docker exec -it inventory-system-db-1 psql -U admin -d inventory_db
```

#### 🧪 Common Queries
```sql
-- Check if tables exist
\dt

-- Check Master Data (with category names)
SELECT p.sku, p.name, c.name AS category, p.price, p.current_stock
FROM products p
JOIN categories c ON p.category_id = c.id;

-- Check Ledger (History)
SELECT * FROM stock_movements ORDER BY created_at DESC;

-- Verify ledger sum matches current_stock snapshot
SELECT p.name, p.current_stock, SUM(sm.change_amount) AS ledger_total
FROM products p
JOIN stock_movements sm ON sm.product_id = p.id
GROUP BY p.id, p.name, p.current_stock;
```

### 🌐 API Endpoints

| Method | Endpoint | Description |
| :----- | :------- | :---------- |
| `GET` | `/health` | Backend + DB + Redis connectivity check |
| `GET` | `/products` | All products with category info (cached) |
| `POST` | `/products/{id}/movements` | Record a SALE or RESTOCK (invalidates cache) |
| `GET` | `/products/{id}/movements` | Full movement history for a product (cached) |

**Example — record a sale:**
```bash
curl -X POST http://localhost:8000/products/1/movements \
  -H "Content-Type: application/json" \
  -d '{"change_amount": -1, "movement_type": "SALE"}'
```

**Movement types:** `SALE`, `RESTOCK`, `RETURN`, `DAMAGE`

> **Note:** In production, all API calls from the browser go through Nginx at `/api/` — e.g. `/api/products`. Nginx strips the `/api/` prefix and proxies to `http://backend:8000/`.

### 🛠️ Debugging

#### 🐍 Test Backend Connectivity (Python)
Run this from Host to verify Backend -> DB connection.
```bash
docker exec -it inventory-system-backend-1 python -c "import socket; print('Connected!' if socket.create_connection(('db', 5432)) else 'Failed')"
```

#### 🔍 Check Logs
```bash
# Follow logs for all services
docker-compose logs -f

# Check just the Database logs (good for seeing init.sql errors)
docker-compose logs -f db

# Production logs
docker-compose -f docker-compose.prod.yml logs -f
```

#### 🗃️ Redis Cache Inspection
```bash
# List all active cache keys
docker exec -it inventory-system-redis-1 redis-cli KEYS "*"

# Check TTL remaining on a key (seconds until expiry)
docker exec -it inventory-system-redis-1 redis-cli TTL "products:all"

# Read a cached value (raw JSON)
docker exec -it inventory-system-redis-1 redis-cli GET "products:all"

# Flush entire cache (forces next request to hit PostgreSQL)
docker exec -it inventory-system-redis-1 redis-cli FLUSHALL
```

#### 🐚 Access Container Shell
Go inside the container to check files or run commands manually.
```bash
# For Backend
docker exec -it inventory-system-backend-1 bash

# For Frontend (Prod/Alpine) uses 'sh' not 'bash'
docker exec -it inventory-system-frontend-1 sh

# For Database
docker exec -it inventory-system-db-1 psql -U admin -d inventory_db
```

#### 📏 Check Image Sizes
Verify optimization results.

```bash
docker images | grep inventory
```

## 🚦 Docker Lifecycle: The Decision Matrix

| IF I Changed... | THEN Run... | WHY? |
| :--- | :--- | :--- |
| **Python / JS Code**<br>(`main.py`, `App.jsx`) | **Nothing** (Just Save) | Volumes map your local file directly into the container. Hot-reload handles the rest. |
| **Dependencies**<br>(`requirements.txt`, `package.json`) | `docker-compose up --build` | Libraries are installed inside the Image. You must rebuild the image to add them. |
| **Configuration**<br>(`.env`, `docker-compose.yml`) | `docker-compose up` | Docker needs to recreate the container config (Ports, Env Vars). |
| **Testing Prod** | `docker-compose -f docker-compose.prod.yml up --build` | Uses optimized images (No Volumes). |
| **Database Schema**<br>(`init.sql`) | `docker-compose down -v` | The DB initialization script only runs if the volume is empty. You must wipe the volume. |
| **Stale cache after manual DB edit** | `docker exec -it inventory-system-redis-1 redis-cli FLUSHALL` | Redis serves cached data for up to 1 hour. Flush it to force fresh reads immediately. |