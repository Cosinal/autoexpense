"""
Receipts API router for listing and filtering receipts.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import date
import math

from app.models.receipt import ReceiptResponse, ReceiptList
from app.utils.supabase import get_supabase_client

router = APIRouter(prefix="/receipts", tags=["receipts"])


@router.get("", response_model=ReceiptList)
async def list_receipts(
    user_id: str = Query(..., description="User ID"),
    vendor: Optional[str] = Query(None, description="Filter by vendor name"),
    min_amount: Optional[float] = Query(None, description="Minimum amount"),
    max_amount: Optional[float] = Query(None, description="Maximum amount"),
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
            query = query.gte('amount', min_amount)

        if max_amount is not None:
            query = query.lte('amount', max_amount)

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

        # Calculate pagination
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return ReceiptList(
            receipts=response.data,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
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
        Receipt details
    """
    try:
        supabase = get_supabase_client()

        response = supabase.table('receipts').select('*').eq('id', receipt_id).eq(
            'user_id', user_id
        ).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Receipt not found")

        return response.data[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch receipt: {str(e)}"
        )


@router.delete("/{receipt_id}")
async def delete_receipt(receipt_id: str, user_id: str = Query(..., description="User ID")):
    """
    Delete a receipt.

    Args:
        receipt_id: Receipt UUID
        user_id: User ID (for authorization)

    Returns:
        Success message
    """
    try:
        supabase = get_supabase_client()

        # Get the receipt first to verify ownership and get file path
        response = supabase.table('receipts').select('*').eq('id', receipt_id).eq(
            'user_id', user_id
        ).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Receipt not found")

        receipt = response.data[0]

        # Delete from database
        supabase.table('receipts').delete().eq('id', receipt_id).execute()

        # TODO: Delete file from storage
        # This would require extracting file path from file_url
        # and calling storage.delete()

        return {"message": "Receipt deleted successfully", "id": receipt_id}

    except HTTPException:
        raise
    except Exception as e:
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
            amount = receipt.get('amount', 0) or 0
            currency = receipt.get('currency', 'USD')

            if currency not in by_currency:
                by_currency[currency] = {
                    "count": 0,
                    "total": 0,
                    "average": 0
                }

            by_currency[currency]["count"] += 1
            by_currency[currency]["total"] += amount

        # Calculate averages
        for currency in by_currency:
            if by_currency[currency]["count"] > 0:
                by_currency[currency]["average"] = round(
                    by_currency[currency]["total"] / by_currency[currency]["count"], 2
                )

        return {
            "total_count": total_count,
            "by_currency": by_currency
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch stats: {str(e)}"
        )
