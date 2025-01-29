from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Any
from ..includes import models, schemas, auth
from ..includes.database import get_db

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=schemas.User)
async def register(user: schemas.UserCreate, db: Session = Depends(get_db)) -> Any:
    # Check if user already exists
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    db_user = models.User(
        email=user.email,
        hashed_password=auth.get_password_hash(user.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create and store verification token
    verification = auth.create_verification_token(db_user.id)
    db.add(verification)
    db.commit()
    
    # Send verification email
    await auth.send_verification_email(user.email, verification.token)
    
    return db_user

@router.post("/verify-email")
async def verify_email(
    token_data: schemas.EmailVerificationConfirm,
    db: Session = Depends(get_db)
) -> Any:
    verification = db.query(models.EmailVerification).filter(
        models.EmailVerification.token == token_data.token,
        models.EmailVerification.used == False,
        models.EmailVerification.expires_at > datetime.utcnow()
    ).first()
    
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    # Mark user as active
    user = db.query(models.User).filter(models.User.id == verification.user_id).first()
    user.is_active = True
    
    # Mark verification token as used
    verification.used = True
    
    db.commit()
    
    return {"message": "Email verified successfully"}

@router.post("/login", response_model=schemas.Token)
async def login(
    form_data: schemas.UserLogin,
    db: Session = Depends(get_db)
) -> Any:
    user = db.query(models.User).filter(models.User.email == form_data.email).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please verify your email first"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/reset-password-request")
async def request_password_reset(
    reset_request: schemas.PasswordResetRequest,
    db: Session = Depends(get_db)
) -> Any:
    user = db.query(models.User).filter(models.User.email == reset_request.email).first()
    if not user:
        # Don't reveal that the email doesn't exist
        return {"message": "If the email exists, a password reset link has been sent"}
    
    # Create and store reset token
    reset = auth.create_password_reset_token(user.id)
    db.add(reset)
    db.commit()
    
    # Send reset email
    await auth.send_password_reset_email(user.email, reset.token)
    
    return {"message": "If the email exists, a password reset link has been sent"}

@router.post("/reset-password-confirm")
async def confirm_password_reset(
    reset_data: schemas.PasswordResetConfirm,
    db: Session = Depends(get_db)
) -> Any:
    reset = db.query(models.PasswordReset).filter(
        models.PasswordReset.token == reset_data.token,
        models.PasswordReset.used == False,
        models.PasswordReset.expires_at > datetime.utcnow()
    ).first()
    
    if not reset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Update user's password
    user = db.query(models.User).filter(models.User.id == reset.user_id).first()
    user.hashed_password = auth.get_password_hash(reset_data.new_password)
    
    # Mark reset token as used
    reset.used = True
    
    db.commit()
    
    return {"message": "Password reset successfully"}

@router.get("/me", response_model=schemas.User)
async def read_users_me(
    current_user: models.User = Depends(auth.get_current_user)
) -> Any:
    return current_user
