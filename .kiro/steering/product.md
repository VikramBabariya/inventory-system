# Product Overview

## What This Is
An inventory management system with real-time stock tracking, designed for warehouse operations. The system provides a dashboard for viewing products, managing stock levels, and auditing inventory changes.

## Core Capabilities
- Product catalog management with SKU-based tracking
- Real-time stock level monitoring
- Complete audit trail of all inventory movements (sales, restocks, returns)
- Category-based product organization
- Performance-optimized with Redis caching

## Key Architecture Principles

### Ledger Pattern
The system uses an immutable ledger for stock movements (similar to bank transactions):
- `stock_movements` table is the source of truth
- All changes are recorded as deltas (+10, -5) not absolute values
- `current_stock` in products table is a denormalized cache for performance
- Never overwrite history—always append to the ledger

### Network Isolation
- **Frontend tier**: Public-facing (React, Nginx)
- **Backend tier**: Private, isolated network (Database, Redis)
- Frontend cannot directly access database—security by design

### Performance Strategy
- Redis cache for high-speed reads (1-hour TTL)
- Cache invalidation on writes to maintain consistency
- Multi-stage Docker builds for minimal container size (95% reduction)
