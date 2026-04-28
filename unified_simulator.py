"""
╔══════════════════════════════════════════════════════════╗
║        AEGIS AI — Unified Simulation Orchestrator        ║
║  Combines: Crisis Injector | Staff Tracker | Load Test   ║
╚══════════════════════════════════════════════════════════╝

Usage:
    python unified_simulator.py              # Interactive menu
    python unified_simulator.py --auto       # Full auto demo (all modules)
    python unified_simulator.py --mode staff # Just staff tracking
    python unified_simulator.py --mode crisis # Just crisis injection
"""
import asyncio
import httpx
import random
import sys
import argparse
import os
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────
API_URL  = os.getenv("API_URL", "http://127.0.0.1:8000")
STAFF_IDS = ["S-01", "S-02", "S-03", "S-04", "S-05", "S-06", "S-07", "S-08", "S-09", "S-10"]
STAFF_TRAVEL_DELAY = 2.5  # seconds per step (≈30s arrival for 12-step path)

GUESTS = [
    ("Priya Singh",    "Hindi",     "मुझे मदद की ज़रूरत है, यहाँ धुआँ है!"),
    ("Amit Patel",     "Gujarati",  "Help me, fire in the hallway!"),
    ("Sita Devi",      "Tamil",     "காப்பாற்றுங்கள், என்னால் மூச்சு விட முடியவில்லை!"),
    ("Vikram Shah",    "English",   "Fire in my room, I need help NOW!"),
    ("Anita Mehta",    "Marathi",   "मदत करा, मी अडकलो आहे!"),
    ("Suresh Nair",    "Malayalam", "ദയവായി സഹായിക്കൂ! തീ ഉണ്ട്!"),
    ("Kavya Reddy",    "Telugu",    "బయటకు వెళ్లలేకపోతున్నాను, సహాయం చేయండి!"),
    ("Arjun Sharma",   "Hindi",     "बचाओ! धुआँ बहुत है!"),
    ("Deepa Iyer",     "Tamil",     "உதவி வேண்டும்! புகை வருகிறது!"),
    ("Ravi Krishnan",  "English",   "Please send someone, trapped in room!"),
    ("Meera Joshi",    "Marathi",   "आग लागली आहे! बाहेर येणं शक्य नाही!"),
    ("Kiran Desai",    "Bengali",   "দয়া করে সাহায্য করুন!"),
    ("Sunita Rao",     "Kannada",   "ಸಹಾಯ ಮಾಡಿ! ಬೆಂಕಿ ಇದೆ!"),
    ("Manoj Gupta",    "Hindi",     "यहाँ बहुत धुआँ है, दरवाज़ा गरम है!"),
    ("Pooja Agarwal",  "English",   "Smoke is filling the corridor, help!"),
    ("Rohit Verma",    "Hindi",     "आग! कोई आ जाओ!"),
    ("Nisha Pillai",   "Malayalam", "തീ! ഒരാൾ വരൂ!"),
    ("Gaurav Tiwari",  "Hindi",     "बचाओ बचाओ!"),
    ("Swati Bose",     "Bengali",   "আগুন! সাহায্য করুন!"),
    ("Deepak Chawla",  "Punjabi",   "ਅੱਗ ਲੱਗ ਗਈ! ਮਦਦ ਕਰੋ!"),
]

# Realistic floor-room map  (floor → list of room_ids)
HOTEL_MAP = {
    0: ["001", "002", "003", "004", "005", "006", "007", "008", "009", "010"],
    1: ["101", "102", "103", "104", "105", "106", "107", "108", "109", "110"],
    2: ["201", "202", "203", "204", "205", "206", "207", "208", "209", "210"],
    3: ["301", "302", "303", "304", "305", "306", "307", "308", "309", "310"],
    4: ["401", "402", "403", "404", "405", "406", "407", "408", "409", "410"],
}

# ── Helpers ──────────────────────────────────────────────────────────────
def ts():
    return datetime.now().strftime("%H:%M:%S")

def log(tag, msg, color=""):
    COLORS = {"red":"\033[91m", "green":"\033[92m", "yellow":"\033[93m",
               "cyan":"\033[96m", "blue":"\033[94m", "magenta":"\033[95m", "":""}
    RESET  = "\033[0m"
    print(f"{COLORS[color]}[{ts()}][{tag}]{RESET} {msg}")

