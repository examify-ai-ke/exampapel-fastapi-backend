from typing import Dict, Any
from app.schemas.common_schema import AuthProvider
import httpx


async def verify_social_token(provider: AuthProvider, token: str) -> Dict[str, Any]:
    """
    Verify social authentication tokens with respective providers
    Returns user information from the provider
    """
    
    if provider == AuthProvider.GOOGLE:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code != 200:
                raise ValueError("Invalid Google token")
            return response.json()
            
    elif provider == AuthProvider.GITHUB:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json"
                }
            )
            if response.status_code != 200:
                raise ValueError("Invalid GitHub token")
            
            # Get email from GitHub (it's a separate request)
            email_response = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json"
                }
            )
            user_data = response.json()
            if email_response.status_code == 200:
                emails = email_response.json()
                primary_email = next(
                    (email["email"] for email in emails if email["primary"]), 
                    None
                )
                if primary_email:
                    user_data["email"] = primary_email
            return user_data
    
    # Add more providers as needed
    # elif provider == AuthProvider.FACEBOOK:
    #     ...
    
    raise ValueError(f"Unsupported provider: {provider}") 