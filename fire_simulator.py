"""
Fire Simulator — Aegis AI
A dedicated simulation client for the deterministic Scenario Engine.
This script replaces `unified_simulator.py` by relying purely on the deterministic
timeline executed by the AI Brain, and only simulates the physical movement of 
staff units and guest self-evacuations.
"""
import asyncio
import httpx
import random
import os
from datetime import datetime

API_URL  = os.getenv("API_URL", "http://127.0.0.1:8000")
STAFF_IDS = ["S-01", "S-02", "S-03", "S-04"] # Staff IDs from scenario_engine.py
STAFF_TRAVEL_DELAY = 2.5  

def ts(): return datetime.now().strftime("%H:%M:%S")

def log(tag, msg, color=""):
    COLORS = {"red":"\033[91m", "green":"\033[92m", "yellow":"\033[93m",
               "cyan":"\033[96m", "blue":"\033[94m", "magenta":"\033[95m", "":""}
    RESET  = "\033[0m"
    print(f"{COLORS[color]}[{ts()}][{tag}]{RESET} {msg}")

# ── Module 1: Staff Tracker ───────────────────────────────────────────────
async def simulate_staff_member(staff_id: str):
    """Simulate one staff member: fetch task → travel → rescue → repeat."""
    async with httpx.AsyncClient() as client:
        # Get initial location (starts at 001 if unknown)
        current_floor = int(staff_id[-1]) if staff_id[-1].isdigit() and int(staff_id[-1]) < 5 else 0
        current_room  = f"{current_floor}01"
        log("STAFF", f"[{staff_id}] Online — starting at Floor {current_floor}, Room {current_room}", "cyan")

        while True:
            try:
                # 1. Fetch next assigned task
                r = await client.get(f"{API_URL}/staff/{staff_id}/next_task", timeout=10)
                if r.status_code != 200:
                    await asyncio.sleep(2)
                    continue
                
                task = r.json()

                if task and "id" in task:
                    target_floor = task["floor"]
                    target_room  = task["room"]
                    log("STAFF", f"[{staff_id}] → Assigned to Rescue {task.get('guest')} in Room {target_room} (Floor {target_floor})", "cyan")

                    # 2. Travel step-by-step
                    while current_room != target_room or current_floor != target_floor:
                        if current_floor < target_floor:
                            current_floor += 1
                        elif current_floor > target_floor:
                            current_floor -= 1

                        if current_floor == target_floor:
                            try:
                                t_num = int(target_room[1:])
                                c_num = int(current_room[1:])
                                if c_num < t_num: c_num += 1
                                elif c_num > t_num: c_num -= 1
                                current_room = f"{current_floor}{c_num:02d}"
                            except ValueError:
                                current_room = target_room
                        else:
                            current_room = f"{current_floor}01"

                        # Push live location
                        try:
                            await client.post(
                                f"{API_URL}/staff/{staff_id}/location",
                                json={"floor": current_floor, "room": current_room},
                                timeout=5
                            )
                            log("STAFF", f"  [{staff_id}] -> Floor {current_floor}, Room {current_room}", "blue")
                        except Exception:
                            pass

                        await asyncio.sleep(STAFF_TRAVEL_DELAY)

                    # 3. Arrived - rescue
                    log("STAFF", f"[{staff_id}] [OK] ARRIVED at Room {target_room}. Executing rescue protocol...", "green")
                    await asyncio.sleep(3)  # rescue time
                    try:
                        await client.post(f"{API_URL}/staff/{staff_id}/complete", timeout=5)
                        log("STAFF", f"[{staff_id}] [OK] Room {target_room} CLEARED.", "green")
                    except Exception as e:
                        log("STAFF", f"[{staff_id}] Complete failed: {e}", "yellow")
                        
                    # After rescue, move to corridor
                    current_room = f"{current_floor}05"
                else:
                    # No task — idle patrol
                    await asyncio.sleep(random.uniform(2, 4))

            except Exception as e:
                log("STAFF", f"[{staff_id}] Error: {e}", "yellow")
                await asyncio.sleep(3)

