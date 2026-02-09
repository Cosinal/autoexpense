"""
Receipts API router for listing and filtering receipts.
Production-grade implementation with Decimal support and signed URLs.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import date
from decimal import Decimal
import math
import logging

from app.models.receipt import ReceiptResponse, ReceiptList
from app.utils.supabase import get_supabase_client
from app.services.storage import StorageService

router = APIRouter(prefix="/receipts", tags=["receipts"])
logger = logging.getLogger(__name__)


def generate_signed_url_for_receipt(receipt_data: dict) -> dict:
    """
    Generate signed URL for receipt file access using file_path.

    Args:
        receipt_data: Receipt dictionary from database

    Returns:
        Receipt data with signed URL added
    """
    try:
        file_path = receipt_data.get('file_path')

        if not file_path:
            logger.warning("Receipt missing file_path", extra={
                "receipt_id": receipt_data.get('id')
            })
            return receipt_data

        storage = StorageService()

        # Generate signed URL (valid for 1 hour)
        signed_url = storage.signed_url(file_path, expires_in=3600)

        if signed_url:
            receipt_data['file_url'] = signed_url
        else:
            logger.warning("Failed to generate signed URL", extra={
                "receipt_id": receipt_data.get('id'),
                "file_path": file_path
            })

    except Exception as e:
        logger.error("Error generating signed URL", extra={
            "receipt_id": receipt_data.get('id'),
            "error": str(e)
        })

    return receipt_data


@router.get("", response_model=ReceiptList)
async def list_receipts(
    user_id: str = Query(..., description="User ID"),
    vendor: Optional[str] = Query(None, description="Filter by vendor name"),
    min_amount: Optional[Decimal] = Query(None, description="Minimum amount"),
    max_amount: Optional[Decimal] = Query(None, description="Maximum amount"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    currency: Optional[str] = Query(None, description="Filter by currency"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page")
):
    """
    List receipts for a user with optional filtering and pagination.

    Filters:
    - vendor: Search by vendor name (partial match)
    - min_amount/max_amount: Filter by amount range
    - start_date/end_date: Filter by date range
    - currency: Filter by currency code

    Returns paginated list of receipts.
    """
    try:
        supabase = get_supabase_client()

        # Build query
        query = supabase.table('receipts').select('*', count='exact')

        # Apply user filter
        query = query.eq('user_id', user_id)

        # Apply filters
        if vendor:
            query = query.ilike('vendor', f'%{vendor}%')

        if min_amount is not None:
            query = query.gte('amount', str(min_amount))

        if max_amount is not None:
            query = query.lte('amount', str(max_amount))

        if start_date:
            query = query.gte('date', start_date.isoformat())

        if end_date:
            query = query.lte('date', end_date.isoformat())

        if currency:
            query = query.eq('currency', currency.upper())

        # Get total count
        count_response = query.execute()
        total = count_response.count if hasattr(count_response, 'count') else len(count_response.data)

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order('created_at', desc=True).range(offset, offset + page_size - 1)

        # Execute query
        response = query.execute()

        # Generate signed URLs for all receipts
        receipts_with_signed_urls = [
            generate_signed_url_for_receipt(receipt)
            for receipt in response.data
        ]

        # Calculate pagination
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return ReceiptList(
            receipts=receipts_with_signed_urls,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error("Failed to fetch receipts", extra={
            "user_id": user_id,
            "error": str(e)
        }, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch receipts: {str(e)}"
        )


@router.get("/{receipt_id}", response_model=ReceiptResponse)
async def get_receipt(receipt_id: str, user_id: str = Query(..., description="User ID")):
    """
    Get a single receipt by ID.

    Args:
        receipt_id: Receipt UUID
        user_id: User ID (for authorization)

    Returns:
        Receipt details with signed URL
    """
    try:
        supabase = get_supabase_client()

        response = supabase.table('receipts').select('*').eq('id', receipt_id).eq(
            'user_id', user_id
        ).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Receipt not found")

        # Generate signed URL for the receipt
        receipt_data = generate_signed_url_for_receipt(response.data[0])

        return receipt_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch receipt", extra={
            "receipt_id": receipt_id,
            "user_id": user_id,
            "error": str(e)
        }, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch receipt: {str(e)}"
        )


@router.delete("/{receipt_id}")
async def delete_receipt(receipt_id: str, user_id: str = Query(..., description="User ID")):
    """
    Delete a receipt and its associated file.

    Args:
        receipt_id: Receipt UUID
        user_id: User ID (for authorization)

    Returns:
        Success message
    """
    try:
        supabase = get_supabase_client()
        storage = StorageService()

        # Get the receipt first to verify ownership and get file path
        response = supabase.table('receipts').select('*').eq('id', receipt_id).eq(
            'user_id', user_id
        ).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Receipt not found")

        receipt = response.data[0]
        file_path = receipt.get('file_path')

        # Delete from database
        supabase.table('receipts').delete().eq('id', receipt_id).execute()

        # Delete file from storage
        if file_path:
            storage.delete_file(file_path)
            logger.info("Deleted receipt and file", extra={
                "receipt_id": receipt_id,
                "file_path": file_path
            })
        else:
            logger.warning("Receipt had no file_path", extra={
                "receipt_id": receipt_id
            })

        return {"message": "Receipt deleted successfully", "id": receipt_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete receipt", extra={
            "receipt_id": receipt_id,
            "user_id": user_id,
            "error": str(e)
        }, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete receipt: {str(e)}"
        )


@router.get("/stats/summary")
async def get_receipt_stats(
    user_id: str = Query(..., description="User ID"),
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date")
):
    """
    Get summary statistics for receipts.

    Returns:
        Total count, total amount, average amount, by currency
    """
    try:
        supabase = get_supabase_client()

        # Build query
        query = supabase.table('receipts').select('amount,currency').eq('user_id', user_id)

        if start_date:
            query = query.gte('date', start_date.isoformat())
        if end_date:
            query = query.lte('date', end_date.isoformat())

        response = query.execute()
        receipts = response.data

        # Calculate stats
        total_count = len(receipts)

        if total_count == 0:
            return {
                "total_count": 0,
                "total_amount": 0,
                "average_amount": 0,
                "by_currency": {}
            }

        # Group by currency
        by_currency = {}
        for receipt in receipts:
            amount_str = receipt.get('amount')
            currency = receipt.get('currency', 'USD')

            # Convert string to Decimal
            try:
                amount = Decimal(amount_str) if amount_str else Decimal('0')
            except (ValueError, TypeError):
                amount = Decimal('0')

            if currency not in by_currency:
                by_currency[currency] = {
                    "count": 0,
                    "total": Decimal('0'),
                    "average": Decimal('0')
                }

            by_currency[currency]["count"] += 1
            by_currency[currency]["total"] += amount

        # Calculate averages and convert to float for JSON
        for currency in by_currency:
            if by_currency[currency]["count"] > 0:
                avg = by_currency[currency]["total"] / by_currency[currency]["count"]
                by_currency[currency]["average"] = float(round(avg, 2))
                by_currency[currency]["total"] = float(round(by_currency[currency]["total"], 2))

        return {
            "total_count": total_count,
            "by_currency": by_currency
        }

    except Exception as e:
        logger.error("Failed to fetch stats", extra={
            "user_id": user_id,
            "error": str(e)
        }, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch stats: {str(e)}"
        )
