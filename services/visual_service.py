import logging
from typing import Dict, List, Optional
import os
from openai import OpenAI
import httpx

logger = logging.getLogger(__name__)

class VisualService:
    """Generate images using DALL-E 3 and emoji fallbacks"""
    
    def __init__(self):
        """Initialize with OpenAI client"""
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if self.openai_api_key:
            # Create explicit httpx client without proxies
            http_client = httpx.Client(
                timeout=60.0,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
            )
            self.client = OpenAI(
                api_key=self.openai_api_key,
                http_client=http_client
            )
            logger.info("✅ Visual Service initialized with DALL-E 3")
        else:
            self.client = None
            logger.warning("⚠️ OPENAI_API_KEY not found - using emoji fallback only")
    
    # Topic-based emoji mappings for fallback
    TOPIC_EMOJIS = {
        "weather": ["🌤️", "☀️", "🌧️", "⛈️", "🌈", "❄️"],
        "rain": ["🌧️", "☔", "💧"],
        "sun": ["☀️", "🌞", "🌅"],
        "snow": ["❄️", "⛄", "🌨️"],
        "space": ["🌍", "🌙", "⭐", "🚀", "🪐"],
        "dinosaur": ["🦕", "🦖", "🦴"],
        "animal": ["🐶", "🐱", "🐘", "🦁", "🐼"],
        "ocean": ["🌊", "🐠", "🐋", "🦈"],
        "seahorse": ["🐴", "🌊", "🐠"],
        "math": ["➕", "➖", "✖️", "➗", "🔢"],
        "science": ["🔬", "🧪", "⚗️", "🧬"],
        "travel": ["✈️", "🚗", "🗺️", "🧳"],
        "food": ["🍎", "🍕", "🍔", "🥗"],
        "school": ["📚", "✏️", "📝", "🎒"],
    }
    
    def should_generate_image(self, question: str, answer: str) -> bool:
        """Decide if concept would benefit from DALL-E image"""
        
        # Topics that benefit from visual representation
        visual_topics = [
            "what does", "show me", "how does", "what is",
            "dinosaur", "animal", "space", "ocean", "plant",
            "weather", "geography", "science experiment",
            "solar system", "body", "anatomy", "seahorse"
        ]
        
        question_lower = question.lower()
        answer_lower = answer.lower()
        
        # Check if question asks for visual explanation
        for topic in visual_topics:
            if topic in question_lower or topic in answer_lower:
                return True
        
        # Don't generate for simple math or text-heavy topics
        if any(word in question_lower for word in ["calculate", "spell", "write", "read"]):
            return False
        
        return False
    
    def generate_visual(
        self,
        text: str,
        question: str,
        grade_level: str
    ) -> Optional[Dict]:
        """Generate visual using DALL-E 3 or emoji fallback"""
        
        try:
            # Check if we should generate an image
            if self.client and self.should_generate_image(question, text):
                return self._generate_dalle_image(question, text, grade_level)
            else:
                # Fallback to emoji visual
                return self._generate_emoji_visual(text, question, grade_level)
                
        except Exception as e:
            logger.error(f"Error generating visual: {e}")
            # Always fallback to emoji on error
            return self._generate_emoji_visual(text, question, grade_level)
    
    def _generate_dalle_image(
        self,
        question: str,
        answer: str,
        grade_level: str
    ) -> Optional[Dict]:
        """Generate image using DALL-E 3"""
        
        try:
            # Create child-friendly, educational prompt
            prompt = f"""Create a simple, colorful, educational illustration suitable for {grade_level} children about: {question}

Style: 
- Cartoon-like and friendly
- Bright, cheerful colors
- Clear and easy to understand
- Educational and accurate
- No text in the image
- Safe for children

The image should help explain the concept visually."""

            logger.info(f"🎨 Generating DALL-E 3 image for: {question[:50]}...")
            
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",  # Use "standard" to save costs vs "hd"
                n=1,
            )
            
            image_url = response.data[0].url
            
            logger.info(f"✅ DALL-E 3 image generated successfully")
            
            return {
                "visual_content": {
                    "type": "dalle_image",
                    "image_url": image_url,
                    "prompt": question,
                    "display_type": "image"
                },
                "visual_description": f"Educational illustration about {question}"
            }
            
        except Exception as e:
            logger.error(f"DALL-E generation failed: {e}, falling back to emoji")
            return self._generate_emoji_visual(answer, question, grade_level)
    
    def _generate_emoji_visual(
        self,
        text: str,
        question: str,
        grade_level: str
    ) -> Optional[Dict]:
        """Generate emoji-based visual (fallback)"""
        
        text_lower = (text + " " + question).lower()
        
        # Find matching topics
        emojis = []
        topic_found = None
        
        for topic, emoji_list in self.TOPIC_EMOJIS.items():
            if topic in text_lower:
                emojis.extend(emoji_list[:3])
                topic_found = topic
        
        if not emojis:
            emojis = ["💡", "✨", "🌟"]
            topic_found = "learning"
        
        return {
            "visual_content": {
                "type": "emoji_visual",
                "emojis": emojis[:5],
                "topic": topic_found,
                "display_type": "inline"
            },
            "visual_description": f"Visual using emojis: {' '.join(emojis[:5])} for {topic_found}"
        }


# Global instance
_visual_service = None

def get_visual_service() -> VisualService:
    """Get or create visual service instance"""
    global _visual_service
    if _visual_service is None:
        _visual_service = VisualService()
    return _visual_service
