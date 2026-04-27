"""
Camera Feed Simulator & YOLO Detection Engine — Aegis AI
Simulates per-floor CCTV cameras with YOLO v8 detection overlays.
Detection classes: fire | smoke | person-running | fallen-person | crowd-dense
"""
import random
import asyncio
from datetime import datetime
from typing import Dict, List, Optional

FLOORS = 10
DETECTION_CLASSES = ["fire", "smoke", "person-running", "fallen-person", "crowd-dense"]

# Zone labels shown on camera panels
ZONE_LABELS = {
    "fire":           "HIGH HEAT ZONE",
    "smoke":          "SMOKE DENSE AREA",
    "person-running": "EVACUATION IN PROGRESS",
    "fallen-person":  "CASUALTY DETECTED",
    "crowd-dense":    "CROWD DENSE - BOTTLENECK",
}

# Canvas dimensions for bounding box generation
CANVAS_W, CANVAS_H = 320, 180


class CameraFeedSimulator:
    """
    Simulates CCTV camera feeds per floor with Gemma-powered Vision analysis.
    """

    def __init__(self):
        self._floor_crisis: Dict[int, List[str]] = {f: [] for f in range(0, FLOORS)}
        self._active_crisis_rooms: List[str] = []
        self._detection_cache: Dict[int, List[Dict]] = {}
        
        # Base backgrounds (simulated URLs or paths)
        self.floor_assets = {
            0: "lobby_cam_base.jpg",
            1: "corridor_fl1_base.jpg",
            2: "corridor_fl2_base.jpg",
            3: "corridor_fl3_base.jpg",
            4: "corridor_fl4_base.jpg",
        }

    def set_crisis_zones(self, fire_zones: List[str], smoke_floors: List[int] = None):
        # We now store a list of specific room IDs that have active crises
        self._active_crisis_rooms = fire_zones
        self._floor_crisis = {f: [] for f in range(0, FLOORS)}
        
        for zone in fire_zones:
            floor = int(zone[:-2])
            if floor in self._floor_crisis:
                if "fire" not in self._floor_crisis[floor]:
                    self._floor_crisis[floor].append("fire")
                if "person-running" not in self._floor_crisis[floor]:
                    self._floor_crisis[floor].append("person-running")
        
        if smoke_floors:
            for f in smoke_floors:
                if f in self._floor_crisis and "smoke" not in self._floor_crisis[f]:
                    self._floor_crisis[f].append("smoke")

    def get_all_feeds(self, people_tracking: Dict[str, Dict] = None) -> Dict:
        feeds = []
        all_detections = []
        people_tracking = people_tracking or {}

        for floor in range(0, 5): # Standard 5 floors
            detections = self._generate_detections(floor, people_tracking)
            self._detection_cache[floor] = detections
            
            # Gemma Vision Analysis for this floor
            gemma_vision = self._run_gemma_vision(floor, detections)
            
            feeds.append({
                "floor": floor,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "detections": detections,
                "gemma_vision": gemma_vision,
                "zone_label": self._floor_zone_label(floor, detections),
                "status": self._floor_status(detections),
                "risk_score": self._floor_risk(detections),
                "canvas": {"width": CANVAS_W, "height": CANVAS_H},
            })
            all_detections.extend(detections)

        return {
            "feeds": feeds,
            "detections": all_detections,
            "timestamp": datetime.now().isoformat(),
        }

    def _generate_detections(self, floor: int, people_tracking: Dict[str, Dict]) -> List[Dict]:
        detections = []
        
        # Only generate detections for rooms actively marked in CRISIS on this floor
        floor_crises = [rid for rid in self._active_crisis_rooms if int(rid[:-2]) == floor]
        
        for zone_id in floor_crises:
            # Deterministic boxes based on room number to ensure they stay in place
            room_num = int(zone_id[-2:])
            x = 20 + (room_num * 25) % (CANVAS_W - 100)
            y = 40 + (room_num * 15) % (CANVAS_H - 80)
            
            # Fire detection
            detections.append({
                "label": "fire",
                "confidence": 0.98,
                "box": [x, y, 80, 80],
                "zone": zone_id,
                "floor": floor,
                "color": self._label_color("fire"),
                "timestamp": datetime.now().isoformat(),
            })

        # Generate people detections based on real state
        for pid, person in people_tracking.items():
            if person["floor"] == floor and person["status"] in ("EVACUATING", "STAYING"):
                pos = person["current_position"]
                try:
                    if "Stairwell" in pos:
                        room_num = int(pos.split("-")[1])
                    else:
                        room_num = int(pos[-2:])
                except ValueError:
                    room_num = 1
                
                x = 20 + (room_num * 30) % (CANVAS_W - 50)
                y = 40 + (room_num * 20) % (CANVAS_H - 80)
                
                label = "person-running" if person["status"] == "EVACUATING" else "person"
                
                detections.append({
                    "label": label,
                    "confidence": 0.95,
                    "box": [x, y, 30, 50],
                    "zone": pos,
                    "floor": floor,
                    "color": self._label_color("person-running") if label == "person-running" else "#a3e635",
                    "timestamp": datetime.now().isoformat(),
                })

        return detections

    def _run_gemma_vision(self, floor: int, detections: List[Dict]) -> Dict:
        """
        Runs Google Vision AI (PaliGemma) analysis of the camera frame.
        """
        from .vision_ai_service import google_vision_ai
        return google_vision_ai.analyze_frame(floor, detections)

    def _label_color(self, label: str) -> str:
        return {
            "fire":           "#ff3e3e", # Brighter Red
            "smoke":          "#cbd5e1",
            "person-running": "#fbbf24",
            "fallen-person":  "#ff0000",
            "crowd-dense":    "#f97316",
        }.get(label, "#ffffff")

    def _floor_zone_label(self, floor: int, detections: List[Dict]) -> str:
        if any(d["label"] == "fire" for d in detections): return "FIRE DETECTED"
        if any(d["label"] == "smoke" for d in detections): return "SMOKE DETECTED"
        return "CLEAR"

    def _floor_status(self, detections: List[Dict]) -> str:
        if any(d["label"] == "fire" for d in detections): return "CRITICAL"
        if any(d["label"] == "smoke" for d in detections): return "DANGER"
        if detections: return "ELEVATED"
        return "SAFE"

    def _floor_risk(self, detections: List[Dict]) -> int:
        score = 0
        for d in detections:
            if d["label"] == "fire": score += 50
            elif d["label"] == "smoke": score += 25
            else: score += 5
        return min(100, score)
