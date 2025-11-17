from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Dict
import uuid
import logging
from datetime import datetime

from database import get_db
from models import Conversation as DBConversation, Message as DBMessage, Child
from services.conversation_service import ConversationService
from services.rag_service import get_rag_service
from services.visual_service import get_visual_service
from sqlalchemy import select

router = APIRouter()
logger = logging.getLogger(__name__)

class MessageCreate(BaseModel):
    conversation_id: Optional[str] = None
    child_id: str
    text: str
    grade_level: str = "2nd grade"
    current_depth: int = 1

class FollowUpOption(BaseModel):
    id: str
    text: str

class FollowUpPrompt(BaseModel):
    text: str
    options: List[FollowUpOption]

class MessageResponse(BaseModel):
    message_id: str
    conversation_id: int
    text: str
    tutoring_depth_level: int
    follow_up_offered: bool
    source_citations: List[Dict]
    source_type: str
    source_label: str
    generated_visuals: List[Dict]
    related_topics: List[str]
    follow_up_prompt: Optional[FollowUpPrompt]
    model_used: str

def calculate_age(date_of_birth: datetime) -> int:
    """Calculate age from date of birth"""
    today = datetime.now()
    age = today.year - date_of_birth.year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1
    return age

@router.post("/message", response_model=MessageResponse)
async def send_message(
    message: MessageCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Send a message and get AI response with web search capability
    Saves conversation to database for parent dashboard
    """
    
    try:
        # Verify child exists
        child_id_int = int(message.child_id)
        child_result = await db.execute(
            select(Child).where(Child.id == child_id_int)
        )
        child = child_result.scalar_one_or_none()
        
        if not child:
            raise HTTPException(status_code=404, detail="Child not found")
        
        # Calculate child's age
        child_age = calculate_age(child.date_of_birth) if child.date_of_birth else None
        
        # Get or create conversation
        conversation = None
        if message.conversation_id:
            conv_result = await db.execute(
                select(DBConversation).where(DBConversation.id == int(message.conversation_id))
            )
            conversation = conv_result.scalar_one_or_none()
        
        if not conversation:
            # Create new conversation
            conversation = DBConversation(
                child_id=child_id_int,
                title=message.text[:50] + "..." if len(message.text) > 50 else message.text,
                folder="General",
                topics=[],
                message_count=0,
                total_depth_reached=message.current_depth
            )
            db.add(conversation)
            await db.flush()  # Get conversation ID
        
        # Save user's question
        user_message = DBMessage(
            conversation_id=conversation.id,
            role="child",
            content=message.text,
            depth_level=message.current_depth,
            visual_content=visual_data.get("visual_content") if visual_data else None,
            visual_description=visual_data.get("visual_description") if visual_data else None
        )
        db.add(user_message)
        
        # Get RAG service response (now with Claude and web search)
        rag = get_rag_service()
        
        result = rag.query(
            question=message.text,
            grade_level=message.grade_level,
            depth_level=message.current_depth,
            child_age=child_age  # Pass calculated age
        )
        
        # Format sources for web search results
        source_citations = []
        for src in result.get("sources", []):
            if src.get("type") == "web_search":
                source_citations.append({
                    "title": "Web Search Result",
                    "type": "web_search",
                    "query": src.get("query", ""),
                    "verified": True
                })
            else:
                source_citations.append({
                    "title": "Educational Content",
                    "type": "verified_source",
                    "snippet": src.get("content", "")[:200],
                    "verified": src.get("verified", True)
                })
        
        # Build response
        conv_service = ConversationService()
        response = conv_service.format_response_with_sources(
            answer=result["answer"],
            sources=source_citations,
            depth_level=message.current_depth,
            visuals=[],
            related_topics=[]
        )
        
        # Determine source type
        if result.get("used_web_search"):
            source_type = "web_search"
            source_label = "🌐 From the web"
        else:
            source_type = "general_knowledge"
            source_label = "ℹ️ From what I know"
        
        response["source_type"] = source_type
        response["source_label"] = source_label
        
        # Extract topics from the question (simple keyword extraction)
        topics = []
        keywords = ["math", "science", "history", "geography", "reading", "writing", "weather", "travel"]
        for keyword in keywords:
            if keyword.lower() in message.text.lower():
                topics.append(keyword)
        
        # Generate emoji visual
        visual_service = get_visual_service()
        visual_data = visual_service.generate_visual(
            text=result["answer"],
            question=message.text,
            grade_level=message.grade_level
        )
        
        
            conversation_id=conversation.id,
            role="assistant",
            content=result["answer"],
            model_used=result["model_used"],
            source_type=source_type,
            sources=source_citations,
            depth_level=message.current_depth,
            visual_content=visual_data.get("visual_content") if visual_data else None,
            visual_description=visual_data.get("visual_description") if visual_data else None
        )
        db.add(ai_message)
        
        # Update conversation
        conversation.message_count += 2  # User message + AI response
        conversation.total_depth_reached = max(conversation.total_depth_reached, message.current_depth)
        if topics:
            conversation.topics = list(set((conversation.topics or []) + topics))
        
        # Update child's last active
        child.last_active = user_message.created_at
        
        await db.commit()
        await db.refresh(conversation)
        
        response["message_id"] = str(uuid.uuid4())
        response["conversation_id"] = conversation.id
        response["model_used"] = result["model_used"]
        
        logger.info(f"✅ Message saved: Child {child_id_int} (age {child_age}), Conversation {conversation.id}, Web search: {result.get('used_web_search', False)}")
        
        return response
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error processing message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@router.get("/conversation/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get full conversation with all messages"""
    
    conv_result = await db.execute(
        select(DBConversation).where(DBConversation.id == conversation_id)
    )
    conversation = conv_result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get all messages
    messages_result = await db.execute(
        select(DBMessage)
        .where(DBMessage.conversation_id == conversation_id)
        .order_by(DBMessage.created_at)
    )
    
    messages = []
    for msg in messages_result.scalars():
        messages.append({
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "source_type": msg.source_type,
            "created_at": msg.created_at.isoformat()
        })
    
    return {
        "conversation_id": conversation.id,
        "child_id": conversation.child_id,
        "title": conversation.title,
        "topics": conversation.topics,
        "message_count": conversation.message_count,
        "messages": messages
    }

class FeedbackCreate(BaseModel):
    message_id: int
    rating: int  # 1 for thumbs up, -1 for thumbs down

@router.post("/feedback")
async def submit_feedback(
    feedback: FeedbackCreate,
    db: AsyncSession = Depends(get_db)
):
    """Submit thumbs up/down feedback for a message"""
    
    try:
        # Get the message
        result = await db.execute(
            select(DBMessage).where(DBMessage.id == feedback.message_id)
        )
        message = result.scalar_one_or_none()
        
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Update feedback
        message.feedback_rating = feedback.rating
        message.feedback_timestamp = func.now()
        
        await db.commit()
        
        logger.info(f"✅ Feedback received: Message {feedback.message_id}, Rating: {'👍' if feedback.rating == 1 else '👎'}")
        
        return {
            "success": True,
            "message": "Feedback recorded",
            "rating": feedback.rating
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error submitting feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/feedback")
async def get_feedback_analytics(
    db: AsyncSession = Depends(get_db)
):
    """Get feedback analytics for improvement"""
    
    try:
        # Get feedback stats
        result = await db.execute(
            select(
                func.count(DBMessage.id).label('total_responses'),
                func.sum(case((DBMessage.feedback_rating == 1, 1), else_=0)).label('thumbs_up'),
                func.sum(case((DBMessage.feedback_rating == -1, 1), else_=0)).label('thumbs_down'),
                func.count(DBMessage.feedback_rating).label('total_feedback')
            )
        )
        
        stats = result.first()
        
        return {
            "total_responses": stats.total_responses or 0,
            "thumbs_up": stats.thumbs_up or 0,
            "thumbs_down": stats.thumbs_down or 0,
            "total_feedback": stats.total_feedback or 0,
            "feedback_rate": round((stats.total_feedback / stats.total_responses * 100), 2) if stats.total_responses > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Error getting feedback analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class FeedbackCreate(BaseModel):
    message_id: int
    rating: int  # 1 for thumbs up, -1 for thumbs down

@router.post("/feedback")
async def submit_feedback(
    feedback: FeedbackCreate,
    db: AsyncSession = Depends(get_db)
):
    """Submit thumbs up/down feedback for a message"""
    
    try:
        result = await db.execute(
            select(DBMessage).where(DBMessage.id == feedback.message_id)
        )
        message = result.scalar_one_or_none()
        
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        from datetime import datetime
        message.feedback_rating = feedback.rating
        message.feedback_timestamp = datetime.now()
        
        await db.commit()
        
        logger.info(f"✅ Feedback: Message {feedback.message_id} = {'👍' if feedback.rating == 1 else '👎'}")
        
        return {"success": True, "rating": feedback.rating}
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))