# High Alert Rooms (Fixed for Simulation)
HIGH_ALERT_ROOMS = {
    2: ["204"],
    3: ["302", "303", "304"],
    4: ["404"]
}

def random_room():
    floor = random.choice(list(HIGH_ALERT_ROOMS.keys()))
    room  = random.choice(HIGH_ALERT_ROOMS[floor])
    return floor, room

# ── Module 1: Crisis Injector ─────────────────────────────────────────────
async def inject_single_crisis(client: httpx.AsyncClient, floor=None, room=None, guest_tuple=None):
    """Inject one crisis into the AI Brain."""
    if floor is None or room is None:
        floor, room = random_room()
    if guest_tuple is None:
        guest_tuple = random.choice(GUESTS)

    name, lang, sos_msg = guest_tuple
    payload = {
        "floor": floor,
        "room": room,
        "guest": name,
        "sos_message": sos_msg,
        "lang": lang
    }
    try:
        resp = await client.post(f"{API_URL}/simulate/crisis", json=payload, timeout=10)
        if resp.status_code == 200:
            log("CRISIS", f"Floor {floor}, Room {room} | {name} ({lang}) -> INJECTED", "red")
        else:
            log("CRISIS", f"Floor {floor}, Room {room} | Status {resp.status_code} → {resp.text[:80]}", "yellow")
    except Exception as e:
        log("CRISIS", f"Failed to inject: {e}", "yellow")

async def run_crisis_loop(interval_s: float = 12.0):
    """Continuously inject crises at a set interval."""
    log("MODULE", "Crisis Injector started — new crisis every {:.0f}s".format(interval_s), "red")
    async with httpx.AsyncClient() as client:
        while True:
            await inject_single_crisis(client)
            await asyncio.sleep(interval_s)

# ── Module 2: Staff Tracker ───────────────────────────────────────────────
async def simulate_staff_member(staff_id: str):
    """Simulate one staff member: fetch task → travel → rescue → repeat."""
    async with httpx.AsyncClient() as client:
        # Custom Distribution: F0: 3, F1: 2, F2: 1, F3: 3, F4: 1
        floor_map = {
            "S-01": 0, "S-02": 0, "S-03": 0,
            "S-04": 1, "S-05": 1,
            "S-06": 2,
            "S-07": 3, "S-08": 3, "S-09": 3,
            "S-10": 4
        }
        current_floor = floor_map.get(staff_id, 0)
        current_room = f"{current_floor}01"
        log("STAFF", f"[{staff_id}] Online — starting at Floor {current_floor}, Room {current_room}", "cyan")

        while True:
            try:
                # 1. Fetch next assigned task
                r    = await client.get(f"{API_URL}/staff/{staff_id}/next_task", timeout=10)
                task = r.json()

                if task and "id" in task:
                    target_floor = task["floor"]
                    target_room  = task["room"]
                    log("STAFF", f"[{staff_id}] -> Assigned Room {target_room} (Floor {target_floor})", "cyan")

                    # 2. Travel step-by-step
                    while current_room != target_room or current_floor != target_floor:
                        # Move floor first
                        if current_floor < target_floor:
                            current_floor += 1
                        elif current_floor > target_floor:
                            current_floor -= 1

                        # Then move room on the correct floor
                        if current_floor == target_floor:
                            t_num = int(target_room[1:])
                            c_num = int(current_room[1:])
                            if c_num < t_num:
                                c_num += 1
                            elif c_num > t_num:
                                c_num -= 1
                            current_room = f"{current_floor}{c_num:02d}"
                        else:
                            current_room = f"{current_floor}01"

                        # Push live location
                        try:
                            await client.post(
                                f"{API_URL}/staff/{staff_id}/location",
                                json={"floor": current_floor, "room": current_room},
                                timeout=5
                            )
                            log("STAFF", f"  [{staff_id}] -> Fl.{current_floor} Room {current_room}", "blue")
                        except Exception:
                            pass

                        await asyncio.sleep(STAFF_TRAVEL_DELAY)

                    # 3. Arrived - rescue
                    log("STAFF", f"[{staff_id}] [OK] ARRIVED at Room {target_room}. Rescuing guest...", "green")
                    await asyncio.sleep(3)  # rescue time
                    try:
                        await client.post(f"{API_URL}/staff/{staff_id}/complete", timeout=5)
                        log("STAFF", f"[{staff_id}] [OK] Room {target_room} CLEARED.", "green")
                    except Exception:
                        pass
                    # Return to lobby
                    current_floor = 0
                    current_room  = "001"
                else:
                    # No task — idle patrol: periodically push location to keep markers alive
                    try:
                        await client.post(
                            f"{API_URL}/staff/{staff_id}/location",
                            json={"floor": current_floor, "room": current_room},
                            timeout=5
                        )
                    except: pass
                    await asyncio.sleep(random.uniform(3, 6))

            except Exception as e:
                log("STAFF", f"[{staff_id}] Error: {e}", "yellow")
                await asyncio.sleep(3)

