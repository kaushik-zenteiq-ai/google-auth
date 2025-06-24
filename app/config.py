from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    db_host: str = "localhost"
    db_user: str = "postgres"
    db_password: str = "yourpassword"
    db_name: str = "first_fastapi"
    db_port: int = 5432
    database_url: str = "postgresql://postgres:yourpassword@localhost:5432/first_fastapi"
    
    # Google OAuth
    google_client_id: str
    google_client_secret: str
    
    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Application
    secret_key: str
    redirect_url: str = "http://127.0.0.1:8000/auth/callback"
    frontend_url: str = "http://127.0.0.1:8000/docs"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
