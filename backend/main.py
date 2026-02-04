from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import models
import database

# 1. App Initialization
app = FastAPI()

# 2. Root Endpoint
@app.get("/")
def read_root():
    return {"message": "Inventory System API is Running"}

# 3. Health Check (The Real Test)
# We inject the database session using Depends(database.get_db)
@app.get("/health")
def health_check(db: Session = Depends(database.get_db)):
    try:
        # Run a simple SQL query to verify connection
        result = db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

# 4. Test Data Endpoint (Optional - Just to see your Init SQL data)
@app.get("/products")
def get_products(db: Session = Depends(database.get_db)):
    products = db.query(models.Product).all()
    return products