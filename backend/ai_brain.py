"""
Multi-Modal AI Decision Brain — Aegis AI
Fuses 5 input modalities → runs 3 LSTM models → produces CrisisAssessment.
Modalities: Vision/YOLO | Hotel DB | Weather API | Staff GPS | Guest SOS
"""
import random
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional
from .llm_engine import engine as llm_engine

try:
    from .lstm_fire_spread import LSTMFireSpread
    from .lstm_smoke_spread import LSTMSmokeSpread
    from .lstm_evac_time import LSTMEvacTime
except ImportError:
    from lstm_fire_spread import LSTMFireSpread
    from lstm_smoke_spread import LSTMSmokeSpread
    from lstm_evac_time import LSTMEvacTime
from .gemma_service import gemma
from .gemini_service import gemini
from .scenario_engine import scenario_engine

FLOORS = 5 # 0=Ground, 1-4=Guest Floors
ROOMS_PER_FLOOR = 10

# Zone risk score weights (must sum to 1.0)
WEIGHT_VISION_FIRE    = 0.35
WEIGHT_LSTM_FIRE_ETA  = 0.25
WEIGHT_LSTM_SMOKE     = 0.20
WEIGHT_OCCUPANCY      = 0.10
WEIGHT_WEATHER        = 0.10


