import requests
import json

BASE_URL = "http://localhost:5000"

def test_endpoint(endpoint, params=None):
    """Test an API endpoint and print results"""
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.get(url, params=params)
        print(f"Testing: {url}")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if("data" in data):
                print(data["data"])
            elif("issues_found" in data):
                print(data["issues_found"])
            elif("period1" in data):
                print(f"Period 1: {data['period1']}")
                print(f"Period 2: {data['period2']}")
                
            print(f"Success! Got {len(data.get('data', []))} records")
        else:
            print(f"Error: {response.text}")
        print("-" * 50)
    except Exception as e:
        print(f"Request failed: {e}")

# Run tests
test_endpoint("/health")
test_endpoint("/api/sales/daily", {"start_date": "2024-01-01", "end_date": "2024-01-31"})
test_endpoint("/api/sales/hourly", {"date": "2024-01-15"})
test_endpoint("/api/sales/compare", {"period1": "2024-01", "period2": "2024-02"})
test_endpoint("/api/data-quality")