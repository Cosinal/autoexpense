-- AutoExpense Row Level Security Policies
-- Run this in your Supabase SQL Editor after running 001_initial_schema.sql

-- Enable RLS on all tables
ALTER TABLE public.receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.processed_emails ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Receipts Policies
-- Users can only read their own receipts
CREATE POLICY "Users can view own receipts"
  ON public.receipts
  FOR SELECT
  USING (auth.uid() = user_id);

-- Users can insert their own receipts
CREATE POLICY "Users can insert own receipts"
  ON public.receipts
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users can update their own receipts
CREATE POLICY "Users can update own receipts"
  ON public.receipts
  FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Users can delete their own receipts
CREATE POLICY "Users can delete own receipts"
  ON public.receipts
  FOR DELETE
  USING (auth.uid() = user_id);

-- Processed Emails Policies
-- Users can only read their own email records
CREATE POLICY "Users can view own processed emails"
  ON public.processed_emails
  FOR SELECT
  USING (auth.uid() = user_id);

-- Users can insert their own email records
CREATE POLICY "Users can insert own processed emails"
  ON public.processed_emails
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users Table Policies (if using custom users table)
-- Users can read their own user record
CREATE POLICY "Users can view own profile"
  ON public.users
  FOR SELECT
  USING (auth.uid() = id);

-- Users can update their own profile
CREATE POLICY "Users can update own profile"
  ON public.users
  FOR UPDATE
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- Service Role Bypass
-- The service role (used by backend) can bypass RLS
-- This is automatic in Supabase when using the service_role key

-- Grant permissions to authenticated users
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT ALL ON public.receipts TO authenticated;
GRANT ALL ON public.processed_emails TO authenticated;
GRANT ALL ON public.users TO authenticated;

-- Grant permissions to service role
GRANT ALL ON public.receipts TO service_role;
GRANT ALL ON public.processed_emails TO service_role;
GRANT ALL ON public.users TO service_role;

COMMENT ON POLICY "Users can view own receipts" ON public.receipts IS 'Ensures users can only see their own receipts';
COMMENT ON POLICY "Users can insert own receipts" ON public.receipts IS 'Allows users to create receipts only for themselves';
