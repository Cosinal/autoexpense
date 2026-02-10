"""
Review API router for manual correction of receipt data.
Stores user corrections for ML training.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal

from app.utils.supabase import get_supabase_client

router = APIRouter(prefix="/review", tags=["review"])


class ReviewCorrection(BaseModel):
    """Model for a single field correction."""
    original: Optional[Any]
    corrected_to: Any
    candidates: list[str] = []
    confidence: float


class SubmitReviewRequest(BaseModel):
    """Request model for submitting manual corrections."""
    receipt_id: str
    corrections: Dict[str, ReviewCorrection]
    user_id: str  # For tracking who made the correction


class SubmitReviewResponse(BaseModel):
    """Response model for review submission."""
    success: bool
    receipt_id: str
    fields_corrected: list[str]


@router.post("/submit", response_model=SubmitReviewResponse)
async def submit_review(request: SubmitReviewRequest):
    """
    Submit manual corrections for a receipt.

    This endpoint:
    1. Updates the receipt with corrected values
    2. Stores the original values + correction in user_corrections for ML training
    3. Sets needs_review=False
    4. Records timestamp of correction

    Args:
        request: Review corrections

    Returns:
        Success status
    """
    try:
        supabase = get_supabase_client()

        # Prepare updates
        updates = {
            'needs_review': False,
            'review_reason': None,
            'corrected_at': datetime.utcnow().isoformat()
        }

        # Build user_corrections for ML training
        user_corrections = {}

        for field_name, correction in request.corrections.items():
            # Update the actual field value
            if field_name == 'vendor':
                updates['vendor'] = correction.corrected_to
            elif field_name == 'amount':
                updates['amount'] = str(Decimal(correction.corrected_to))
            elif field_name == 'date':
                updates['date'] = correction.corrected_to
            elif field_name == 'currency':
                updates['currency'] = correction.corrected_to
            elif field_name == 'tax':
                updates['tax'] = str(Decimal(correction.corrected_to)) if correction.corrected_to else None

            # Store correction for ML training
            user_corrections[field_name] = {
                'original': correction.original,
                'corrected_to': correction.corrected_to,
                'candidates': correction.candidates,
                'confidence': correction.confidence,
                'corrected_by': request.user_id
            }

        updates['user_corrections'] = user_corrections

        # Update receipt in database
        response = supabase.table('receipts').update(updates).eq(
            'id', request.receipt_id
        ).execute()

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail=f"Receipt {request.receipt_id} not found"
            )

        return SubmitReviewResponse(
            success=True,
            receipt_id=request.receipt_id,
            fields_corrected=list(request.corrections.keys())
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit review: {str(e)}"
        )


@router.get("/pending")
async def get_pending_reviews(user_id: str, limit: int = 50):
    """
    Get receipts that need manual review.

    Args:
        user_id: User ID
        limit: Maximum number of receipts to return

    Returns:
        List of receipts needing review with candidate options
    """
    try:
        supabase = get_supabase_client()

        # Get receipts that need review
        response = supabase.table('receipts').select('*').eq(
            'user_id', user_id
        ).eq(
            'needs_review', True
        ).order(
            'created_at', desc=True
        ).limit(limit).execute()

        receipts = response.data

        # Add signed URLs for file access
        from app.services.storage import StorageService
        storage = StorageService()

        for receipt in receipts:
            if receipt.get('file_path'):
                signed_url = storage.signed_url(receipt['file_path'], expires_in=3600)
                if signed_url:
                    receipt['file_url'] = signed_url

        return {
            'receipts': receipts,
            'total': len(receipts)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch pending reviews: {str(e)}"
        )


@router.get("/corrections/export")
async def export_corrections(
    user_id: str,
    format: str = "jsonl"
):
    """
    Export user corrections for ML training.

    Returns all receipts with user_corrections in JSONL format
    suitable for training a correction model.

    Args:
        user_id: User ID (optional - admin can export all)
        format: Export format (jsonl or csv)

    Returns:
        Training data with corrections
    """
    try:
        supabase = get_supabase_client()

        # Get all receipts with corrections
        query = supabase.table('receipts').select('*')

        if user_id != 'admin':  # Allow admin to export all
            query = query.eq('user_id', user_id)

        response = query.not_.is_('user_corrections', 'null').execute()

        receipts = response.data

        if format == "jsonl":
            # Return JSONL format for ML training
            import json
            lines = []
            for receipt in receipts:
                training_example = {
                    'receipt_id': receipt['id'],
                    'original_text': None,  # Would need to store OCR text
                    'original_extractions': {
                        'vendor': receipt.get('vendor'),
                        'amount': receipt.get('amount'),
                        'date': receipt.get('date'),
                        'currency': receipt.get('currency'),
                        'tax': receipt.get('tax')
                    },
                    'corrections': receipt.get('user_corrections'),
                    'ingestion_debug': receipt.get('ingestion_debug'),
                    'corrected_at': receipt.get('corrected_at')
                }
                lines.append(json.dumps(training_example))

            return {
                'format': 'jsonl',
                'data': '\n'.join(lines),
                'count': len(lines)
            }

        return {
            'format': 'json',
            'data': receipts,
            'count': len(receipts)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export corrections: {str(e)}"
        )
