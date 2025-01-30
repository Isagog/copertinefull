from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from . import models, schemas
from .database import get_db
import os
from dotenv import load_dotenv
import secrets
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pathlib import Path

load_dotenv()

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
VERIFICATION_TOKEN_EXPIRE_HOURS = 24
PASSWORD_RESET_TOKEN_EXPIRE_HOURS = 1

# Email configuration
# Load and validate email configuration
EMAIL_CONFIG = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME", "any"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", "any"),
    MAIL_FROM=os.getenv("MAIL_FROM", "test@example.com"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", "1025")),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "localhost"),
    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS", "False").lower() == "true",
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS", "False").lower() == "true",
    USE_CREDENTIALS=os.getenv("MAIL_USERNAME") not in (None, "any"),
    TEMPLATE_FOLDER=Path(__file__).parent / "email_templates",
    VALIDATE_CERTS=os.getenv("MAIL_VALIDATE_CERTS", "False").lower() == "true"
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
fastmail = FastMail(EMAIL_CONFIG)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified"
        )
    return user

def create_verification_token(user_id: str) -> models.EmailVerification:
    token = secrets.token_urlsafe(32)
    verification = models.EmailVerification(
        user_id=user_id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS)
    )
    return verification

def create_password_reset_token(user_id: str) -> models.PasswordReset:
    token = secrets.token_urlsafe(32)
    reset = models.PasswordReset(
        user_id=user_id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
    )
    return reset

async def send_verification_email(email: str, token: str):
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    verification_url = f"{frontend_url}/copertine/auth/verify?token={token}"
    
    # Load email template
    template_path = Path(__file__).parent / "email_templates" / "verification.html"
    with open(template_path) as f:
        template = f.read()
        
    # Replace template variables
    html_content = template.replace("{{ verification_url }}", verification_url)
    html_content = html_content.replace("{{ expire_hours }}", str(VERIFICATION_TOKEN_EXPIRE_HOURS))
    
    message = MessageSchema(
        subject="Verify your email",
        recipients=[email],
        body=html_content,
        subtype="html"
    )
    
    await fastmail.send_message(message)

async def send_password_reset_email(email: str, token: str):
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    reset_url = f"{frontend_url}/copertine/auth/reset-password/confirm?token={token}"
    
    # Load email template
    template_path = Path(__file__).parent / "email_templates" / "password_reset.html"
    with open(template_path) as f:
        template = f.read()
        
    # Replace template variables
    html_content = template.replace("{{ reset_url }}", reset_url)
    html_content = html_content.replace("{{ expire_hours }}", str(PASSWORD_RESET_TOKEN_EXPIRE_HOURS))
    
    message = MessageSchema(
        subject="Reset your password",
        recipients=[email],
        body=html_content,
        subtype="html"
    )
    
    await fastmail.send_message(message)