async def run_staff_simulation():
    """Launch all staff members concurrently."""
    log("MODULE", f"Staff Tracker started — {len(STAFF_IDS)} staff active: {', '.join(STAFF_IDS)}", "cyan")
    await asyncio.gather(*[simulate_staff_member(sid) for sid in STAFF_IDS])

# ── Module 3: Load Test (Mass Crisis) ────────────────────────────────────
async def run_load_test(num_crises: int = 15, num_cycles: int = 3):
    """Mass inject crises to test AI Brain queue handling."""
    log("MODULE", f"Load Test: {num_crises} crises × {num_cycles} cycles", "magenta")
    async with httpx.AsyncClient() as client:
        for cycle in range(1, num_cycles + 1):
            log("LOAD", f"=== Cycle {cycle}/{num_cycles} ===", "magenta")
            tasks = []
            selected_guests = random.choices(GUESTS, k=num_crises)
            for g in selected_guests:
                floor, room = random_room()
                tasks.append(inject_single_crisis(client, floor, room, g))
            await asyncio.gather(*tasks)
            log("LOAD", f"Cycle {cycle} complete. Waiting 15s...", "magenta")
            await asyncio.sleep(15)
    log("LOAD", "[OK] Load Test complete. Check GM Dashboard for AI prioritization.", "magenta")

# ── Module 4: Guest Self-Rescue Simulation ──────────────────────────────
async def simulate_guest_self_rescue(room_id: str, floor: int):
    """Simulate a guest self-evacuating: wait for travel time -> complete."""
    guest_id = f"GUEST_{room_id}"
    async with httpx.AsyncClient() as client:
        log("GUEST", f"[{guest_id}] Starting self-evacuation from Room {room_id}...", "magenta")
        
        # Simulate travel time to exit (approx 15-25 seconds)
        travel_time = random.uniform(15, 25)
        await asyncio.sleep(travel_time)
        
        try:
            # Complete the rescue task
            resp = await client.post(f"{API_URL}/staff/{guest_id}/complete", timeout=5)
            if resp.status_code == 200:
                log("GUEST", f"[{guest_id}] SUCCESS: Self-evacuation complete. Room {room_id} clear.", "green")
            else:
                log("GUEST", f"[{guest_id}] Completion failed: {resp.status_code}", "yellow")
        except Exception as e:
            log("GUEST", f"[{guest_id}] Error completing: {e}", "yellow")

async def run_guest_self_rescue_loop():
    """Poll queue stats and log guest rescue activity."""
    log("MODULE", "Guest Self-Rescue Tracker started -- monitoring queue", "magenta")
    async with httpx.AsyncClient() as client:
        while True:
            try:
                r = await client.get(f"{API_URL}/queue/stats", timeout=10)
                if r.status_code == 200:
                    stats = r.json()
                    active  = stats.get("active", 0)
                    queued  = stats.get("queued_red", 0) + stats.get("queued_yellow", 0) + stats.get("queued_green", 0)
                    done    = stats.get("completed", 0)
                    log("QUEUE", f"Active rescues: {active} | Queued: {queued} | Completed: {done}", "magenta")
            except Exception as e:
                log("GUEST_LOOP", f"Queue poll error: {e}", "yellow")
            await asyncio.sleep(8)

# ── Module 5: Targeted Scenario ──────────────────────────────────────────
async def run_scenario(floor: int, room: str, guest_name: str = "Demo Guest"):
    """Inject a specific targeted crisis for a live demo."""
    log("SCENARIO", f"Injecting targeted crisis: Floor {floor}, Room {room}, Guest: {guest_name}", "yellow")
    async with httpx.AsyncClient() as client:
        await inject_single_crisis(
            client, floor=floor, room=room,
            guest_tuple=(guest_name, "English", f"Fire in room {room}! Need help NOW!")
        )
    log("SCENARIO", "Done. Open the Guest App to see real-time response.", "yellow")

