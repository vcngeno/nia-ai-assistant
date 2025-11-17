from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime, date
import logging

from database import get_db
from models import User, Child, UsageLog, AuditLog
from auth import get_current_active_parent, hash_pin, verify_pin

router = APIRouter()
logger = logging.getLogger(__name__)

# ==================== REQUEST/RESPONSE MODELS ====================

class ChildCreate(BaseModel):
    first_name: str
    nickname: Optional[str] = None
    date_of_birth: date
    grade_level: str
    pin: Optional[str] = None
    avatar_url: Optional[str] = None
    
    @field_validator('first_name')
    def validate_first_name(cls, v):
        if len(v) < 1 or len(v) > 50:
            raise ValueError('First name must be 1-50 characters')
        if not v.replace(' ', '').isalpha():
            raise ValueError('First name must contain only letters')
        return v.strip()
    
    @field_validator('grade_level')
    def validate_grade_level(cls, v):
        valid_grades = [
            'Pre-K', 'K', 
            '1st', '2nd', '3rd', '4th', '5th', '6th',
            '7th', '8th', '9th', '10th', '11th', '12th'
        ]
        if v not in valid_grades:
            raise ValueError(f'Grade level must be one of: {", ".join(valid_grades)}')
        return v
    
    @field_validator('pin')
    def validate_pin(cls, v):
        if v is None:
            return v
        if not v.isdigit():
            raise ValueError('PIN must contain only digits')
        if len(v) < 4 or len(v) > 6:
            raise ValueError('PIN must be 4-6 digits')
        return v
    
    @field_validator('date_of_birth')
    def validate_age(cls, v):
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        
        if age < 3:
            raise ValueError('Child must be at least 3 years old')
        if age > 18:
            raise ValueError('Child must be under 18 years old')
        
        return v

class ChildUpdate(BaseModel):
    first_name: Optional[str] = None
    nickname: Optional[str] = None
    grade_level: Optional[str] = None
    pin: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None
    requires_supervision: Optional[bool] = None
    content_filter_level: Optional[str] = None
    learning_preferences: Optional[dict] = None

class ChildResponse(BaseModel):
    id: int
    parent_id: int
    first_name: str
    nickname: Optional[str]
    display_name: str  # Computed: nickname or first_name
    age: int  # Computed from date_of_birth
    grade_level: str
    avatar_url: Optional[str]
    is_active: bool
    requires_supervision: bool
    content_filter_level: str
    learning_preferences: Optional[dict]
    created_at: datetime
    last_active: Optional[datetime]
    
    class Config:
        from_attributes = True

class ChildPinVerify(BaseModel):
    child_id: int
    pin: str

class ChildStats(BaseModel):
    total_conversations: int
    total_messages: int
    questions_asked: int
    topics_explored: List[str]
    last_7_days_activity: int
    favorite_subjects: List[dict]

# ==================== HELPER FUNCTIONS ====================

def calculate_age(date_of_birth: date) -> int:
    """Calculate age from date of birth"""
    today = date.today()
    return today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))

def get_display_name(child: Child) -> str:
    """Get child's display name (nickname or first name)"""
    return child.nickname if child.nickname else child.first_name

async def log_audit(
    db: AsyncSession,
    user_id: int,
    child_id: Optional[int],
    action: str,
    resource: str,
    details: dict,
    ip_address: Optional[str] = None,
    success: bool = True
):
    """Log audit trail for compliance"""
    audit = AuditLog(
        user_id=user_id,
        child_id=child_id,
        action=action,
        resource=resource,
        details=details,
        ip_address=ip_address,
        success=success
    )
    db.add(audit)

# ==================== ENDPOINTS ====================

@router.post("/", response_model=ChildResponse, status_code=status.HTTP_201_CREATED)
async def create_child_profile(
    child_data: ChildCreate,
    current_user: User = Depends(get_current_active_parent),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new child profile (COPPA compliant)
    
    - **first_name**: Child's first name (required)
    - **nickname**: Optional nickname they want to be called
    - **date_of_birth**: Birth date (must be 3-18 years old)
    - **grade_level**: Current grade (Pre-K through 12th)
    - **pin**: Optional 4-6 digit PIN for child login
    - **avatar_url**: Optional profile picture URL
    """
    
    # Check if parent has reached child limit (e.g., 10 children max)
    result = await db.execute(
        select(Child).where(Child.parent_id == current_user.id)
    )
    existing_children = result.scalars().all()
    
    if len(existing_children) >= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum of 10 child profiles per parent account"
        )
    
    # Create child profile
    new_child = Child(
        parent_id=current_user.id,
        first_name=child_data.first_name.strip(),
        nickname=child_data.nickname.strip() if child_data.nickname else None,
        date_of_birth=datetime.combine(child_data.date_of_birth, datetime.min.time()),
        grade_level=child_data.grade_level,
        pin_hash=hash_pin(child_data.pin) if child_data.pin else None,
        avatar_url=child_data.avatar_url,
        is_active=True,
        requires_supervision=True,  # Default: supervision required
        content_filter_level="strict"  # Default: strict filtering
    )
    
    db.add(new_child)
    await db.flush()  # Get child ID
    
    # Log audit trail
    await log_audit(
        db=db,
        user_id=current_user.id,
        child_id=new_child.id,
        action="CREATE",
        resource="child_profile",
        details={
            "first_name": new_child.first_name,
            "grade_level": new_child.grade_level,
            "age": calculate_age(child_data.date_of_birth)
        },
        success=True
    )
    
    await db.commit()
    await db.refresh(new_child)
    
    logger.info(f"✅ Child profile created: {new_child.first_name} (Parent: {current_user.email})")
    
    # Build response
    return ChildResponse(
        id=new_child.id,
        parent_id=new_child.parent_id,
        first_name=new_child.first_name,
        nickname=new_child.nickname,
        display_name=get_display_name(new_child),
        age=calculate_age(child_data.date_of_birth),
        grade_level=new_child.grade_level,
        avatar_url=new_child.avatar_url,
        is_active=new_child.is_active,
        requires_supervision=new_child.requires_supervision,
        content_filter_level=new_child.content_filter_level,
        learning_preferences=new_child.learning_preferences,
        created_at=new_child.created_at,
        last_active=new_child.last_active
    )

@router.get("/", response_model=List[ChildResponse])
async def get_all_children(
    current_user: User = Depends(get_current_active_parent),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all child profiles for the current parent
    """
    
    result = await db.execute(
        select(Child)
        .where(Child.parent_id == current_user.id)
        .order_by(Child.created_at.desc())
    )
    children = result.scalars().all()
    
    response = []
    for child in children:
        response.append(ChildResponse(
            id=child.id,
            parent_id=child.parent_id,
            first_name=child.first_name,
            nickname=child.nickname,
            display_name=get_display_name(child),
            age=calculate_age(child.date_of_birth.date()),
            grade_level=child.grade_level,
            avatar_url=child.avatar_url,
            is_active=child.is_active,
            requires_supervision=child.requires_supervision,
            content_filter_level=child.content_filter_level,
            learning_preferences=child.learning_preferences,
            created_at=child.created_at,
            last_active=child.last_active
        ))
    
    return response

@router.get("/{child_id}", response_model=ChildResponse)
async def get_child_profile(
    child_id: int,
    current_user: User = Depends(get_current_active_parent),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific child's profile
    """
    
    result = await db.execute(
        select(Child).where(
            Child.id == child_id,
            Child.parent_id == current_user.id
        )
    )
    child = result.scalar_one_or_none()
    
    if not child:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child profile not found"
        )
    
    return ChildResponse(
        id=child.id,
        parent_id=child.parent_id,
        first_name=child.first_name,
        nickname=child.nickname,
        display_name=get_display_name(child),
        age=calculate_age(child.date_of_birth.date()),
        grade_level=child.grade_level,
        avatar_url=child.avatar_url,
        is_active=child.is_active,
        requires_supervision=child.requires_supervision,
        content_filter_level=child.content_filter_level,
        learning_preferences=child.learning_preferences,
        created_at=child.created_at,
        last_active=child.last_active
    )

@router.put("/{child_id}", response_model=ChildResponse)
async def update_child_profile(
    child_id: int,
    child_data: ChildUpdate,
    current_user: User = Depends(get_current_active_parent),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a child's profile
    """
    
    result = await db.execute(
        select(Child).where(
            Child.id == child_id,
            Child.parent_id == current_user.id
        )
    )
    child = result.scalar_one_or_none()
    
    if not child:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child profile not found"
        )
    
    # Track changes for audit
    changes = {}
    
    # Update fields
    if child_data.first_name is not None:
        changes['first_name'] = {'old': child.first_name, 'new': child_data.first_name}
        child.first_name = child_data.first_name.strip()
    
    if child_data.nickname is not None:
        changes['nickname'] = {'old': child.nickname, 'new': child_data.nickname}
        child.nickname = child_data.nickname.strip() if child_data.nickname else None
    
    if child_data.grade_level is not None:
        changes['grade_level'] = {'old': child.grade_level, 'new': child_data.grade_level}
        child.grade_level = child_data.grade_level
    
    if child_data.pin is not None:
        child.pin_hash = hash_pin(child_data.pin)
        changes['pin'] = 'updated'
    
    if child_data.avatar_url is not None:
        child.avatar_url = child_data.avatar_url
    
    if child_data.is_active is not None:
        changes['is_active'] = {'old': child.is_active, 'new': child_data.is_active}
        child.is_active = child_data.is_active
    
    if child_data.requires_supervision is not None:
        changes['requires_supervision'] = {'old': child.requires_supervision, 'new': child_data.requires_supervision}
        child.requires_supervision = child_data.requires_supervision
    
    if child_data.content_filter_level is not None:
        if child_data.content_filter_level not in ['strict', 'moderate', 'relaxed']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="content_filter_level must be 'strict', 'moderate', or 'relaxed'"
            )
        changes['content_filter_level'] = {'old': child.content_filter_level, 'new': child_data.content_filter_level}
        child.content_filter_level = child_data.content_filter_level
    
    if child_data.learning_preferences is not None:
        child.learning_preferences = child_data.learning_preferences
    
    # Log audit trail
    await log_audit(
        db=db,
        user_id=current_user.id,
        child_id=child.id,
        action="UPDATE",
        resource="child_profile",
        details=changes,
        success=True
    )
    
    await db.commit()
    await db.refresh(child)
    
    logger.info(f"✅ Child profile updated: {child.first_name} (ID: {child.id})")
    
    return ChildResponse(
        id=child.id,
        parent_id=child.parent_id,
        first_name=child.first_name,
        nickname=child.nickname,
        display_name=get_display_name(child),
        age=calculate_age(child.date_of_birth.date()),
        grade_level=child.grade_level,
        avatar_url=child.avatar_url,
        is_active=child.is_active,
        requires_supervision=child.requires_supervision,
        content_filter_level=child.content_filter_level,
        learning_preferences=child.learning_preferences,
        created_at=child.created_at,
        last_active=child.last_active
    )

@router.delete("/{child_id}")
async def delete_child_profile(
    child_id: int,
    current_user: User = Depends(get_current_active_parent),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a child's profile (soft delete - deactivate)
    
    WARNING: This will also delete all associated conversations and data
    """
    
    result = await db.execute(
        select(Child).where(
            Child.id == child_id,
            Child.parent_id == current_user.id
        )
    )
    child = result.scalar_one_or_none()
    
    if not child:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child profile not found"
        )
    
    child_name = child.first_name
    
    # Log audit before deletion
    await log_audit(
        db=db,
        user_id=current_user.id,
        child_id=child.id,
        action="DELETE",
        resource="child_profile",
        details={
            "first_name": child.first_name,
            "grade_level": child.grade_level
        },
        success=True
    )
    
    # Soft delete - just deactivate
    child.is_active = False
    
    # Or hard delete (uncomment if you want permanent deletion)
    # await db.delete(child)
    
    await db.commit()
    
    logger.info(f"✅ Child profile deleted: {child_name} (ID: {child_id})")
    
    return {"message": f"Child profile '{child_name}' has been deleted"}

@router.post("/verify-pin")
async def verify_child_pin(
    pin_data: ChildPinVerify,
    current_user: User = Depends(get_current_active_parent),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify a child's PIN for authentication
    """
    
    result = await db.execute(
        select(Child).where(
            Child.id == pin_data.child_id,
            Child.parent_id == current_user.id
        )
    )
    child = result.scalar_one_or_none()
    
    if not child:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child profile not found"
        )
    
    if not child.pin_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No PIN set for this child"
        )
    
    if not child.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Child profile is inactive"
        )
    
    # Verify PIN
    if not verify_pin(pin_data.pin, child.pin_hash):
        # Log failed attempt
        await log_audit(
            db=db,
            user_id=current_user.id,
            child_id=child.id,
            action="VERIFY_PIN",
            resource="child_authentication",
            details={"result": "failed"},
            success=False
        )
        await db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect PIN"
        )
    
    # Update last active
    child.last_active = datetime.utcnow()
    
    # Log successful authentication
    await log_audit(
        db=db,
        user_id=current_user.id,
        child_id=child.id,
        action="VERIFY_PIN",
        resource="child_authentication",
        details={"result": "success"},
        success=True
    )
    
    await db.commit()
    
    logger.info(f"✅ Child PIN verified: {child.first_name} (ID: {child.id})")
    
    return {
        "verified": True,
        "child": {
            "id": child.id,
            "display_name": get_display_name(child),
            "grade_level": child.grade_level,
            "requires_supervision": child.requires_supervision
        }
    }

