-- Migration 001: Production-grade ingestion schema
-- Adds status tracking, source traceability, and financial precision

-- ============================================================================
-- processed_emails: Add status tracking and provider field
-- ============================================================================

-- Add status column with state machine: processing -> success/no_receipts/failed
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='processed_emails' AND column_name='status'
    ) THEN
        ALTER TABLE processed_emails
        ADD COLUMN status TEXT NOT NULL DEFAULT 'success'
        CHECK (status IN ('processing', 'success', 'no_receipts', 'failed'));
    END IF;
END $$;

-- Add failure reason for failed status
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='processed_emails' AND column_name='failure_reason'
    ) THEN
        ALTER TABLE processed_emails ADD COLUMN failure_reason TEXT;
    END IF;
END $$;

-- Add provider field (default 'gmail', allows future extensibility)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='processed_emails' AND column_name='provider'
    ) THEN
        ALTER TABLE processed_emails
        ADD COLUMN provider TEXT NOT NULL DEFAULT 'gmail';
    END IF;
END $$;

-- Add unique constraint for idempotent UPSERT operations
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'processed_emails_user_provider_msg_key'
    ) THEN
        ALTER TABLE processed_emails
        ADD CONSTRAINT processed_emails_user_provider_msg_key
        UNIQUE (user_id, provider_message_id);
    END IF;
END $$;

-- ============================================================================
-- receipts: Add source traceability and financial precision
-- ============================================================================

-- Add file_path for deterministic storage paths (content-addressed)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='receipts' AND column_name='file_path'
    ) THEN
        ALTER TABLE receipts ADD COLUMN file_path TEXT;
    END IF;
END $$;

-- Add source_message_id to trace receipts back to emails
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='receipts' AND column_name='source_message_id'
    ) THEN
        ALTER TABLE receipts ADD COLUMN source_message_id TEXT;
    END IF;
END $$;

-- Add source_type to distinguish attachments vs email body
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='receipts' AND column_name='source_type'
    ) THEN
        ALTER TABLE receipts
        ADD COLUMN source_type TEXT DEFAULT 'attachment'
        CHECK (source_type IN ('attachment', 'body'));
    END IF;
END $$;

-- Add attachment_index for ordering multiple attachments from same email
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='receipts' AND column_name='attachment_index'
    ) THEN
        ALTER TABLE receipts ADD COLUMN attachment_index INTEGER;
    END IF;
END $$;

-- Add ingestion_debug for parser metadata (patterns matched, confidence, etc.)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='receipts' AND column_name='ingestion_debug'
    ) THEN
        ALTER TABLE receipts ADD COLUMN ingestion_debug JSONB;
    END IF;
END $$;

-- Add unique constraint: one receipt per file content per user (deduplication)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'receipts_user_file_hash_key'
    ) THEN
        ALTER TABLE receipts
        ADD CONSTRAINT receipts_user_file_hash_key
        UNIQUE (user_id, file_hash);
    END IF;
END $$;

-- Convert amount and tax to NUMERIC for exact financial precision
-- Note: This assumes existing data fits in NUMERIC(15,4)
DO $$
BEGIN
    -- Check if amount is not already NUMERIC
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='receipts' AND column_name='amount'
        AND data_type != 'numeric'
    ) THEN
        ALTER TABLE receipts ALTER COLUMN amount TYPE NUMERIC(15,4);
    END IF;

    -- Check if tax is not already NUMERIC
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='receipts' AND column_name='tax'
        AND data_type != 'numeric'
    ) THEN
        ALTER TABLE receipts ALTER COLUMN tax TYPE NUMERIC(15,4);
    END IF;
END $$;

-- ============================================================================
-- Indexes for performance
-- ============================================================================

-- Index on status for filtering by processing state
CREATE INDEX IF NOT EXISTS idx_processed_emails_status
ON processed_emails(status);

-- Index on source_message_id for tracing receipts to emails
CREATE INDEX IF NOT EXISTS idx_receipts_source_message
ON receipts(source_message_id);
