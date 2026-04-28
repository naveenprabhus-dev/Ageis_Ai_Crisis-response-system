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
            "Bengali": "Bengali SOS. Simple distress call. Sentiment: High urgency.",
            "Malayalam": "Malayalam SOS. Kerala origin detected. High urgency for coastal/water-related or fire distress.",
            "Kannada": "Kannada SOS. Bangalore-region dialect. Urgent request for immediate corridor clearance."
        }

        # Centralized mock mapping for demo consistency
        self._mock_map = {
            "मुझे मदद की ज़रूरत है, यहाँ धुआँ है!": {"lang": "Hindi", "trans": "I need help, there is smoke here!"},
            "காப்பாற்றுங்கள், என்னால் மூச்சு விட முடியவில்லை!": {"lang": "Tamil", "trans": "Save me, I can't breathe!"},
            "Help me, fire in the hallway!": {"lang": "English", "trans": "Help me, fire in the hallway!"},
            "मदत करा, मी अडकलो आहे!": {"lang": "Marathi", "trans": "Help, I am stuck!"},
            "బయటకు వెళ్లలేకపోతున్నాను, సహాయం చేయండి!": {"lang": "Telugu", "trans": "I can't go out, please help!"},
            "ದಯವಿಟ್ಟು ಸಹಾಯ ಮಾಡಿ, ನನಗೆ ದಾರಿ ಕಾಣುತ್ತಿಲ್ಲ!": {"lang": "Kannada", "trans": "Please help, I cannot see the way!"},
            "സഹായിക്കൂ, ഇവിടെ തീ പിടിച്ചിരിക്കുന്നു!": {"lang": "Malayalam", "trans": "Help, there is a fire here!"},
            "बचाओ! मेरे कमरे में आग लग गई है!": {"lang": "Hindi", "trans": "Help! There is a fire in my room!"},
            "உதவி! மின்சாரப் பெட்டியில் தீப்பிடித்துள்ளது!": {"lang": "Tamil", "trans": "Help! The electrical box is on fire!"},
            "దయచేసి సహాయం చేయండి, మెట్ల మీద పొగ ఉంది!": {"lang": "Telugu", "trans": "Please help, there is smoke on the stairs!"}
        }

    def detect_language(self, text: str) -> str:
        """
        Detects language based on character ranges.
        """
        has_hindi = any('\u0900' <= c <= '\u097F' for c in text)
        has_tamil = any('\u0B80' <= c <= '\u0BFF' for c in text)
        has_telugu = any('\u0C00' <= c <= '\u0C7F' for c in text)
        has_kannada = any('\u0C80' <= c <= '\u0CFF' for c in text)
        has_malayalam = any('\u0D00' <= c <= '\u0D7F' for c in text)
        
        if has_tamil: return "Tamil"
        if has_telugu: return "Telugu"
        if has_kannada: return "Kannada"
        if has_malayalam: return "Malayalam"
        if has_hindi: return "Hindi"
        return "English"

    def analyze_sos(self, message: str) -> Dict[str, str]:
        """
        Gemma-powered SOS Analysis: Detects Language, Translates, and provides Reasoning.
        """
        if self.demo_mode:
            time.sleep(random.uniform(0.3, 0.7)) # LLM Latency simulation
            
            lang = self.detect_language(message)
            data = self._mock_map.get(message, {"lang": lang, "trans": message})
            
            return {
                "detected_language": lang,
                "english_translation": data["trans"],
                "sentiment": "Critical" if any(k in data["trans"].lower() for k in ["help", "breathe", "fire", "smoke", "बचाओ", "உதவி"]) else "Urgent",
                "reasoning": self._reasoning_bank.get(lang, "Standard SOS pattern recognized. Analyzing proximity to fire zones...")
            }
        else:
            return {"detected_language": "Unknown", "english_translation": message, "reasoning": "API Offline"}

    def generate_strategic_advice(self, crisis_type: str, severity: int, affected_floors: list) -> str:
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
        if self.demo_mode:
            if text in self._mock_map:
                return self._mock_map[text]["trans"]
            
            detected = self.detect_language(text)
            if detected == "English":
                return text
            
            generic_translations = {
                "Hindi": "[AI Translation]: Emergency! I need immediate assistance.",
                "Tamil": "[AI Translation]: Alert! There is danger and I am trapped.",
                "Telugu": "[AI Translation]: Help! I cannot exit the room, please send rescue.",
                "Kannada": "[AI Translation]: Immediate assistance requested. Potential blockage.",
                "Malayalam": "[AI Translation]: Distress signal detected. Urgent life safety threat."
            }
            return generic_translations.get(detected, f"[AI Translation]: Distress signal in {detected}.")
        return text

    def translate_to_guest(self, text: str, target_lang: str) -> str:
        if self.demo_mode:
            reverse_map = {v["trans"]: k for k, v in self._mock_map.items() if v["lang"] == target_lang}
            return reverse_map.get(text, text)
        return text

# Instantiate a singleton
gemma = GemmaService()