# ── Status Checker ────────────────────────────────────────────────────────
async def check_status():
    """Quick health + zone check."""
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{API_URL}/", timeout=5)
            info = r.json()
            log("STATUS", f"[OK] Backend Online: {info.get('message')} v{info.get('version')}", "green")
        except Exception as e:
            log("STATUS", f"[ERR] Backend OFFLINE: {e}", "red")
            return False

        try:
            r = await client.get(f"{API_URL}/queue/stats", timeout=5)
            stats = r.json()
            log("STATUS", f"Queue → Pending: {stats.get('pending',0)} | Active: {stats.get('active',0)} | Done: {stats.get('completed',0)}", "green")
        except Exception:
            log("STATUS", "Queue stats unavailable", "yellow")

        return True

# ── Interactive Menu ──────────────────────────────────────────────────────
def print_banner():
    print("------------------------------------------------------------")
    print("           AEGIS AI - Unified Simulation Console            ")
    print("------------------------------------------------------------")
    print("  1. Full Auto Demo  (Crisis + Staff simultaneously)      ")
    print("  2. Crisis Injector (continuous, 12s interval)           ")
    print("  3. Staff Tracker   (7 staff agents online)              ")
    print("  4. Load Test       (mass crisis injection)              ")
    print("  5. Inject Targeted Scenario (specific room)             ")
    print("  6. Check Backend Status                                  ")
    print("  0. Exit                                                  ")
    print("------------------------------------------------------------")

async def interactive_menu():
    print_banner()
    while True:
        choice = input("Select mode [0-6]: ").strip()
        if choice == "1":
            log("AEGIS", "Starting Full Auto Demo...", "green")
            await asyncio.gather(
                run_crisis_loop(interval_s=12),
                run_staff_simulation(),
                run_guest_self_rescue_loop()
            )
        elif choice == "2":
            await run_crisis_loop(interval_s=12)
        elif choice == "3":
            await run_staff_simulation()
        elif choice == "4":
            await run_load_test()
        elif choice == "5":
            floor = int(input("  Floor [0-4]: ").strip())
            room  = input(f"  Room  (e.g. {floor}02): ").strip()
            guest = input("  Guest name: ").strip() or "Demo Guest"
            await run_scenario(floor, room, guest)
            print_banner()
        elif choice == "6":
            await check_status()
        elif choice == "0":
            log("AEGIS", "Shutting down simulator. Goodbye.", "green")
            break
        else:
            print("Invalid choice. Please enter 0-6.")

# ── Entry Point ───────────────────────────────────────────────────────────
async def main():
    parser = argparse.ArgumentParser(description="Aegis AI Unified Simulator")
    parser.add_argument("--auto",   action="store_true", help="Run full auto demo (crisis + staff)")
    parser.add_argument("--mode",   choices=["crisis", "staff", "load", "status"], help="Run a specific module")
    parser.add_argument("--floor",  type=int, default=None, help="Floor for targeted scenario")
    parser.add_argument("--room",   type=str, default=None, help="Room for targeted scenario")
    parser.add_argument("--guest",  type=str, default="Demo Guest", help="Guest name for targeted scenario")
    args = parser.parse_args()

    # Always check status first
    online = await check_status()
    if not online:
        print("\n[!] Backend is offline. Start it with:")
        print("   uvicorn backend.main:app --reload --port 8000")
        print("   (from inside the aegis_ai directory)\n")
        sys.exit(1)

    if args.auto:
        log("AEGIS", "Full Auto Demo mode activated.", "green")
        await asyncio.gather(
            run_crisis_loop(interval_s=12),
            run_staff_simulation(),
            run_guest_self_rescue_loop()
        )
    elif args.mode == "crisis":
        await run_crisis_loop(interval_s=12)
    elif args.mode == "staff":
        await run_staff_simulation()
    elif args.mode == "load":
        await run_load_test()
    elif args.mode == "status":
        pass  # already done above
    elif args.floor is not None and args.room is not None:
        await run_scenario(args.floor, args.room, args.guest)
    else:
        await interactive_menu()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\033[93m[AEGIS] Simulator stopped by user.\033[0m")
