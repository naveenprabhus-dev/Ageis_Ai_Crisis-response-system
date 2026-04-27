"""
Load Test / Demo Script — Aegis AI
Simulates a mass crisis event by injecting 20 simultaneous SOS calls
across 5 floors to demonstrate queue handling and AI prioritization.
"""
import asyncio
import httpx
import random

BASE_URL = "http://localhost:8000"

GUESTS = [
    ("Priya Singh", "Hindi"), ("Amit Patel", "Gujarati"), ("Sita Devi", "Tamil"),
    ("Vikram Shah", "English"), ("Anita Mehta", "Marathi"), ("Suresh Nair", "Malayalam"),
    ("Kavya Reddy", "Telugu"), ("Arjun Sharma", "Hindi"), ("Deepa Iyer", "Tamil"),
    ("Ravi Krishnan", "English"), ("Meera Joshi", "Marathi"), ("Kiran Desai", "Bengali"),
    ("Sunita Rao", "Kannada"), ("Manoj Gupta", "Hindi"), ("Pooja Agarwal", "English"),
    ("Rohit Verma", "Hindi"), ("Nisha Pillai", "Malayalam"), ("Gaurav Tiwari", "Hindi"),
    ("Swati Bose", "Bengali"), ("Deepak Chawla", "Punjabi")
]

async def inject_crisis(floor, room, guest, lang):
    async with httpx.AsyncClient() as client:
        payload = {
            "floor": floor,
            "room": f"{floor}{room:02d}",
            "type": "fire",
            "severity": random.randint(60, 95),
            "guest": guest,
            "lang": lang
        }
        try:
            resp = await client.post(f"{BASE_URL}/simulate/crisis", json=payload)
            print(f"[Injected] Floor {floor} Room {room} - {guest} ({lang}) -> {resp.status_code}")
        except Exception as e:
            print(f"[Error] Failed to inject: {e}")

async def run_demo():
    print("--- Aegis AI Mass Crisis Simulation ---")
    print("Injecting 20 simultaneous crises...")
    
    tasks = []
    # Run multiple cycles
    for cycle in range(5):
        print(f"--- Simulation Cycle {cycle+1} ---")
        for _ in range(3):
            floor = random.randint(0, 4)
            room = random.randint(1, 10)
            guest, lang = random.choice(GUESTS)
            tasks.append(inject_crisis(floor, room, guest, lang))
        
    await asyncio.gather(*tasks)
    print("--- Simulation Complete ---")
    print("Check the GM Dashboard to see the AI Brain handling the queue.")

if __name__ == "__main__":
    asyncio.run(run_demo())
