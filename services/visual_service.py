import logging
from typing import Dict, List, Optional
import os
from openai import OpenAI
import httpx

logger = logging.getLogger(__name__)

class VisualService:
    """Generate images using DALL-E 3 only when explicitly requested"""
    
    def __init__(self):
        """Initialize with OpenAI client"""
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if self.openai_api_key:
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
    
    TOPIC_EMOJIS = {
        "weather": ["🌤️", "☀️", "🌧️"],
        "space": ["🌍", "🌙", "⭐", "🚀"],
        "animal": ["🐶", "🐱", "🐘"],
        "ocean": ["🌊", "🐠", "🐋"],
        "seahorse": ["🐴", "🌊"],
        "math": ["➕", "➖", "✖️", "➗"],
        "science": ["🔬", "🧪", "⚗️"],
    }
    
    def should_generate_image(self, question: str, answer: str) -> bool:
        """Only generate DALL-E images for EXPLICIT visual requests"""
        
        question_lower = question.lower()
        
        # ONLY generate for these explicit phrases
        explicit_visual_requests = [
            "show me",
            "what does",
            "what do",
            "how does it look",
            "picture of",
            "image of",
            "draw",
            "can you show"
        ]
        
        return any(phrase in question_lower for phrase in explicit_visual_requests)
    
    def generate_visual(self, text: str, question: str, grade_level: str) -> Optional[Dict]:
        """Generate visual - DALL-E only for explicit requests, else emoji"""
        
        try:
            if self.client and self.should_generate_image(question, text):
                logger.info("🎨 Visual explicitly requested - generating DALL-E image")
                return self._generate_dalle_image(question, text, grade_level)
            else:
                # Quick emoji fallback for faster responses
                return self._generate_emoji_visual(text, question, grade_level)
                
        except Exception as e:
            logger.error(f"Error generating visual: {e}")
            return self._generate_emoji_visual(text, question, grade_level)
    
    def _generate_dalle_image(self, question: str, answer: str, grade_level: str) -> Optional[Dict]:
        """Generate image using DALL-E 3"""
        
        try:
            prompt = f"""Create a simple, colorful, educational illustration suitable for {grade_level} children about: {question}

Style: Cartoon-like, bright colors, clear, educational, no text, safe for children."""

            logger.info(f"🎨 Generating DALL-E 3 image...")
            
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            
            image_url = response.data[0].url
            logger.info(f"✅ DALL-E 3 image generated")
            
            return {
                "visual_content": {
                    "type": "dalle_image",
                    "image_url": image_url,
                    "prompt": question,
                    "display_type": "image"
                },
                "visual_description": f"Illustration about {question}"
            }
            
        except Exception as e:
            logger.error(f"DALL-E failed: {e}")
            return self._generate_emoji_visual(answer, question, grade_level)
    
    def _generate_emoji_visual(self, text: str, question: str, grade_level: str) -> Optional[Dict]:
        """Generate emoji visual (instant, no API call)"""
        
        text_lower = (text + " " + question).lower()
        emojis = []
        topic_found = None
        
        for topic, emoji_list in self.TOPIC_EMOJIS.items():
            if topic in text_lower:
                emojis.extend(emoji_list[:3])
                topic_found = topic
                break
        
        if not emojis:
            emojis = ["💡", "✨"]
            topic_found = "learning"
        
        return {
            "visual_content": {
                "type": "emoji_visual",
                "emojis": emojis[:4],
                "topic": topic_found,
                "display_type": "inline"
            },
            "visual_description": f"Emojis for {topic_found}"
        }


_visual_service = None

def get_visual_service() -> VisualService:
    global _visual_service
    if _visual_service is None:
        _visual_service = VisualService()
    return _visual_service
