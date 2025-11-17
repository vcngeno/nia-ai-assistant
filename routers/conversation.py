from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Dict
import uuid
import logging

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

@router.post("/message", response_model=MessageResponse)
async def send_message(
    message: MessageCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Send a message and get AI response
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
            depth_level=message.current_depth
        )
        db.add(user_message)
        
        # Get RAG service response
        rag = get_rag_service()
        
        result = rag.query(
            question=message.text,
            grade_level=message.grade_level,
            depth_level=message.current_depth,
            num_sources=3
        )
        
        # Format sources
        source_citations = [
            {
                "title": "Educational Content",
                "type": "verified_source",
                "snippet": src["content"][:200] + "...",
                "grade_level": src["grade_level"],
                "verified": src.get("verified", True)
            }
            for src in result["sources"]
        ]
        
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
        source_type = response.get("source_type", "general_knowledge")
        
        # Extract topics from the question (simple keyword extraction)
        topics = []
        keywords = ["math", "science", "history", "geography", "reading", "writing", "multiplication", "addition"]
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
        
        logger.info(f"✅ Message saved: Child {child_id_int}, Conversation {conversation.id}")
        
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
