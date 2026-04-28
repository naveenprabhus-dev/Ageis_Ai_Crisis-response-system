import requests
import time
import random
import sys

# Ensure UTF-8 output for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

API_URL = "http://localhost:8000"

MESSAGES = [
    {"lang": "English", "msg": "There is a lot of smoke in the corridor! Please help!", "guest": "John Doe", "room": "205", "floor": 2},
    {"lang": "Hindi", "msg": "बचाओ! मेरे कमरे में आग लग गई है!", "guest": "Rajesh Kumar", "room": "304", "floor": 3},
    {"lang": "Tamil", "msg": "உதவி! மின்சாரப் பெட்டியில் தீப்பிடித்துள்ளது!", "guest": "Anbu Selvan", "room": "108", "floor": 1},
    {"lang": "Telugu", "msg": "దయచేసి సహాయం చేయండి, మెట్ల మీద పొగ ఉంది!", "guest": "Venkatesh Rao", "room": "402", "floor": 4},
]

def send_sos(data):
    print(f"Sending SOS from {data['guest']} (Room {data['room']})...")
    try:
        r = requests.post(f"{API_URL}/guest/sos", json={
            "floor": data["floor"],
            "room": data["room"],
            "guest": data["guest"],
            "lang": data["lang"],
            "sos_message": data["msg"]
        })
        if r.status_code == 200:
            try:
                print(f"  [SUCCESS] Intercepted: {data['msg']}")
            except UnicodeEncodeError:
                print(f"  [SUCCESS] Intercepted: [Multilingual Message]")
        else:
            print(f"  [FAILED] {r.text}")
    except Exception as e:
        print(f"  [ERROR] {e}")

if __name__ == "__main__":
    print("Aegis AI - SOS Interception Stress Test")
    print("=======================================")
    
    for m in MESSAGES:
        send_sos(m)
        time.sleep(2)
    
    print("\nTest Complete. Check the 'SOS' tab in the GM App.")
