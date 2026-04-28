"""
Scenario Engine — Aegis AI
Predefined, deterministic crisis scenarios with timeline support.
"""

SCENARIOS = {
    "standard_fire": {
        "name": "Standard Emergency: Floor 3 Fire Origin",
        "initial_state": {
            "fire_zones": ["304"],
            "smoke_floors": [3],
            "high_alert_rooms": ["304"],
            "guests": {
                "304": {"name": "Rajesh Kumar", "vulnerable": False, "status": "CRISIS", "language": "Hindi"},
                "303": {"name": "Priya Singh", "vulnerable": False, "status": "STAYING", "language": "English"},
                "302": {"name": "Amit Patel", "vulnerable": False, "status": "STAYING", "language": "English"},
                "204": {"name": "Sita Devi", "vulnerable": False, "status": "STAYING", "language": "Tamil"},
                "404": {"name": "Vikram Shah", "vulnerable": False, "status": "STAYING", "language": "English"},
                "305": {"name": "Arjun Das", "vulnerable": False, "status": "STAYING", "language": "English"},
                "401": {"name": "Naveen Prabhu", "vulnerable": False, "status": "STAYING", "language": "English"},
            },
            "staff": {
                "S-01": {"floor": 0, "room": "001", "name": "S-01"},
                "S-02": {"floor": 0, "room": "010", "name": "S-02"},
                "S-03": {"floor": 0, "room": "005", "name": "S-03"},
                "S-04": {"floor": 1, "room": "101", "name": "S-04"},
                "S-05": {"floor": 1, "room": "110", "name": "S-05"},
                "S-06": {"floor": 2, "room": "201", "name": "S-06"},
                "S-07": {"floor": 3, "room": "301", "name": "S-07"},
                "S-08": {"floor": 3, "room": "310", "name": "S-08"},
                "S-09": {"floor": 3, "room": "305", "name": "S-09"},
                "S-10": {"floor": 4, "room": "401", "name": "S-10"},
            }
        },
        "timeline": [
            {"cycle": 2, "action": "spread_fire", "room": "303"},
            {"cycle": 3, "action": "spread_fire", "room": "302"},
            {"cycle": 4, "action": "spread_fire", "room": "204"},
            {"cycle": 4, "action": "spread_fire", "room": "404"},
            {"cycle": 5, "action": "sos_received", "room": "302", "msg": "There is fire everywhere and I am trapped!"},
        ],
        "fixed_responses": {
            "FIRE_DETECTION": "Critical thermal signature detected in Room 304. Initiating level 4 response protocol.",
            "STRATEGIC_ADVICE": "Prioritize evacuation of Floor 3. High alert zone identified.",
        }
    }
}

class ScenarioEngine:
    def __init__(self, scenario_id: str = "standard_fire"):
        self.scenario_id = scenario_id
        self.scenario = SCENARIOS.get(scenario_id)
        self.cycle = 0
        
    def get_initial_state(self):
        return self.scenario["initial_state"]
    
    def get_fixed_response(self, key: str) -> str:
        return self.scenario["fixed_responses"].get(key)
    
    def get_events_for_cycle(self, current_cycle: int):
        return [e for e in self.scenario["timeline"] if e["cycle"] == current_cycle]

scenario_engine = ScenarioEngine()
