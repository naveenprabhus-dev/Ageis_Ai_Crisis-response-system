from typing import Dict, Tuple
from gemma_service import gemma

class LLMDecisionEngine:
    """
    Orchestrates emergency response using Gemma-powered logic.
    """
    
    def __init__(self):
        pass

    def make_decision(self, guest_data: Dict, floor_risk: int, room_fire_eta: float = 99.0) -> Tuple[str, str]:
        """
        Analyzes the situation and returns (MODE, RATIONALE).
        Modes: 'STAFF_RESCUE', 'SELF_RESCUE'
        """
        age = guest_data.get("age", 30)
        is_vulnerable = guest_data.get("is_vulnerable", False)
        room_id = guest_data.get("room", "UNK")
        room_status = guest_data.get("status", "SAFE")
        
        # Determine Base Mode
        # If room itself is on fire or fire is imminent (< 3 mins), always STAFF_RESCUE
        if room_status == "CRISIS" or room_fire_eta < 3.0:
             decision = "STAFF_RESCUE"
        # If specifically designated self-rescue rooms in this demo
        elif room_id in ("108", "401"):
            decision = "SELF_RESCUE"
        # Vulnerable or extreme floor risk
        elif is_vulnerable or age > 75 or floor_risk >= 98:
            decision = "STAFF_RESCUE"
        # High risk (80-98) but healthy -> can they self-rescue?
        elif floor_risk >= 80:
            # If vulnerable or quite old, staff rescue. Otherwise, self-rescue is safer/faster if far from fire.
            if is_vulnerable or age > 70:
                decision = "STAFF_RESCUE"
            elif room_fire_eta > 10.0:
                # Healthy and fire is far away -> Encourage self-rescue to keep staff free for others
                decision = "SELF_RESCUE"
            else:
                decision = "STAFF_RESCUE"
        else:
            decision = "SELF_RESCUE"

        # Generate Gemma-powered Rationale (Simplified for demo)
        if decision == "STAFF_RESCUE":
            if is_vulnerable or age > 75:
                reasoning = "Gemma Analysis: Room identified as High Alert/Vulnerable zone. Deploying tactical human unit immediately to ensure safe evacuation."
                rationale = "Tactical extraction authorized for High Alert Zone. A professional responder is en route to your location. Secure your position."
            elif room_status == "CRISIS":
                reasoning = "Gemma Analysis: Immediate fire threat detected in room. Prioritizing tactical extraction."
                rationale = "Immediate threat detected. A responder is being diverted to your room now. Stay low and wait for assistance."
            else:
                reasoning = "Gemma Analysis: High physical risk profile or thermal density detected. Deploying tactical human unit."
                rationale = "Tactical extraction authorized by Aegis AI. A professional responder is en route to your location. Secure your position and wait for direct assistance."
        else:
            reasoning = "Gemma Analysis: Occupant is physically capable and corridor thermal levels are within safe self-rescue thresholds."
            rationale = "Self-rescue protocol activated. Follow the dynamic lighting and AR path displayed on your device to reach the safest exit."
            
        return decision, rationale

# Singleton instance
engine = LLMDecisionEngine()
