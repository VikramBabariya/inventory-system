ADR 004: Selection of PostgreSQL as Primary Datastore

Status: Accepted Context: The Inventory System manages highly structured data (Products, Stock Levels, Orders) with strict relationships. We need to ensure data consistency—e.g., we cannot sell a product that doesn't exist.

Decision: We chose PostgreSQL (Relational Database).

Justification:

ACID Compliance (vs. NoSQL): Inventory management requires strict "Atomicity." When a product is bought, the stock deduction and order creation must happen together or fail together. We cannot risk "eventual consistency" (common in NoSQL like MongoDB) where the stock count might be wrong for a few seconds.

Relational Integrity: We need Foreign Keys. A StockEntry must be linked to a valid Product. PostgreSQL enforces this at the engine level.

Advanced Features: PostgreSQL offers powerful features like JSONB (to store unstructured product attributes) and robust concurrency control (MVCC) to handle multiple admins updating stock simultaneously.

Market Relevance: It is the default choice for modern cloud-native applications in the Indian tech industry, widely preferred over MySQL for complex applications.