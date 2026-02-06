"""
Upload API router for direct file uploads.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
import uuid

from app.services.storage import StorageService
from app.services.ocr import OCRService
from app.services.parser import ReceiptParser
from app.utils.supabase import get_supabase_client

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("")
async def upload_receipt(
    file: UploadFile = File(...),
    user_id: str = Form(...)
):
    """
    Upload a receipt file directly (drag-and-drop or file selection).

    This endpoint:
    1. Accepts file upload (PDF, JPG, PNG)
    2. Stores file in Supabase Storage
    3. Runs OCR and parsing
    4. Creates receipt record
    5. Returns parsed data

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

        # Generate receipt ID
        receipt_id = str(uuid.uuid4())

        # Upload file to storage
        file_url, file_hash, file_path = storage.upload_receipt_file(
            user_id=user_id,
            filename=file.filename or "uploaded_receipt",
            file_data=file_data,
            mime_type=file.content_type or "application/octet-stream",
            receipt_id=receipt_id
        )

        if not file_url:
            raise HTTPException(
                status_code=500,
                detail="Failed to upload file to storage"
            )

        # Run OCR
        ocr_text = ocr.extract_and_normalize(
            file_data=file_data,
            mime_type=file.content_type or "application/octet-stream",
            filename=file.filename or ""
        )

        # Parse receipt data
        parsed_data = parser.parse(ocr_text)

        # Create receipt record in database
        receipt_data = {
            "id": receipt_id,
            "user_id": user_id,
            "vendor": parsed_data.get("vendor"),
            "amount": float(parsed_data["amount"]) if parsed_data.get("amount") else None,
            "currency": parsed_data.get("currency", "USD"),
            "date": parsed_data.get("date"),
            "tax": float(parsed_data["tax"]) if parsed_data.get("tax") else None,
            "file_name": file.filename,
            "file_url": file_url,
            "file_hash": file_hash,
            "mime_type": file.content_type,
        }

        response = supabase.table('receipts').insert(receipt_data).execute()

        if not response.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to create receipt record"
            )

        # Generate signed URL for response
        signed_url = storage.create_signed_url(file_path, expires_in=3600)
        if signed_url:
            receipt_data['file_url'] = signed_url

        return {
            **receipt_data,
            "message": "Receipt uploaded and processed successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
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
        "failed": 0,
        "receipts": [],
        "errors": []
    }

    for file in files:
        try:
            # Process each file using the single upload endpoint logic
            file_data = await file.read()

            # Validate file type
            allowed_types = ["application/pdf", "image/jpeg", "image/jpg", "image/png"]
            if file.content_type not in allowed_types:
                results["errors"].append({
                    "filename": file.filename,
                    "error": f"Invalid file type: {file.content_type}"
                })
                results["failed"] += 1
                continue

            # Initialize services
            storage = StorageService()
            ocr = OCRService()
            parser = ReceiptParser()
            supabase = get_supabase_client()

            # Generate receipt ID
            receipt_id = str(uuid.uuid4())

            # Upload file
            file_url, file_hash, file_path = storage.upload_receipt_file(
                user_id=user_id,
                filename=file.filename or "uploaded_receipt",
                file_data=file_data,
                mime_type=file.content_type or "application/octet-stream",
                receipt_id=receipt_id
            )

            if not file_url:
                results["errors"].append({
                    "filename": file.filename,
                    "error": "Storage upload failed"
                })
                results["failed"] += 1
                continue

            # Run OCR and parse
            ocr_text = ocr.extract_and_normalize(
                file_data=file_data,
                mime_type=file.content_type or "application/octet-stream",
                filename=file.filename or ""
            )

            parsed_data = parser.parse(ocr_text)

            # Create receipt record
            receipt_data = {
                "id": receipt_id,
                "user_id": user_id,
                "vendor": parsed_data.get("vendor"),
                "amount": float(parsed_data["amount"]) if parsed_data.get("amount") else None,
                "currency": parsed_data.get("currency", "USD"),
                "date": parsed_data.get("date"),
                "tax": float(parsed_data["tax"]) if parsed_data.get("tax") else None,
                "file_name": file.filename,
                "file_url": file_url,
                "file_hash": file_hash,
                "mime_type": file.content_type,
            }

            response = supabase.table('receipts').insert(receipt_data).execute()

            if response.data:
                results["successful"] += 1
                results["receipts"].append({
                    "id": receipt_id,
                    "filename": file.filename,
                    "vendor": parsed_data.get("vendor"),
                    "amount": parsed_data.get("amount")
                })
            else:
                results["errors"].append({
                    "filename": file.filename,
                    "error": "Database insert failed"
                })
                results["failed"] += 1

        except Exception as e:
            results["errors"].append({
                "filename": file.filename,
                "error": str(e)
            })
            results["failed"] += 1

    return results
