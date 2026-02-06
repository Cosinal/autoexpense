"""
Email sync router for triggering manual email ingestion.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.ingestion import IngestionService

router = APIRouter(prefix="/sync", tags=["sync"])


class SyncRequest(BaseModel):
    """Request model for sync endpoint."""
    user_id: str
    days_back: Optional[int] = 7


class SyncResponse(BaseModel):
    """Response model for sync endpoint."""
    success: bool
    messages_checked: int
    messages_processed: int
    receipts_created: int
    errors: list


@router.post("", response_model=SyncResponse)
async def sync_emails(request: SyncRequest):
    """
    Manually trigger email sync for a user.

    This endpoint:
    1. Fetches unprocessed emails from Gmail
    2. Extracts attachments
    3. Uploads files to storage
    4. Creates receipt records

    Args:
        request: Sync request with user_id and optional days_back

    Returns:
        Summary of sync operation
    """
    try:
        ingestion = IngestionService()

        summary = ingestion.sync_emails(
            user_id=request.user_id,
            days_back=request.days_back
        )

        return SyncResponse(
            success=len(summary['errors']) == 0,
            messages_checked=summary['messages_checked'],
            messages_processed=summary['messages_processed'],
            receipts_created=summary['receipts_created'],
            errors=summary['errors']
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {str(e)}"
        )


@router.get("/status")
async def sync_status():
    """
    Check if email sync service is configured and ready.

    Returns:
        Configuration status
    """
    from app.config import settings

    config_status = {
        "gmail_configured": bool(settings.GMAIL_CLIENT_ID and
                                settings.GMAIL_CLIENT_SECRET and
                                settings.GMAIL_REFRESH_TOKEN),
        "intake_email": settings.INTAKE_EMAIL or "Not configured",
        "supabase_connected": bool(settings.SUPABASE_URL and
                                   settings.SUPABASE_SERVICE_KEY)
    }

    return {
        "ready": all(config_status.values()),
        "config": config_status
    }
