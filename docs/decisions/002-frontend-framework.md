ADR 002: Selection of React + Vite for Frontend Service

Status: Accepted Context: The Inventory System requires a highly interactive "Single Page Application" (SPA) where stock updates happen in real-time without reloading the page.

Decision: We chose React (bootstrapped with Vite).

Justification:

Virtual DOM: React updates only the specific numbers in the table that changed (e.g., stock count) rather than reloading the entire webpage. This is critical for an inventory dashboard with frequent updates.

Component Architecture: We can build reusable components (e.g., <ProductCard />, <StockBadge />) which keeps the code clean and modular.

Vite vs. Create-React-App (CRA): We explicitly chose Vite over the older CRA because Vite uses native ES modules in the browser. It starts the dev server in milliseconds, whereas CRA takes several seconds/minutes as the project grows.

Market Standard: React is the dominant frontend library in the Indian tech ecosystem.

Consequences:

We must handle "Client-Side Routing" (using react-router-dom) since the browser never actually asks the server for new HTML pages.