from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import case, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from prometheus_fastapi_instrumentator import Instrumentator

from .config import settings
from .db import Base, engine, get_db
from .models import Product
from .schemas import ProductCreate, ProductOut, ProductUpdate, StatsOut, StockAdjustment

app = FastAPI(title=settings.app_name, version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

@app.on_event("startup")
def startup():
    # Production containers run Alembic before Uvicorn; create_all keeps tests self-contained.
    Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"service": settings.app_name, "version": "2.0.0", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "UP"}

@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(select(func.count(Product.id)))
    return {"status": "READY"}

def get_or_404(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.get("/api/products", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    return list(db.scalars(select(Product).order_by(Product.name)))

@app.get("/api/products/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db)):
    row = db.execute(select(
        func.count(Product.id),
        func.coalesce(func.sum(Product.quantity), 0),
        func.count(case((Product.quantity == 0, 1))),
        func.count(case(((Product.quantity > 0) & (Product.quantity <= Product.reorder_level), 1))),
        func.coalesce(func.sum(Product.quantity * Product.unit_price), 0),
    )).one()
    return StatsOut(products=row[0], units=row[1], outOfStock=row[2], lowStock=row[3], inventoryValue=float(row[4]))

@app.get("/api/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, product_id)

@app.post("/api/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    product = Product(**payload.model_dump())
    db.add(product)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"SKU {payload.sku} already exists")
    db.refresh(product)
    return product

@app.put("/api/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)):
    product = get_or_404(db, product_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product

@app.post("/api/products/{product_id}/adjust", response_model=ProductOut)
def adjust_stock(product_id: int, payload: StockAdjustment, db: Session = Depends(get_db)):
    # Single atomic UPDATE so concurrent adjustments can't overwrite each other
    result = db.execute(
        update(Product)
        .where(Product.id == product_id, Product.quantity + payload.delta >= 0)
        .values(quantity=Product.quantity + payload.delta)
    )
    db.commit()
    product = get_or_404(db, product_id)
    if result.rowcount == 0:
        raise HTTPException(status_code=400, detail=f"Only {product.quantity} units in stock")
    db.refresh(product)
    return product

@app.delete("/api/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, product_id))
    db.commit()