async def run_staff_simulation():
    """Launch all staff members concurrently."""
    log("MODULE", f"Staff Tracker started — {len(STAFF_IDS)} staff active: {', '.join(STAFF_IDS)}", "cyan")
    await asyncio.gather(*[simulate_staff_member(sid) for sid in STAFF_IDS])

# ── Module 2: Guest Self-Rescue Simulation ──────────────────────────────
async def simulate_guest_self_rescue(room_id: str, floor: int):
    """Simulate a guest self-evacuating: wait for travel time -> complete."""
    guest_id = f"GUEST_{room_id}"
    async with httpx.AsyncClient() as client:
        log("GUEST", f"[{guest_id}] Starting self-evacuation from Room {room_id}...", "magenta")
        
        # Simulate travel time to exit (approx 15-25 seconds)
        travel_time = random.uniform(15, 25)
        await asyncio.sleep(travel_time)
        
        try:
            # Complete the rescue task via staff endpoint (it handles virtual guests too)
            resp = await client.post(f"{API_URL}/staff/{guest_id}/complete", timeout=5)
            if resp.status_code == 200:
                log("GUEST", f"[{guest_id}] SUCCESS: Self-evacuation complete. Room {room_id} clear.", "green")
            else:
                log("GUEST", f"[{guest_id}] Completion failed: {resp.status_code}", "yellow")
        except Exception as e:
            log("GUEST", f"[{guest_id}] Error completing: {e}", "yellow")

async def run_guest_self_rescue_loop():
    """Poll for self-rescuing guests and trigger their simulation."""
    log("MODULE", "Guest Self-Rescue Tracker started — monitoring AI assessments", "magenta")
    simulating = set()
    async with httpx.AsyncClient() as client:
        while True:
            try:
                r = await client.get(f"{API_URL}/ai/assessment", timeout=10)
                if r.status_code == 200:
                    assessment = r.json()
                    assignments = assessment.get("staff_assignments", {})
                    
                    for sid, data in assignments.items():
                        if sid.startswith("GUEST_") and sid not in simulating:
                            simulating.add(sid)
                            asyncio.create_task(simulate_guest_self_rescue(data["room"], data["floor"]))
                    
                    # Cleanup simulating set (only keep active assignments)
                    active_guests = {sid for sid in assignments if sid.startswith("GUEST_")}
                    simulating = simulating.intersection(active_guests)
                
            except Exception as e:
                # Silently fail on network errors
                pass
            
            await asyncio.sleep(4)

# ── Status Checker ────────────────────────────────────────────────────────
async def check_status():
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{API_URL}/", timeout=5)
            info = r.json()
            log("STATUS", f"[OK] Backend Online: {info.get('message')} v{info.get('version')}", "green")
            return True
        except Exception as e:
            log("STATUS", f"[ERR] Backend OFFLINE: {e}", "red")
            return False

# ── Entry Point ───────────────────────────────────────────────────────────
async def main():
    print("------------------------------------------------------------")
    print("           AEGIS AI - Deterministic Fire Simulator          ")
    print("------------------------------------------------------------")
    print(" This simulator listens to the backend AI Brain's Scenario")
    print(" Engine and physically simulates the movement of Staff and")
    print(" Guests in real-time. No random events are injected.")
    print("------------------------------------------------------------")
    
    online = await check_status()
    if not online:
        print("\n[!] Backend is offline. Start it with:")
        print("   uvicorn backend.main:app --reload --port 8000")
        return

    log("AEGIS", "Starting Simulator Components...", "green")
    await asyncio.gather(
        run_staff_simulation(),
        run_guest_self_rescue_loop()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\033[93m[AEGIS] Simulator stopped by user.\033[0m")
