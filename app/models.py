from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Index
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(255), unique=True, index=True, nullable=False)  # Google user ID
    email_id = Column(String(255), unique=True, index=True, nullable=False)
    user_name = Column(String(255), nullable=True)
    user_pic = Column(Text, nullable=True)
    first_logged_in = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Create indexes for better performance
    __table_args__ = (
        Index('idx_user_email', 'email_id'),
        Index('idx_user_google_id', 'user_id'),
    )

class IssuedToken(Base):
    __tablename__ = "issued_tokens"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    token = Column(Text, nullable=False, index=True)
    email_id = Column(String(255), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    user_id = Column(String(255), nullable=True)  # Google user ID
    token_type = Column(String(50), default="access", nullable=False)  # access, refresh
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Create indexes for better performance
    __table_args__ = (
        Index('idx_token_email', 'email_id'),
        Index('idx_token_session', 'session_id'),
        Index('idx_token_active', 'is_active'),
        Index('idx_token_expires', 'expires_at'),
    )
    