import asyncio
import httpx
from inserter import create_sample_exam_paper

BASE_URL = "http://localhost:80/api/v1"

async def verify():
    # 1. Login
    async with httpx.AsyncClient() as client:
        headers_init = {"Host": "fastapi.localhost"}
        
        # NOTE: Using credentials from inserter.py
        login_data = {
            "email": "david@techgrids.com", 
            "password": "##Jipanoran2020",
            "provider": "email"
        }
        
        print(f"Logging in with {login_data['email']}...")
        resp = await client.post(f"{BASE_URL}/login", json=login_data, headers=headers_init)
        if resp.status_code != 200:
            print(f"Login failed: {resp.status_code} {resp.text}")
            return
            
        token = resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}", "Host": "fastapi.localhost"}
        
        # 2. Prepare payload
        print("Preparing payload...")
        sample_data = create_sample_exam_paper()
        
        # Convert date/datetime objects to strings
        import json
        from datetime import date, datetime
        
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (date, datetime)):
                    return obj.isoformat()
                return super(DateTimeEncoder, self).default(obj)
        
        # Dump and reload to ensure JSON compatibility
        sample_data = json.loads(json.dumps(sample_data, cls=DateTimeEncoder))

        # Randomize to avoid collisions
        import uuid
        import random
        suffix = str(uuid.uuid4())[:8]
        salt = random.randint(1000, 9999)
        
        sample_data["prerequisites"]["institution"]["name"] += f" {suffix}"
        # Enum handling makes hacking programme name risky without mapping logic matches
        # So we skip programme name randomization if it's "Bachelors/Undergraduate" 
        # But we can try randomizing Course name
        sample_data["prerequisites"]["course"]["name"] += f" {suffix}"
        sample_data["prerequisites"]["exam_title"]["name"] += f" {suffix}"
        sample_data["exam_paper"]["year_of_exam"] = f"2025/{salt}"

        # 3. Call new endpoint
        print("Calling /exam-paper-builder/...")
        resp = await client.post(
            f"{BASE_URL}/exam-paper-builder/", 
            json=sample_data, 
            headers=headers,
            timeout=120.0
        )
        
        if resp.status_code == 200:
            data = resp.json()
            print("Success! Created Exam Paper:")
            print(f"ID: {data['id']}")
            print(f"Title: {data.get('title', {}).get('name')}")
            # print(f"Response: {data}")
        else:
            print(f"Failed: {resp.status_code}")
            print(resp.text)

if __name__ == "__main__":
    asyncio.run(verify())
