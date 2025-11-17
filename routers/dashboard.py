from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timedelta, date
import logging
from collections import defaultdict

from database import get_db
from models import User, Child, Conversation, Message, UsageLog, AuditLog
from auth import get_current_active_parent

router = APIRouter()
logger = logging.getLogger(__name__)

# ==================== RESPONSE MODELS ====================

class DashboardOverview(BaseModel):
    total_children: int
    active_children: int
    total_conversations: int
    total_questions: int
    hours_learning: float
    most_active_child: Optional[Dict]
    recent_activity: List[Dict]
    
class ChildProgress(BaseModel):
    child_id: int
    child_name: str
    age: int
    grade_level: str
    total_questions: int
    conversations_count: int
    favorite_subjects: List[Dict]
    learning_streak_days: int
    last_active: Optional[datetime]
    progress_summary: Dict
    
class ConversationDetail(BaseModel):
    id: int
    child_id: int
    child_name: str
    title: Optional[str]
    message_count: int
    topics: Optional[List[str]]
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[Dict]] = None
    
class LearningAnalytics(BaseModel):
    date_range: Dict
    questions_by_subject: Dict
    questions_by_day: List[Dict]
    source_breakdown: Dict  # curated vs general knowledge
    average_depth: float
    popular_topics: List[Dict]
    
class SafetyReport(BaseModel):
    child_id: int
    child_name: str
    content_filter_level: str
    requires_supervision: bool
    flagged_conversations: int
    recent_concerns: List[Dict]
    recommendations: List[str]

# ==================== DASHBOARD OVERVIEW ====================

@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(
    current_user: User = Depends(get_current_active_parent),
    db: AsyncSession = Depends(get_db)
):
    """
    Get overall dashboard overview for parent
    
    Shows:
    - Total and active children
    - Total conversations and questions
    - Learning time
    - Most active child
    - Recent activity
    """
    
    # Get all children
    children_result = await db.execute(
        select(Child).where(Child.parent_id == current_user.id)
    )
    children = children_result.scalars().all()
    
    total_children = len(children)
    active_children = len([c for c in children if c.is_active])
    
    if not children:
        return DashboardOverview(
            total_children=0,
            active_children=0,
            total_conversations=0,
            total_questions=0,
            hours_learning=0.0,
            most_active_child=None,
            recent_activity=[]
        )
    
    child_ids = [c.id for c in children]
    
    # Get total conversations
    conv_result = await db.execute(
        select(func.count(Conversation.id))
        .where(Conversation.child_id.in_(child_ids))
    )
    total_conversations = conv_result.scalar() or 0
    
    # Get total questions (messages with role='child')
    msg_result = await db.execute(
        select(func.count(Message.id))
        .join(Conversation)
        .where(
            Conversation.child_id.in_(child_ids),
            Message.role == 'child'
        )
    )
    total_questions = msg_result.scalar() or 0
    
    # Calculate learning hours (estimate: 2 min per question)
    hours_learning = round((total_questions * 2) / 60, 1)
    
    # Find most active child
    most_active = None
    max_questions = 0
    
    for child in children:
        child_questions = await db.execute(
            select(func.count(Message.id))
            .join(Conversation)
            .where(
                Conversation.child_id == child.id,
                Message.role == 'child'
            )
        )
        count = child_questions.scalar() or 0
        
        if count > max_questions:
            max_questions = count
            most_active = {
                "id": child.id,
                "name": child.nickname or child.first_name,
                "questions": count
            }
    
    # Get recent activity (last 5 questions)
    recent_result = await db.execute(
        select(Message, Conversation, Child)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .join(Child, Conversation.child_id == Child.id)
        .where(
            Conversation.child_id.in_(child_ids),
            Message.role == 'child'
        )
        .order_by(Message.created_at.desc())
        .limit(5)
    )
    
    recent_activity = []
    for msg, conv, child in recent_result:
        recent_activity.append({
            "child_name": child.nickname or child.first_name,
            "question": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
            "timestamp": msg.created_at.isoformat(),
            "conversation_id": conv.id
        })
    
    logger.info(f"📊 Dashboard overview accessed by {current_user.email}")
    
    return DashboardOverview(
        total_children=total_children,
        active_children=active_children,
        total_conversations=total_conversations,
        total_questions=total_questions,
        hours_learning=hours_learning,
        most_active_child=most_active,
        recent_activity=recent_activity
    )

# ==================== CHILD PROGRESS ====================

