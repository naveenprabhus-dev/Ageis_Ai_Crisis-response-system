"""
LSTM Evacuation Time Predictor — Aegis AI
Predicts time (minutes) to fully evacuate each floor given:
  - Occupancy count
  - Available exit routes (not blocked by smoke/fire)
  - Staff rescuers assigned to floor
  - Time already elapsed in evacuation
Sequence length: 5 steps (rolling window as evacuation progresses).
"""
import numpy as np
from typing import Dict, List


FLOORS = 5
ROOMS_PER_FLOOR = 10
SEQUENCE_LENGTH = 5

# Hotel exit capacity: each floor has 2 stairwell exits
EXITS_PER_FLOOR = 2
# People per minute that can pass through one exit (safe flow rate)
EXIT_FLOW_RATE = 4  # people/min per exit


class LSTMEvacTime:
    def __init__(self):
        self.sequence_length = SEQUENCE_LENGTH
        self.evac_history: List[Dict[int, Dict]] = []

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #
    def predict(
        self,
        occupancy_per_floor: Dict[int, int],
        blocked_corridors: List[str],
        staff_per_floor: Dict[int, int],
        time_elapsed_min: float = 0.0,
        already_evacuated_per_floor: Dict[int, int] = None,
    ) -> Dict:
        """
        LSTM inference: predict evacuation time per floor.
        Returns:
            evac_times        — { floor: minutes_to_clear }
            priority_order    — floors sorted worst-first
            total_evac_time   — max across all floors
            floor_summaries   — detailed breakdown per floor
        """
        if already_evacuated_per_floor is None:
            already_evacuated_per_floor = {}

        state = self._build_state(
            occupancy_per_floor, blocked_corridors, staff_per_floor,
            time_elapsed_min, already_evacuated_per_floor
        )
        self.evac_history.append(state)
        if len(self.evac_history) > self.sequence_length:
            self.evac_history.pop(0)

        temporal_factor = self._temporal_learning_factor()
        evac_times: Dict[int, float] = {}
        floor_summaries: Dict[int, Dict] = {}

        for floor in range(0, FLOORS):
            remaining_people = max(
                0,
                occupancy_per_floor.get(floor, 0) - already_evacuated_per_floor.get(floor, 0)
            )
            if remaining_people == 0:
                evac_times[floor] = 0.0
                floor_summaries[floor] = {
                    "floor": floor, "remaining": 0,
                    "evac_time_min": 0.0, "status": "CLEAR"
                }
                continue

            # Effective exits = exits not blocked by smoke on this floor
            blocked_on_floor = sum(
                1 for c in blocked_corridors if c.startswith(f"F{floor}-")
            )
            effective_exits = max(1, EXITS_PER_FLOOR - (blocked_on_floor // 3))

            # Staff multiplier: each staff member speeds evac by 30%
            staff = staff_per_floor.get(floor, 0)
            staff_multiplier = 1.0 + (staff * 0.30)

            # LSTM-simulated evacuation time
            base_time = remaining_people / (EXIT_FLOW_RATE * effective_exits * staff_multiplier)
            # Temporal adjustment: LSTM learns improving evacuation pace
            adjusted_time = base_time * (1.0 - temporal_factor * 0.15)
            # Add congestion overhead for large crowds
            if remaining_people > 6:
                adjusted_time *= 1.20
            # Add noise (LSTM stochasticity)
            adjusted_time += np.random.normal(0, 0.3)
            adjusted_time = max(0.5, round(adjusted_time, 1))

            evac_times[floor] = adjusted_time
            floor_summaries[floor] = {
                "floor": floor,
                "remaining": remaining_people,
                "evac_time_min": adjusted_time,
                "effective_exits": effective_exits,
                "staff_assigned": staff,
                "status": "CRITICAL" if adjusted_time > 10 else ("HIGH" if adjusted_time > 5 else "MANAGEABLE"),
            }

        # Sort floors by urgency (longest evacuation time first)
        priority_order = sorted(evac_times, key=lambda f: evac_times[f], reverse=True)
        total_time = max(evac_times.values()) if evac_times else 0.0

        return {
            "evac_times": {f: evac_times[f] for f in range(0, FLOORS)},
            "priority_order": priority_order,
            "total_evac_time": round(total_time, 1),
            "floor_summaries": floor_summaries,
            "temporal_factor": round(temporal_factor, 2),
        }

    # ------------------------------------------------------------------ #
    #  Internal LSTM-Simulated Computations                               #
    # ------------------------------------------------------------------ #
    def _build_state(
        self, occupancy, blocked_corridors, staff_per_floor,
        time_elapsed, already_evacuated
    ) -> Dict[int, Dict]:
        state = {}
        for floor in range(0, FLOORS):
            state[floor] = {
                "remaining": max(0, occupancy.get(floor, 0) - already_evacuated.get(floor, 0)),
                "blocked_count": sum(1 for c in blocked_corridors if c.startswith(f"F{floor}-")),
                "staff": staff_per_floor.get(floor, 0),
                "time_elapsed": time_elapsed,
            }
        return state

    def _temporal_learning_factor(self) -> float:
        """
        LSTM hidden state approximation:
        As more time steps are observed, the model 'learns' the evacuation pace.
        Returns a factor 0.0–1.0 representing accumulated temporal knowledge.
        """
        return min(len(self.evac_history) / self.sequence_length, 1.0)
