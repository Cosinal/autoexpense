-- Add user corrections column for ML training
-- Stores manual corrections made by users during review process

ALTER TABLE receipts
ADD COLUMN IF NOT EXISTS user_corrections JSONB;

-- Add index for querying corrected receipts (for ML training dataset)
CREATE INDEX IF NOT EXISTS idx_receipts_user_corrections
ON receipts USING GIN (user_corrections)
WHERE user_corrections IS NOT NULL;

-- Add timestamp for when correction was made
ALTER TABLE receipts
ADD COLUMN IF NOT EXISTS corrected_at TIMESTAMPTZ;

-- Comments
COMMENT ON COLUMN receipts.user_corrections IS 'Manual corrections made by user during review. Format: {"field_name": {"original": "X", "corrected_to": "Y", "candidates": [...], "confidence": 0.5}}';
COMMENT ON COLUMN receipts.corrected_at IS 'Timestamp when user made manual corrections';

-- Example user_corrections structure:
-- {
--   "vendor": {
--     "original": "Acuvue Oasys 1-Day",
--     "corrected_to": "Browz Eyeware & Eyecare",
--     "candidates": ["Acuvue Oasys 1-Day", "Jorden Shaw", "Browz Eyeware"],
--     "confidence": 0.42,
--     "corrected_by": "user_id"
--   },
--   "amount": {
--     "original": null,
--     "corrected_to": "792.00",
--     "candidates": ["200.00", "792.00", "880.00"],
--     "confidence": 0.0
--   }
-- }
