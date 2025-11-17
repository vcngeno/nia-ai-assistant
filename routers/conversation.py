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
    """Send a message and get AI response with web search"""
    
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
            conversation = DBConversation(
                child_id=child_id_int,
                title=message.text[:50] + "..." if len(message.text) > 50 else message.text,
                folder="General",
                topics=[],
                message_count=0,
                total_depth_reached=message.current_depth
            )
            db.add(conversation)
            await db.flush()
        
        # Save user's question
        user_message = DBMessage(
            conversation_id=conversation.id,
            role="child",
            content=message.text,
            depth_level=message.current_depth
        )
        db.add(user_message)
        
        # Get RAG service response with Claude and web search
        rag = get_rag_service()
        
        result = rag.query(
            question=message.text,
            grade_level=message.grade_level,
            depth_level=message.current_depth,
            child_age=child_age
        )
        
        # Format sources
        source_citations = []
        for src in result.get("sources", []):
            if src.get("type") == "web_search":
                source_citations.append({
                    "title": "Web Search",
                    "type": "web_search",
                    "query": src.get("query", ""),
                    "verified": True
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
        
        # Extract topics
        topics = []
        keywords = ["math", "science", "history", "geography", "weather", "travel"]
        for keyword in keywords:
            if keyword.lower() in message.text.lower():
                topics.append(keyword)
        
        # Save AI response
        ai_message = DBMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=result["answer"],
            model_used=result["model_used"],
            source_type=source_type,
            sources=source_citations,
            depth_level=message.current_depth
        )
        db.add(ai_message)
        
        # Update conversation
        conversation.message_count += 2
        conversation.total_depth_reached = max(conversation.total_depth_reached, message.current_depth)
        if topics:
            conversation.topics = list(set((conversation.topics or []) + topics))
        
        child.last_active = user_message.created_at
        
        await db.commit()
        await db.refresh(conversation)
        
        response["message_id"] = str(uuid.uuid4())
        response["conversation_id"] = conversation.id
        response["model_used"] = result["model_used"]
        
        logger.info(f"✅ Message saved: Child {child_id_int}, Web search: {result.get('used_web_search', False)}")
        
        return response
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/conversation/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get conversation with messages"""
    
    conv_result = await db.execute(
        select(DBConversation).where(DBConversation.id == conversation_id)
    )
    conversation = conv_result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
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