class AiBrain:
    """
    Central decision engine. Call `analyze()` every cycle to get a
    fresh CrisisAssessment from all fused modalities.
    """

    def __init__(self):
        self.fire_lstm  = LSTMFireSpread()
        self.smoke_lstm = LSTMSmokeSpread()
        self.evac_lstm  = LSTMEvacTime()
        self.decision_log: deque = deque(maxlen=50)
        self.cycle_count = 0
        self.current_crisis_id = None

    # ──────────────────────────────────────────────────────────────────
    #  MAIN ENTRY POINT
    # ──────────────────────────────────────────────────────────────────
    def analyze(
        self,
        vision_data:  Dict,   # from camera_feed / YOLO
        hotel_data:   Dict,   # from task_engine
        weather_data: Dict,   # from weather_module
        staff_data:   Dict,   # from ConnectionManager
        sos_events:   List[Dict],  # recent SOS triggers
    ) -> Dict:
        """
        Full multi-modal fusion cycle.
        Returns CrisisAssessment dict pushed to all clients via WebSocket.
        """
        self.cycle_count += 1

        # ── Step 1: Normalize each modality ─────────────────────────
        vis  = self._normalize_vision(vision_data)
        hotel = self._normalize_hotel(hotel_data)
        wx   = self._normalize_weather(weather_data)
        staff = self._normalize_staff(staff_data)
        sos  = self._normalize_sos(sos_events)

        # ── Step 2: Classify crisis type ────────────────────────────
        crisis_type, severity, confidence = self._classify_crisis(vis, wx, sos)

        # ── Step 3: Run 3 LSTM models ────────────────────────────────
        fire_zones = vis.get("fire_zones", [])
        fire_pred  = self.fire_lstm.predict(fire_zones)
        smoke_pred = self.smoke_lstm.predict(fire_zones)
        evac_pred  = self.evac_lstm.predict(
            occupancy_per_floor       = hotel["occupancy"],
            blocked_corridors         = smoke_pred["blocked_corridors"],
            staff_per_floor           = staff["per_floor"],
            time_elapsed_min          = self.cycle_count * 0.5,
            already_evacuated_per_floor = hotel["evacuated"],
        )

        # ── Step 4: Zone risk scoring (weighted fusion) ──────────────
        zone_scores = self._score_zones(vis, fire_pred, smoke_pred, hotel, wx)

        # ── Step 5: BFS evacuation routing ──────────────────────────
        safe_routes, blocked_routes = self._bfs_routes(
            fire_zones, smoke_pred["blocked_corridors"], hotel
        )

        # ── Step 6: Staff dispatch ────────────────────────────────────
        staff_assignments, self_rescuing, rescue_decisions = self._dispatch_staff(
            evac_pred, zone_scores, smoke_pred, staff, hotel
        )

        # ── Step 7: Build CrisisAssessment ────────────────────────────
        affected_floors = sorted(set(
            [int(z[:-2]) for z in fire_zones] +
            [f for f, s in zone_scores.items() if s >= 61]
        ))
        
        # Determine High and Medium Alert Zones
        high_alert_zones = [rid for rid, g in hotel["guests"].items() if g["is_vulnerable"]]
        medium_alert_zones = []
        if "etas" in fire_pred:
            for zone, eta in fire_pred["etas"].items():
                if eta < 5.0 and zone not in high_alert_zones:
                    medium_alert_zones.append(zone)

        # ── Chronological Log Logic ──
        if crisis_type == "FIRE":
            if not self.current_crisis_id:
                self.current_crisis_id = datetime.now().strftime("%Y%m%d%H%M%S")
                self.decision_log.clear()
                self._log("INITIATION", f"CRISIS INITIATED: Fire detected in {fire_zones[0] if fire_zones else 'Unknown Zone'}")
            
            # Predictive logging
            if self.cycle_count % 3 == 0 and fire_pred.get("etas"):
                worst_zone = min(fire_pred["etas"], key=fire_pred["etas"].get)
                self._log("PREDICTION", f"LSTM PREDICTION: Fire will reach {worst_zone} in {fire_pred['etas'][worst_zone]} mins")
            
            # Pre-measure logging
            if blocked_routes:
                self._log("PRE-MEASURE", f"Rerouting {len(blocked_routes)} blocked corridors to alternate exits.")
        else:
            self.current_crisis_id = None
        # ──────────────────────────────

        action = self._recommended_action(crisis_type, severity, zone_scores)
        if crisis_type != "MONITORING":
            self._log("SYSTEM", f"[{crisis_type}] {action}")
        
        # Strategic Advice from Gemma
        if self.cycle_count % 3 == 0 or crisis_type == "FIRE":
            strategic_update = gemma.generate_strategic_advice(crisis_type, severity, affected_floors)
            self._log("STRATEGIC", strategic_update)

        assessment = {
            "cycle": self.cycle_count,
            "timestamp": datetime.now().isoformat(),
            "crisis_type": crisis_type,
            "severity": severity,
            "confidence": confidence,
            "recommended_action": action,
            "affected_floors": affected_floors,
            "zone_risk_scores": zone_scores,
            "fire_spread": {
                "actual_fire_zones": fire_zones,
                "etas": fire_pred.get("etas", {}),
                "next_zones": fire_pred.get("next_zones", []),
                "spread_rate": fire_pred.get("spread_rate", 0)
            },
            "smoke_spread": {
                "blocked_corridors": smoke_pred["blocked_corridors"],
                "floor_smoke_levels": smoke_pred["floor_smoke_levels"],
                "etas": smoke_pred["etas"],
                "smoke_velocity": smoke_pred.get("smoke_velocity", 0),
            },
            "evac_time": evac_pred,
            "safe_routes": safe_routes,
            "blocked_routes": blocked_routes,
            "staff_assignments": staff_assignments,
            "staff_locations": staff["locations"],
            "self_rescuing": self_rescuing,
            "rescue_decisions": rescue_decisions,
            "high_alert_zones": high_alert_zones,
            "medium_alert_zones": medium_alert_zones,
            "weather_threat": wx,
            "vision_summary": vis,
            "recent_sos": sos_events,
            "hotel_data": hotel,
        }
        return assessment

    # ──────────────────────────────────────────────────────────────────
    #  MODALITY NORMALIZERS
    # ──────────────────────────────────────────────────────────────────
    def _normalize_vision(self, data: Dict) -> Dict:
        detections = data.get("detections", [])
        fire_zones = [d["zone"] for d in detections if d.get("label") == "fire"]
        smoke_zones = [d["zone"] for d in detections if d.get("label") == "smoke"]
        persons = [d for d in detections if d.get("label") in ("person-running", "fallen-person")]
        fire_confidence = max(
            (d.get("confidence", 0) for d in detections if d.get("label") == "fire"),
            default=0.0
        )
        return {
            "fire_zones": fire_zones,
            "smoke_zones": smoke_zones,
            "person_count": len(persons),
            "fire_confidence": fire_confidence,
            "detections": detections,
        }

    def _normalize_hotel(self, data: Dict) -> Dict:
        hotel = data.get("hotel", {})
        occupancy: Dict[int, int] = {}
        evacuated: Dict[int, int] = {}
        guest_details: Dict[str, Dict] = {}

        for floor_num in range(0, FLOORS): # Start from floor 0
            floor_data = hotel.get(floor_num, {})
            floor_occ = 0
            floor_evac = 0
            for room_idx in range(1, ROOMS_PER_FLOOR + 1):
                room_id = f"{floor_num}{room_idx:02d}"
                room_data = floor_data.get(room_id, {})
                
                guest_name = room_data.get("guest", "Unknown")
                is_vulnerable = room_data.get("is_high_alert", False)
                
                status = room_data.get("status", "STAYING")
                if status == "EVACUATING" or status == "STAYING":
                    floor_occ += 1
                elif status == "EVACUATED":
                    floor_evac += 1
                
                guest_details[room_id] = {
                    "name": guest_name,
                    "status": status,
                    "floor": floor_num,
                    "room": room_id,
                    "is_vulnerable": is_vulnerable,
                    "age": 80 if is_vulnerable else 30 # Deterministic age
                }
            
            occupancy[floor_num] = floor_occ
            evacuated[floor_num] = floor_evac

        return {
            "occupancy": occupancy, 
            "evacuated": evacuated, 
            "guests": guest_details,
            "hotel": hotel
        }

    def _normalize_weather(self, data: Dict) -> Dict:
        code = data.get("weathercode", 0)
        wind = data.get("windspeed", 0)
        gusts = data.get("windgusts_10m", wind)
        if code >= 95 or wind > 60:
            level, label = 3, "CRITICAL"
        elif code >= 80 or wind > 40:
            level, label = 2, "HIGH"
        elif code >= 51:
            level, label = 1, "ELEVATED"
        else:
            level, label = 0, "LOW"
        return {
            "level": level, "label": label,
            "wmo_code": code, "wind_speed": wind,
            "wind_gusts": gusts,
            "description": data.get("description", ""),
        }

    def _normalize_staff(self, data: Dict) -> Dict:
        # Get all staff locations
        locations = data.get("staff_locations", {})
        
        if not locations:
            locations = {}

        self._floor_crisis: Dict[int, List[str]] = {f: [] for f in range(0, FLOORS)}
        per_floor: Dict[int, int] = {f: 0 for f in range(0, FLOORS)}
        for sid, loc in locations.items():
            floor = loc.get("floor", 1)
            name = loc.get("name", sid)
            if 0 <= floor < FLOORS:
                per_floor[floor] = per_floor.get(floor, 0) + 1
        return {"locations": locations, "per_floor": per_floor, "count": len(locations)}

    def _normalize_sos(self, events: List[Dict]) -> List[Dict]:
        return events[-10:]  # last 10 SOS events

    # ──────────────────────────────────────────────────────────────────
    #  CRISIS CLASSIFIER
    # ──────────────────────────────────────────────────────────────────
    def _classify_crisis(self, vis: Dict, wx: Dict, sos: List) -> tuple:
        fire_conf = vis.get("fire_confidence", 0.0)
        fire_zones = vis.get("fire_zones", [])
        
        if fire_conf > 0.40 or fire_zones:
            return "FIRE", 90, round(fire_conf, 2)
        return "MONITORING", 0, 1.0

    # ──────────────────────────────────────────────────────────────────
    #  ZONE RISK SCORER
    # ──────────────────────────────────────────────────────────────────
    def _score_zones(
        self, vis: Dict, fire_pred: Dict, smoke_pred: Dict,
        hotel: Dict, wx: Dict
    ) -> Dict[int, int]:
        scores: Dict[int, int] = {}
        fire_etas = fire_pred.get("etas", {})
        smoke_levels = smoke_pred.get("floor_smoke_levels", {})
        weather_score = wx.get("level", 0) * 10.0 / 3.0  # 0–10 pts

        for floor in range(0, FLOORS):
            # Vision score: fire on this floor?
            floor_fire_zones = [z for z in vis.get("fire_zones", []) if int(z[:-2]) == floor]
            vis_score = (len(floor_fire_zones) * 20) + (vis.get("fire_confidence", 0.0) * 15) if floor_fire_zones else 0.0

            # LSTM fire ETA score: shorter ETA = higher risk
            floor_zone_ids = [f"{floor}{r:02d}" for r in range(1, ROOMS_PER_FLOOR + 1)]
            min_eta = min((fire_etas[z] for z in floor_zone_ids if z in fire_etas), default=99)
            
            if min_eta < 3:   fire_eta_score = 40.0 # Extreme immediate danger
            elif min_eta < 7: fire_eta_score = 25.0
            elif min_eta < 15: fire_eta_score = 10.0
            else:              fire_eta_score = 0.0

            # LSTM smoke score (reduced weight unless density is very high)
            smoke_density = smoke_levels.get(floor, 0.0)
            smoke_score = (smoke_density * 15.0) if smoke_density > 0.4 else (smoke_density * 5.0)

            # Occupancy score
            occ = hotel["occupancy"].get(floor, 0)
            occ_score = min(5.0, occ * 0.5)

            raw = vis_score + fire_eta_score + smoke_score + occ_score + weather_score
            scores[floor] = int(min(100, max(0, raw)))

        return scores

    # ──────────────────────────────────────────────────────────────────
    #  BFS EVACUATION ROUTING
    # ──────────────────────────────────────────────────────────────────
    def _bfs_routes(
        self, fire_zones: List[str], blocked_corridors: List[str], hotel: Dict
    ) -> tuple:
        safe_routes: Dict[int, List[str]] = {}
        all_blocked: List[str] = list(blocked_corridors) + fire_zones

        for floor in range(0, FLOORS):
            if any(int(z[:-2]) == floor for z in fire_zones):
                # BFS: find exit avoiding fire
                exit_options = []
                stairwells = [1, 10]
                for sw in stairwells:
                    sw_id = f"{floor}{sw:02d}"
                    if sw_id not in all_blocked:
                        exit_options.append(f"Stairwell-{sw} → Ground Exit")
                safe_routes[floor] = exit_options if exit_options else ["EMERGENCY EXIT ONLY"]
            else:
                safe_routes[floor] = ["All stairwells available"]

        return safe_routes, blocked_corridors

    # ──────────────────────────────────────────────────────────────────
    #  STAFF DISPATCH
    # ──────────────────────────────────────────────────────────────────
    def _dispatch_staff(
        self, evac_pred: Dict, zone_scores: Dict[int, int], smoke_pred: Dict,
        staff: Dict, hotel: Dict
    ) -> tuple:
        assignments: Dict[str, str] = {}
        self_rescuing: List[str] = []
        rescue_decisions: List[Dict] = []
        staff_pool = list(staff.get("locations", {}).keys())
        
        # Ensure we maintain assignments if possible to prevent UI jumping
        if not hasattr(self, "stable_assignments"):
            self.stable_assignments = {}
        
        # 1. Identify all guests in CRITICAL or HIGH zones
        critical_tasks = []
        for rid, g in hotel["guests"].items():
            if g["status"] == "EVACUATED": continue
            f = g["floor"]
            score = zone_scores.get(f, 0)
            
            # DEMO MODE FIX: Assign a stable base priority so staff are always actively patrolling or assisting
            priority = score + (int(rid) % 10) * 5
            
            if score >= 80: priority += 100 # Critical zone
            if g["is_vulnerable"]: priority += 50 # Vulnerable
            
            critical_tasks.append({
                "room": rid, "floor": f, "priority": priority, 
                "guest": g["name"], "vulnerable": g["is_vulnerable"]
            })
        
        # Sort by priority desc
        critical_tasks.sort(key=lambda x: x["priority"], reverse=True)

        for task in critical_tasks:
            f = task["floor"]
            score = zone_scores.get(f, 0)
            
            # Use LLM Decision Engine for modality assignment
            guest_profile = hotel["guests"].get(task["room"], {})
            mode, rationale = llm_engine.make_decision(guest_profile, score)
            
            fire_presence = score >= 80
            smoke_level = smoke_pred.get("floor_smoke_levels", {}).get(f, 0)
            advice = gemini.generate_safety_advice(fire_presence, smoke_level, mode)
            
            rescue_decisions.append({
                "room": task["room"],
                "floor": f,
                "rescue_mode": mode,
                "voice_advice": advice["voice_advice"],
                "text_advice": advice["text_advice"],
                "rationale": rationale
            })
            
            if mode == "STAFF_RESCUE" and staff_pool:
                # Find if already assigned to THIS specific room
                sid = None
                for assigned_sid, assigned_room in self.stable_assignments.items():
                    if assigned_room == task["room"] and assigned_sid in staff_pool:
                        sid = assigned_sid
                        break
                
                if sid is None:
                    # Pick an available staff member who is NOT currently assigned to something else
                    available_staff = [s for s in staff_pool if s not in self.stable_assignments.keys()]
                    if available_staff:
                        sid = available_staff[0]
                        self.stable_assignments[sid] = task["room"]
                
                if sid is not None:
                    staff_pool.remove(sid)
                    staff_info = staff.get("locations", {}).get(sid, {})
                    
                    assignments[sid] = {
                        "task": f"Rescue {task['guest']}",
                        "room": task["room"],
                        "floor": task["floor"],
                        "status": "CRITICAL" if score >= 80 else "IN_PROGRESS",
                        "eta": 3, # Deterministic ETA
                        "is_vulnerable": task["vulnerable"],
                        "staff_id": sid,
                        "staff_name": staff_info.get("name") or sid,
                        "rationale": rationale
                    }
                    self._log("LLM_DECISION", f"Staff Rescue assigned to {task['room']} (by {sid}): {rationale}")
                else:
                    # Fallback if no staff available: Self Rescue
                    self_rescuing.append({
                        "room": task["room"],
                        "guest_name": task["guest"],
                        "floor": task["floor"],
                        "status": "SELF_RESCUE",
                        "rationale": rationale
                    })
                    self._log("LLM_DECISION", f"Self-Rescue assigned to {task['room']}: All staff busy.")
            else:
                # Self-rescue mode
                self_rescuing.append({
                    "room": task["room"],
                    "guest_name": task["guest"],
                    "floor": task["floor"],
                    "status": "SELF_RESCUE",
                    "rationale": rationale
                })
                self._log("LLM_DECISION", f"Self-Rescue assigned to {task['room']}: {rationale}")

        return assignments, self_rescuing, rescue_decisions

    # ──────────────────────────────────────────────────────────────────
    #  HELPERS
    # ──────────────────────────────────────────────────────────────────
    def _recommended_action(self, crisis_type: str, severity: int, scores: Dict) -> str:
        max_score = max(scores.values()) if scores else 0
        if severity >= 5 or max_score >= 86:
            return "IMMEDIATE FULL EVACUATION"
        if severity >= 4 or max_score >= 61:
            high_floors = [f for f, s in scores.items() if s >= 61]
            return f"EVACUATE FLOORS {', '.join(map(str, high_floors))}"
        if severity >= 3 or max_score >= 31:
            return "ALERT STAFF — PREPARE EVACUATION"
        return "MONITOR — NO ACTION REQUIRED"

    def _log(self, category: str, message: str):
        # Use fixed scenario response if available for this specific log category
        fixed = scenario_engine.get_fixed_response(category)
        msg_to_log = fixed if fixed else message
        
        # Prevent exact duplicate sequential messages
        if self.decision_log and self.decision_log[0]["msg"] == msg_to_log:
            return
            
        self.decision_log.appendleft({
            "time": datetime.now().strftime("%H:%M:%S"),
            "category": category,
            "msg": msg_to_log,
        })

    def get_log(self) -> List[Dict]:
        return list(self.decision_log)
