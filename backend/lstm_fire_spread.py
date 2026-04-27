"""
LSTM Fire Spread Predictor — Aegis AI
Simulates LSTM inference for fire spread prediction using a cellular automaton
model with rolling sequence history (mimicking LSTM hidden state).
Each time step = 30 seconds of simulated spread.
"""
import numpy as np
import random
from typing import Dict, List


FLOORS = 5
ROOMS_PER_FLOOR = 10
TIME_STEP_SECONDS = 30
SEQUENCE_LENGTH = 10  # LSTM lookback window


class LSTMFireSpread:
    def __init__(self):
        self.sequence_length = SEQUENCE_LENGTH
        self.fire_history: List[Dict[str, int]] = []
        self.adjacency = self._build_hotel_graph()

    # ------------------------------------------------------------------ #
    #  Hotel Graph                                                         #
    # ------------------------------------------------------------------ #
    def _build_hotel_graph(self) -> Dict[str, List[str]]:
        """Rooms/corridors as nodes, edges = physical adjacency + stairwells."""
        adj: Dict[str, List[str]] = {}
        for floor in range(0, FLOORS):
            for room in range(1, ROOMS_PER_FLOOR + 1):
                rid = f"{floor}{room:02d}"
                neighbors = []
                # Horizontal adjacency (same floor)
                if room > 1:
                    neighbors.append(f"{floor}{room - 1:02d}")
                if room < ROOMS_PER_FLOOR:
                    neighbors.append(f"{floor}{room + 1:02d}")
                # Stairwells at positions 1, 5, 10
                if room in (1, 5, 10):
                    if floor > 0:
                        neighbors.append(f"{floor - 1}{room:02d}")
                    if floor < FLOORS - 1:
                        neighbors.append(f"{floor + 1}{room:02d}")
                adj[rid] = neighbors
        return adj

    # ------------------------------------------------------------------ #
    #  State Update                                                        #
    # ------------------------------------------------------------------ #
    def update(self, fire_zones: List[str]):
        """Push current fire state into LSTM history (sliding window)."""
        state = {
            f"{f}{r:02d}": (1 if f"{f}{r:02d}" in fire_zones else 0)
            for f in range(0, FLOORS)
            for r in range(1, ROOMS_PER_FLOOR + 1)
        }
        self.fire_history.append(state)
        if len(self.fire_history) > self.sequence_length:
            self.fire_history.pop(0)

    # ------------------------------------------------------------------ #
    #  LSTM Inference                                                      #
    # ------------------------------------------------------------------ #
    def predict(self, current_fire_zones: List[str]) -> Dict:
        """
        Returns:
            next_zones  — list of zones predicted to catch fire next
            etas        — { zone_id: minutes_until_fire }
            spread_rate — 0.0–1.0 velocity of fire progression
            predictions — sorted detail list
        """
        if not current_fire_zones:
            return {"next_zones": [], "etas": {}, "spread_rate": 0.0, "predictions": []}

        self.update(current_fire_zones)
        velocity = self._spread_velocity()
        predictions: Dict[str, Dict] = {}

        for zone in current_fire_zones:
            for neighbor in self.adjacency.get(zone, []):
                if neighbor in current_fire_zones:
                    continue
                prob = self._spread_probability(zone, neighbor, velocity)
                if prob > 0.3:
                    eta = self._eta(prob, velocity)
                    if neighbor not in predictions or predictions[neighbor]["eta"] > eta:
                        predictions[neighbor] = {
                            "zone": neighbor,
                            "floor": int(neighbor[0]),
                            "eta": round(eta, 1),
                            "probability": round(prob, 2),
                            "from_zone": zone,
                        }

        sorted_preds = sorted(predictions.values(), key=lambda x: x["eta"])
        return {
            "next_zones": [p["zone"] for p in sorted_preds[:3]],
            "etas": {p["zone"]: p["eta"] for p in sorted_preds},
            "spread_rate": round(velocity, 2),
            "predictions": sorted_preds[:5],
        }

    # ------------------------------------------------------------------ #
    #  Internal LSTM-Simulated Computations                                #
    # ------------------------------------------------------------------ #
    def _spread_velocity(self) -> float:
        """Approximate LSTM hidden state via growth rate in recent steps."""
        if len(self.fire_history) < 2:
            return 0.4
        growth = [
            sum(self.fire_history[-i].values()) - sum(self.fire_history[-i - 1].values())
            for i in range(1, min(5, len(self.fire_history)))
        ]
        avg = np.mean(growth) if growth else 0
        return float(np.clip(avg / 3.0, 0.1, 1.0))

    def _spread_probability(self, source: str, target: str, velocity: float) -> float:
        """LSTM output node: probability of spread from source → target."""
        base = 0.60
        # Temporal accumulation factor (more history = more certain)
        temporal = min(len(self.fire_history) / self.sequence_length, 1.0) * 0.15
        # Upward spread bonus (heat rises)
        upward = 0.18 if int(target[:-2]) > int(source[:-2]) else 0.0
        # Velocity contribution
        vel_factor = velocity * 0.12
        # Deterministic probability to prevent UI flickering
        return float(np.clip(base + temporal + upward + vel_factor, 0.0, 1.0))

    def _eta(self, probability: float, velocity: float) -> float:
        """Convert LSTM output probability → ETA in minutes."""
        if probability > 0.90:   base = 2.0
        elif probability > 0.75: base = 5.0
        elif probability > 0.55: base = 9.0
        else:                    base = 14.0
        return max(1.0, base * (1.0 - velocity * 0.35))
