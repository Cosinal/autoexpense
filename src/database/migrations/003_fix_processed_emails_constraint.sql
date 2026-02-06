-- Fix processed_emails unique constraint
-- Should be unique per (user_id, provider_message_id) not just provider_message_id

-- Drop the old unique constraint
ALTER TABLE public.processed_emails
DROP CONSTRAINT IF EXISTS processed_emails_provider_message_id_key;

-- Add composite unique constraint
ALTER TABLE public.processed_emails
ADD CONSTRAINT processed_emails_user_message_unique
UNIQUE (user_id, provider_message_id);
