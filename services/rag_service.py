import anthropic
import os
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        """Initialize RAG service with Anthropic Claude"""
        
        # Get API key
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        
        # Initialize Anthropic client
        self.client = anthropic.Anthropic(api_key=self.api_key)
        
        logger.info(f"✅ RAG Service initialized with Anthropic Claude (with web search)")
    
    def query(
        self,
        question: str,
        grade_level: str = "5th grade",
        depth_level: int = 1,
        child_age: Optional[int] = None
    ) -> Dict:
        """Query Claude with web search for age-appropriate answers"""
        
        try:
            # Get grade-appropriate system prompt
            system_prompt = self._get_grade_appropriate_prompt(grade_level, depth_level, child_age)
            
            # Call Claude with web search enabled
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": question}
                ],
                tools=[
                    {
                        "type": "web_search_20250305",
                        "name": "web_search"
                    }
                ]
            )
            
            # Extract answer and sources
            answer_text = ""
            sources = []
            
            for block in response.content:
                if block.type == "text":
                    answer_text += block.text
                elif block.type == "tool_use" and block.name == "web_search":
                    # Web search was used - mark it
                    sources.append({
                        "type": "web_search",
                        "query": block.input.get("query", ""),
                        "verified": True
                    })
            
            # Determine if web search was used
            used_web_search = any(s["type"] == "web_search" for s in sources)
            
            # Add source indicator if not already in answer
            if used_web_search and "🌐" not in answer_text and "From the web" not in answer_text:
                answer_text = "🌐 From the web:\n\n" + answer_text
            elif not used_web_search and "ℹ️" not in answer_text and "From general knowledge" not in answer_text:
                answer_text = "ℹ️ From general knowledge:\n\n" + answer_text
            
            return {
                "answer": answer_text,
                "sources": sources,
                "model_used": "claude-sonnet-4",
                "used_web_search": used_web_search
            }
            
        except Exception as e:
            logger.error(f"Error in Claude query: {e}", exc_info=True)
            raise
    
    def _get_grade_appropriate_prompt(
        self, 
        grade_level: str, 
        depth_level: int,
        child_age: Optional[int] = None
    ) -> str:
        """Generate grade and depth appropriate system prompt"""
        
        # Base guidelines by grade level
        grade_guides = {
            "K-1st": "Use very simple words (1-2 syllables). Short sentences (5-7 words). Lots of examples from daily life. Use emojis to make it fun! 🌟",
            "2nd-3rd": "Use simple, clear language. Short paragraphs. Relate to things kids know (playground, pets, family). Be friendly and encouraging! 🎈",
            "4th-5th": "Use clear explanations. Can include some bigger words but explain them. Give interesting examples. Make learning exciting! 🚀",
            "6th-8th": "Use more advanced vocabulary. Include deeper concepts. Make connections between ideas. Encourage curiosity! 🔬",
            "9th-12th": "Use sophisticated vocabulary. Explore complex ideas. Encourage critical thinking and analysis. 📚"
        }
        
        # Determine appropriate guide
        base_guide = grade_guides.get(grade_level, grade_guides["4th-5th"])
        
        # Depth-based adjustments
        depth_guides = {
            1: "Give a brief, clear answer (2-3 sentences). Be friendly and encouraging.",
            2: "Provide more detail (4-6 sentences). Include examples and interesting facts. Use emojis to keep it fun!",
            3: "Give comprehensive explanation (6-8 sentences). Connect concepts. Include real-world applications. Be thorough but engaging!"
        }
        
        depth_guide = depth_guides.get(depth_level, depth_guides[1])
        
        age_guidance = ""
        if child_age:
            age_guidance = f"\nCHILD'S AGE: {child_age} years old - Keep this in mind for vocabulary and examples."
        
        return f"""You are Nia, a warm, intelligent, and friendly AI learning assistant for children. You help kids learn about anything they're curious about!

GRADE LEVEL: {grade_level}
RESPONSE DEPTH: Level {depth_level}{age_guidance}

COMMUNICATION GUIDELINES:
- {base_guide}
- {depth_guide}
- Always be encouraging and build confidence
- Use "you" and "your" to make it personal
- Celebrate their curiosity!

🔍 WEB SEARCH USAGE:
- For current events, weather, travel info, recent facts: USE WEB SEARCH
- For timeless educational topics (math, science concepts, history): USE YOUR KNOWLEDGE
- For homework help with current information: USE WEB SEARCH
- Always verify information is age-appropriate before sharing

⚠️ CHILD SAFETY (CRITICAL):
- NEVER share personal contact information
- NEVER suggest meeting people in person
- Keep all content educational and appropriate
- If a question seems inappropriate, gently redirect to learning
- Focus on educational value

📝 SOURCE TRANSPARENCY:
- If using web search, start with: "🌐 From the web:"
- If using your knowledge, start with: "ℹ️ From what I know:"
- Be clear about where information comes from

ANSWER QUALITY:
- Be factually accurate
- Use age-appropriate vocabulary
- Include examples kids can relate to
- Make learning FUN and engaging!
- End with an encouraging note or curiosity question when appropriate

Remember: You're here to make learning exciting and accessible for every child! 🌟"""


# Global RAG service instance
_rag_service = None

def get_rag_service() -> RAGService:
    """Get or create the global RAG service instance"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
