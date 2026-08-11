from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text
from pydantic import BaseModel
import redis
import models
import database
import cache as cache_module
from cache import (
    get_cache,
    cache_get,
    cache_set,
    cache_delete,
    PRODUCTS_ALL_KEY,
    movements_key,
)

# 1. App Initialization
app = FastAPI(title="Inventory System API")

# 2. CORS (permissive for dev; nginx proxy handles prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Pydantic Schemas
class MovementCreate(BaseModel):
    change_amount: int
    movement_type: str  # SALE, RESTOCK, RETURN, DAMAGE

# 4. Root
@app.get("/")
def read_root():
    return {"message": "Inventory System API is Running"}

# 5. Health Check — also reports Redis connectivity status
@app.get("/health")
def health_check(db: Session = Depends(database.get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

    # Check Redis separately — Redis being down is degraded, not unhealthy
    redis_client = cache_module.get_redis_client()
    try:
        redis_status = "connected" if redis_client and redis_client.ping() else "unavailable"
    except redis.RedisError:
        redis_status = "unavailable"

    return {"status": "healthy", "database": db_status, "cache": redis_status}

# 6. Get all products (with category eagerly loaded)
# Cache strategy: READ from cache first; on MISS query DB and populate cache.
@app.get("/products")
def get_products(
    db: Session = Depends(database.get_db),
    cache: redis.Redis | None = Depends(get_cache),
):
    # --- Cache READ ---
    cached = cache_get(cache, PRODUCTS_ALL_KEY)
    if cached is not None:
        return cached

    # --- Cache MISS: query PostgreSQL ---
    products = (
        db.query(models.Product)
        .options(joinedload(models.Product.category))
        .all()
    )
    result = []
    for p in products:
        result.append({
            "id": p.id,
            "sku": p.sku,
            "name": p.name,
            "price": str(p.price),
            "current_stock": p.current_stock,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "category": {"id": p.category.id, "name": p.category.name} if p.category else None,
        })

    # --- Populate cache ---
    cache_set(cache, PRODUCTS_ALL_KEY, result)

    return result

# 7. Record a stock movement (sale or restock)
# Cache strategy: WRITE to DB, then INVALIDATE affected cache keys.
@app.post("/products/{product_id}/movements")
def create_movement(
    product_id: int,
    body: MovementCreate,
    db: Session = Depends(database.get_db),
    cache: redis.Redis | None = Depends(get_cache),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Validate stock won't go negative
    new_stock = product.current_stock + body.change_amount
    if new_stock < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock. Available: {product.current_stock}"
        )

    allowed_types = {"SALE", "RESTOCK", "RETURN", "DAMAGE"}
    if body.movement_type.upper() not in allowed_types:
        raise HTTPException(status_code=400, detail=f"movement_type must be one of {allowed_types}")

    # Append to ledger
    movement = models.StockMovement(
        product_id=product_id,
        change_amount=body.change_amount,
        movement_type=body.movement_type.upper(),
    )
    db.add(movement)

    # Update denormalized snapshot
    product.current_stock = new_stock
    db.commit()

    # --- Cache INVALIDATION ---
    # current_stock changed → product list is stale
    # new movement added   → movement history for this product is stale
    cache_delete(cache, PRODUCTS_ALL_KEY, movements_key(product_id))

    return {"id": movement.id, "product_id": product_id, "new_stock": new_stock}

# 8. Get movement history for a product
# Cache strategy: READ from cache first; on MISS query DB and populate cache.
@app.get("/products/{product_id}/movements")
def get_movements(
    product_id: int,
    db: Session = Depends(database.get_db),
    cache: redis.Redis | None = Depends(get_cache),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    key = movements_key(product_id)

    # --- Cache READ ---
    cached = cache_get(cache, key)
    if cached is not None:
        return cached

    # --- Cache MISS: query PostgreSQL ---
    movements = (
        db.query(models.StockMovement)
        .filter(models.StockMovement.product_id == product_id)
        .order_by(models.StockMovement.created_at.desc())
        .all()
    )
    result = [
        {
            "id": m.id,
            "change_amount": m.change_amount,
            "movement_type": m.movement_type,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in movements
    ]

    # --- Populate cache ---
    cache_set(cache, key, result)

    return result
