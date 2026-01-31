ADR 006: Implementation of Redis Caching Layer

Date: 2026-01-29 Status: Accepted

Context
Our application relies on a persistent database (Postgres/DynamoDB) as the source of truth. As user traffic increases, we are observing (or anticipating) two key issues:

 1. Read Latency: Repeated complex queries to the database are increasing response times.

 2. Database Load: High frequency of identical read requests (e.g., fetching user profile, product catalogs) is consuming unnecessary database resources (CPU/IOPS).

We need a mechanism to offload read-heavy traffic from the primary database to improve performance and scalability.


Decision
We will implement a caching layer using Redis (Remote Dictionary Server).

1. Technology Choice: We selected Redis over Memcached because:

    It supports complex data structures (Lists, Sets, Hashes) which are useful for future features (e.g., leaderboards, session store).

    It offers persistence options (AOF/RDB), allowing the cache to survive restarts if necessary.

    It is the industry standard for AWS/DevOps roles in our target market (India).

2. Placement & Networking:

    The Redis container will be placed on the private backend network alongside the Database.

    It will not expose ports to the host machine or the public internet. Access is restricted strictly to the Backend Service via internal Docker DNS.

3. Caching Pattern:
    We will use the Cache-Aside (Lazy Loading) pattern.
    
    Flow: App checks Redis --> If present (HIT), return data. --> If missing (MISS), fetch from DB, write to Redis, then return data.
    
    TTL (Time To Live): All cache keys must have a default TTL (e.g., 3600 seconds) to prevent stale data accumulation.

Consequences

Positive:
    Performance: Data retrieval for cached items reduces from milliseconds (disk) to microseconds (memory).

    Cost Efficiency: Reduces the read throughput required on the primary database, potentially lowering costs for managed databases (e.g., DynamoDB RCUs).

    Scalability: The application can handle significantly higher concurrent traffic spikes.

Negative:

    Complexity: Introduces a new infrastructure component to manage and monitor.

    Consistency: We introduce Eventual Consistency. There is a risk that data in the cache is "stale" if the database is updated but the cache is not invalidated immediately.

    Memory limits: Redis stores data in RAM. If the dataset grows beyond available memory, we must implement eviction policies (e.g., LRU - Least Recently Used).