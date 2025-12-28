import httpx
import asyncio
import os
import json

# Configuration
BASE_URL = "http://localhost:80/api/v1"
EMAIL = "david@techgrids.com"
PASSWORD = "##Jipanoran2020"

async def verify_get_endpoint():
    print(f"Logging in with {EMAIL}...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Login
        login_data = {
            "username": EMAIL,
            "password": PASSWORD
        }
        
        headers = {"Host": "fastapi.localhost"}
        
        try:
            response = await client.post(
                f"{BASE_URL}/login/access-token", 
                data=login_data,
                headers=headers
            )
            
            # Try alternative login if first fails (some setups use different paths/formats)
            if response.status_code != 200:
                print("Trying JSON login...")
                response = await client.post(
                     f"{BASE_URL}/login", 
                     json=login_data,
                     headers=headers
                )

            response.raise_for_status()
            tokens = response.json()
            access_token = tokens["access_token"]
            
            # 2. Call GET endpoint
            print("Calling GET /exampaper...")
            auth_headers = {
                "Authorization": f"Bearer {access_token}",
                "Host": "fastapi.localhost"
            }
            
            response = await client.get(
                f"{BASE_URL}/exampaper?skip=0&limit=50",
                headers=auth_headers
            )
            
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                print("Success! Response JSON sample:")
                data = response.json()
                # Print first item summary to be safe
                if isinstance(data, list) and len(data) > 0:
                     print(json.dumps(data[0], indent=2))
                elif isinstance(data, dict) and "items" in data:
                     # Pagination response
                     items = data["items"]
                     if items:
                         print(json.dumps(items[0], indent=2))
                     else:
                         print("Empty items list")
                else:
                     print(str(data)[:200])
            else:
                print("Failed!")
                print(response.text)

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(verify_get_endpoint())
