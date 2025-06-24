from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from typing import Optional, List
from . import models, schemas

# User CRUD operations
def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """Get user by email"""
    return db.query(models.User).filter(models.User.email_id == email).first()

def get_user_by_google_id(db: Session, google_user_id: str) -> Optional[models.User]:
    """Get user by Google user ID"""
    return db.query(models.User).filter(models.User.user_id == google_user_id).first()

def get_user_by_id(db: Session, user_id: int) -> Optional[models.User]:
    """Get user by database ID"""
    return db.query(models.User).filter(models.User.id == user_id).first()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    """Create a new user"""
    db_user = models.User(
        user_id=user.user_id,
        email_id=user.email_id,
        user_name=user.user_name,
        user_pic=user.user_pic,
        first_logged_in=datetime.utcnow(),
        last_accessed=datetime.utcnow()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: str, user_update: schemas.UserUpdate) -> Optional[models.User]:
    """Update user information"""
    db_user = get_user_by_google_id(db, user_id)
    if not db_user:
        return None
    
    update_data = user_update.dict(exclude_unset=True)
    update_data['last_accessed'] = datetime.utcnow()
    
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_last_accessed(db: Session, user_id: str) -> Optional[models.User]:
    """Update user's last accessed time"""
    db_user = get_user_by_google_id(db, user_id)
    if db_user:
        db_user.last_accessed = datetime.utcnow()
        db.commit()
        db.refresh(db_user)
    return db_user

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    """Get all users with pagination"""
    return db.query(models.User).filter(models.User.is_active == True).offset(skip).limit(limit).all()

# Token CRUD operations
def create_issued_token(db: Session, token_data: schemas.IssuedTokenCreate) -> models.IssuedToken:
    """Create a new issued token"""
    db_token = models.IssuedToken(
        token=token_data.token,
        email_id=token_data.email_id,
        session_id=token_data.session_id,
        user_id=token_data.user_id,
        token_type=token_data.token_type,
        expires_at=token_data.expires_at
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token

def get_token_by_value(db: Session, token: str) -> Optional[models.IssuedToken]:
    """Get token by token value"""
    return db.query(models.IssuedToken).filter(
        and_(
            models.IssuedToken.token == token,
            models.IssuedToken.is_active == True
        )
    ).first()

def get_tokens_by_user(db: Session, user_id: str, active_only: bool = True) -> List[models.IssuedToken]:
    """Get all tokens for a user"""
    query = db.query(models.IssuedToken).filter(models.IssuedToken.user_id == user_id)
    if active_only:
        query = query.filter(models.IssuedToken.is_active == True)
    return query.all()

def get_tokens_by_session(db: Session, session_id: str) -> List[models.IssuedToken]:
    """Get all tokens for a session"""
    return db.query(models.IssuedToken).filter(
        and_(
            models.IssuedToken.session_id == session_id,
            models.IssuedToken.is_active == True
        )
    ).all()

def revoke_token(db: Session, token: str) -> bool:
    """Revoke a specific token"""
    db_token = get_token_by_value(db, token)
    if db_token:
        db_token.is_active = False
        db_token.revoked_at = datetime.utcnow()
        db.commit()
        return True
    return False

def revoke_user_tokens(db: Session, user_id: str, exclude_session: Optional[str] = None) -> int:
    """Revoke all tokens for a user, optionally excluding a specific session"""
    query = db.query(models.IssuedToken).filter(
        and_(
            models.IssuedToken.user_id == user_id,
            models.IssuedToken.is_active == True
        )
    )
    
    if exclude_session:
        query = query.filter(models.IssuedToken.session_id != exclude_session)
    
    tokens = query.all()
    count = 0
    
    for token in tokens:
        token.is_active = False
        token.revoked_at = datetime.utcnow()
        count += 1
    
    db.commit()
    return count

def revoke_session_tokens(db: Session, session_id: str) -> int:
    """Revoke all tokens for a specific session"""
    tokens = get_tokens_by_session(db, session_id)
    count = 0
    
    for token in tokens:
        token.is_active = False
        token.revoked_at = datetime.utcnow()
        count += 1
    
    db.commit()
    return count

def cleanup_expired_tokens(db: Session) -> int:
    """Clean up expired tokens"""
    expired_tokens = db.query(models.IssuedToken).filter(
        and_(
            models.IssuedToken.expires_at < datetime.utcnow(),
            models.IssuedToken.is_active == True
        )
    ).all()
    
    count = 0
    for token in expired_tokens:
        token.is_active = False
        token.revoked_at = datetime.utcnow()
        count += 1
    
    db.commit()
    return count

def get_token_stats(db: Session) -> dict:
    """Get token statistics"""
    total_tokens = db.query(models.IssuedToken).count()
    active_tokens = db.query(models.IssuedToken).filter(models.IssuedToken.is_active == True).count()
    expired_tokens = db.query(models.IssuedToken).filter(
        and_(
            models.IssuedToken.expires_at < datetime.utcnow(),
            models.IssuedToken.is_active == True
        )
    ).count()
    
    return {
        "total_tokens": total_tokens,
        "active_tokens": active_tokens,
        "expired_tokens": expired_tokens,
        "revoked_tokens": total_tokens - active_tokens
    }