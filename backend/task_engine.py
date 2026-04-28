"""
Task Engine — Aegis AI
Hotel model: 5 floors × 10 rooms.
Handles room state, task management, evacuation tracking, and BFS routing.
"""
from datetime import datetime
import random
from typing import Dict, List, Optional
from collections import deque

from scenario_engine import scenario_engine

FLOORS = 5 
ROOMS_PER_FLOOR = 10

def _build_hotel_graph() -> Dict[str, List[str]]:
    """BFS graph: 2 stairwells at rooms 1 and 10."""
    adj: Dict[str, List[str]] = {}
    for floor in range(0, FLOORS):
        for room in range(1, ROOMS_PER_FLOOR + 1):
            rid = f"{floor}{room:02d}"
            neighbors = []
            if room > 1:             neighbors.append(f"{floor}{room - 1:02d}")
            if room < ROOMS_PER_FLOOR: neighbors.append(f"{floor}{room + 1:02d}")
            
            # Stairwells at both ends of the building
            if room in (1, 10):
                if floor > 0:        neighbors.append(f"{floor - 1}{room:02d}")
                if floor < FLOORS-1: neighbors.append(f"{floor + 1}{room:02d}")
            adj[rid] = neighbors
    return adj

HOTEL_GRAPH = _build_hotel_graph()
EXIT_NODES = ["001", "010"]

