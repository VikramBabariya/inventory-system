from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DECIMAL, TIMESTAMP, text, CheckConstraint
from sqlalchemy.orm import relationship
from database import Base

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)

    # Relationship: One Category has many Products
    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, index=True, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    price = Column(DECIMAL(10, 2), CheckConstraint("price >= 0"), nullable=False)
    current_stock = Column(Integer, default=0) # Snapshot field
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    
    # Relationships
    category = relationship("Category", back_populates="products")
    movements = relationship("StockMovement", back_populates="product")


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"))
    change_amount = Column(Integer, nullable=False) # The Ledger delta
    movement_type = Column(String, nullable=False) # SALE, RESTOCK
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

    # Relationship
    product = relationship("Product", back_populates="movements")