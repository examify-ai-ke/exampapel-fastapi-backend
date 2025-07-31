import requests
import time
import sys

def test_connectivity():
    endpoints = [
        "http://localhost/health",
        "http://fastapi.localhost/health",
        "http://fastapi_server:8000/health"
    ]
    
    for endpoint in endpoints:
        try:
            print(f"Testing {endpoint}...", end="")
            resp = requests.get(endpoint, timeout=5)
            print(f" Status: {resp.status_code}, Response: {resp.text}")
        except Exception as e:
            print(f" Error: {str(e)}")
    
    print("Test complete")

if __name__ == "__main__":
    # Wait for services to start
    time.sleep(10)
    test_connectivity()
    sys.exit(0) 