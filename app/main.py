# app/main.py
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
import time
import logging

from .config import settings
from .database import get_db, create_tables, engine
from . import models, schemas, crud, auth

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="FastAPI Google OAuth Authentication",
    description="A complete FastAPI application with Google OAuth authentication and PostgreSQL",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# Middleware to log request processing time
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"Request: {request.method} {request.url.path} completed in {process_time:.4f} seconds")
    return response

# Startup event
@app.on_event("startup")
async def startup_event():
    """Create database tables on startup"""
    create_tables()
    logger.info("Database tables created successfully")

# Health check endpoint
@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {
        "message": "FastAPI Google OAuth Authentication Server",
        "status": "healthy",
        "version": "1.0.0"
    }

@app.get("/health", tags=["Health"])
async def health_check(db: Session = Depends(get_db)):
    """Detailed health check with database connectivity"""
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": time.time()
    }

# Authentication endpoints
@app.get("/auth/login", tags=["Authentication"])
async def login(request: Request):
    """Initiate Google OAuth login"""
    return await auth.google_login(request)

@app.get("/auth/callback", tags=["Authentication"])
async def callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback"""
    return await auth.google_callback(request, db)

@app.post("/auth/logout", response_model=schemas.LogoutResponse, tags=["Authentication"])
async def logout(
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Logout current user"""
    return auth.logout_user(response, db, current_user)

@app.post("/auth/revoke-all", tags=["Authentication"])
async def revoke_all_tokens(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Revoke all tokens for current user"""
    return auth.revoke_all_user_tokens(db, current_user)

# User endpoints
@app.get("/me", response_model=schemas.UserResponse, tags=["Users"])
async def get_current_user_info(
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get current user information"""
    return {"user": current_user, "message": "User information retrieved successfully"}

@app.get("/users/me", response_model=schemas.User, tags=["Users"])
async def get_me(current_user: models.User = Depends(auth.get_current_user)):
    """Get current user details (alternative endpoint)"""
    return current_user

@app.put("/users/me", response_model=schemas.User, tags=["Users"])
async def update_me(
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Update current user information"""
    updated_user = crud.update_user(db, current_user.user_id, user_update)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

# Protected endpoint example
@app.get("/protected", tags=["Protected"])
async def protected_endpoint(
    current_user: models.User = Depends(auth.get_current_user)
):
    """Example protected endpoint that requires authentication"""
    return {
        "message": f"Hello {current_user.user_name or current_user.email_id}!",
        "user_id": current_user.user_id,
        "email": current_user.email_id,
        "access_time": time.time()
    }

# Chat endpoint (as requested)
@app.get("/chat", tags=["Chat"])
async def chat_endpoint(
    current_user: models.User = Depends(auth.get_current_user)
):
    """Protected chat endpoint"""
    return {
        "message": "Welcome to the chat!",
        "user": {
            "id": current_user.user_id,
            "name": current_user.user_name,
            "email": current_user.email_id,
            "picture": current_user.user_pic
        },
        "timestamp": time.time()
    }

# Admin endpoints (optional - add proper admin authentication in production)
@app.get("/admin/users", response_model=list[schemas.User], tags=["Admin"])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)  # Add admin check here
):
    """Get all users (admin only)"""
    return crud.get_users(db, skip=skip, limit=limit)

@app.post("/admin/cleanup-tokens", tags=["Admin"])
async def cleanup_expired_tokens(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)  # Add admin check here
):
    """Cleanup expired tokens (admin only)"""
    return auth.cleanup_expired_tokens(db)

@app.get("/admin/token-stats", tags=["Admin"])
async def get_token_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)  # Add admin check here
):
    """Get token statistics (admin only)"""
    return auth.get_token_statistics(db)

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return {
        "error": exc.detail,
        "status_code": exc.status_code,
        "path": request.url.path
    }

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    return {
        "error": "Internal server error",
        "status_code": 500,
        "path": request.url.path
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )