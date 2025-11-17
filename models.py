from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum

class UserRole(str, enum.Enum):
    PARENT = "parent"
    CHILD = "child"
    ADMIN = "admin"

class ConsentType(str, enum.Enum):
    COPPA = "coppa"
    TERMS = "terms"
    PRIVACY = "privacy"
    DATA_COLLECTION = "data_collection"

class User(Base):
    """Parent/Guardian accounts"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    role = Column(SQLEnum(UserRole), default=UserRole.PARENT, nullable=False)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    children = relationship("Child", back_populates="parent", cascade="all, delete-orphan")
    consent_records = relationship("ConsentRecord", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")

class Child(Base):
    """Child profiles (COPPA compliant - no email required)"""
    __tablename__ = "children"
    
    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Child information
    first_name = Column(String, nullable=False)
    nickname = Column(String, nullable=True)  # What they want to be called
    date_of_birth = Column(DateTime(timezone=True), nullable=False)
    grade_level = Column(String, nullable=False)  # "K", "1st", "2nd", etc.
    
    # Authentication (optional PIN for child)
    pin_hash = Column(String, nullable=True)  # Simple 4-6 digit PIN
    
    # Settings
    avatar_url = Column(String, nullable=True)
    learning_preferences = Column(JSON, nullable=True)  # subjects, pace, etc.
    
    # Safety & monitoring
    is_active = Column(Boolean, default=True, nullable=False)
    requires_supervision = Column(Boolean, default=True, nullable=False)
    content_filter_level = Column(String, default="strict", nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_active = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    parent = relationship("User", back_populates="children")
    conversations = relationship("Conversation", back_populates="child", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="child", cascade="all, delete-orphan")

class Session(Base):
    """User sessions (JWT tokens)"""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Token information
    access_token = Column(String, unique=True, index=True, nullable=False)
    refresh_token = Column(String, unique=True, index=True, nullable=False)
    
    # Session details
    device_info = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="sessions")

class ConsentRecord(Base):
    """COPPA and legal consent tracking"""
    __tablename__ = "consent_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Consent details
    consent_type = Column(SQLEnum(ConsentType), nullable=False)
    granted = Column(Boolean, nullable=False)
    consent_text = Column(Text, nullable=False)  # What they agreed to
    version = Column(String, nullable=False)  # Terms version
    
    # Verification
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Timestamps
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="consent_records")

class Conversation(Base):
    """Chat conversations between child and Nia"""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id", ondelete="CASCADE"), nullable=False)
    
    # Conversation details
    title = Column(String, nullable=True)
    folder = Column(String, default="General", nullable=False)
    topics = Column(JSON, nullable=True)  # ["math", "fractions"]
    
    # Metadata
    message_count = Column(Integer, default=0, nullable=False)
    total_depth_reached = Column(Integer, default=1, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    child = relationship("Child", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    """Individual messages in conversations"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    
    # Message details
    role = Column(String, nullable=False)  # "child" or "assistant"
    content = Column(Text, nullable=False)
    
    # AI metadata
    model_used = Column(String, nullable=True)
    source_type = Column(String, nullable=True)  # "curated_content" or "general_knowledge"
    sources = Column(JSON, nullable=True)
    depth_level = Column(Integer, default=1, nullable=False)
    
        # Feedback tracking
    feedback_rating = Column(Integer, nullable=True)  # 1 for thumbs up, -1 for thumbs down, None for no feedback
    feedback_timestamp = Column(DateTime(timezone=True), nullable=True)
    
    # Visual support
    visual_url = Column(String, nullable=True)  # URL to generated image/diagram
    visual_description = Column(String, nullable=True)  # Alt text for accessibility
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

class UsageLog(Base):
    """Detailed usage tracking for analytics and safety"""
    __tablename__ = "usage_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id", ondelete="CASCADE"), nullable=False)
    
    # Activity details
    activity_type = Column(String, nullable=False)  # "question", "follow_up", "login", etc.
    question = Column(Text, nullable=True)
    response_type = Column(String, nullable=True)  # "curated" or "general"
    
    # Session info
    session_duration = Column(Integer, nullable=True)  # seconds
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    child = relationship("Child", back_populates="usage_logs")

class AuditLog(Base):
    """Security and compliance audit trail"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Who & What
    user_id = Column(Integer, nullable=True)
    child_id = Column(Integer, nullable=True)
    action = Column(String, nullable=False)
    resource = Column(String, nullable=False)
    details = Column(JSON, nullable=True)
    
    # Context
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    success = Column(Boolean, nullable=False)
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
