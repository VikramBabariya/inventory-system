ADR-007: The Ledger Pattern vs. Snapshot Updates

**Context** 
In a standard CRUD application, inventory is often handled by simply overwriting the value: `UPDATE products SET quantity = 45 WHERE id = 1;`

**Problem** 
Overwriting data destroys history. If stock goes missing, we cannot determine if it was due to a sale, theft, or data corruption. It prevents auditing and debugging.

**Decision** 
We implemented the Ledger Pattern (similar to a Bank Passbook).

1. **Source of Truth**: The stock_movements table is the source of truth. The actual stock is mathematically the sum of all movements.

2. **Performance Optimization**: We maintain a current_stock column on the products table. This is updated strictly as a consequence of a movement.

**Example Flow**

- Action: User sells 5 iPhones.

- Step 1 (Ledger): Insert row into stock_movements (change_amount: -5, type: 'SALE').

- Step 2 (Snapshot): Update products (current_stock = current_stock - 5).