-- Add review flagging columns to receipts table
-- Phase 3: Automatic quality control

ALTER TABLE receipts
ADD COLUMN IF NOT EXISTS needs_review BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS review_reason TEXT;

-- Add index for filtering receipts needing review
CREATE INDEX IF NOT EXISTS idx_receipts_needs_review
ON receipts(user_id, needs_review)
WHERE needs_review = TRUE;

-- Add comment
COMMENT ON COLUMN receipts.needs_review IS 'Automatically flagged for manual review if confidence < 0.7';
COMMENT ON COLUMN receipts.review_reason IS 'Specific reasons why receipt needs review (e.g., missing fields, low confidence)';
