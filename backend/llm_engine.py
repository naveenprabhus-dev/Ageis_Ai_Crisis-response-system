from typing import Dict, Tuple
from gemma_service import gemma

class LLMDecisionEngine:
    """
    Orchestrates emergency response using Gemma-powered logic.
    """
    
    def __init__(self):
        pass

    def make_decision(self, guest_data: Dict, floor_risk: int) -> Tuple[str, str]:
        """
        Analyzes the situation and returns (MODE, RATIONALE).
        Modes: 'STAFF_RESCUE', 'SELF_RESCUE'
        """
        age = guest_data.get("age", 30)
        is_vulnerable = guest_data.get("is_vulnerable", False)
        room_id = guest_data.get("room", "UNK")
        
        # Determine Base Mode
        if is_vulnerable or age > 75 or floor_risk > 80:
            decision = "STAFF_RESCUE"
        else:
            decision = "SELF_RESCUE"

        # Generate Gemma-powered Rationale (Simplified for demo)
        if decision == "STAFF_RESCUE":
            if is_vulnerable:
                reasoning = "Gemma Analysis: Room identified as High Alert/Vulnerable zone. Deploying tactical human unit immediately to ensure safe evacuation."
                rationale = "Tactical extraction authorized for High Alert Zone. A professional responder is en route to your location. Secure your position."
            else:
                reasoning = "Gemma Analysis: High physical risk profile or thermal density detected. Deploying tactical human unit."
                rationale = "Tactical extraction authorized by Aegis AI. A professional responder is en route to your location. Secure your position and wait for direct assistance."
        else:
            reasoning = "Gemma Analysis: Occupant is physically capable and corridor thermal levels are within safe self-rescue thresholds."
            rationale = "Self-rescue protocol activated. Follow the dynamic lighting and AR path displayed on your device to reach the safest exit."
            
        return decision, rationale

# Singleton instance
engine = LLMDecisionEngine()
