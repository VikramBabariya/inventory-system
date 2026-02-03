-- 1. Categories Table (Lookup table)
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);

-- 2. Products Table (Master Data)
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(20) UNIQUE NOT NULL, -- Stock Keeping Unit (Barcode)
    name VARCHAR(100) NOT NULL,
    category_id INTEGER REFERENCES categories(id),
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    current_stock INTEGER DEFAULT 0, -- Denormalized field for speed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Inventory Transactions (The Ledger / Audit Trail)
-- We never DELETE from here. This is our history.
CREATE TABLE IF NOT EXISTS stock_movements (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    change_amount INTEGER NOT NULL, -- Negative for removal, Positive for addition
    movement_type VARCHAR(20) NOT NULL, -- 'SALE', 'RESTOCK', 'RETURN', 'DAMAGE'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Initial Seed Data
INSERT INTO categories (name) VALUES ('Electronics'), ('Accessories');

INSERT INTO products (sku, name, category_id, price, current_stock) VALUES 
('LPT-001', 'MacBook Pro', 1, 2000.00, 10),
('MSE-001', 'Logitech MX Master', 2, 99.00, 50);

-- Record the initial stock as a movement too (Best Practice)
INSERT INTO stock_movements (product_id, change_amount, movement_type) VALUES
(1, 10, 'RESTOCK'),
(2, 50, 'RESTOCK');