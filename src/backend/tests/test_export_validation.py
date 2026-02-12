"""
Test suite for Phase 1.7: Export reliability validation.

Tests cover:
- CSV header includes Review Status and Validation Warnings columns
- Amount/tax formatting (2 decimal places)
- Missing field handling (N/A instead of empty strings)
- Review status indication (Reviewed vs Needs Review)
- Validation warnings exported (amount inconsistency, low confidence, forwarding)
- Data completeness validation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.routers.export import router
from fastapi.testclient import TestClient
from fastapi import FastAPI
import csv
import io
from decimal import Decimal
import pytest
from unittest.mock import Mock, patch


# Create test app
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestCSVExportHeaders:
    """Test that CSV export includes all required columns."""

    @patch('app.routers.export.get_supabase_client')
    def test_csv_header_includes_review_status(self, mock_supabase):
        """Verify CSV header includes 'Review Status' column."""
        # Mock database response
        mock_response = Mock()
        mock_response.data = [
            {
                'id': 'test-id-1',
                'date': '2024-01-15',
                'vendor': 'Starbucks',
                'amount': '8.50',
                'currency': 'USD',
                'tax': '1.10',
                'needs_review': False,
                'file_name': 'receipt.pdf',
                'file_url': '',
                'ingestion_debug': {}
            }
        ]

        mock_client = Mock()
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response
        mock_supabase.return_value = mock_client

        # Call export endpoint
        response = client.get("/export/csv?user_id=test-user")

        assert response.status_code == 200
        csv_content = response.text

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        headers = reader.fieldnames

        # Verify required columns exist
        assert 'Review Status' in headers
        assert 'Validation Warnings' in headers
        assert 'Date' in headers
        assert 'Vendor' in headers
        assert 'Amount' in headers
        assert 'Currency' in headers
        assert 'Tax' in headers

    @patch('app.routers.export.get_supabase_client')
    def test_csv_header_includes_validation_warnings(self, mock_supabase):
        """Verify CSV header includes 'Validation Warnings' column."""
        # Mock database response
        mock_response = Mock()
        mock_response.data = [
            {
                'id': 'test-id-1',
                'date': '2024-01-15',
                'vendor': 'Uber',
                'amount': '14.13',
                'currency': 'USD',
                'tax': '1.63',
                'needs_review': True,
                'file_name': 'receipt.pdf',
                'file_url': '',
                'ingestion_debug': {
                    'confidence_per_field': {
                        'vendor': 0.85,
                        'amount': 0.92
                    }
                }
            }
        ]

        mock_client = Mock()
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response
        mock_supabase.return_value = mock_client

        # Call export endpoint
        response = client.get("/export/csv?user_id=test-user")

        assert response.status_code == 200
        csv_content = response.text

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        headers = reader.fieldnames

        assert 'Validation Warnings' in headers


class TestAmountFormatting:
    """Test that amounts and tax are formatted correctly in export."""

    @patch('app.routers.export.get_supabase_client')
    def test_amount_formatted_with_two_decimals(self, mock_supabase):
        """Verify amounts are formatted to 2 decimal places."""
        # Mock database response
        mock_response = Mock()
        mock_response.data = [
            {
                'id': 'test-id-1',
                'date': '2024-01-15',
                'vendor': 'Apple',
                'amount': '126.07',  # Already has 2 decimals
                'currency': 'USD',
                'tax': '16.39',
                'needs_review': False,
                'file_name': 'receipt.pdf',
                'file_url': '',
                'ingestion_debug': {}
            },
            {
                'id': 'test-id-2',
                'date': '2024-01-16',
                'vendor': 'Steam',
                'amount': '19.9',  # Only 1 decimal
                'currency': 'USD',
                'tax': '2.587',  # 3 decimals
                'needs_review': False,
                'file_name': 'receipt2.pdf',
                'file_url': '',
                'ingestion_debug': {}
            }
        ]

        mock_client = Mock()
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response
        mock_supabase.return_value = mock_client

        # Call export endpoint
        response = client.get("/export/csv?user_id=test-user")

        assert response.status_code == 200
        csv_content = response.text

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        # Check first row (already 2 decimals)
        assert rows[0]['Amount'] == '126.07'
        assert rows[0]['Tax'] == '16.39'

        # Check second row (format to 2 decimals)
        assert rows[1]['Amount'] == '19.90'  # Should pad to 2 decimals
        assert rows[1]['Tax'] == '2.59'  # Should round to 2 decimals

    @patch('app.routers.export.get_supabase_client')
    def test_missing_amount_shows_na(self, mock_supabase):
        """Verify missing amounts show 'N/A' instead of empty string."""
        # Mock database response
        mock_response = Mock()
        mock_response.data = [
            {
                'id': 'test-id-1',
                'date': '2024-01-15',
                'vendor': 'Unknown Vendor',
                'amount': None,  # Missing amount
                'currency': 'USD',
                'tax': None,  # Missing tax
                'needs_review': True,
                'file_name': 'receipt.pdf',
                'file_url': '',
                'ingestion_debug': {}
            }
        ]

        mock_client = Mock()
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response
        mock_supabase.return_value = mock_client

        # Call export endpoint
        response = client.get("/export/csv?user_id=test-user")

        assert response.status_code == 200
        csv_content = response.text

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        # Missing fields should show 'N/A', not empty strings
        assert rows[0]['Amount'] == 'N/A'
        assert rows[0]['Tax'] == 'N/A'
        assert rows[0]['Vendor'] == 'Unknown Vendor'


class TestReviewStatusColumn:
    """Test that review status is correctly indicated in export."""

    @patch('app.routers.export.get_supabase_client')
    def test_needs_review_true_shows_needs_review(self, mock_supabase):
        """Verify needs_review=True shows 'Needs Review' in export."""
        # Mock database response
        mock_response = Mock()
        mock_response.data = [
            {
                'id': 'test-id-1',
                'date': '2024-01-15',
                'vendor': 'Ambiguous Vendor',
                'amount': '50.00',
                'currency': 'USD',
                'tax': '6.50',
                'needs_review': True,  # Flagged for review
                'file_name': 'receipt.pdf',
                'file_url': '',
                'ingestion_debug': {
                    'confidence_per_field': {
                        'vendor': 0.65,  # Low confidence
                        'amount': 0.92
                    }
                }
            }
        ]

        mock_client = Mock()
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response
        mock_supabase.return_value = mock_client

        # Call export endpoint
        response = client.get("/export/csv?user_id=test-user")

        assert response.status_code == 200
        csv_content = response.text

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        assert rows[0]['Review Status'] == 'Needs Review'

    @patch('app.routers.export.get_supabase_client')
    def test_needs_review_false_shows_reviewed(self, mock_supabase):
        """Verify needs_review=False shows 'Reviewed' in export."""
        # Mock database response
        mock_response = Mock()
        mock_response.data = [
            {
                'id': 'test-id-1',
                'date': '2024-01-15',
                'vendor': 'Starbucks',
                'amount': '8.50',
                'currency': 'USD',
                'tax': '1.10',
                'needs_review': False,  # High confidence, no review needed
                'file_name': 'receipt.pdf',
                'file_url': '',
                'ingestion_debug': {
                    'confidence_per_field': {
                        'vendor': 0.92,
                        'amount': 0.95
                    }
                }
            }
        ]

        mock_client = Mock()
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response
        mock_supabase.return_value = mock_client

        # Call export endpoint
        response = client.get("/export/csv?user_id=test-user")

        assert response.status_code == 200
        csv_content = response.text

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        assert rows[0]['Review Status'] == 'Reviewed'


class TestValidationWarningsColumn:
    """Test that validation warnings are correctly exported."""

    @patch('app.routers.export.get_supabase_client')
    def test_amount_inconsistency_warning_exported(self, mock_supabase):
        """Verify amount inconsistency warnings appear in export."""
        # Mock database response
        mock_response = Mock()
        mock_response.data = [
            {
                'id': 'test-id-1',
                'date': '2024-01-15',
                'vendor': 'Test Vendor',
                'amount': '60.00',
                'currency': 'USD',
                'tax': '5.00',
                'needs_review': True,
                'file_name': 'receipt.pdf',
                'file_url': '',
                'ingestion_debug': {
                    'amount_validation': {
                        'is_consistent': False,  # Failed validation
                        'subtotal': '50.00',
                        'tax': '5.00',
                        'calculated_total': '55.00',
                        'extracted_total': '60.00'
                    },
                    'confidence_per_field': {
                        'vendor': 0.85,
                        'amount': 0.78
                    }
                }
            }
        ]

        mock_client = Mock()
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response
        mock_supabase.return_value = mock_client

        # Call export endpoint
        response = client.get("/export/csv?user_id=test-user")

        assert response.status_code == 200
        csv_content = response.text

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        warnings = rows[0]['Validation Warnings']
        assert 'Amount inconsistency detected' in warnings

    @patch('app.routers.export.get_supabase_client')
    def test_low_confidence_warnings_exported(self, mock_supabase):
        """Verify low confidence warnings appear in export."""
        # Mock database response
        mock_response = Mock()
        mock_response.data = [
            {
                'id': 'test-id-1',
                'date': '2024-01-15',
                'vendor': 'John Smith',  # Person name (low confidence)
                'amount': '45.00',
                'currency': 'USD',
                'tax': '5.85',
                'needs_review': True,
                'file_name': 'receipt.pdf',
                'file_url': '',
                'ingestion_debug': {
                    'confidence_per_field': {
                        'vendor': 0.45,  # Very low confidence
                        'amount': 0.92
                    }
                }
            }
        ]

        mock_client = Mock()
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response
        mock_supabase.return_value = mock_client

        # Call export endpoint
        response = client.get("/export/csv?user_id=test-user")

        assert response.status_code == 200
        csv_content = response.text

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        warnings = rows[0]['Validation Warnings']
        assert 'Low confidence vendor' in warnings
        assert '0.45' in warnings

    @patch('app.routers.export.get_supabase_client')
    def test_forwarded_email_warning_exported(self, mock_supabase):
        """Verify forwarded email warnings appear in export."""
        # Mock database response
        mock_response = Mock()
        mock_response.data = [
            {
                'id': 'test-id-1',
                'date': '2024-01-15',
                'vendor': 'Uber',
                'amount': '14.13',
                'currency': 'USD',
                'tax': '1.63',
                'needs_review': False,
                'file_name': 'receipt.pdf',
                'file_url': '',
                'ingestion_debug': {
                    'vendor_is_forwarded': True,  # Forwarded email detected
                    'confidence_per_field': {
                        'vendor': 0.82,
                        'amount': 0.95
                    }
                }
            }
        ]

        mock_client = Mock()
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response
        mock_supabase.return_value = mock_client

        # Call export endpoint
        response = client.get("/export/csv?user_id=test-user")

        assert response.status_code == 200
        csv_content = response.text

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        warnings = rows[0]['Validation Warnings']
        assert 'Forwarded email' in warnings

    @patch('app.routers.export.get_supabase_client')
    def test_no_warnings_shows_none(self, mock_supabase):
        """Verify receipts with no warnings show 'None' in Validation Warnings column."""
        # Mock database response
        mock_response = Mock()
        mock_response.data = [
            {
                'id': 'test-id-1',
                'date': '2024-01-15',
                'vendor': 'Starbucks',
                'amount': '8.50',
                'currency': 'USD',
                'tax': '1.10',
                'needs_review': False,
                'file_name': 'receipt.pdf',
                'file_url': '',
                'ingestion_debug': {
                    'amount_validation': {
                        'is_consistent': True
                    },
                    'confidence_per_field': {
                        'vendor': 0.92,
                        'amount': 0.95
                    },
                    'vendor_is_forwarded': False
                }
            }
        ]

        mock_client = Mock()
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response
        mock_supabase.return_value = mock_client

        # Call export endpoint
        response = client.get("/export/csv?user_id=test-user")

        assert response.status_code == 200
        csv_content = response.text

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        assert rows[0]['Validation Warnings'] == 'None'


class TestMissingFieldHandling:
    """Test that missing fields are handled properly in export."""

    @patch('app.routers.export.get_supabase_client')
    def test_missing_vendor_shows_na(self, mock_supabase):
        """Verify missing vendor shows 'N/A'."""
        # Mock database response
        mock_response = Mock()
        mock_response.data = [
            {
                'id': 'test-id-1',
                'date': '2024-01-15',
                'vendor': None,  # Missing vendor
                'amount': '50.00',
                'currency': 'USD',
                'tax': '6.50',
                'needs_review': True,
                'file_name': 'receipt.pdf',
                'file_url': '',
                'ingestion_debug': {}
            }
        ]

        mock_client = Mock()
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response
        mock_supabase.return_value = mock_client

        # Call export endpoint
        response = client.get("/export/csv?user_id=test-user")

        assert response.status_code == 200
        csv_content = response.text

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        assert rows[0]['Vendor'] == 'N/A'

    @patch('app.routers.export.get_supabase_client')
    def test_missing_date_shows_na(self, mock_supabase):
        """Verify missing date shows 'N/A'."""
        # Mock database response
        mock_response = Mock()
        mock_response.data = [
            {
                'id': 'test-id-1',
                'date': None,  # Missing date
                'vendor': 'Test Vendor',
                'amount': '50.00',
                'currency': 'USD',
                'tax': '6.50',
                'needs_review': True,
                'file_name': 'receipt.pdf',
                'file_url': '',
                'ingestion_debug': {}
            }
        ]

        mock_client = Mock()
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response
        mock_supabase.return_value = mock_client

        # Call export endpoint
        response = client.get("/export/csv?user_id=test-user")

        assert response.status_code == 200
        csv_content = response.text

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        assert rows[0]['Date'] == 'N/A'

    @patch('app.routers.export.get_supabase_client')
    def test_missing_currency_defaults_to_usd(self, mock_supabase):
        """Verify missing currency defaults to 'USD'."""
        # Mock database response
        mock_response = Mock()
        mock_response.data = [
            {
                'id': 'test-id-1',
                'date': '2024-01-15',
                'vendor': 'Test Vendor',
                'amount': '50.00',
                'currency': None,  # Missing currency
                'tax': '6.50',
                'needs_review': False,
                'file_name': 'receipt.pdf',
                'file_url': '',
                'ingestion_debug': {}
            }
        ]

        mock_client = Mock()
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response
        mock_supabase.return_value = mock_client

        # Call export endpoint
        response = client.get("/export/csv?user_id=test-user")

        assert response.status_code == 200
        csv_content = response.text

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        # Currency should default to USD
        assert rows[0]['Currency'] == 'USD'


class TestExportIntegrity:
    """Test overall export integrity and completeness."""

    @patch('app.routers.export.get_supabase_client')
    def test_all_receipts_exported_with_complete_data(self, mock_supabase):
        """Verify all receipts are exported with complete field data."""
        # Mock database response with multiple receipts
        mock_response = Mock()
        mock_response.data = [
            {
                'id': 'test-id-1',
                'date': '2024-01-15',
                'vendor': 'Starbucks',
                'amount': '8.50',
                'currency': 'USD',
                'tax': '1.10',
                'needs_review': False,
                'file_name': 'receipt1.pdf',
                'file_url': '',
                'ingestion_debug': {'confidence_per_field': {'vendor': 0.92, 'amount': 0.95}}
            },
            {
                'id': 'test-id-2',
                'date': '2024-01-16',
                'vendor': 'Uber',
                'amount': '14.13',
                'currency': 'USD',
                'tax': '1.63',
                'needs_review': False,
                'file_name': 'receipt2.pdf',
                'file_url': '',
                'ingestion_debug': {'confidence_per_field': {'vendor': 0.88, 'amount': 0.93}}
            },
            {
                'id': 'test-id-3',
                'date': '2024-01-17',
                'vendor': 'Apple',
                'amount': '126.07',
                'currency': 'USD',
                'tax': '16.39',
                'needs_review': False,
                'file_name': 'receipt3.pdf',
                'file_url': '',
                'ingestion_debug': {'confidence_per_field': {'vendor': 0.95, 'amount': 0.98}}
            }
        ]

        mock_client = Mock()
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response
        mock_supabase.return_value = mock_client

        # Call export endpoint
        response = client.get("/export/csv?user_id=test-user")

        assert response.status_code == 200
        csv_content = response.text

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        # Should have all 3 receipts
        assert len(rows) == 3

        # Verify all rows have all required fields
        for row in rows:
            assert row['Date']
            assert row['Vendor']
            assert row['Amount']
            assert row['Currency']
            assert row['Tax']
            assert row['Review Status']
            assert row['Validation Warnings']
            assert row['File Name']
            assert row['Receipt ID']

        # Verify specific data
        assert rows[0]['Vendor'] == 'Starbucks'
        assert rows[1]['Vendor'] == 'Uber'
        assert rows[2]['Vendor'] == 'Apple'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
