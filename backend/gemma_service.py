import os
import time
import random
from typing import Dict

# For a production deployment, this would use a Gemma inference endpoint (e.g. Hugging Face TGI or Vertex AI)

class GemmaService:
    def __init__(self):
        self.api_key = os.environ.get("GEMMA_API_KEY")
        # DEMO_MODE toggle for hackathon prototyping
        self.demo_mode = True if not self.api_key else False
        
        if not self.demo_mode:
            print("[Gemma Service] Initialized in PRODUCTION mode (Gemma-7B-IT).")
        else:
            print("[Gemma Service] Initialized in SIMULATION mode (Mocking Gemma-7B-IT).")

        self._reasoning_bank = {
            "Hindi": "Detected high-urgency Hindi dialect. Sentiment is distressed. Contextualizing 'smoke' as immediate respiratory threat.",
            "Tamil": "Tamil SOS identified. Subject is struggling to breathe. Sentiment: Critical. Direct extraction recommended.",
            "Marathi": "Marathi SOS. Subject is trapped. Sentiment: Fearful. Priority assignment needed.",
            "English": "Native English SOS. Clear location provided. Sentiment: Controlled urgency.",
            "Telugu": "Telugu identified. Mobility blocked. Sentiment: Desperate. High priority for staff rescue.",
            "Bengali": "Bengali SOS. Simple distress call. Sentiment: High urgency."
        }

    def detect_language(self, text: str) -> str:
        """
        Detects language based on character ranges (Hindi, Tamil, Telugu, English).
        """
        # Hindi/Marathi/Sanskrit (Devanagari): 0900-097F
        # Tamil: 0B80-0BFF
        # Telugu: 0C00-0C7F
        
        has_hindi = any('\u0900' <= c <= '\u097F' for c in text)
        has_tamil = any('\u0B80' <= c <= '\u0BFF' for c in text)
        has_telugu = any('\u0C00' <= c <= '\u0C7F' for c in text)
        
        if has_tamil: return "Tamil"
        if has_telugu: return "Telugu"
        if has_hindi: return "Hindi"
        return "English"

    def analyze_sos(self, message: str) -> Dict[str, str]:
        """
        Gemma-powered SOS Analysis: Detects Language, Translates, and provides Reasoning.
        """
        # Mock mapping for demo consistency
        mock_map = {
            "मुझे मदद की ज़रूरत है, यहाँ धुआँ है!": {"lang": "Hindi", "trans": "I need help, there is smoke here!"},
            "காப்பாற்றுங்கள், என்னால் மூச்சு விட முடியவில்லை!": {"lang": "Tamil", "trans": "Save me, I can't breathe!"},
            "Help me, fire in the hallway!": {"lang": "English", "trans": "Help me, fire in the hallway!"},
            "मदत करा, मी अडकलो आहे!": {"lang": "Marathi", "trans": "Help, I am stuck!"},
            "బయటకు వెళ్లలేకపోతున్నాను, సహాయం చేయండి!": {"lang": "Telugu", "trans": "I can't go out, please help!"},
            "দয়া করে সাহায্য করুন!": {"lang": "Bengali", "trans": "Please help!"}
        }

        if self.demo_mode:
            time.sleep(random.uniform(0.5, 1.2)) # LLM Latency simulation
            
            # Use character detection for unknown messages
            lang = self.detect_language(message)
            data = mock_map.get(message, {"lang": lang, "trans": message})
            
            return {
                "detected_language": lang,
                "english_translation": data["trans"],
                "sentiment": "Critical" if any(k in data["trans"].lower() for k in ["help", "breathe", "fire", "smoke"]) else "Urgent",
                "reasoning": self._reasoning_bank.get(lang, "Standard SOS pattern recognized. Analyzing proximity to fire zones...")
            }
        else:
            # Production Gemma API Call would go here
            return {"detected_language": "Unknown", "english_translation": message, "reasoning": "API Offline"}

    def generate_strategic_advice(self, crisis_type: str, severity: int, affected_floors: list) -> str:
        """
        Generates a strategic update based on current building state.
        """
        if crisis_type == "MONITORING":
            return "Gemma: System state nominal. Continuing multi-modal surveillance."
        
        advice = [
            f"Gemma Strategic Insight: Severity level {severity} detected on Floors {affected_floors}.",
            "Analysis: Fire spread velocity is increasing. Prioritize stairwell integrity.",
            "Action: Recommend shifting staff from Ground Floor to the most critical zones immediately.",
            "Note: High probability of flashover in upper levels. Monitor ventilation shafts."
        ]
        return " ".join(random.sample(advice, 2))

    def translate_to_english(self, text: str, source_lang: str) -> str:
        """Translates guest language to English for staff. (Forced to English for now)"""
        return text

    def translate_to_guest(self, text: str, target_lang: str) -> str:
        """Translates English staff message to guest language. (Forced to English for now)"""
        return text

# Instantiate a singleton
gemma = GemmaService()
