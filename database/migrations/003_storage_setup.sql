-- AutoExpense Storage Bucket Setup
-- Run this in your Supabase SQL Editor

-- Create the receipts storage bucket
INSERT INTO storage.buckets (id, name, public)
VALUES ('receipts', 'receipts', false)
ON CONFLICT (id) DO NOTHING;

-- Storage Policies for receipts bucket

-- Allow authenticated users to upload files to their own folder
CREATE POLICY "Users can upload own receipts"
  ON storage.objects
  FOR INSERT
  TO authenticated
  WITH CHECK (
    bucket_id = 'receipts' AND
    auth.uid()::text = (storage.foldername(name))[1]
  );

-- Allow users to read their own receipt files
CREATE POLICY "Users can view own receipts"
  ON storage.objects
  FOR SELECT
  TO authenticated
  USING (
    bucket_id = 'receipts' AND
    auth.uid()::text = (storage.foldername(name))[1]
  );

-- Allow users to update their own receipt files
CREATE POLICY "Users can update own receipts"
  ON storage.objects
  FOR UPDATE
  TO authenticated
  USING (
    bucket_id = 'receipts' AND
    auth.uid()::text = (storage.foldername(name))[1]
  )
  WITH CHECK (
    bucket_id = 'receipts' AND
    auth.uid()::text = (storage.foldername(name))[1]
  );

-- Allow users to delete their own receipt files
CREATE POLICY "Users can delete own receipts"
  ON storage.objects
  FOR DELETE
  TO authenticated
  USING (
    bucket_id = 'receipts' AND
    auth.uid()::text = (storage.foldername(name))[1]
  );

-- Service role has full access (bypass RLS)
-- This is automatic when using service_role key

COMMENT ON POLICY "Users can upload own receipts" ON storage.objects IS 'Users can upload files to their own folder in receipts bucket';
COMMENT ON POLICY "Users can view own receipts" ON storage.objects IS 'Users can download their own receipt files';
