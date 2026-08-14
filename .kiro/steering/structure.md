# Project Structure

## Root Directory Layout
```
inventory-system/
├── backend/              # Python FastAPI application
├── frontend/             # React + Vite application
├── db_init/              # Database initialization scripts
├── docs/                 # Architecture and decision records
├── .kiro/                # AI assistant configuration
├── docker-compose.yml    # Development environment
├── docker-compose.prod.yml # Production environment
├── .env.example          # Environment template
└── setup.sh              # Setup script
```

## Backend Structure (`/backend`)
```
backend/
├── main.py              # FastAPI app entry point & routes
├── models.py            # SQLAlchemy ORM models
├── database.py          # Database connection & session management
├── requirements.txt     # Python dependencies
├── Dockerfile.dev       # Development container
└── Dockerfile           # Production multi-stage build
```

### Backend Conventions
- **Entry point**: `main.py` initializes FastAPI app
- **Database sessions**: Use dependency injection `Depends(database.get_db)`
- **Models**: SQLAlchemy ORM classes defined in `models.py`
- **API docs**: Auto-generated at `/docs` endpoint (Swagger UI)
- **Health check**: `/health` endpoint tests database connectivity

## Frontend Structure (`/frontend`)
```
frontend/
├── src/
│   ├── main.jsx         # React app entry point
│   ├── App.jsx          # Root component
│   ├── App.css          # App-level styles
│   ├── index.css        # Global styles
│   └── assets/          # Static assets (images, icons)
├── public/              # Public static files
├── index.html           # HTML template
├── vite.config.js       # Vite configuration
├── package.json         # Node dependencies & scripts
├── eslint.config.js     # ESLint configuration
├── nginx.conf           # Nginx config (production only)
├── Dockerfile.dev       # Development container
└── Dockerfile           # Production multi-stage build
```

### Frontend Conventions
- **Entry point**: `main.jsx` renders the React app
- **Component architecture**: Build reusable components
- **API calls**: Use `VITE_API_URL` environment variable for backend endpoint
- **Styling**: CSS files co-located with components
- **ESM modules**: Use ES6 imports/exports

## Database Initialization (`/db_init`)
```
db_init/
└── init.sql             # SQL script run on first container startup
```

### Database Conventions
- `init.sql` runs automatically on first PostgreSQL container start
- Script is idempotent—uses `CREATE TABLE IF NOT EXISTS`
- Seeds initial data for development

## Documentation Structure (`/docs`)
```
docs/
├── architecture/
│   ├── database_schema.md       # ERD and table definitions
│   ├── hld/
│   │   └── system-architecture.md  # High-level design, network topology
│   ├── lld/
│   │   ├── data-flow.md         # Sequence diagrams
│   │   ├── network-topology.md  # Network design details
│   │   └── images/              # Architecture diagrams
│   └── concepts/
│       └── environments.md      # Dev vs prod environments
├── decisions/
│   ├── 001-backend-framework.md    # ADR: Why FastAPI
│   ├── 002-frontend-framework.md   # ADR: Why React + Vite
│   ├── 003-reverse-proxy.md        # ADR: Nginx choice
│   ├── 004-database-strategy.md    # ADR: PostgreSQL choice
│   ├── 005-database-isolation.md   # ADR: Network isolation
│   ├── 006-caching-stratagy.md     # ADR: Redis strategy
│   ├── 007-ledger-pattern-vs-snapshot-updates.md  # ADR: Ledger pattern
│   ├── 008-multi-stage-builds.md   # ADR: Docker optimization
│   ├── 009-dual-environment-config.md  # ADR: Dev/prod configs
│   └── 100-future-ADR.md           # Template for new decisions
├── runbooks/
│   └── aws-manual-deployment.md    # Deployment procedures
├── logs/
│   └── troubleshooting.md          # Common issues and fixes
├── metrics/
│   └── optimization_report.md      # Performance metrics
├── cheatsheet.md                   # Quick reference guide
└── security.md                     # Security considerations
```

### Documentation Conventions
- **ADRs (Architecture Decision Records)**: Numbered sequentially (001, 002, etc.)
- **Format**: Context → Decision → Justification → Consequences
- Use Mermaid diagrams for architecture visualization
- Keep docs close to code—update with architectural changes

## Docker Configuration

### Development vs Production
- **Development**: Uses `Dockerfile.dev` with hot reload, mounted volumes
- **Production**: Uses multi-stage `Dockerfile` for minimal image size

### Docker Networks
- **frontend_tier**: Accessible by frontend and backend
- **backend_tier**: Private network for database and Redis
- Frontend CANNOT access database directly (security by design)

### Container Naming
- `inventory_db` - PostgreSQL database
- `inventory_redis` - Redis cache
- `inventory_backend` - FastAPI service
- `inventory_frontend` - React application

## Environment Configuration
- `.env.example` - Template with required variables
- `.env` - Actual configuration (git-ignored)
- Variables injected via `env_file` in docker-compose

### Required Environment Variables
```
POSTGRES_USER=<username>
POSTGRES_PASSWORD=<password>
POSTGRES_DB=<database_name>
VITE_API_URL=http://localhost:8000
```

## File Naming Conventions
- **Python**: snake_case (e.g., `database.py`, `stock_movements`)
- **JavaScript/React**: PascalCase for components (e.g., `App.jsx`), camelCase for utilities
- **Docker**: `Dockerfile` (production), `Dockerfile.dev` (development)
- **Config files**: kebab-case (e.g., `docker-compose.yml`)
- **Documentation**: kebab-case (e.g., `system-architecture.md`)

## Port Mapping
- **8000**: Backend API (FastAPI/Uvicorn)
- **5173**: Frontend dev server (Vite)
- **5432**: PostgreSQL (internal to backend_tier only)
- **6379**: Redis (internal to backend_tier only)

## Code Organization Principles

### Backend
- Keep route handlers in `main.py` (or separate routers as app grows)
- Database models in `models.py`
- Use dependency injection for database sessions
- Async endpoints for I/O-bound operations

### Frontend
- Component-based architecture
- Co-locate styles with components
- Use React hooks for state management
- Keep API calls separate from UI logic

### Database
- Follow the Ledger Pattern—never delete from `stock_movements`
- Use transactions for write operations
- Maintain `current_stock` as a denormalized cache
- Categories and products use foreign key relationships
