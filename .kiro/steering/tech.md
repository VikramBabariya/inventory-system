# Technology Stack

## Backend
- **Framework**: FastAPI (Python)
- **Server**: Uvicorn (ASGI server for async support)
- **ORM**: SQLAlchemy
- **Database Driver**: psycopg2-binary (PostgreSQL)
- **Database**: PostgreSQL 15 (Alpine)
- **Cache**: Redis (Alpine)
- **Environment**: python-dotenv for configuration

### Why FastAPI
- Native async/await for high-concurrency operations
- Auto-generated OpenAPI/Swagger documentation at `/docs`
- High performance (comparable to Node.js/Go)
- Type hints with Pydantic validation

## Frontend
- **Framework**: React 19.x
- **Build Tool**: Vite (fast dev server with native ES modules)
- **Language**: JavaScript (ESM modules)
- **Linter**: ESLint with React plugins
- **Reverse Proxy**: Nginx (production only)

### Why React + Vite
- Virtual DOM for efficient real-time updates
- Component-based architecture
- Vite provides instant dev server startup (much faster than CRA)

## Infrastructure
- **Containerization**: Docker with Docker Compose
- **Build Strategy**: Multi-stage builds for security and size optimization
- **Networks**: Bridge networks for tier isolation (frontend_tier, backend_tier)
- **Volumes**: Named volumes for database persistence

## Common Commands

### Development Mode (Hot Reload)
```bash
# Start all services with live reload
docker-compose up --build

# Stop all services
docker-compose down

# View logs
docker-compose logs -f [service-name]

# Access backend API docs
# http://localhost:8000/docs
```

### Production Mode (Optimized Build)
```bash
# Start production-optimized build
docker-compose -f docker-compose.prod.yml up --build

# Stop production services
docker-compose -f docker-compose.prod.yml down
```

### Backend Development
```bash
# Install dependencies (if running locally)
pip install -r backend/requirements.txt

# Run backend directly (outside Docker)
cd backend && uvicorn main:app --reload
```

### Frontend Development
```bash
# Install dependencies
cd frontend && npm install

# Run dev server
npm run dev

# Build for production
npm run build

# Run linter
npm run lint

# Preview production build
npm run preview
```

### Database Access
```bash
# Connect to PostgreSQL container
docker exec -it inventory_db psql -U <POSTGRES_USER> -d <POSTGRES_DB>

# View tables
\dt

# Exit psql
\q
```

### Health Checks
```bash
# Backend health check
curl http://localhost:8000/health

# Redis ping
docker exec -it inventory_redis redis-cli ping

# PostgreSQL ready check
docker exec -it inventory_db pg_isready -U <POSTGRES_USER>
```

## Environment Configuration
- Copy `.env.example` to `.env` before first run
- Environment variables are injected via `env_file` in docker-compose
- Frontend uses `VITE_API_URL` for backend API endpoint

## Key Dependencies

### Backend (requirements.txt)
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `sqlalchemy` - ORM
- `psycopg2-binary` - PostgreSQL driver
- `python-dotenv` - Environment management

### Frontend (package.json)
- `react` / `react-dom` - UI framework
- `vite` - Build tool and dev server
- `eslint` - Code linting
- `@vitejs/plugin-react` - Vite React integration

## Docker Image Sizes
- **Frontend**: 93MB (production), 1.84GB (dev)
- **Backend**: 271MB (production), 1.63GB (dev)
- Multi-stage builds eliminate compilers and dev tools from production images
- All production containers run as non-root users
