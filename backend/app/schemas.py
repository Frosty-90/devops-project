from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

StockStatus = Literal["IN_STOCK", "LOW_STOCK", "OUT_OF_STOCK"]

class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(default="General", max_length=80)
    supplier: str = Field(default="", max_length=120)
    quantity: int = Field(default=0, ge=0)
    reorder_level: int = Field(default=10, ge=0)
    unit_price: float = Field(default=0, ge=0)

class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=80)
    supplier: str | None = Field(default=None, max_length=120)
    quantity: int | None = Field(default=None, ge=0)
    reorder_level: int | None = Field(default=None, ge=0)
    unit_price: float | None = Field(default=None, ge=0)

class StockAdjustment(BaseModel):
    delta: int = Field(description="Units received (positive) or shipped (negative)")

class ProductOut(ProductCreate):
    id: int
    stock_status: StockStatus
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class StatsOut(BaseModel):
    products: int
    units: int
    lowStock: int
    outOfStock: int
    inventoryValue: float
