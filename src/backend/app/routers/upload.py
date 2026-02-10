"""
Upload API router for direct file uploads.
Production-grade implementation with new storage API and Decimal precision.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
from decimal import Decimal
import uuid
import logging

from app.services.storage import StorageService
from app.services.ocr import OCRService
from app.services.parser import ReceiptParser, ParseContext
from app.utils.supabase import get_supabase_client

router = APIRouter(prefix="/upload", tags=["upload"])
logger = logging.getLogger(__name__)


def _decimal_to_str(value: Optional[Decimal]) -> Optional[str]:
    """Convert Decimal to string for database storage."""
    return str(value) if value is not None else None


@router.post("")
async def upload_receipt(
    file: UploadFile = File(...),
    user_id: str = Form(...)
):
    """
    Upload a receipt file directly (drag-and-drop or file selection).

    This endpoint:
    1. Accepts file upload (PDF, JPG, PNG)
    2. Stores file in Supabase Storage with content-addressed path
    3. Runs OCR and parsing
    4. Creates receipt record
    5. Returns parsed data with signed URL

    Args:
        file: Uploaded file
        user_id: User ID

    Returns:
        Receipt data with parsed fields
    """
    try:
        # Validate file type
        allowed_types = ["application/pdf", "image/jpeg", "image/jpg", "image/png"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.content_type}. Allowed: PDF, JPG, PNG"
            )

        # Validate file size (10MB limit)
        file_data = await file.read()
        file_size_mb = len(file_data) / (1024 * 1024)

        if file_size_mb > 10:
            raise HTTPException(
                status_code=400,
                detail=f"File too large: {file_size_mb:.2f}MB. Maximum: 10MB"
            )

        # Initialize services
        storage = StorageService()
        ocr = OCRService()
        parser = ReceiptParser()
        supabase = get_supabase_client()

        # Upload file to storage (content-addressed, idempotent)
        file_hash, file_path = storage.upload_receipt(
            user_id=user_id,
            filename=file.filename or "uploaded_receipt",
            file_data=file_data,
            mime_type=file.content_type or "application/octet-stream"
        )

        if not file_path:
            raise HTTPException(
                status_code=500,
                detail="Failed to upload file to storage"
            )

        logger.info("File uploaded to storage", extra={
            "user_id": user_id,
            "filename": file.filename,
            "file_hash": file_hash,
            "file_path": file_path
        })

        # Check if receipt with this hash already exists (deduplication)
        existing = supabase.table('receipts').select('id').eq(
            'user_id', user_id
        ).eq('file_hash', file_hash).limit(1).execute()

        if existing.data:
            receipt_id = existing.data[0]['id']
            logger.info("Duplicate file detected, returning existing receipt", extra={
                "receipt_id": receipt_id,
                "file_hash": file_hash
            })

            # Get full receipt data
            receipt_response = supabase.table('receipts').select('*').eq('id', receipt_id).execute()
            receipt_data = receipt_response.data[0]

            # Generate signed URL
            signed_url = storage.signed_url(file_path, expires_in=3600)
            if signed_url:
                receipt_data['file_url'] = signed_url

            return {
                **receipt_data,
                "message": "Receipt already exists (duplicate file)",
                "duplicate": True
            }

        # Run OCR
        logger.debug("Running OCR on uploaded file")
        ocr_text = ocr.extract_and_normalize(
            file_data=file_data,
            mime_type=file.content_type or "application/octet-stream",
            filename=file.filename or ""
        )

        # Parse receipt data (no email context for direct uploads)
        logger.debug("Parsing receipt data")
        parsed_data = parser.parse(ocr_text, context=None)

        # Smart currency defaulting with provenance tracking
        currency = parsed_data.get("currency")
        currency_source = "parsed"

        if currency is None:
            # No currency detected - use smart defaulting
            # TODO: Check user preferences
            currency = "USD"
            currency_source = "defaulted_to_usd"

            # Record warning in debug
            debug = parsed_data.get("debug", {})
            if "warnings" not in debug:
                debug["warnings"] = []
            debug["warnings"].append(f"Currency defaulted to {currency} (no strong evidence found)")
            parsed_data["debug"] = debug

            logger.debug("Currency defaulted", extra={
                "source": currency_source,
                "currency": currency
            })

        # Record currency source in debug
        if parsed_data.get("debug"):
            parsed_data["debug"]["currency_source"] = currency_source

        # Review flagging for low-confidence receipts
        confidence = parsed_data.get("confidence", 0.0)
        needs_review = False
        review_reason = None

        if confidence < 0.7:
            needs_review = True
            reasons = []

            if not parsed_data.get("vendor"):
                reasons.append("missing vendor")
            if not parsed_data.get("amount"):
                reasons.append("missing amount")
            if not parsed_data.get("date"):
                reasons.append("missing date")
            if currency_source == "defaulted_to_usd":
                reasons.append("defaulted currency")
            if confidence < 0.5:
                reasons.append(f"low confidence ({confidence:.2f})")
            elif confidence < 0.7:
                reasons.append(f"medium confidence ({confidence:.2f})")

            review_reason = "; ".join(reasons) if reasons else "low confidence extraction"

        # Create receipt record in database
        receipt_id = str(uuid.uuid4())
        receipt_data = {
            "id": receipt_id,
            "user_id": user_id,
            "file_path": file_path,
            "file_hash": file_hash,
            "file_name": file.filename,
            "mime_type": file.content_type,
            "vendor": parsed_data.get("vendor"),
            "amount": _decimal_to_str(parsed_data.get("amount")),
            "currency": currency,
            "date": parsed_data.get("date"),
            "tax": _decimal_to_str(parsed_data.get("tax")),
            "needs_review": needs_review,
            "review_reason": review_reason,
            "source_type": "upload",
            "ingestion_debug": parsed_data.get("debug")
        }

        response = supabase.table('receipts').insert(receipt_data).execute()

        if not response.data:
            # Cleanup orphaned file
            storage.delete_file(file_path)
            raise HTTPException(
                status_code=500,
                detail="Failed to create receipt record"
            )

        logger.info("Receipt created successfully", extra={
            "receipt_id": receipt_id,
            "vendor": parsed_data.get("vendor"),
            "amount": parsed_data.get("amount")
        })

        # Generate signed URL for response
        signed_url = storage.signed_url(file_path, expires_in=3600)
        if signed_url:
            receipt_data['file_url'] = signed_url

        return {
            **receipt_data,
            "message": "Receipt uploaded and processed successfully",
            "duplicate": False
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Upload failed", extra={
            "user_id": user_id,
            "filename": file.filename if file else None,
            "error": str(e)
        }, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )


@router.post("/bulk")
async def upload_bulk_receipts(
    files: list[UploadFile] = File(...),
    user_id: str = Form(...)
):
    """
    Upload multiple receipt files at once.

    Args:
        files: List of uploaded files
        user_id: User ID

    Returns:
        Summary of upload results
    """
    results = {
        "total": len(files),
        "successful": 0,
        "duplicates": 0,
        "failed": 0,
        "receipts": [],
        "errors": []
    }

    logger.info("Starting bulk upload", extra={
        "user_id": user_id,
        "file_count": len(files)
    })

    for file in files:
        try:
            # Validate file type
            allowed_types = ["application/pdf", "image/jpeg", "image/jpg", "image/png"]
            if file.content_type not in allowed_types:
                results["errors"].append({
                    "filename": file.filename,
                    "error": f"Invalid file type: {file.content_type}"
                })
                results["failed"] += 1
                continue

            # Read file data
            file_data = await file.read()

            # Initialize services
            storage = StorageService()
            ocr = OCRService()
            parser = ReceiptParser()
            supabase = get_supabase_client()

            # Upload file
            file_hash, file_path = storage.upload_receipt(
                user_id=user_id,
                filename=file.filename or "uploaded_receipt",
                file_data=file_data,
                mime_type=file.content_type or "application/octet-stream"
            )

            if not file_path:
                results["errors"].append({
                    "filename": file.filename,
                    "error": "Storage upload failed"
                })
                results["failed"] += 1
                continue

            # Check for duplicate
            existing = supabase.table('receipts').select('id').eq(
                'user_id', user_id
            ).eq('file_hash', file_hash).limit(1).execute()

            if existing.data:
                results["duplicates"] += 1
                results["receipts"].append({
                    "id": existing.data[0]['id'],
                    "filename": file.filename,
                    "duplicate": True
                })
                continue

            # Run OCR and parse
            ocr_text = ocr.extract_and_normalize(
                file_data=file_data,
                mime_type=file.content_type or "application/octet-stream",
                filename=file.filename or ""
            )

            parsed_data = parser.parse(ocr_text, context=None)

            # Smart currency defaulting with provenance tracking
            currency = parsed_data.get("currency")
            currency_source = "parsed"

            if currency is None:
                # No currency detected - use smart defaulting
                # TODO: Check user preferences
                currency = "USD"
                currency_source = "defaulted_to_usd"

                # Record warning in debug
                debug = parsed_data.get("debug", {})
                if "warnings" not in debug:
                    debug["warnings"] = []
                debug["warnings"].append(f"Currency defaulted to {currency} (no strong evidence found)")
                parsed_data["debug"] = debug

            # Record currency source in debug
            if parsed_data.get("debug"):
                parsed_data["debug"]["currency_source"] = currency_source

            # Review flagging for low-confidence receipts
            confidence = parsed_data.get("confidence", 0.0)
            needs_review = False
            review_reason = None

            if confidence < 0.7:
                needs_review = True
                reasons = []

                if not parsed_data.get("vendor"):
                    reasons.append("missing vendor")
                if not parsed_data.get("amount"):
                    reasons.append("missing amount")
                if not parsed_data.get("date"):
                    reasons.append("missing date")
                if currency_source == "defaulted_to_usd":
                    reasons.append("defaulted currency")
                if confidence < 0.5:
                    reasons.append(f"low confidence ({confidence:.2f})")
                elif confidence < 0.7:
                    reasons.append(f"medium confidence ({confidence:.2f})")

                review_reason = "; ".join(reasons) if reasons else "low confidence extraction"

            # Create receipt record
            receipt_id = str(uuid.uuid4())
            receipt_data = {
                "id": receipt_id,
                "user_id": user_id,
                "file_path": file_path,
                "file_hash": file_hash,
                "file_name": file.filename,
                "mime_type": file.content_type,
                "vendor": parsed_data.get("vendor"),
                "amount": _decimal_to_str(parsed_data.get("amount")),
                "currency": currency,
                "date": parsed_data.get("date"),
                "tax": _decimal_to_str(parsed_data.get("tax")),
                "needs_review": needs_review,
                "review_reason": review_reason,
                "source_type": "upload",
                "ingestion_debug": parsed_data.get("debug")
            }

            response = supabase.table('receipts').insert(receipt_data).execute()

            if response.data:
                results["successful"] += 1
                results["receipts"].append({
                    "id": receipt_id,
                    "filename": file.filename,
                    "vendor": parsed_data.get("vendor"),
                    "amount": str(parsed_data.get("amount")) if parsed_data.get("amount") else None,
                    "duplicate": False
                })
            else:
                # Cleanup orphaned file
                storage.delete_file(file_path)
                results["errors"].append({
                    "filename": file.filename,
                    "error": "Database insert failed"
                })
                results["failed"] += 1

        except Exception as e:
            logger.error("Error processing file in bulk upload", extra={
                "filename": file.filename,
                "error": str(e)
            }, exc_info=True)
            results["errors"].append({
                "filename": file.filename,
                "error": str(e)
            })
            results["failed"] += 1

    logger.info("Bulk upload complete", extra={
        "user_id": user_id,
        "total": results["total"],
        "successful": results["successful"],
        "duplicates": results["duplicates"],
        "failed": results["failed"]
    })

    return results
