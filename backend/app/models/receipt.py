"""
Pydantic models for receipts.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from decimal import Decimal


class ReceiptBase(BaseModel):
    """Base receipt model."""
    vendor: Optional[str] = None
    amount: Optional[float] = None
    currency: str = "USD"
    date: Optional[date] = None
    tax: Optional[float] = None
    file_name: Optional[str] = None
    mime_type: Optional[str] = None


class ReceiptCreate(ReceiptBase):
    """Model for creating a receipt."""
    user_id: str
    file_url: str
    file_hash: str


class ReceiptResponse(ReceiptBase):
    """Model for receipt API responses."""
    id: str
    user_id: str
    file_url: str
    file_hash: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReceiptList(BaseModel):
    """Model for paginated receipt list."""
    receipts: list[ReceiptResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ReceiptFilter(BaseModel):
    """Model for filtering receipts."""
    user_id: str
    vendor: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    currency: Optional[str] = None
    page: int = 1
    page_size: int = 50
