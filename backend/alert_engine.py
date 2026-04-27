"""
Multilingual Alert Engine — Aegis AI
Generates emergency messages in 7 Indian languages + English.
Used by: Guest Portal (room notification) + Staff App (radio script).
"""
from typing import Dict

LANGUAGES = ["English", "Hindi", "Tamil", "Telugu", "Marathi", "Bengali", "Kannada"]

# Pre-translated emergency templates
# Keys: language → { template_key: message }
TEMPLATES: Dict[str, Dict[str, str]] = {
    "English": {
        "evacuate":    "EMERGENCY: Please evacuate immediately via {exit}. Help is coming.",
        "stay_calm":   "Stay calm. Emergency teams are on the way to Room {room}.",
        "safe":        "You are now safe. Please proceed to the assembly point.",
        "staff_script":"Go to Room {room}, Floor {floor}. Guest speaks {lang}. Say: '{message}'",
        "fire_alert":  "Fire detected on Floor {floor}. Use {exit} to evacuate now.",
        "cyclone":     "Severe weather alert. All guests move to internal corridors.",
    },
    "Hindi": {
        "evacuate":    "आपातकाल: कृपया {exit} के माध्यम से तुरंत निकालें। मदद आ रही है।",
        "stay_calm":   "शांत रहें। आपातकालीन दल कमरा {room} में आ रहे हैं।",
        "safe":        "आप अभी सुरक्षित हैं। कृपया असेंबली पॉइंट की ओर जाएं।",
        "staff_script":"कमरा {room}, मंजिल {floor} पर जाएं। मेहमान {lang} बोलते हैं।",
        "fire_alert":  "मंजिल {floor} पर आग लगी है। {exit} से तुरंत निकलें।",
        "cyclone":     "गंभीर मौसम चेतावनी। सभी मेहमान आंतरिक गलियारों में जाएं।",
    },
    "Tamil": {
        "evacuate":    "அவசரகாலம்: {exit} வழியாக உடனடியாக வெளியேறுங்கள். உதவி வருகிறது.",
        "stay_calm":   "அமைதியாக இருங்கள். அவசர குழுக்கள் அறை {room} க்கு வருகின்றனர்.",
        "safe":        "நீங்கள் இப்போது பாதுகாப்பாக இருக்கிறீர்கள். சந்திப்பு இடத்திற்கு செல்லுங்கள்.",
        "staff_script":"அறை {room}, தளம் {floor} க்கு செல்லுங்கள். விருந்தினர் {lang} பேசுகிறார்.",
        "fire_alert":  "தளம் {floor} இல் தீ கண்டறியப்பட்டது. {exit} வழியாக வெளியேறுங்கள்.",
        "cyclone":     "கடுமையான வானிலை எச்சரிக்கை. அனைவரும் உள் நடைபாதைகளுக்கு செல்லுங்கள்.",
    },
    "Telugu": {
        "evacuate":    "అత్యవసరం: {exit} ద్వారా వెంటనే నిష్క్రమించండి. సహాయం వస్తోంది.",
        "stay_calm":   "శాంతంగా ఉండండి. అత్యవసర బృందాలు గది {room}కి వస్తున్నారు.",
        "safe":        "మీరు ఇప్పుడు సురక్షితంగా ఉన్నారు. సమావేశ స్థానానికి వెళ్ళండి.",
        "staff_script":"గది {room}, అంతస్థు {floor}కి వెళ్ళండి. అతిథి {lang} మాట్లాడతారు.",
        "fire_alert":  "అంతస్థు {floor}లో అగ్ని గుర్తించబడింది. {exit} ద్వారా నిష్క్రమించండి.",
        "cyclone":     "తీవ్రమైన వాతావరణ హెచ్చరిక. అందరూ లోపలి కారిడార్లకు వెళ్ళండి.",
    },
    "Marathi": {
        "evacuate":    "आणीबाणी: {exit} मार्गे ताबडतोब बाहेर पडा. मदत येत आहे.",
        "stay_calm":   "शांत राहा. आपत्कालीन पथक खोली {room} मध्ये येत आहे.",
        "safe":        "तुम्ही आता सुरक्षित आहात. कृपया संमेलन स्थळी जा.",
        "staff_script":"खोली {room}, मजला {floor} वर जा. पाहुणे {lang} बोलतात.",
        "fire_alert":  "मजला {floor} वर आग आढळली. {exit} मार्गे बाहेर पडा.",
        "cyclone":     "तीव्र हवामान इशारा. सर्व पाहुणे आतील कॉरिडॉरमध्ये जा.",
    },
    "Bengali": {
        "evacuate":    "জরুরি অবস্থা: {exit} দিয়ে অবিলম্বে বেরিয়ে যান। সাহায্য আসছে।",
        "stay_calm":   "শান্ত থাকুন। জরুরি দল রুম {room} এ আসছে।",
        "safe":        "আপনি এখন নিরাপদ। অনুগ্রহ করে সমাবেশ স্থানে যান।",
        "staff_script":"রুম {room}, তলা {floor} এ যান। অতিথি {lang} বলেন।",
        "fire_alert":  "তলা {floor} এ আগুন সনাক্ত হয়েছে। {exit} দিয়ে বেরিয়ে যান।",
        "cyclone":     "তীব্র আবহাওয়া সতর্কতা। সকল অতিথি অভ্যন্তরীণ করিডোরে যান।",
    },
    "Kannada": {
        "evacuate":    "ತುರ್ತು: {exit} ಮೂಲಕ ತಕ್ಷಣ ನಿರ್ಗಮಿಸಿ. ಸಹಾಯ ಬರುತ್ತಿದೆ.",
        "stay_calm":   "ಶಾಂತವಾಗಿರಿ. ತುರ್ತು ತಂಡ ಕೊಠಡಿ {room} ಗೆ ಬರುತ್ತಿದೆ.",
        "safe":        "ನೀವು ಈಗ ಸುರಕ್ಷಿತವಾಗಿದ್ದೀರಿ. ಸಭೆ ಸ್ಥಳಕ್ಕೆ ಹೋಗಿ.",
        "staff_script":"ಕೊಠಡಿ {room}, ಮಹಡಿ {floor} ಗೆ ಹೋಗಿ. ಅತಿಥಿ {lang} ಮಾತನಾಡುತ್ತಾರೆ.",
        "fire_alert":  "ಮಹಡಿ {floor} ನಲ್ಲಿ ಬೆಂಕಿ ಪತ್ತೆಯಾಗಿದೆ. {exit} ಮೂಲಕ ನಿರ್ಗಮಿಸಿ.",
        "cyclone":     "ತೀವ್ರ ಹವಾಮಾನ ಎಚ್ಚರಿಕೆ. ಎಲ್ಲರೂ ಒಳ ಕಾರಿಡಾರ್‌ಗಳಿಗೆ ಹೋಗಿ.",
    },
}


