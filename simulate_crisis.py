import requests
import sys

API_URL = "http://localhost:8000"

def trigger_crisis(floor, room_num, guest="Test User"):
    room = f"{floor}{room_num:02d}"
    sos_message = "Help me, fire in the hallway!"
    
    print(f"Triggering Manual SOS: Floor {floor}, Room {room} (Guest: {guest})")
    try:
        r = requests.post(f"{API_URL}/simulate/crisis", json={
            "floor": floor,
            "room": room,
            "guest": guest,
            "sos_message": sos_message
        })
        if r.status_code == 200:
            print("Successfully injected into AI Brain.")
        else:
            print(f"Failed: {r.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Aegis AI Deterministic Manual SOS Trigger")
    print("-----------------------------------------")
    print("Usage: python simulate_crisis.py [floor] [room_num]")
    print("Note: Fire spread is now automatically managed by the deterministic Scenario Engine.")
    
    floor = 3
    room_num = 4
    if len(sys.argv) == 3:
        floor = int(sys.argv[1])
        room_num = int(sys.argv[2])
    
    trigger_crisis(floor, room_num)
