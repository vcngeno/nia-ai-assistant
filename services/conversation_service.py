from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

class ConversationService:
    
    @staticmethod
    def format_response_with_sources(
        answer: str,
        sources: List[Dict],
        depth_level: int = 1,
        visuals: Optional[List[Dict]] = None,
        related_topics: Optional[List[str]] = None
    ) -> Dict:
        """Format AI response with clear source attribution and follow-up prompt"""
        
        # Determine if answer used curated content or general knowledge
        has_sources = len(sources) > 0
        
        # Check if answer explicitly marked its source
        is_from_materials = "📚" in answer or "From my learning materials" in answer
        is_general_knowledge = "ℹ️" in answer or "From general knowledge" in answer
        
        # Build source attribution
        if has_sources and is_from_materials:
            source_type = "curated_content"
            source_label = "📚 From Nia's Learning Materials"
        elif is_general_knowledge or not has_sources:
            source_type = "general_knowledge"
            source_label = "ℹ️ General Educational Knowledge"
        else:
            source_type = "hybrid"
            source_label = "📚 From Nia's Materials"
        
        # Follow-up prompts based on depth
        follow_up_prompts = {
            1: {
                "text": "Would you like to learn more about this? 🤔",
                "options": [
                    {"id": "yes", "text": "Yes, tell me more! 🐠"},
                    {"id": "done", "text": "I'm all done for now ✅"}
                ]
            },
            2: {
                "text": "Want to dive even deeper into this topic? 🌊",
                "options": [
                    {"id": "yes", "text": "Yes, go deeper! 🔍"},
                    {"id": "done", "text": "That's enough for now ✅"}
                ]
            },
            3: {
                "text": "Would you like to explore related topics? 🗺️",
                "options": [
                    {"id": "yes", "text": "Yes, show me more! 🌟"},
                    {"id": "done", "text": "I'm done learning for now ✅"}
                ]
            }
        }
        
        return {
            "text": answer,
            "tutoring_depth_level": depth_level,
            "follow_up_offered": True,
            "source_citations": sources,
            "source_type": source_type,
            "source_label": source_label,
            "generated_visuals": visuals or [],
            "related_topics": related_topics or [],
            "follow_up_prompt": follow_up_prompts.get(depth_level, follow_up_prompts[1])
        }
    
    @staticmethod
    def get_deeper_content_prompt(
        original_query: str,
        depth_level: int,
        grade_level: str
    ) -> Dict:
        """Generate prompts for deeper content based on depth level"""
        
        prompts = {
            1: f"Explain '{original_query}' in 2-3 simple sentences for {grade_level}. Be encouraging and friendly.",
            2: f"Provide 4-5 interesting facts about '{original_query}' suitable for {grade_level}. Include examples and make it engaging with emojis.",
            3: f"Explain '{original_query}' in depth for {grade_level}, connecting it to related topics and everyday life. Be comprehensive but age-appropriate."
        }
        
        return {
            "prompt": prompts.get(depth_level, prompts[1]),
            "requires_images": depth_level >= 2,
            "max_related_topics": 3 if depth_level == 3 else 0
        }