class TaskEngine:
    def __init__(self):
        # Master State — Initialized from Scenario
        state = scenario_engine.get_initial_state()
        
        self.hotel = self._build_layout_from_scenario(state)
        self.tasks: List[Dict] = []
        self.staff_assignments: Dict[str, Dict] = {}
        self.completed_tasks: List[Dict] = []
        self.recent_sos: deque = deque(maxlen=20)

        # Initialize Virtual Staff from Scenario
        self.staff_locations = state.get("staff", {})
        
        self.total_occupied = sum(
            1 for floor in self.hotel.values()
            for room in floor.values() if room["guest"]
        )
        self.rescued_count = 0
        self.evacuation_history: List[Dict] = []
        self.staff_efficiency: Dict[str, int] = {}
        
        # Initialize People Tracking
        self.people_tracking: Dict[str, Dict] = {}
        for floor in self.hotel.values():
            for room in floor.values():
                if room["guest"]:
                    pid = f"P-{room['room_id']}"
                    self.people_tracking[pid] = {
                        "id": pid,
                        "room": room['room_id'],
                        "current_position": room['room_id'],
                        "path": [],
                        "path_index": 0,
                        "status": "SAFE",
                        "floor": room['floor']
                    }

        # Create initial crisis tasks from scenario
        for rid in state.get("fire_zones", []):
            floor = int(rid[0])
            room = self.hotel[floor][rid]
            self._create_crisis(room)

    def _build_layout_from_scenario(self, state: Dict) -> Dict:
        layout: Dict[int, Dict[str, Dict]] = {}
        scenario_guests = state.get("guests", {})
        high_alerts = state.get("high_alert_rooms", [])
        
        for floor in range(0, FLOORS):
            layout[floor] = {}
            for room_num in range(1, ROOMS_PER_FLOOR + 1):
                room_id = f"{floor}{room_num:02d}"
                guest_data = scenario_guests.get(room_id)
                
                is_vulnerable = guest_data.get("vulnerable", False) if guest_data else False
                is_high_alert = (room_id in high_alerts) or is_vulnerable
                
                layout[floor][room_id] = {
                    "room_id":   room_id,
                    "floor":     floor,
                    "room_num":  room_num,
                    "guest":     guest_data["name"] if guest_data else None,
                    "language":  guest_data.get("language", "English") if guest_data else "English",
                    "status":    guest_data.get("status", "SAFE") if guest_data else "SAFE",
                    "is_high_alert": is_high_alert,
                    "is_vulnerable": is_vulnerable
                }
        return layout

    def process_timeline_events(self, cycle: int):
        events = scenario_engine.get_events_for_cycle(cycle)
        for event in events:
            action = event.get("action")
            if action == "spread_fire":
                rid = event["room"]
                floor = int(rid[0])
                room = self.hotel[floor][rid]
                room["is_high_alert"] = True
                if room["status"] != "CRISIS":
                    self._create_crisis(room)
            elif action == "sos_received":
                self.create_task(
                    floor=int(event["room"][0]),
                    room_id=event["room"],
                    guest_name=self.hotel[int(event["room"][0])][event["room"]]["guest"],
                    sos_message=event["msg"]
                )

    # ──────────────────────────────────────────────────────────────────
    #  Crisis Creation
    # ──────────────────────────────────────────────────────────────────
    def _create_crisis(self, room: Dict) -> Dict:
        room["status"] = "CRISIS"
        
        # Corrected impact logic: High alert rooms have LESS time (3 mins)
        is_high_alert = room.get("is_high_alert", False)
        is_vulnerable = room.get("is_vulnerable", False)
        
        # High alert/Vulnerable = 5 mins, Regular = 15 mins
        impact = 5 if (is_high_alert or is_vulnerable) else 15
        
        # Deterministic Task ID based on room to prevent duplicates or random IDs
        task_id = f"TASK_{room['room_id']}_{self.cycle if hasattr(self, 'cycle') else 1}"
        
        task = {
            "id":                     task_id,
            "floor":                  room["floor"],
            "room":                   room["room_id"],
            "guest":                  room["guest"],
            "language":               room["language"] or "English",
            "predicted_impact_mins":  impact,
            "must_reach_mins":        max(1, impact - 2),
            "status":                 "PENDING",
            "priority":               "RED" if impact <= 5 else "YELLOW",
            "created_at":             datetime.now().isoformat(),
        }
        self.tasks.append(task)
        return task

    def create_task(self, floor: int, room_id: str, guest_name: str, sos_message: str = "", detected_language: str = "English", english_translation: str = "", sentiment: str = "Urgent", reasoning: str = "") -> Optional[Dict]:
        floor_data = self.hotel.get(floor)
        if not floor_data:
            return None
        if room_id not in floor_data:
            floor_data[room_id] = {
                "room_id": room_id, "floor": floor,
                "room_num": int(room_id[1:]) if room_id[1:].isdigit() else 0,
                "guest": guest_name, "language": "English", "status": "SAFE",
                "is_high_alert": False, "is_vulnerable": False
            }
            self.total_occupied += 1
        room = floor_data[room_id]
        room["guest"] = guest_name
        room["language"] = detected_language
        sos = {
            "room": room_id, 
            "floor": floor, 
            "guest": guest_name,
            "original_message": sos_message,
            "detected_language": detected_language,
            "translation": english_translation,
            "sentiment": sentiment,
            "reasoning": reasoning,
            "time": datetime.now().isoformat()
        }
        self.recent_sos.appendleft(sos)

        if room["status"] == "CRISIS":
            existing = next(
                (t for t in self.tasks if t["room"] == room_id and t["status"] in ("PENDING", "IN_PROGRESS")),
                None
            )
            if existing:
                return existing

        return self._create_crisis(room)

    # ──────────────────────────────────────────────────────────────────
    #  People Movement Engine
    # ──────────────────────────────────────────────────────────────────
    def set_person_mode(self, room_id: str, mode: str):
        pid = f"P-{room_id}"
        if pid not in self.people_tracking:
            return
        person = self.people_tracking[pid]
        if mode == "SELF_RESCUE" and person["status"] not in ("EVACUATING", "EVACUATED"):
            label, path = self._best_exit(room_id)
            person["path"] = path
            person["path_index"] = 0
            person["status"] = "EVACUATING"
        elif mode == "STAFF_RESCUE" and person["status"] not in ("EVACUATING", "EVACUATED"):
            person["status"] = "STAYING"

    def update_people_movement(self, blocked_corridors: List[str] = None):
        blocked = blocked_corridors or []
        for pid, person in self.people_tracking.items():
            if person["status"] == "EVACUATING":
                if person["path"] and person["path_index"] < len(person["path"]) - 1:
                    next_node = person["path"][person["path_index"] + 1]
                    if next_node not in blocked:
                        person["path_index"] += 1
                        person["current_position"] = next_node
                        
                        # Update floor dynamically if it's a stairwell or different floor
                        if next_node.isdigit():
                            person["floor"] = int(next_node[0])
                            
                        if next_node in EXIT_NODES:
                            person["status"] = "EVACUATED"
                elif person["path"] and person["path_index"] >= len(person["path"]) - 1:
                    person["status"] = "EVACUATED"

    # ──────────────────────────────────────────────────────────────────
    #  Staff Task Assignment
    # ──────────────────────────────────────────────────────────────────
    def get_next_task(self, staff_id: str) -> Optional[Dict]:
        if staff_id in self.staff_assignments:
            return self.staff_assignments[staff_id]
        pending = sorted(
            [t for t in self.tasks if t["status"] == "PENDING"],
            key=lambda x: x["predicted_impact_mins"]
        )
        if not pending:
            return None
        task = pending[0]
        task["status"] = "IN_PROGRESS"
        task["assigned_to"] = staff_id
        task["started_at"] = datetime.now().isoformat()
        label, path = self._best_exit(task["room"])
        task["exit_route"] = label
        task["exit_path"] = path
        self.staff_assignments[staff_id] = task
        return task

    def complete_task(self, staff_id: str) -> Optional[Dict]:
        # Handle regular staff assignments
        task = self.staff_assignments.pop(staff_id, None)
        
        # Handle virtual Guest Self-Rescue assignments
        if not task and staff_id.startswith("GUEST_"):
            room_id = staff_id.replace("GUEST_", "")
            task = next(
                (t for t in self.tasks if t["room"] == room_id and t["status"] in ("PENDING", "IN_PROGRESS")),
                None
            )
            
            # If no formal task exists but guest evacuated, create a "virtual" completion
            if not task:
                floor = int(room_id[0]) if room_id[0].isdigit() else 0
                room = self.hotel.get(floor, {}).get(room_id)
                if room and room["guest"]:
                    task = {
                        "id": f"VIRT_{room_id}_{datetime.now().strftime('%H%M%S')}",
                        "room": room_id, "floor": floor,
                        "guest": room["guest"], "status": "COMPLETED"
                    }
                else:
                    return None
            else:
                task["assigned_to"] = staff_id 

        if not task:
            return None

        task["status"] = "COMPLETED"
        task["completed_at"] = datetime.now().isoformat()
        if "id" in task and not task["id"].startswith("VIRT_"):
            self.completed_tasks.append(task)
            
        room = self.hotel.get(task["floor"], {}).get(task["room"])
        if room:
            room["status"] = "EVACUATED"
            pid = f"P-{room['room_id']}"
            if pid in self.people_tracking:
                self.people_tracking[pid]["status"] = "EVACUATED"
            self.rescued_count = min(self.rescued_count + 1, self.total_occupied)
            
            # Track efficiency
            sid = task.get("assigned_to", "UNKNOWN")
            self.staff_efficiency[sid] = self.staff_efficiency.get(sid, 0) + 1
            
            # Record history snapshot
            self.evacuation_history.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "percentage": self.get_evacuation_percentage()
            })
            if len(self.evacuation_history) > 20:
                self.evacuation_history.pop(0)
            
        return task

    # ──────────────────────────────────────────────────────────────────
    #  BFS Routing
    # ──────────────────────────────────────────────────────────────────
    def _best_exit(self, room_id: str, blocked: List[str] = None) -> tuple:
        """BFS from a specific room to nearest ground exit."""
        blocked = blocked or []
        visited, queue = set(), deque()
        queue.append((room_id, [room_id]))
        visited.add(room_id)
        
        while queue:
            node, path = queue.popleft()
            if node in EXIT_NODES:
                stairwell = node[-2:]
                return f"Stairwell-{stairwell.lstrip('0') or '0'} → Exit", path
            for neighbor in HOTEL_GRAPH.get(node, []):
                if neighbor not in visited and neighbor not in blocked:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return "Emergency Exit", [room_id]

    def find_path(self, start_node: str, end_node: str, blocked: List[str] = None) -> List[str]:
        """BFS from start to end avoiding blocked nodes."""
        blocked = blocked or []
        if start_node == end_node: return [start_node]
        
        visited, queue = set(), deque()
        queue.append((start_node, [start_node]))
        visited.add(start_node)
        
        while queue:
            node, path = queue.popleft()
            if node == end_node:
                return path
            for neighbor in HOTEL_GRAPH.get(node, []):
                if neighbor not in visited and neighbor not in blocked:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return [start_node]

    def get_task_tactical_data(self, staff_id: str, task: Dict, hazards: Dict = None) -> Dict:
        """Calculate ETA, Risk, and Path for a specific task."""
        hazards = hazards or {}
        fire_zones = hazards.get("fire_zones", [])
        blocked_corridors = hazards.get("blocked_corridors", [])
        all_blocked = list(set(fire_zones + blocked_corridors))
        
        staff_loc = self.staff_locations.get(staff_id, {"floor": 0, "room": "001"})
        staff_node = f"{staff_loc['floor']}{staff_loc['room'][-2:]}" if isinstance(staff_loc.get('room'), str) else "001"
        
        # 1. Path to Victim
        path_to_victim = self.find_path(staff_node, task["room"], all_blocked)
        staff_eta = len(path_to_victim) * 0.1 # 6 seconds per node approx
        
        # 2. Path to Exit
        exit_label, path_to_exit = self._best_exit(task["room"], all_blocked)
        
        # 3. Fire ETA (from hazards or default)
        fire_etas = hazards.get("fire_etas", {})
        fire_eta = fire_etas.get(task["room"], task.get("predicted_impact_mins", 5.0))
        
        # 4. Risk Level
        risk_level = "LOW"
        if fire_eta < 2.0 or task["room"] in fire_zones: risk_level = "CRITICAL"
        elif fire_eta < 5.0: risk_level = "HIGH"
        
        return {
            "staff_eta": round(staff_eta, 1),
            "fire_eta": round(fire_eta, 1),
            "risk_level": risk_level,
            "path_to_victim": path_to_victim,
            "path_to_exit": path_to_exit,
            "exit_label": exit_label,
            "is_critical": staff_eta > fire_eta
        }

    def get_evacuation_routes(self, floor: int, blocked: List[str] = None) -> Dict:
        """Return all available evacuation routes for a floor."""
        blocked = blocked or []
        stairwells = [1, 10, 20]
        routes = []
        for sw in stairwells:
            sw_id = f"{floor}{sw:02d}"
            if sw_id not in blocked:
                routes.append({
                    "stairwell": sw,
                    "path": f"Room → Corridor → Stairwell-{sw} → Ground Floor Exit",
                    "status": "CLEAR",
                })
            else:
                routes.append({
                    "stairwell": sw,
                    "path": f"Stairwell-{sw} BLOCKED",
                    "status": "BLOCKED",
                })
        return {"floor": floor, "routes": routes}

    def get_all_staff_tactical_data(self, hazards: Dict = None) -> Dict[str, Dict]:
        """Get tactical data for all active staff."""
        data = {}
        for staff_id, task in self.staff_assignments.items():
            if not staff_id.startswith("GUEST_"):
                data[staff_id] = self.get_task_tactical_data(staff_id, task, hazards)
        return data

    # ──────────────────────────────────────────────────────────────────
    #  Stats & Layout
    # ──────────────────────────────────────────────────────────────────
    def get_evacuation_percentage(self) -> float:
        if self.total_occupied == 0:
            return 100.0
        return min(round(self.rescued_count / self.total_occupied * 100, 1), 100.0)

    def get_gm_stats(self) -> Dict:
        return {
            "evacuation_percentage": self.get_evacuation_percentage(),
            "rescued_count":  self.rescued_count,
            "total_occupied": self.total_occupied,
            "active_rescues": len(self.staff_assignments),
            "pending_count":  len([t for t in self.tasks if t["status"] == "PENDING"]),
            "completed_count": len(self.completed_tasks),
            "floors": FLOORS,
            "rooms_per_floor": ROOMS_PER_FLOOR,
            "history": self.evacuation_history,
            "efficiency": self.staff_efficiency,
        }

    def get_floor_layout(self, floor: int) -> Dict:
        floor_data = self.hotel.get(floor, {})
        return {"floor": floor, "rooms": list(floor_data.values())}

    def get_full_hotel(self) -> Dict:
        return {"hotel": self.hotel, "floors": FLOORS, "rooms_per_floor": ROOMS_PER_FLOOR}

    def get_fire_zones(self) -> List[str]:
        return [
            room_id
            for floor_data in self.hotel.values()
            for room_id, room in floor_data.items()
            if room["status"] == "CRISIS"
        ]

    def get_occupancy_per_floor(self) -> Dict[int, int]:
        return {
            floor: sum(1 for r in rooms.values() if r["guest"] and r["status"] != "EVACUATED")
            for floor, rooms in self.hotel.items()
        }

    def get_recent_sos(self) -> List[Dict]:
        return list(self.recent_sos)
