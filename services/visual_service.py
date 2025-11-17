import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class VisualService:
    """Generate emoji-based visuals for learning"""
    
    TOPIC_EMOJIS = {
        "weather": ["🌤️", "☀️", "🌧️"],
        "space": ["🌍", "🌙", "⭐", "🚀"],
        "animal": ["🐶", "🐱", "🐘"],
        "ocean": ["🌊", "🐠", "🐋"],
        "seahorse": ["🐴", "🌊"],
        "math": ["➕", "➖", "✖️"],
        "science": ["🔬", "🧪"],
    }
    
    def generate_visual(self, text: str, question: str, grade_level: str) -> Optional[Dict]:
        """Generate emoji visual"""
        
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

def get_visual_service():
    global _visual_service
    if _visual_service is None:
        _visual_service = VisualService()
    return _visual_service
