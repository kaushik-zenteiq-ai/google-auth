from fastapi import HTTPException, status, Depends, Request, Cookie, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt, JWTError, ExpiredSignatureError
import requests
import uuid
from typing import Optional

from .config import settings
from .database import get_db
from . import crud, schemas, models

# Security
security = HTTPBearer(auto_error=False)

# OAuth setup
oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    access_token_url="https://oauth2.googleapis.com/token",
    jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
    client_kwargs={
        "scope": "openid email profile",
        "redirect_uri": settings.redirect_url
    }
)

# JWT utility functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def verify_token(token: str) -> schemas.TokenData:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        
        if user_id is None or email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        return schemas.TokenData(user_id=user_id, email=email)
    
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

def get_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Cookie(None, alias="access_token"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> models.User:
    """Get current authenticated user from token"""
    
    # Try to get token from cookie first, then from Authorization header
    access_token = token
    if not access_token and credentials:
        access_token = credentials.credentials
    
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify token
    token_data = verify_token(access_token)
    
    # Check if token exists in database and is active
    db_token = crud.get_token_by_value(db, access_token)
    if not db_token or not db_token.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or revoked"
        )
    
    # Get user from database
    user = crud.get_user_by_google_id(db, token_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled"
        )
    
    # Update last accessed time
    crud.update_user_last_accessed(db, user.user_id)
    
    return user

async def google_login(request: Request) -> RedirectResponse:
    """Initiate Google OAuth login"""
    request.session.clear()
    
    # Store the frontend URL for redirect after authentication
    frontend_url = settings.frontend_url
    request.session["login_redirect"] = frontend_url
    
    # Redirect to Google OAuth
    return await oauth.google.authorize_redirect(request, settings.redirect_url)

async def google_callback(request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    """Handle Google OAuth callback"""
    try:
        # Exchange authorization code for access token
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google authentication failed"
        )
    
    try:
        # Get user info from Google
        user_info_endpoint = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f"Bearer {token['access_token']}"}
        google_response = requests.get(user_info_endpoint, headers=headers)
        google_response.raise_for_status()
        user_info = google_response.json()
        print(f"User info from Google: {type(user_info)}")
                
        print(f"User info from Google: {user_info.values()}")         
        
        # Extract user data from token
        user_data = token.get("userinfo", {})
        google_user_id = user_data.get("sub")
        email = user_data.get("email")
        
        # Validate required fields
        if not google_user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user data from Google"
            )
        
        # Verify issuer
        iss = user_data.get("iss")
        if iss not in ["https://accounts.google.com", "accounts.google.com"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token issuer"
            )
        
        # Check if user exists, create if not
        user = crud.get_user_by_google_id(db, google_user_id)
        if not user:
            # Create new user
            user_create = schemas.UserCreate(
                user_id=google_user_id,
                email_id=email,
                user_name=user_info.get("name"),
                user_pic=user_info.get("picture")
            )
            user = crud.create_user(db, user_create)
        else:
            # Update existing user info
            user_update = schemas.UserUpdate(
                user_name=user_info.get("name"),
                user_pic=user_info.get("picture")
            )
            user = crud.update_user(db, google_user_id, user_update)
        
        # Create JWT token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": google_user_id, "email": email},
            expires_delta=access_token_expires
        )
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Store token in database
        token_create = schemas.IssuedTokenCreate(
            token=access_token,
            email_id=email,
            session_id=session_id,
            user_id=google_user_id,
            expires_at=datetime.utcnow() + access_token_expires
        )
        crud.create_issued_token(db, token_create)
        
        # Prepare redirect response
        redirect_url = request.session.pop("login_redirect", settings.frontend_url)
        response = RedirectResponse(url=redirect_url)
        
        # Set secure cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=settings.access_token_expire_minutes * 60
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication processing failed: {str(e)}"
        )

def logout_user(
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    token: Optional[str] = Cookie(None, alias="access_token")
) -> dict:
    """Logout user and revoke tokens"""
    
    if token:
        # Revoke the current token
        crud.revoke_token(db, token)
        
        # Clear the cookie
        response.delete_cookie(key="access_token")
    
    return {"message": "Successfully logged out"}

def revoke_all_user_tokens(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
) -> dict:
    """Revoke all tokens for the current user"""
    
    count = crud.revoke_user_tokens(db, current_user.user_id)
    
    return {
        "message": f"Successfully revoked {count} tokens",
        "revoked_count": count
    }

# Optional: Admin functions (add authentication check for admin users)
def cleanup_expired_tokens(db: Session = Depends(get_db)) -> dict:
    """Clean up expired tokens (admin function)"""
    count = crud.cleanup_expired_tokens(db)
    return {
        "message": f"Cleaned up {count} expired tokens",
        "cleaned_count": count
    }

def get_token_statistics(db: Session = Depends(get_db)) -> dict:
    """Get token statistics (admin function)"""
    return crud.get_token_stats(db)