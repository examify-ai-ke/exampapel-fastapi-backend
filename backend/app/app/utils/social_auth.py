from typing import Dict, Any
from app.schemas.common_schema import AuthProvider
import httpx
import logging
import jwt


async def verify_social_token(provider: AuthProvider, token: str) -> Dict[str, Any]:
    """
    Verify social authentication tokens with respective providers
    Returns user information from the provider
    """
    logging.info(f"verify_social_token called with provider: {provider} (type: {type(provider)})")
    
    if provider == AuthProvider.google:
        try:
            # First, try to decode as ID token (JWT)
            try:
                logging.info("Attempting to decode as Google ID token (JWT)...")
                decoded = jwt.decode(token, options={"verify_signature": False})
                
                # Validate it's a Google token
                if decoded.get("iss") in ["https://accounts.google.com", "accounts.google.com"]:
                    logging.info(f"Valid Google ID token decoded for: {decoded.get('email', 'NO_EMAIL')}")
                    
                    # Validate required fields
                    if "email" not in decoded:
                        raise ValueError("Google ID token missing email field")
                    if "sub" not in decoded:
                        raise ValueError("Google ID token missing sub (user ID) field")
                    
                    return decoded
            except jwt.DecodeError:
                logging.info("Not a JWT token, trying as access token...")
            
            # If not JWT, try as access token
            async with httpx.AsyncClient() as client:
                logging.info(f"Verifying Google access token...")
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                logging.info(f"Google API response status: {response.status_code}")
                
                if response.status_code != 200:
                    error_detail = response.text
                    logging.error(f"Google token verification failed: {response.status_code} - {error_detail}")
                    raise ValueError(f"Invalid Google token: {response.status_code} - {error_detail}")
                
                user_data = response.json()
                logging.info(f"Google user data received: {user_data.get('email', 'NO_EMAIL')}")
                
                # Validate required fields
                if "email" not in user_data:
                    raise ValueError("Google response missing email field")
                if "sub" not in user_data:
                    raise ValueError("Google response missing sub (user ID) field")
                
                return user_data
        except httpx.RequestError as e:
            logging.error(f"Network error during Google token verification: {str(e)}")
            raise ValueError(f"Network error contacting Google: {str(e)}")
            
    elif provider == AuthProvider.github:
        try:
            async with httpx.AsyncClient() as client:
                logging.info(f"Verifying GitHub token...")
                response = await client.get(
                    "https://api.github.com/user",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json"
                    }
                )
                
                logging.info(f"GitHub API response status: {response.status_code}")
                
                if response.status_code != 200:
                    error_detail = response.text
                    logging.error(f"GitHub token verification failed: {response.status_code} - {error_detail}")
                    raise ValueError(f"Invalid GitHub token: {response.status_code} - {error_detail}")
                
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
                
                logging.info(f"GitHub user data received: {user_data.get('email', 'NO_EMAIL')}")
                return user_data
        except httpx.RequestError as e:
            logging.error(f"Network error during GitHub token verification: {str(e)}")
            raise ValueError(f"Network error contacting GitHub: {str(e)}")
    
    elif provider == AuthProvider.twitter:
        try:
            async with httpx.AsyncClient() as client:
                logging.info(f"Verifying Twitter token...")
                response = await client.get(
                    "https://api.twitter.com/2/users/me",
                    params={"user.fields": "confirmed_email,profile_image_url,username,name,verified", "expansions": "pinned_tweet_id"},
                    headers={
                        "Authorization": f"Bearer {token}"
                    }
                )
                
                logging.info(f"Twitter API response status: {response.status_code}")
                
                if response.status_code != 200:
                    error_detail = response.text
                    logging.error(f"Twitter token verification failed: {response.status_code} - {error_detail}")
                    raise ValueError(f"Invalid Twitter token: {response.status_code} - {error_detail}")
                
                user_data_resp = response.json()
                logging.info(f"Twitter user data received: {user_data_resp.get('data', {})}")
                user_data = user_data_resp.get("data", {})
                
                twitter_id = user_data.get("id")
                username = user_data.get("username")
                name = user_data.get("name")
                email = user_data.get("confirmed_email")
                
                if not email:
                    # Treat email as optional for Twitter v2 and provide placeholder
                    email = f"{twitter_id or username}@twitter.local"
                    user_data["email_verified"] = False
                else:
                    user_data["email_verified"] = True
                
                user_data["email"] = email
                
                logging.info(f"Twitter user data received for: {username} with email: {email}")
                return user_data
                
        except httpx.RequestError as e:
            logging.error(f"Network error during Twitter token verification: {str(e)}")
            raise ValueError(f"Network error contacting Twitter: {str(e)}")

    # Add more providers as needed
    # elif provider == AuthProvider.facebook:
    #     ...
    
    raise ValueError(f"Unsupported provider: {provider}") 