@router.get("/{child_id}/stats", response_model=ChildStats)
async def get_child_statistics(
    child_id: int,
    current_user: User = Depends(get_current_active_parent),
    db: AsyncSession = Depends(get_db)
):
    """
    Get learning statistics for a specific child
    """
    
    from sqlalchemy import func
    from models import Conversation, Message
    from datetime import timedelta
    
    # Verify ownership
    result = await db.execute(
        select(Child).where(
            Child.id == child_id,
            Child.parent_id == current_user.id
        )
    )
    child = result.scalar_one_or_none()
    
    if not child:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child profile not found"
        )
    
    # Get conversation count
    conv_result = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.child_id == child_id)
    )
    total_conversations = conv_result.scalar() or 0
    
    # Get message count
    msg_result = await db.execute(
        select(func.count(Message.id))
        .join(Conversation)
        .where(Conversation.child_id == child_id)
    )
    total_messages = msg_result.scalar() or 0
    
    # Get questions asked (messages with role='child')
    question_result = await db.execute(
        select(func.count(Message.id))
        .join(Conversation)
        .where(
            Conversation.child_id == child_id,
            Message.role == 'child'
        )
    )
    questions_asked = question_result.scalar() or 0
    
    # Get topics explored (unique topics from conversations)
    topics_result = await db.execute(
        select(Conversation.topics)
        .where(
            Conversation.child_id == child_id,
            Conversation.topics.isnot(None)
        )
    )
    
    all_topics = []
    for row in topics_result:
        if row[0]:
            all_topics.extend(row[0])
    
    unique_topics = list(set(all_topics))[:10]  # Top 10 topics
    
    # Get last 7 days activity
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_activity_result = await db.execute(
        select(func.count(UsageLog.id))
        .where(
            UsageLog.child_id == child_id,
            UsageLog.timestamp >= seven_days_ago
        )
    )
    last_7_days_activity = recent_activity_result.scalar() or 0
    
    # TODO: Implement favorite subjects based on usage patterns
    favorite_subjects = [
        {"subject": "Math", "count": 15},
        {"subject": "Science", "count": 12},
        {"subject": "Reading", "count": 8}
    ]
    
    return ChildStats(
        total_conversations=total_conversations,
        total_messages=total_messages,
        questions_asked=questions_asked,
        topics_explored=unique_topics,
        last_7_days_activity=last_7_days_activity,
        favorite_subjects=favorite_subjects
    )
