"""
Async Priority Task Queue — Aegis AI
Handles N simultaneous crisis inputs without congestion.
Priority: RED (< 5 min impact) → YELLOW → GREEN
Dead-letter queue for timed-out tasks.
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque
import uuid


class QueueEngine:
    """
    asyncio-based priority task queue.
    Supports concurrent enqueue from any number of sources simultaneously.
    """

    def __init__(self):
        # Three priority buckets: 0=RED, 1=YELLOW, 2=GREEN
        self._queues: Dict[int, asyncio.Queue] = {
            0: asyncio.Queue(),
            1: asyncio.Queue(),
            2: asyncio.Queue(),
        }
        self._active: Dict[str, Dict] = {}      # staff_id → task
        self._completed: deque = deque(maxlen=200)
        self._dead_letter: List[Dict] = []
        self._stats = {"enqueued": 0, "completed": 0, "dead_letter": 0}
        self._lock = asyncio.Lock()

    # ──────────────────────────────────────────────────────────────────
    #  Enqueue (thread-safe, handles N concurrent inputs)
    # ──────────────────────────────────────────────────────────────────
    async def enqueue(self, task: Dict) -> Dict:
        """
        Add a crisis task to the appropriate priority queue.
        Assigns priority based on predicted_impact_mins.
        Returns enriched task with queue_id.
        """
        impact = task.get("predicted_impact_mins", 10)
        if impact < 5:    priority, priority_label = 0, "RED"
        elif impact < 10: priority, priority_label = 1, "YELLOW"
        else:             priority, priority_label = 2, "GREEN"

        enriched = {
            **task,
            "queue_id":      str(uuid.uuid4())[:8],
            "priority":      priority_label,
            "priority_level": priority,
            "queued_at":     datetime.now().isoformat(),
            "status":        "QUEUED",
        }
        async with self._lock:
            await self._queues[priority].put(enriched)
            self._stats["enqueued"] += 1
        return enriched

    # ──────────────────────────────────────────────────────────────────
    #  Dequeue (highest priority first)
    # ──────────────────────────────────────────────────────────────────
    async def dequeue_next(self, staff_id: str) -> Optional[Dict]:
        """
        Assign the highest-priority available task to a staff member.
        Returns None if no tasks available or staff already assigned.
        """
        if staff_id in self._active:
            return self._active[staff_id]

        for priority in (0, 1, 2):
            q = self._queues[priority]
            if not q.empty():
                try:
                    task = q.get_nowait()
                    task["status"] = "IN_PROGRESS"
                    task["assigned_to"] = staff_id
                    task["started_at"] = datetime.now().isoformat()
                    async with self._lock:
                        self._active[staff_id] = task
                    return task
                except asyncio.QueueEmpty:
                    continue
        return None

    # ──────────────────────────────────────────────────────────────────
    #  Complete
    # ──────────────────────────────────────────────────────────────────
    async def complete(self, staff_id: str) -> Optional[Dict]:
        """Mark active task as completed."""
        async with self._lock:
            task = self._active.pop(staff_id, None)
        if task:
            task["status"] = "COMPLETED"
            task["completed_at"] = datetime.now().isoformat()
            self._completed.appendleft(task)
            self._stats["completed"] += 1
        return task

    # ──────────────────────────────────────────────────────────────────
    #  Dead Letter (timeout handling)
    # ──────────────────────────────────────────────────────────────────
    async def sweep_dead_letter(self, timeout_minutes: float = 15.0):
        """Move timed-out active tasks to dead-letter queue."""
        now = datetime.now()
        dead = []
        async with self._lock:
            for sid, task in list(self._active.items()):
                started = datetime.fromisoformat(task.get("started_at", now.isoformat()))
                elapsed = (now - started).total_seconds() / 60
                if elapsed > timeout_minutes:
                    task["status"] = "TIMEOUT"
                    task["timed_out_at"] = now.isoformat()
                    dead.append((sid, task))
            for sid, task in dead:
                del self._active[sid]
                self._dead_letter.append(task)
                self._stats["dead_letter"] += 1
        return [t for _, t in dead]

    # ──────────────────────────────────────────────────────────────────
    #  Stats
    # ──────────────────────────────────────────────────────────────────
    def get_stats(self) -> Dict:
        return {
            "queued_red":    self._queues[0].qsize(),
            "queued_yellow": self._queues[1].qsize(),
            "queued_green":  self._queues[2].qsize(),
            "active":        len(self._active),
            "completed":     self._stats["completed"],
            "total_enqueued": self._stats["enqueued"],
            "dead_letter":   self._stats["dead_letter"],
        }

    def get_completed(self) -> List[Dict]:
        return list(self._completed)[:20]

    def pending_count(self) -> int:
        return sum(q.qsize() for q in self._queues.values())
