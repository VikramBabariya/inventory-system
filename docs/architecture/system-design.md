# System Architecture & Security Design

## 1. High-Level Network Topology
This diagram illustrates the separation between the public-facing frontend tier and the isolated backend tier using Docker networks.

```mermaid
graph TD
    Internet((Internet User / API Client)) -->|Port 80: HTTP| Nginx[Nginx Reverse Proxy]

    subgraph "Network: frontend-tier (Public Facing)"
        Nginx -->|Proxy Pass /api| Backend[Backend API Container<br/>Python FastAPI:8000]
        Nginx -->|Proxy Pass /| Frontend[Frontend Container<br/>React/Node:3000]
    end

    subgraph "Network: backend-tier (Private / Isolated)"
        Backend -->|TCP 5432| DB[(Database Container<br/>PostgreSQL)]
        Backend -->|TCP 6379| Redis[(Cache Container<br/>Redis)]
    end

    %% Styling
    style Nginx fill:#f97316,stroke:#c2410c,color:white,stroke-width:2px
    style Backend fill:#3b82f6,stroke:#1d4ed8,color:white,stroke-width:2px
    style Frontend fill:#3b82f6,stroke:#1d4ed8,color:white,stroke-width:2px
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
    participant Client as Warehouse Admin
    participant API as Python Backend
    participant Redis as Redis Cache
    participant DB as PostgreSQL DB

    Note over Client, DB: Scenario 1: High-Speed READ (Viewing Dashboard)
    Client->>API: GET /stock/iphone-15
    API->>Redis: Exists in cache? (KEY: stock:iphone-15)
    alt Cache HIT (Data exists)
        Redis-->>API: Return stock count (e.g., 50)
        API-->>Client: Return 200 OK (Fast Response)
    else Cache MISS (First time load)
        Redis-->>API: No
        API->>DB: SELECT stock FROM items WHERE sku='iphone-15'
        DB-->>API: Return 50
        API->>Redis: SET stock:iphone-15 = 50 (TTL: 1 hour)
        API-->>Client: Return 200 OK (Slower Response)
    end

    Note over Client, DB: Scenario 2: Transactional WRITE (Updating Stock)
    Client->>API: POST /stock/update (sku='iphone-15', new_stock=45)
    API->>DB: UPDATE items SET stock=45...
    DB-->>API: Success Commit
    API->>Redis: INVALIDATE/DELETE (KEY: stock:iphone-15)
    Note right of Redis: Next read will force a DB fetch so data is fresh.
    API-->>Client: Return 201 Created
```