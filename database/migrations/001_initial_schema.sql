-- AutoExpense Initial Schema Migration
-- Run this in your Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table (optional - can also use Supabase auth.users)
-- If you want to extend user data, create this table
CREATE TABLE IF NOT EXISTS public.users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT UNIQUE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Receipts table
CREATE TABLE IF NOT EXISTS public.receipts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL,
  vendor TEXT,
  amount NUMERIC(10, 2),
  currency TEXT DEFAULT 'USD',
  date DATE,
  tax NUMERIC(10, 2),
  file_url TEXT,
  file_hash TEXT,
  file_name TEXT,
  mime_type TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  -- Foreign key to Supabase auth users
  CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Email tracking table (to prevent duplicate processing)
CREATE TABLE IF NOT EXISTS public.processed_emails (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL,
  provider_message_id TEXT UNIQUE NOT NULL,
  received_at TIMESTAMP WITH TIME ZONE,
  processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  receipt_count INTEGER DEFAULT 0,

  CONSTRAINT fk_user_email FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_receipts_user_id ON public.receipts(user_id);
CREATE INDEX IF NOT EXISTS idx_receipts_date ON public.receipts(date);
CREATE INDEX IF NOT EXISTS idx_receipts_vendor ON public.receipts(vendor);
CREATE INDEX IF NOT EXISTS idx_receipts_created_at ON public.receipts(created_at);
CREATE INDEX IF NOT EXISTS idx_receipts_file_hash ON public.receipts(file_hash);
CREATE INDEX IF NOT EXISTS idx_processed_emails_user_id ON public.processed_emails(user_id);
CREATE INDEX IF NOT EXISTS idx_processed_emails_message_id ON public.processed_emails(provider_message_id);

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add triggers for updated_at
CREATE TRIGGER update_receipts_updated_at
  BEFORE UPDATE ON public.receipts
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at
  BEFORE UPDATE ON public.users
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE public.receipts IS 'Stores parsed receipt data and file references';
COMMENT ON TABLE public.processed_emails IS 'Tracks processed email messages to prevent duplicates';
COMMENT ON COLUMN public.receipts.file_hash IS 'SHA-256 hash for deduplication';
COMMENT ON COLUMN public.receipts.vendor IS 'Merchant/vendor name extracted from receipt';
COMMENT ON COLUMN public.receipts.amount IS 'Total amount from receipt';
COMMENT ON COLUMN public.receipts.tax IS 'Tax amount if extracted';
