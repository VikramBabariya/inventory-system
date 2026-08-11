# System Architecture & Security Design

## 1. High-Level Network Topology
This diagram illustrates the separation between the public-facing frontend tier and the isolated backend tier using Docker networks.

> **Note:** Nginx is **embedded inside the Frontend container** (not a separate service). The multi-stage production build compiles React into static files and serves them via Nginx. Nginx also proxies `/api/*` requests to the backend container.

```mermaid
graph TD
    Browser((Browser\nlocalhost:5173)) -->|Port 5173→80: HTTP| Frontend

    subgraph "Network: frontend-tier (Public Facing)"
        subgraph "Frontend Container"
            Nginx[Nginx :80\nServes React static files]
            React[React App\ncompiled to /dist]
        end
        Nginx -->|Proxy /api/ → :8000| Backend[Backend Container\nPython FastAPI :8000]
    end

    subgraph "Network: backend-tier (Private / Isolated)"
        Backend -->|TCP 5432| DB[(PostgreSQL :5432)]
        Backend -->|TCP 6379| Redis[(Redis :6379)]
    end

    %% Styling
    style Nginx fill:#f97316,stroke:#c2410c,color:white,stroke-width:2px
    style React fill:#61dafb,stroke:#0ea5e9,color:#111,stroke-width:2px
    style Backend fill:#3b82f6,stroke:#1d4ed8,color:white,stroke-width:2px
    style DB fill:#10b981,stroke:#047857,color:white,stroke-width:2px
    style Redis fill:#a855f7,stroke:#7e22ce,color:white,stroke-width:2px
```

## 2. Security Posture: Blast Radius Limitation
Even if the frontend is compromised, the database remains inaccessible due to network isolation.

```mermaid
graph TD
    subgraph "Hacker's View"
        Attacker[Attacker] -->|Compromises| Frontend[Frontend Container]
    end

    subgraph "Private Data Zone"
        DB[(Database Container<br/>PostgreSQL)]
    end

    Frontend -.-x|Blocked by Docker Network| DB

    Note[Architect Note:<br/>Frontend and DB are on different<br/>networks. No route exists.]

    %% Styling
    style Attacker fill:#000000,stroke:#ef4444,color:white
    style Frontend fill:#ef4444,stroke:#991b1b,color:white
    style DB fill:#10b981,stroke:#047857,color:white,stroke-width:2px
    style Note fill:#fffbeb,stroke:#f59e0b,stroke-dasharray: 5 5
```

## 3. Data Flow: Caching & Transaction Logic
Detailed sequence showing how the system handles high-speed reads and ensures data integrity during writes.

```mermaid
sequenceDiagram
    participant Browser as Browser (React)
    participant Nginx as Nginx (Frontend Container)
    participant API as FastAPI (Backend)
    participant Redis as Redis Cache
    participant DB as PostgreSQL DB

    Note over Browser, DB: Scenario 1: High-Speed READ (Loading Dashboard)
    Browser->>Nginx: GET /api/products
    Nginx->>API: GET /products (proxy strips /api/)
    API->>Redis: Exists in cache? (KEY: products:all)
    alt Cache HIT
        Redis-->>API: Return cached JSON
        API-->>Browser: 200 OK (fast)
    else Cache MISS
        Redis-->>API: No
        API->>DB: SELECT products JOIN categories
        DB-->>API: Return rows
        API->>Redis: SET products:all (TTL: 1 hour)
        API-->>Browser: 200 OK
    end

    Note over Browser, DB: Scenario 2: Transactional WRITE (Recording a Sale)
    Browser->>Nginx: POST /api/products/1/movements {change_amount: -1, movement_type: "SALE"}
    Nginx->>API: POST /products/1/movements (proxy)
    API->>DB: Validate: current_stock - 1 >= 0
    API->>DB: INSERT INTO stock_movements (ledger append)
    API->>DB: UPDATE products SET current_stock = current_stock - 1
    DB-->>API: Commit OK
    API->>Redis: INVALIDATE products:all
    Note right of Redis: Next read forces fresh DB fetch.
    API-->>Browser: 200 OK {new_stock: 9}
    Browser->>Nginx: GET /api/products (re-fetch to update UI)
```