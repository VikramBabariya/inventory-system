# ⚡ Developer Cheatsheet & Commands

## 🐳 Docker Operations

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
docker exec -it inventory_db psql -U admin -d inventory_db
```

#### 🧪 Common Queries
```sql
-- Check if tables exist
\dt

-- Check Master Data
SELECT * FROM products;

-- Check Ledger (History)
SELECT * FROM stock_movements;
```

### 🛠️ Debugging

#### 🐍 Test Backend Connectivity (Python)
Run this from Host to verify Backend -> DB connection.
```bash
docker exec -it inventory_backend python -c "import socket; print('Connected!' if socket.create_connection(('db', 5432)) else 'Failed')"
```

#### 🔍 Check Logs
```bash
# Follow logs for all services
docker-compose logs -f

# Check just the Database logs (good for seeing init.sql errors)
docker-compose logs -f db
```