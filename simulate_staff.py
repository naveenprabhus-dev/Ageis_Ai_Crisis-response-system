import asyncio
import httpx
import time
import random

API_URL = "http://127.0.0.1:8000"
STAFF_IDS = ["ALPHA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOXTROT", "GOLF"]

async def simulate_staff_member(staff_id: str):
    async with httpx.AsyncClient() as client:
        # Start at Ground Floor
        current_floor = 0
        current_room = "001"
        
        while True:
            # 1. Fetch next task
            try:
                r = await client.get(f"{API_URL}/staff/{staff_id}/next_task")
                task = r.json()
                
                if task and "id" in task:
                    print(f"[{staff_id}] Assigned to Rescue Guest in Room {task['room']}...")
                    target_floor = task['floor']
                    target_room = task['room']
                    
                    # Travel to target
                    while current_room != target_room:
                        # Move floor first
                        if current_floor < target_floor:
                            current_floor += 1
                        elif current_floor > target_floor:
                            current_floor -= 1
                        
                        # Once on right floor, move room
                        if current_floor == target_floor:
                            target_num = int(target_room[1:])
                            curr_num = int(current_room[1:])
                            if curr_num < target_num:
                                curr_num += 1
                            elif curr_num > target_num:
                                curr_num -= 1
                            current_room = f"{current_floor}{curr_num:02d}"
                        else:
                            # In stairwell
                            current_room = f"{current_floor}01"

                        # Push location update
                        try:
                            await client.post(f"{API_URL}/staff/{staff_id}/location", json={
                                "floor": current_floor,
                                "room": current_room
                            })
                        except Exception as e:
                            pass
                            
                        # Smooth tracking delay (slowed down for 30s arrival demo)
                        await asyncio.sleep(7.5)
                    
                    # 2. Complete task
                    print(f"[{staff_id}] ARRIVED. Rescuing Guest in Room {task['room']}...")
                    await asyncio.sleep(2) # Rescue time
                    
                    try:
                        await client.post(f"{API_URL}/staff/{staff_id}/complete")
                        print(f"[{staff_id}] SUCCESS: Room {task['room']} cleared.")
                    except Exception as e:
                        pass
                else:
                    # Random patrol on current floor
                    await asyncio.sleep(random.uniform(2, 5))
            except Exception as e:
                await asyncio.sleep(2)

async def main():
    print("Aegis AI Advanced Staff Activity Simulator")
    tasks = [simulate_staff_member(sid) for sid in STAFF_IDS]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
