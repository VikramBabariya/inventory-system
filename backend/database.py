from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# 1. Get the URL from the environment (Secure)
# We default to a dummy string to prevent crashes if env is missing, 
# but the code will fail when trying to connect (Fail Fast).
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")

# 2. Create the Engine (The Connection Pool)
# echo=True means "Print all SQL queries to the console" -> Great for debugging!
engine = create_engine(DATABASE_URL, echo=True)

# 3. Create the Session Local class
# Each request will get its own separate database session.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Create the Base class
# All our models (Product, Category) will inherit from this.
Base = declarative_base()

# 5. Dependency Injection (The "FastAPI Way")
# This function ensures we open a connection, do work, and ALWAYS close it.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()