@router.get("/children/{child_id}/progress", response_model=ChildProgress)
async def get_child_progress(
    child_id: int,
    days: int = Query(30, description="Number of days to analyze"),
    current_user: User = Depends(get_current_active_parent),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed learning progress for a specific child
    
    Includes:
    - Question count and conversation count
    - Favorite subjects
    - Learning streak
    - Progress summary
    """
    
    # Verify child belongs to parent
    child_result = await db.execute(
        select(Child).where(
            Child.id == child_id,
            Child.parent_id == current_user.id
        )
    )
    child = child_result.scalar_one_or_none()
    
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    
    # Calculate age
    today = date.today()
    age = today.year - child.date_of_birth.year - (
        (today.month, today.day) < (child.date_of_birth.month, child.date_of_birth.day)
    )
    
    # Get total questions
    questions_result = await db.execute(
        select(func.count(Message.id))
        .join(Conversation)
        .where(
            Conversation.child_id == child_id,
            Message.role == 'child'
        )
    )
    total_questions = questions_result.scalar() or 0
    
    # Get conversation count
    conv_result = await db.execute(
        select(func.count(Conversation.id))
        .where(Conversation.child_id == child_id)
    )
    conversations_count = conv_result.scalar() or 0
    
    # Get favorite subjects from topics
    topics_result = await db.execute(
        select(Conversation.topics)
        .where(
            Conversation.child_id == child_id,
            Conversation.topics.isnot(None)
        )
    )
    
    topic_counts = defaultdict(int)
    for row in topics_result:
        if row[0]:
            for topic in row[0]:
                topic_counts[topic] += 1
    
    favorite_subjects = [
        {"subject": topic, "count": count}
        for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    ]
    
    # Calculate learning streak (days with activity)
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    streak_result = await db.execute(
        select(func.date(Message.created_at))
        .join(Conversation)
        .where(
            Conversation.child_id == child_id,
            Message.created_at >= cutoff_date
        )
        .distinct()
    )
    
    active_dates = [row[0] for row in streak_result]
    learning_streak_days = len(active_dates)
    
    # Progress summary
    progress_summary = {
        "total_time_minutes": total_questions * 2,  # Estimate
        "questions_this_week": 0,  # TODO: Calculate
        "improvement_trend": "steady",  # TODO: Calculate
        "engagement_level": "high" if total_questions > 50 else "moderate" if total_questions > 10 else "low"
    }
    
    logger.info(f"📈 Progress report generated for child {child_id}")
    
    return ChildProgress(
        child_id=child.id,
        child_name=child.nickname or child.first_name,
        age=age,
        grade_level=child.grade_level,
        total_questions=total_questions,
        conversations_count=conversations_count,
        favorite_subjects=favorite_subjects,
        learning_streak_days=learning_streak_days,
        last_active=child.last_active,
        progress_summary=progress_summary
    )

# ==================== CONVERSATION MANAGEMENT ====================

@router.get("/conversations", response_model=List[ConversationDetail])
async def get_all_conversations(
    child_id: Optional[int] = Query(None, description="Filter by child"),
    start_date: Optional[date] = Query(None, description="Filter from date"),
    end_date: Optional[date] = Query(None, description="Filter to date"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    limit: int = Query(50, le=100, description="Maximum number of results"),
    current_user: User = Depends(get_current_active_parent),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all conversations with optional filters
    
    Parents can view all their children's conversations
    """
    
    # Get all child IDs for this parent
    children_result = await db.execute(
        select(Child.id).where(Child.parent_id == current_user.id)
    )
    child_ids = [row[0] for row in children_result]
    
    if not child_ids:
        return []
    
    # Build query
    query = select(Conversation, Child).join(Child).where(
        Conversation.child_id.in_(child_ids)
    )
    
    # Apply filters
    if child_id:
        if child_id not in child_ids:
            raise HTTPException(status_code=403, detail="Access denied")
        query = query.where(Conversation.child_id == child_id)
    
    if start_date:
        query = query.where(Conversation.created_at >= datetime.combine(start_date, datetime.min.time()))
    
    if end_date:
        query = query.where(Conversation.created_at <= datetime.combine(end_date, datetime.max.time()))
    
    if topic:
        # PostgreSQL JSON contains operation
        query = query.where(Conversation.topics.contains([topic]))
    
    query = query.order_by(Conversation.updated_at.desc()).limit(limit)
    
    result = await db.execute(query)
    
    conversations = []
    for conv, child in result:
        conversations.append(ConversationDetail(
            id=conv.id,
            child_id=conv.child_id,
            child_name=child.nickname or child.first_name,
            title=conv.title,
            message_count=conv.message_count,
            topics=conv.topics,
            created_at=conv.created_at,
            updated_at=conv.updated_at
        ))
    
    logger.info(f"📋 Retrieved {len(conversations)} conversations for {current_user.email}")
    
    return conversations

@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation_detail(
    conversation_id: int,
    current_user: User = Depends(get_current_active_parent),
    db: AsyncSession = Depends(get_db)
):
    """
    Get full conversation with all messages
    """
    
    # Verify access
    conv_result = await db.execute(
        select(Conversation, Child)
        .join(Child)
        .where(
            Conversation.id == conversation_id,
            Child.parent_id == current_user.id
        )
    )
    
    conv_data = conv_result.first()
    if not conv_data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conv, child = conv_data
    
    # Get all messages
    messages_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    
    messages = []
    for msg in messages_result.scalars():
        messages.append({
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "source_type": msg.source_type,
            "model_used": msg.model_used,
            "created_at": msg.created_at.isoformat()
        })
    
    return ConversationDetail(
        id=conv.id,
        child_id=conv.child_id,
        child_name=child.nickname or child.first_name,
        title=conv.title,
        message_count=conv.message_count,
        topics=conv.topics,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=messages
    )

# ==================== ANALYTICS ====================

@router.get("/analytics", response_model=LearningAnalytics)
async def get_learning_analytics(
    child_id: Optional[int] = Query(None, description="Specific child or all"),
    days: int = Query(30, description="Number of days to analyze"),
    current_user: User = Depends(get_current_active_parent),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed learning analytics
    
    Shows trends, subject breakdown, and insights
    """
    
    # Get child IDs
    if child_id:
        # Verify ownership
        child_result = await db.execute(
            select(Child).where(
                Child.id == child_id,
                Child.parent_id == current_user.id
            )
        )
        if not child_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Access denied")
        child_ids = [child_id]
    else:
        children_result = await db.execute(
            select(Child.id).where(Child.parent_id == current_user.id)
        )
        child_ids = [row[0] for row in children_result]
    
    if not child_ids:
        return LearningAnalytics(
            date_range={"start": datetime.utcnow(), "end": datetime.utcnow(), "days": days},
            questions_by_subject={},
            questions_by_day=[],
            source_breakdown={},
            average_depth=0.0,
            popular_topics=[]
        )
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Questions by subject (from topics)
    topics_result = await db.execute(
        select(Conversation.topics)
        .where(
            Conversation.child_id.in_(child_ids),
            Conversation.created_at >= start_date
        )
    )
    
    subject_counts = defaultdict(int)
    for row in topics_result:
        if row[0]:
            for topic in row[0]:
                subject_counts[topic] += 1
    
    # Questions by day
    daily_result = await db.execute(
        select(
            func.date(Message.created_at).label('date'),
            func.count(Message.id).label('count')
        )
        .join(Conversation)
        .where(
            Conversation.child_id.in_(child_ids),
            Message.role == 'child',
            Message.created_at >= start_date
        )
        .group_by(func.date(Message.created_at))
        .order_by('date')
    )
    
    questions_by_day = [
        {"date": str(row[0]), "count": row[1]}
        for row in daily_result
    ]
    
    # Source breakdown
    source_result = await db.execute(
        select(
            Message.source_type,
            func.count(Message.id)
        )
        .join(Conversation)
        .where(
            Conversation.child_id.in_(child_ids),
            Message.role == 'assistant',
            Message.created_at >= start_date
        )
        .group_by(Message.source_type)
    )
    
    source_breakdown = {row[0]: row[1] for row in source_result if row[0]}
    
    # Average depth
    depth_result = await db.execute(
        select(func.avg(Message.depth_level))
        .join(Conversation)
        .where(
            Conversation.child_id.in_(child_ids),
            Message.created_at >= start_date
        )
    )
    average_depth = float(depth_result.scalar() or 0.0)
    
    # Popular topics
    popular_topics = [
        {"topic": topic, "count": count}
        for topic, count in sorted(subject_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ]
    
    logger.info(f"📊 Analytics generated for {days} days")
    
    return LearningAnalytics(
        date_range={
            "start": start_date.isoformat(),
            "end": datetime.utcnow().isoformat(),
            "days": days
        },
        questions_by_subject=dict(subject_counts),
        questions_by_day=questions_by_day,
        source_breakdown=source_breakdown,
        average_depth=round(average_depth, 2),
        popular_topics=popular_topics
    )

# ==================== EXPORT ====================

@router.get("/export/conversations")
async def export_conversations(
    child_id: Optional[int] = Query(None),
    format: str = Query("json", regex="^(json|csv)$"),
    current_user: User = Depends(get_current_active_parent),
    db: AsyncSession = Depends(get_db)
):
    """
    Export conversation history
    
    Formats: JSON or CSV
    """
    
    # Get child IDs
    if child_id:
        child_result = await db.execute(
            select(Child).where(
                Child.id == child_id,
                Child.parent_id == current_user.id
            )
        )
        if not child_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Access denied")
        child_ids = [child_id]
    else:
        children_result = await db.execute(
            select(Child.id).where(Child.parent_id == current_user.id)
        )
        child_ids = [row[0] for row in children_result]
    
    # Get all conversations and messages
    result = await db.execute(
        select(Conversation, Child, Message)
        .join(Child, Conversation.child_id == Child.id)
        .join(Message, Message.conversation_id == Conversation.id)
        .where(Conversation.child_id.in_(child_ids))
        .order_by(Conversation.created_at, Message.created_at)
    )
    
    data = []
    for conv, child, msg in result:
        data.append({
            "conversation_id": conv.id,
            "child_name": child.nickname or child.first_name,
            "child_grade": child.grade_level,
            "message_role": msg.role,
            "message_content": msg.content,
            "source_type": msg.source_type,
            "timestamp": msg.created_at.isoformat(),
            "topics": conv.topics
        })
    
    if format == "json":
        from fastapi.responses import JSONResponse
        return JSONResponse(content={
            "export_date": datetime.utcnow().isoformat(),
            "total_messages": len(data),
            "data": data
        })
    
    elif format == "csv":
        import csv
        import io
        from fastapi.responses import StreamingResponse
        
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=conversations.csv"}
        )

# ==================== SAFETY CONTROLS ====================

@router.get("/safety/{child_id}", response_model=SafetyReport)
async def get_safety_report(
    child_id: int,
    current_user: User = Depends(get_current_active_parent),
    db: AsyncSession = Depends(get_db)
):
    """
    Get safety and supervision report for a child
    """
    
    # Verify ownership
    child_result = await db.execute(
        select(Child).where(
            Child.id == child_id,
            Child.parent_id == current_user.id
        )
    )
    child = child_result.scalar_one_or_none()
    
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    
    # TODO: Implement flagging system
    flagged_conversations = 0
    recent_concerns = []
    
    recommendations = []
    if child.content_filter_level == "relaxed":
        recommendations.append("Consider using 'moderate' or 'strict' filtering for better safety")
    
    if not child.requires_supervision:
        recommendations.append("Enabling supervision mode allows you to review conversations")
    
    return SafetyReport(
        child_id=child.id,
        child_name=child.nickname or child.first_name,
        content_filter_level=child.content_filter_level,
        requires_supervision=child.requires_supervision,
        flagged_conversations=flagged_conversations,
        recent_concerns=recent_concerns,
        recommendations=recommendations
    )

@router.put("/safety/{child_id}/settings")
async def update_safety_settings(
    child_id: int,
    content_filter_level: Optional[str] = Query(None, regex="^(strict|moderate|relaxed)$"),
    requires_supervision: Optional[bool] = None,
    current_user: User = Depends(get_current_active_parent),
    db: AsyncSession = Depends(get_db)
):
    """
    Update safety settings for a child
    """
    
    # Verify ownership
    child_result = await db.execute(
        select(Child).where(
            Child.id == child_id,
            Child.parent_id == current_user.id
        )
    )
    child = child_result.scalar_one_or_none()
    
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    
    # Update settings
    if content_filter_level:
        child.content_filter_level = content_filter_level
    
    if requires_supervision is not None:
        child.requires_supervision = requires_supervision
    
    # Log audit
    from routers.children import log_audit
    await log_audit(
        db=db,
        user_id=current_user.id,
        child_id=child.id,
        action="UPDATE_SAFETY_SETTINGS",
        resource="child_safety",
        details={
            "content_filter_level": child.content_filter_level,
            "requires_supervision": child.requires_supervision
        },
        success=True
    )
    
    await db.commit()
    
    logger.info(f"🔒 Safety settings updated for child {child_id}")
    
    return {
        "message": "Safety settings updated",
        "content_filter_level": child.content_filter_level,
        "requires_supervision": child.requires_supervision
    }
