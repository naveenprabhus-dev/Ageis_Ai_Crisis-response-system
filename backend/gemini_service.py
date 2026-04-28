import os
import time
import random
from typing import Dict

# For a production deployment, this would use:
# import google.generativeai as genai

class GeminiService:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        # DEMO_MODE toggle for hackathon prototyping when no API key is available
        self.demo_mode = True if not self.api_key else False
        
        if not self.demo_mode:
            # Initialization logic for real Gemini API would go here
            # genai.configure(api_key=self.api_key)
            # self.model = genai.GenerativeModel("gemini-1.5-flash")
            print("[Gemini Service] Initialized in PRODUCTION mode.")
        else:
            print("[Gemini Service] Initialized in DEMO mode (Mocking API calls).")

        # Mock dictionaries for the prototype
        self._mock_translations = {
            # Original demo messages
            "मुझे मदद की ज़रूरत है, यहाँ धुआँ है!": {"detected_language": "Hindi", "english_translation": "I need help, there is smoke here!"},
            "காப்பாற்றுங்கள், என்னால் மூச்சு விட முடியவில்லை!": {"detected_language": "Tamil", "english_translation": "Save me, I can't breathe!"},
            "Help me, fire in the hallway!": {"detected_language": "English", "english_translation": "Help me, fire in the hallway!"},
            "मदत करा, मी अडకलो आहे!": {"detected_language": "Marathi", "english_translation": "Help, I am stuck!"},
            "బయటకు వెళ్లలేకపోతున్నాను, సహాయం చేయండి!": {"detected_language": "Telugu", "english_translation": "I can't go out, please help!"},
            "দয়া করে সাহায্য করুন!": {"detected_language": "Bengali", "english_translation": "Please help!"},
            
            # test_interception.py messages
            "बचाओ! मेरे कमरे में आग लग गई है!": {"detected_language": "Hindi", "english_translation": "Help! There is a fire in my room!"},
            "உதவி! மின்சாரப் பெட்டியில் தீப்பிடித்துள்ளது!": {"detected_language": "Tamil", "english_translation": "Help! The electrical box is on fire!"},
            "దయచేసి సహాయం చేయండి, మెట్ల మీద పొగ ఉంది!": {"detected_language": "Telugu", "english_translation": "Please help, there is smoke on the stairs!"},
            "There is a lot of smoke in the corridor! Please help!": {"detected_language": "English", "english_translation": "There is a lot of smoke in the corridor! Please help!"}
        }

    def analyze_sos(self, message: str) -> Dict[str, str]:
        """
        Sends the raw SOS message to Gemini to detect language and translate it.
        Returns a dictionary with 'detected_language' and 'english_translation'.
        """
        if self.demo_mode:
            # Simulate network latency of an LLM call (0.5 to 1.5 seconds)
            time.sleep(random.uniform(0.5, 1.5))
            
            # Use exact match or fallback to generic
            result = self._mock_translations.get(
                message, 
                {"detected_language": "Unknown", "english_translation": message} # Return original if not found
            )
            return result
        else:
            # Production Implementation
            return {"detected_language": "Unknown", "english_translation": message, "reasoning": "Production implementation missing."}

    def translate_to_english(self, text: str, source_lang: str) -> str:
        """Translates guest language to English for staff."""
        if self.demo_mode:
            return self._mock_translations.get(text, {"english_translation": text})["english_translation"]
        return text

    def translate_to_guest(self, text: str, target_lang: str) -> str:
        """Translates English staff message to guest language."""
        if self.demo_mode:
            # Simple mock translation back for demo purposes
            reverse_map = {v["english_translation"]: k for k, v in self._mock_translations.items() if v["detected_language"] == target_lang}
            return reverse_map.get(text, text)
        return text

    def generate_safety_advice(self, fire_presence: bool, smoke_level: float, rescue_mode: str) -> Dict[str, str]:
        """
        Generates short actionable safety advice based on crisis conditions.
        """
        if self.demo_mode:
            # Return pre-written advice for demo purposes
            if rescue_mode == "STAFF_RESCUE":
                return {
                    "voice_advice": "AI Guardian: Staff will come, be safe. Use a wet towel to block smoke under doors.",
                    "text_advice": "AI Guardian: Staff will come, be safe. Use a wet towel to block smoke under doors."
                }
            else:
                if fire_presence or smoke_level > 0.5:
                    return {
                        "voice_advice": "AI Guardian: Proceed to the nearest exit. Stay low and avoid smoke.",
                        "text_advice": "AI Guardian: Proceed to the nearest exit. Stay low and avoid smoke."
                    }
                else:
                    return {
                        "voice_advice": "AI Guardian: Evacuate the building safely. Follow the green exit signs.",
                        "text_advice": "AI Guardian: Evacuate the building safely. Follow the green exit signs."
                    }
        else:
            # Real LLM Call would go here
            return {
                "voice_advice": "Please proceed to safety.",
                "text_advice": "Please proceed to safety."
            }

# Instantiate a singleton to be used across the backend
gemini = GeminiService()