class AlertEngine:
    def guest_alert(
        self, template_key: str, language: str,
        room: str = "?", floor: int = 1, exit_route: str = "Stairwell 1"
    ) -> str:
        lang = language if language in TEMPLATES else "English"
        tmpl = TEMPLATES[lang].get(template_key, TEMPLATES["English"].get(template_key, ""))
        return tmpl.format(exit=exit_route, room=room, floor=floor, lang=language)

    def staff_script(self, task: Dict) -> str:
        """Generate staff radio script for approaching a guest."""
        room     = task.get("room", "?")
        floor    = task.get("floor", 1)
        lang     = task.get("language", "English")
        exit_rt  = task.get("exit_route", "Stairwell 1")
        guest_msg = self.guest_alert("evacuate", lang, room, floor, exit_rt)
        eng_tmpl  = TEMPLATES["English"]["staff_script"]
        return eng_tmpl.format(room=room, floor=floor, lang=lang, message=guest_msg)

    def broadcast_message(self, template_key: str, floor: int, exit_route: str = "Stairwell 1") -> Dict[str, str]:
        """Return messages in all 7 languages for a given alert type."""
        return {
            lang: TEMPLATES[lang].get(template_key, "").format(
                exit=exit_route, floor=floor, room="all", lang=lang
            )
            for lang in LANGUAGES
        }
