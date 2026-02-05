"""
Export API router for generating CSV and other export formats.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import date
import io
import csv

from app.utils.supabase import get_supabase_client

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/csv")
async def export_csv(
    user_id: str = Query(..., description="User ID"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    currency: Optional[str] = Query(None, description="Filter by currency")
):
    """
    Export receipts as CSV file.

    Filters:
    - start_date/end_date: Export receipts in date range
    - currency: Export only receipts in specific currency

    Returns:
        CSV file download
    """
    try:
        supabase = get_supabase_client()

        # Build query
        query = supabase.table('receipts').select('*').eq('user_id', user_id)

        # Apply filters
        if start_date:
            query = query.gte('date', start_date.isoformat())
        if end_date:
            query = query.lte('date', end_date.isoformat())
        if currency:
            query = query.eq('currency', currency.upper())

        # Order by date
        query = query.order('date', desc=False)

        # Execute query
        response = query.execute()
        receipts = response.data

        if not receipts:
            raise HTTPException(status_code=404, detail="No receipts found for export")

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            'Date',
            'Vendor',
            'Amount',
            'Currency',
            'Tax',
            'File Name',
            'File URL',
            'Receipt ID'
        ])

        # Write data
        for receipt in receipts:
            writer.writerow([
                receipt.get('date', ''),
                receipt.get('vendor', ''),
                receipt.get('amount', ''),
                receipt.get('currency', 'USD'),
                receipt.get('tax', ''),
                receipt.get('file_name', ''),
                receipt.get('file_url', ''),
                receipt.get('id', '')
            ])

        # Prepare filename
        filename = f"receipts_{user_id}"
        if start_date and end_date:
            filename += f"_{start_date}_{end_date}"
        elif start_date:
            filename += f"_{start_date}_onwards"
        elif end_date:
            filename += f"_until_{end_date}"
        filename += ".csv"

        # Return as downloadable file
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export CSV: {str(e)}"
        )


@router.get("/summary")
async def export_summary(
    user_id: str = Query(..., description="User ID"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get export summary with totals by month and currency.

    Returns:
        JSON with monthly breakdown and totals
    """
    try:
        supabase = get_supabase_client()

        # Build query
        query = supabase.table('receipts').select('date,amount,currency,vendor').eq(
            'user_id', user_id
        )

        if start_date:
            query = query.gte('date', start_date.isoformat())
        if end_date:
            query = query.lte('date', end_date.isoformat())

        response = query.execute()
        receipts = response.data

        if not receipts:
            return {
                "total_receipts": 0,
                "date_range": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                },
                "by_month": {},
                "by_currency": {},
                "grand_total": {}
            }

        # Group by month and currency
        by_month = {}
        by_currency = {}
        grand_total = {}

        for receipt in receipts:
            receipt_date = receipt.get('date')
            amount = receipt.get('amount', 0) or 0
            currency = receipt.get('currency', 'USD')

            if not receipt_date:
                continue

            # Extract year-month
            month_key = receipt_date[:7]  # YYYY-MM

            # Group by month
            if month_key not in by_month:
                by_month[month_key] = {"count": 0, "total": {}}

            by_month[month_key]["count"] += 1

            if currency not in by_month[month_key]["total"]:
                by_month[month_key]["total"][currency] = 0

            by_month[month_key]["total"][currency] += amount

            # Group by currency
            if currency not in by_currency:
                by_currency[currency] = {"count": 0, "total": 0}

            by_currency[currency]["count"] += 1
            by_currency[currency]["total"] += amount

            # Grand total
            if currency not in grand_total:
                grand_total[currency] = 0
            grand_total[currency] += amount

        return {
            "total_receipts": len(receipts),
            "date_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "by_month": by_month,
            "by_currency": by_currency,
            "grand_total": grand_total
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate summary: {str(e)}"
        )
