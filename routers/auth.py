from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Dict  # Added Dict here
from datetime import datetime, timedelta
from jose import JWTError
import logging

from database import get_db
from models import User, Session as DBSession, ConsentRecord, ConsentType
from auth import AuthService, get_current_user, get_current_active_parent

router = APIRouter()
logger = logging.getLogger(__name__)

# ==================== REQUEST/RESPONSE MODELS ====================

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None
    
    @field_validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain number')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class ConsentRequest(BaseModel):
    consent_type: ConsentType
    granted: bool
    version: str = "1.0"

# ==================== ENDPOINTS ====================

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new parent account
    
    - **email**: Valid email address
    - **password**: Strong password (min 8 chars, uppercase, lowercase, number)
    - **full_name**: Parent's full name
    - **phone**: Optional phone number
    """
    
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = AuthService.get_password_hash(user_data.password)
    
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        phone=user_data.phone,
        role="parent",
        is_active=True,
        is_verified=False  # Email verification required
    )
    
    db.add(new_user)
    await db.flush()  # Get user ID
    
    # Create COPPA consent record (required for child profiles)
    consent = ConsentRecord(
        user_id=new_user.id,
        consent_type=ConsentType.COPPA,
        granted=True,  # Will be prompted after registration
        consent_text="Parent agrees to COPPA terms for creating child profiles",
        version="1.0",
        ip_address=request.client.host if request.client else None
    )
    
    db.add(consent)
    await db.commit()
    await db.refresh(new_user)
    
    # Generate tokens
    access_token = AuthService.create_access_token({"sub": new_user.id})
    refresh_token = AuthService.create_refresh_token({"sub": new_user.id})
    
    # Save session
    expires_at = datetime.utcnow() + timedelta(days=7)
    session = DBSession(
        user_id=new_user.id,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    db.add(session)
    await db.commit()
    
    logger.info(f"✅ New parent registered: {new_user.email}")
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 1800,  # 30 minutes
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "full_name": new_user.full_name,
            "role": new_user.role
        }
    }

@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with email and password
    
    Returns JWT access token and refresh token
    """
    
    # Find user
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()
    
    if not user or not AuthService.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Generate tokens
    access_token = AuthService.create_access_token({"sub": user.id})
    refresh_token = AuthService.create_refresh_token({"sub": user.id})
    
    # Save session
    expires_at = datetime.utcnow() + timedelta(days=7)
    session = DBSession(
        user_id=user.id,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    db.add(session)
    
    # Update last login
    user.last_login = datetime.utcnow()
    
    await db.commit()
    
    logger.info(f"✅ Parent logged in: {user.email}")
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 1800,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        }
    }

@router.post("/refresh")
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    
    try:
        payload = AuthService.decode_token(refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        
        # Verify session exists and is valid
        result = await db.execute(
            select(DBSession).where(
                DBSession.refresh_token == refresh_token,
                DBSession.is_active == True,
                DBSession.expires_at > datetime.utcnow()
            )
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        # Generate new access token
        new_access_token = AuthService.create_access_token({"sub": user_id})
        
        # Update session
        session.access_token = new_access_token
        session.last_used = datetime.utcnow()
        
        await db.commit()
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": 1800
        }
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout and invalidate all user sessions
    """
    
    # Deactivate all user sessions
    result = await db.execute(
        select(DBSession).where(DBSession.user_id == current_user.id)
    )
    sessions = result.scalars().all()
    
    for session in sessions:
        session.is_active = False
    
    await db.commit()
    
    logger.info(f"✅ Parent logged out: {current_user.email}")
    
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information
    """
    return current_user

@router.post("/consent")
async def record_consent(
    consent_data: ConsentRequest,
    request: Request,
    current_user: User = Depends(get_current_active_parent),
    db: AsyncSession = Depends(get_db)
):
    """
    Record parental consent (COPPA compliance)
    """
    
    consent = ConsentRecord(
        user_id=current_user.id,
        consent_type=consent_data.consent_type,
        granted=consent_data.granted,
        consent_text=f"Parent consent for {consent_data.consent_type.value}",
        version=consent_data.version,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    db.add(consent)
    await db.commit()
    
    logger.info(f"✅ Consent recorded: {current_user.email} - {consent_data.consent_type.value}")
    
    return {"message": "Consent recorded successfully", "consent_id": consent.id}
