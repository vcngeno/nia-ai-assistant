import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class VisualService:
    """Generate emoji/icon-based visual representations for learning"""
    
    # Topic-based emoji mappings
    TOPIC_EMOJIS = {
        # Weather & Nature
        "weather": ["🌤️", "☀️", "🌧️", "⛈️", "🌈", "❄️", "🌪️"],
        "rain": ["🌧️", "☔", "💧"],
        "sun": ["☀️", "🌞", "🌅"],
        "snow": ["❄️", "⛄", "🌨️"],
        "wind": ["💨", "🌬️", "🍃"],
        
        # Science
        "space": ["🌍", "🌙", "⭐", "🚀", "🪐", "🌌"],
        "dinosaur": ["🦕", "🦖", "🦴"],
        "animal": ["🐶", "🐱", "🐘", "🦁", "🐼", "🦒"],
        "ocean": ["🌊", "🐠", "🐋", "🦈", "🐙"],
        "plant": ["🌱", "🌻", "🌳", "🌸", "🍀"],
        
        # Math
        "math": ["➕", "➖", "✖️", "➗", "🔢", "📊"],
        "number": ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"],
        "counting": ["🔢", "📝", "✏️"],
        
        # Geography
        "travel": ["✈️", "🚗", "🗺️", "🧳"],
        "city": ["🏙️", "🌆", "🏛️"],
        "country": ["🗺️", "🌍", "🌎"],
        "mountain": ["⛰️", "🏔️"],
        
        # Food
        "food": ["🍎", "🍕", "🍔", "🥗", "🍰"],
        
        # Learning & School
        "school": ["📚", "✏️", "📝", "🎒", "👩‍🏫"],
        "book": ["📚", "📖", "📕"],
        "reading": ["📖", "👀", "💭"],
        
        # Time & Calendar
        "time": ["🕐", "⏰", "📅"],
        "day": ["🌅", "☀️", "🌙"],
        
        # Emotions & Learning
        "happy": ["😊", "🎉", "⭐", "✨"],
        "question": ["❓", "🤔", "💭"],
        "idea": ["💡", "⚡", "✨"],
    }
    
    @staticmethod
    def generate_visual(
        text: str,
        question: str,
        grade_level: str
    ) -> Optional[Dict]:
        """Generate emoji/icon visual based on content"""
        
        try:
            text_lower = (text + " " + question).lower()
            
            # Find matching topics
            emojis = []
            topic_found = None
            
            for topic, emoji_list in VisualService.TOPIC_EMOJIS.items():
                if topic in text_lower:
                    emojis.extend(emoji_list[:3])  # Take up to 3 emojis per topic
                    topic_found = topic
            
            if not emojis:
                # Default learning emojis
                emojis = ["💡", "✨", "🌟"]
                topic_found = "learning"
            
            # Create visual content
            visual = {
                "type": "emoji_visual",
                "emojis": emojis[:5],  # Limit to 5 emojis
                "topic": topic_found,
                "display_type": "inline"  # Can be "inline", "banner", or "decorative"
            }
            
            # Add description for accessibility
            emoji_string = " ".join(emojis[:5])
            description = f"Visual representation using emojis: {emoji_string} representing {topic_found}"
            
            return {
                "visual_content": visual,
                "visual_description": description
            }
            
        except Exception as e:
            logger.error(f"Error generating visual: {e}")
            return None
    
    @staticmethod
    def create_concept_diagram(concept: str, grade_level: str) -> Optional[Dict]:
        """Create a simple emoji-based concept diagram"""
        
        # Simple concept diagrams
        diagrams = {
            "water cycle": {
                "emojis": ["☀️", "→", "💧", "→", "☁️", "→", "🌧️", "→", "🌊"],
                "description": "Water cycle: Sun heats water, creates vapor, forms clouds, rain falls, returns to ocean"
            },
            "food chain": {
                "emojis": ["🌱", "→", "🐛", "→", "🐦", "→", "🦅"],
                "description": "Food chain: Plants eaten by insects, insects eaten by birds, birds eaten by eagles"
            },
            "solar system": {
                "emojis": ["☀️", "☿️", "♀️", "🌍", "♂️", "🪐", "🌌"],
                "description": "Solar system: Sun and the planets in order"
            }
        }
        
        concept_lower = concept.lower()
        for key, diagram in diagrams.items():
            if key in concept_lower:
                return {
                    "visual_content": {
                        "type": "diagram",
                        "emojis": diagram["emojis"],
                        "topic": key,
                        "display_type": "diagram"
                    },
                    "visual_description": diagram["description"]
                }
        
        return None


# Global instance
_visual_service = None

def get_visual_service() -> VisualService:
    """Get or create visual service instance"""
    global _visual_service
    if _visual_service is None:
        _visual_service = VisualService()
    return _visual_service
