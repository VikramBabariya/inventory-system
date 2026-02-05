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

#### 🐚 Access Container Shell
Go inside the container to check files or run commands manually.
```bash
# For Backend
docker exec -it inventory_backend bash

# For Frontend (Prod/Alpine) uses 'sh' not 'bash'
docker exec -it inventory_frontend sh

# For Database
docker exec -it inventory_db psql -U admin -d inventory_db
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