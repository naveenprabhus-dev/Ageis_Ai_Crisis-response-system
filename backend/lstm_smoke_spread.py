"""
LSTM Smoke Spread Predictor — Aegis AI
Simulates LSTM inference for smoke spread prediction.
Smoke follows HVAC airflow direction — faster than fire, blocks corridors.
Sequence length: 8 steps (each step = 30s). Smoke travels ~2x faster than fire.
"""
import numpy as np
from typing import Dict, List


FLOORS = 5
ROOMS_PER_FLOOR = 10
SEQUENCE_LENGTH = 8
DANGEROUS_DENSITY = 0.60   # above this → route blocked


# HVAC flow map: each floor has a dominant airflow direction (East or West)
# Smoke follows airflow preferentially
HVAC_FLOW: Dict[int, str] = {
    0: "east", 1: "west", 2: "east", 3: "west", 4: "east"
}

# Corridors between room pairs (room_a, room_b) on each floor
CORRIDORS: Dict[int, List[tuple]] = {
    f: [(r, r + 1) for r in range(1, ROOMS_PER_FLOOR)]
    for f in range(0, FLOORS)
}


class LSTMSmokeSpread:
    def __init__(self):
        self.sequence_length = SEQUENCE_LENGTH
        self.smoke_history: List[Dict[str, float]] = []
        # corridor_density[floor][corridor_key] = density 0.0–1.0
        self.corridor_density: Dict[str, float] = {}

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #
    def update(self, fire_zones: List[str]):
        """Push new smoke state derived from fire zones into LSTM history."""
        state: Dict[str, float] = {}
        for zone in fire_zones:
            floor = int(zone[:-2])
            room = int(zone[-2:])
            # Smoke originates at fire location (density 1.0)
            state[zone] = 1.0
            # Spreads to adjacent rooms with decay
            for offset in range(1, 5):
                for direction in (1, -1):
                    neighbor_room = room + (offset * direction)
                    if 1 <= neighbor_room <= ROOMS_PER_FLOOR:
                        neighbor_id = f"{floor}{neighbor_room:02d}"
                        density = max(0.0, 1.0 - offset * 0.22)
                        # HVAC flow amplifies spread in dominant direction
                        if floor in HVAC_FLOW:
                            if HVAC_FLOW[floor] == "east" and direction == 1:
                                density = min(1.0, density * 1.25)
                            elif HVAC_FLOW[floor] == "west" and direction == -1:
                                density = min(1.0, density * 1.25)
                        existing = state.get(neighbor_id, 0.0)
                        state[neighbor_id] = max(existing, density)

        self.smoke_history.append(state)
        if len(self.smoke_history) > self.sequence_length:
            self.smoke_history.pop(0)

    def predict(self, fire_zones: List[str]) -> Dict:
        """
        LSTM inference for smoke spread.
        Returns:
            corridor_risks     — { corridor_key: density_0_to_1 }
            blocked_corridors  — corridors with density > 0.6 (impassable)
            floor_smoke_levels — { floor_num: avg_density }
            etas               — { corridor_key: minutes_to_dangerous }
        """
        if not fire_zones:
            return {
                "corridor_risks": {}, "blocked_corridors": [],
                "floor_smoke_levels": {}, "etas": {}
            }

        self.update(fire_zones)
        velocity = self._smoke_velocity()
        current_state = self.smoke_history[-1] if self.smoke_history else {}

        corridor_risks: Dict[str, float] = {}
        blocked: List[str] = []
        etas: Dict[str, float] = {}

        for floor in range(0, FLOORS):
            for r1, r2 in CORRIDORS[floor]:
                key = f"F{floor}-C{r1}{r2}"
                d1 = current_state.get(f"{floor}{r1:02d}", 0.0)
                d2 = current_state.get(f"{floor}{r2:02d}", 0.0)
                # LSTM output: corridor density = weighted average of adjacent rooms
                density = round(self._lstm_corridor_density(d1, d2, velocity), 3)
                corridor_risks[key] = density
                self.corridor_density[key] = density

                if density >= DANGEROUS_DENSITY:
                    blocked.append(key)
                elif density > 0.2:
                    time_remaining = self._eta_to_dangerous(density, velocity)
                    etas[key] = round(time_remaining, 1)

        # Floor-level smoke summary
        floor_smoke_levels: Dict[int, float] = {}
        for floor in range(0, FLOORS):
            floor_densities = [
                current_state.get(f"{floor}{r:02d}", 0.0)
                for r in range(1, ROOMS_PER_FLOOR + 1)
            ]
            floor_smoke_levels[floor] = round(np.mean(floor_densities), 3) if floor_densities else 0.0

        return {
            "corridor_risks": corridor_risks,
            "blocked_corridors": blocked,
            "floor_smoke_levels": floor_smoke_levels,
            "etas": etas,
            "smoke_velocity": round(velocity, 2),
        }

    def is_corridor_blocked(self, corridor_key: str) -> bool:
        return self.corridor_density.get(corridor_key, 0.0) >= DANGEROUS_DENSITY

    # ------------------------------------------------------------------ #
    #  Internal LSTM-Simulated Computations                               #
    # ------------------------------------------------------------------ #
    def _smoke_velocity(self) -> float:
        if len(self.smoke_history) < 2:
            return 0.5
        prev_total = sum(self.smoke_history[-2].values())
        curr_total = sum(self.smoke_history[-1].values())
        growth = curr_total - prev_total
        return float(np.clip(growth / 5.0, 0.2, 1.0))

    def _lstm_corridor_density(self, d1: float, d2: float, velocity: float) -> float:
        """LSTM output: corridor density from adjacent room densities."""
        base = (d1 + d2) / 2.0
        temporal = min(len(self.smoke_history) / self.sequence_length, 1.0) * 0.1
        vel_contribution = velocity * 0.08
        noise = np.random.normal(0, 0.02)
        return float(np.clip(base + temporal + vel_contribution + noise, 0.0, 1.0))

    def _eta_to_dangerous(self, current_density: float, velocity: float) -> float:
        """Minutes until corridor density reaches DANGEROUS_DENSITY."""
        remaining = DANGEROUS_DENSITY - current_density
        if remaining <= 0:
            return 0.0
        rate_per_step = velocity * 0.18  # density increase per 30s step
        steps = remaining / max(rate_per_step, 0.01)
        return max(0.5, (steps * 30) / 60)  # convert to minutes
