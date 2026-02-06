"""
Test script for all API endpoints.
Make sure the backend is running: uvicorn app.main:app --reload

Usage:
    python test_api_endpoints.py
"""

import requests
import json
from datetime import date, timedelta

BASE_URL = "http://localhost:8000"
TEST_USER_ID = "00000000-0000-0000-0000-000000000000"


def test_health():
    """Test health check endpoint."""
    print("\n" + "="*60)
    print("Testing: GET /health")
    print("="*60)

    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    assert response.status_code == 200, "Health check failed"
    print("✓ Health check passed")


def test_list_receipts():
    """Test list receipts endpoint."""
    print("\n" + "="*60)
    print("Testing: GET /receipts")
    print("="*60)

    response = requests.get(
        f"{BASE_URL}/receipts",
        params={"user_id": TEST_USER_ID}
    )

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Total receipts: {data['total']}")
        print(f"Page: {data['page']} of {data['total_pages']}")
        print(f"Receipts on this page: {len(data['receipts'])}")

        if data['receipts']:
            print("\nFirst receipt:")
            receipt = data['receipts'][0]
            print(f"  ID: {receipt['id']}")
            print(f"  Vendor: {receipt.get('vendor', 'N/A')}")
            print(f"  Amount: {receipt.get('currency', 'USD')} {receipt.get('amount', 'N/A')}")
            print(f"  Date: {receipt.get('date', 'N/A')}")

        print("✓ List receipts passed")
    else:
        print(f"✗ Failed: {response.text}")


def test_filter_receipts():
    """Test receipt filtering."""
    print("\n" + "="*60)
    print("Testing: GET /receipts with filters")
    print("="*60)

    # Test vendor filter
    response = requests.get(
        f"{BASE_URL}/receipts",
        params={
            "user_id": TEST_USER_ID,
            "vendor": "Apple"
        }
    )

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Receipts matching 'Apple': {data['total']}")
        print("✓ Filter test passed")
    else:
        print(f"✗ Failed: {response.text}")


def test_receipt_stats():
    """Test receipt statistics endpoint."""
    print("\n" + "="*60)
    print("Testing: GET /receipts/stats/summary")
    print("="*60)

    response = requests.get(
        f"{BASE_URL}/receipts/stats/summary",
        params={"user_id": TEST_USER_ID}
    )

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Total receipts: {data['total_count']}")
        print("By currency:")
        for currency, stats in data.get('by_currency', {}).items():
            print(f"  {currency}: {stats['count']} receipts, "
                  f"Total: {stats['total']:.2f}, "
                  f"Average: {stats['average']:.2f}")

        print("✓ Stats test passed")
    else:
        print(f"✗ Failed: {response.text}")


def test_export_summary():
    """Test export summary endpoint."""
    print("\n" + "="*60)
    print("Testing: GET /export/summary")
    print("="*60)

    response = requests.get(
        f"{BASE_URL}/export/summary",
        params={"user_id": TEST_USER_ID}
    )

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Total receipts: {data['total_receipts']}")
        print(f"Date range: {data['date_range']}")
        print("\nBy month:")
        for month, stats in sorted(data.get('by_month', {}).items()):
            print(f"  {month}: {stats['count']} receipts")
            for currency, total in stats['total'].items():
                print(f"    {currency}: {total:.2f}")

        print("\nGrand total:")
        for currency, total in data.get('grand_total', {}).items():
            print(f"  {currency}: {total:.2f}")

        print("✓ Export summary passed")
    else:
        print(f"✗ Failed: {response.text}")


def test_export_csv():
    """Test CSV export endpoint."""
    print("\n" + "="*60)
    print("Testing: GET /export/csv")
    print("="*60)

    response = requests.get(
        f"{BASE_URL}/export/csv",
        params={"user_id": TEST_USER_ID}
    )

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        # Check content type
        content_type = response.headers.get('content-type', '')
        print(f"Content-Type: {content_type}")

        # Check for CSV content
        csv_content = response.text
        lines = csv_content.split('\n')
        print(f"CSV lines: {len(lines)}")
        print(f"Header: {lines[0] if lines else 'N/A'}")

        if len(lines) > 1:
            print(f"First data row: {lines[1][:100]}...")

        print("✓ CSV export passed")
    else:
        print(f"✗ Failed: {response.text}")


def test_sync_status():
    """Test sync status endpoint."""
    print("\n" + "="*60)
    print("Testing: GET /sync/status")
    print("="*60)

    response = requests.get(f"{BASE_URL}/sync/status")

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Ready: {data['ready']}")
        print("Configuration:")
        for key, value in data['config'].items():
            print(f"  {key}: {value}")

        print("✓ Sync status passed")
    else:
        print(f"✗ Failed: {response.text}")


def run_all_tests():
    """Run all API tests."""
    print("\n" + "="*60)
    print("AutoExpense API Endpoint Tests")
    print("="*60)
    print("\nMake sure the backend is running:")
    print("  uvicorn app.main:app --reload")
    print()

    try:
        # Test basic endpoints
        test_health()

        # Test receipts endpoints
        test_list_receipts()
        test_filter_receipts()
        test_receipt_stats()

        # Test export endpoints
        test_export_summary()
        test_export_csv()

        # Test sync endpoints
        test_sync_status()

        print("\n" + "="*60)
        print("✓ All API tests passed!")
        print("="*60)

    except requests.exceptions.ConnectionError:
        print("\n✗ Connection error!")
        print("Make sure the backend is running:")
        print("  cd backend")
        print("  source venv/bin/activate")
        print("  uvicorn app.main:app --reload")

    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
