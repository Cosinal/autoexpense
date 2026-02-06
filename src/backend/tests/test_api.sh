#!/bin/bash

# Test script for API endpoints
# Make sure the backend is running first: uvicorn app.main:app --reload

echo "Testing AutoExpense API..."
echo "=========================================="

# Test 1: Health check
echo -e "\n1. Testing health endpoint..."
curl -s http://localhost:8000/health | jq '.'

# Test 2: Sync status
echo -e "\n2. Testing sync status..."
curl -s http://localhost:8000/sync/status | jq '.'

# Test 3: Trigger sync (with test user ID)
echo -e "\n3. Testing email sync..."
curl -s -X POST http://localhost:8000/sync \
  -H "Content-Type: application/json" \
  -d '{"user_id":"00000000-0000-0000-0000-000000000000","days_back":7}' | jq '.'

echo -e "\n=========================================="
echo "API tests complete!"
