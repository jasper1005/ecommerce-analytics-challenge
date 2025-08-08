# tests/test_examples.py
"""
Sample test cases for the e-commerce analytics API.
These are examples to inspire your testing approach.
"""

import pytest
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

# Import your app modules
try:
    from app import app
    import processors

except ImportError as e:
    pytest.skip(f"Could not import app modules: {e}", allow_module_level=True)

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

class TestDateTimeHandling:
    """Test cases for date/time handling edge cases"""
    
    def test_dst_spring_forward(self):
        """Test handling of non-existent time during DST spring forward"""
        # March 10, 2024, 2:30 AM doesn't exist in America/New_York
        timestamp = "2024-03-10 02:30:00"
        timezone_str = "America/New_York"
        parsed_dt, issues = processors.parse_timestamp(timestamp, timezone_str, dst_check = True)
        
        # Should handle gracefully and create a valid datetime
        assert parsed_dt is not None
        convert_dt = processors.convert_timezone(parsed_dt, timezone_str)
        assert convert_dt.hour == 3  # Should be adjusted to 3:30 AM
        pass
    
    def test_dst_fall_back(self):
        """Test handling of ambiguous time during DST fall back"""
        # November 3, 2024, 1:30 AM occurs twice in America/New_York
        dst_check = False
        timestamp = "November 3, 2024, 1:30 AM"
        timezone_str = "America/New_York"
        parsed_dt, issues = processors.parse_timestamp(timestamp, timezone_str, dst_check)
        assert parsed_dt is not None
        assert parsed_dt.hour == 6

        # round-trip check
        dst_check = True
        parsed_dt, issues = processors.parse_timestamp(timestamp, timezone_str, dst_check)
        assert parsed_dt is not None
        assert parsed_dt.hour == 5
        pass
    
    def test_missing_timezone(self):
        """Test handling of transactions with missing timezone info"""
        parsed_dt, issues = processors.parse_timestamp("2024-11-03 01:30:00", timezone_str=None, dst_check=False)
        assert parsed_dt is not None
        assert 'missing_timezone' in issues
        pass
    
    def test_mixed_date_formats(self):
        """Test parsing of different date formats"""
        test_formats = [
            "2024-01-15 14:30:00",
            "01/15/24 2:30 PM", 
            "15-Jan-2024 14:30",
            "2024-01-15T14:30:00Z"
        ]
        for ts in test_formats:
            parsed_dt, issues = processors.parse_timestamp(ts, timezone_str="UTC", dst_check=False)
            print(f"Parsed {ts} to {parsed_dt} with issues: {issues}")
            assert parsed_dt is not None, f"Failed to parse timestamp: {ts}"
        # Your parsing logic should handle all these formats
        pass

class TestAPIEndpoints:
    @pytest.fixture(autouse=True)
    def _setup_client(self, client):
        self.client = client

    def test_daily_sales_basic(self):
        """Test basic daily sales endpoint"""
        client = self.client
        response = client.get('/api/sales/daily?start_date=2024-01-01&end_date=2024-01-31')

        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, dict)
        assert len(data) > 0
        if(len(data["data"]) == 0):
            pytest.skip("No data available for the given date range")
        else:
            first = data["data"][0]
        assert set(["date", "total_sales", "transaction_count", "average_order_value"]).issubset(first.keys())
        pass
    
    def test_daily_sales_with_timezone(self):
        """Test daily sales with timezone conversion"""
        client = self.client
        response = client.get('/api/sales/daily?start_date=2024-01-01&end_date=2024-01-31&timezon=America/New_York')

        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, dict)
        assert len(data) > 0

        if(len(data["data"]) == 0):
            pytest.skip("No data available for the given date range")
        else:
            first = data["data"][0]
        assert set(["date", "total_sales", "transaction_count", "average_order_value"]).issubset(first.keys())
        pass
    
    def test_hourly_sales(self):
        """Test hourly sales endpoint"""
        client = self.client
        response = client.get('http://localhost:5000/api/sales/hourly?date=2024-01-15&timezone=UTC')

        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, dict)
        assert len(data) > 0

        if(len(data["data"]) == 0):
            pytest.skip("No data available for the given date range")
        else:
            first = data["data"][0]
        assert set(["hour", "total_sales", "transaction_count"]).issubset(first.keys())
        pass
    
    def test_sales_comparison(self):
        """Test sales comparison endpoint"""
        client = self.client
        response = client.get('http://localhost:5000/api/sales/compare?period1=2024-01&period2=2024-02')

        assert response.status_code == 200

        data = response.get_json()
        print(data)
        assert isinstance(data, dict)
        assert len(data) > 0
        first = data["period1"]
        assert set(["end","start","total_sales","transaction_count"]).issubset(first.keys())
        second = data["period2"]
        assert set(["end","start","total_sales","transaction_count"]).issubset(second.keys())
        pass
    
    def test_data_quality_report(self):
        """Test data quality report endpoint"""
        client = self.client
        response = client.get('http://localhost:5000/api/data-quality')

        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, dict)
        assert len(data) > 0
        first = data["issues_found"]
        assert set(["duplicate_transactions","invalid_dates","missing_timezones","out_of_order_records"]).issubset(first.keys())
        pass

class TestErrorHandling:
    """Test error handling scenarios"""
    @pytest.fixture(autouse=True)
    def _setup_client(self, client):
        self.client = client

    def test_invalid_date_format(self):
        """Test response to invalid date formats"""
        client = self.client
        response = client.get('/api/sales/daily?start_date=2024-01-0d1&end_date=2024-01-31')

        assert response.status_code == 400
        pass
    
    def test_invalid_timezone(self):
        """Test response to invalid timezone"""
        client = self.client
        response = client.get('/api/sales/daily?start_date=2024-01-0d1&end_date=2024-01-31&timezone=Invalid/Timezone')

        assert response.status_code == 400
        pass
    
    def test_date_range_too_large(self):
        """Test response to overly large date ranges"""
        pytest.skip("Not implemented yet")
        pass

# To run tests: python -m pytest -vv -ra tests/test.py
