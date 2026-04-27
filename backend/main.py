"""
Aegis AI — Main Backend Server
FastAPI + WebSocket hub wiring all modules:
  AI Brain | LSTM Models | Camera Feed | Weather | Alert Engine | Queue Engine
"""
import asyncio
import json
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from task_engine import TaskEngine
from ai_brain import AiBrain
from camera_feed import CameraFeedSimulator
from weather_module import WeatherModule
from alert_engine import AlertEngine
from queue_engine import QueueEngine
from gemma_service import gemma
from scenario_engine import scenario_engine

class GuestSosRequest(BaseModel):
    floor: int
    room: str
    guest: str = "Guest"
    lang: str = "English"
    sos_message: str = ""

# ──────────────────────────────────────────────────────────────────────
#  App + Module Instances
# ──────────────────────────────────────────────────────────────────────
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="Aegis AI — Crisis Response Engine")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# Mount frontend
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

engine  = TaskEngine()
brain   = AiBrain()
camera  = CameraFeedSimulator()
weather = WeatherModule()
alerts  = AlertEngine()
queue   = QueueEngine()


# ──────────────────────────────────────────────────────────────────────
#  WebSocket Connection Manager
# ──────────────────────────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.gm:    list[WebSocket] = []
        self.staff: list[WebSocket] = []
        self.guest: list[WebSocket] = []
        self.staff_locations: dict = {}

    async def connect(self, ws: WebSocket, role: str):
        await ws.accept()
        getattr(self, role if role in ("gm", "staff", "guest") else "guest").append(ws)

    def disconnect(self, ws: WebSocket, role: str):
        pool = getattr(self, role if role in ("gm", "staff", "guest") else "guest")
        try: pool.remove(ws)
        except ValueError: pass

    async def broadcast(self, pool: list[WebSocket], msg: dict):
        text = json.dumps(msg)
        dead = []
        for ws in pool:
            try:   await ws.send_text(text)
            except: dead.append(ws)
        for ws in dead:
            try: pool.remove(ws)
            except ValueError: pass

    async def broadcast_gm(self, msg: dict): await self.broadcast(self.gm, msg)
    async def broadcast_staff(self, msg: dict): await self.broadcast(self.staff, msg)
    async def broadcast_guest(self, msg: dict): await self.broadcast(self.guest, msg)


manager = ConnectionManager()


# ──────────────────────────────────────────────────────────────────────
#  Background AI Brain Cycle (every 5 seconds)
# ──────────────────────────────────────────────────────────────────────
async def ai_brain_cycle():
    """Main AI processing loop — runs every 5 seconds."""
    while True:
        try:
            # Advance Scenario Timeline
            scenario_engine.cycle += 1
            engine.process_timeline_events(scenario_engine.cycle)

            # Sync Virtual Staff to Connection Manager if needed
            if not manager.staff_locations and hasattr(engine, "staff_locations"):
                manager.staff_locations.update(engine.staff_locations)

            # Gather all modality data
            wx_data     = await weather.get_threat()
            camera_data = camera.get_all_feeds(engine.people_tracking)
            hotel_data  = engine.get_full_hotel()
            staff_data  = {"staff_locations": manager.staff_locations}
            sos_events  = engine.get_recent_sos()

            # Update camera simulator with current fire zones
            fire_zones = engine.get_fire_zones()
            camera.set_crisis_zones(fire_zones)

            # Run AI Brain
            assessment = brain.analyze(
                vision_data  = camera_data,
                hotel_data   = hotel_data,
                weather_data = wx_data,
                staff_data   = staff_data,
                sos_events   = sos_events,
            )

            # Update people movement based on AI decisions
            for decision in assessment.get("rescue_decisions", []):
                engine.set_person_mode(decision["room"], decision["rescue_mode"])
            
            engine.update_people_movement(assessment.get("smoke_spread", {}).get("blocked_corridors", []))
            
            people_list = list(engine.people_tracking.values())

            # Push full assessment to GM dashboard
            await manager.broadcast_gm({
                "type":       "AI_ASSESSMENT",
                "assessment": assessment,
                "stats":      engine.get_gm_stats(),
                "camera":     camera_data,
                "weather":    wx_data,
                "log":        brain.get_log()[:10],
                "tactical_data": engine.get_all_staff_tactical_data({
                    "fire_zones": assessment["fire_spread"]["actual_fire_zones"],
                    "blocked_corridors": assessment["smoke_spread"]["blocked_corridors"],
                    "fire_etas": assessment["fire_spread"]["etas"]
                })
            })

            # Broadcast people locations
            await manager.broadcast_gm({
                "type": "PEOPLE_UPDATE",
                "people": people_list
            })
            await manager.broadcast_guest({
                "type": "PEOPLE_UPDATE",
                "people": people_list
            })

            # Sync Guest App
            await manager.broadcast_guest({
                "type": "AI_ASSESSMENT",
                "assessment": assessment
            })

            # Sync Staff App
            await manager.broadcast_staff({
                "type": "AI_ASSESSMENT",
                "assessment": assessment,
                "tactical_data": engine.get_all_staff_tactical_data({
                    "fire_zones": assessment["fire_spread"]["actual_fire_zones"],
                    "blocked_corridors": assessment["smoke_spread"]["blocked_corridors"],
                    "fire_etas": assessment["fire_spread"]["etas"]
                })
            })

        except Exception as e:
            import traceback
            print(f"[Brain Cycle Error] {e}")
            traceback.print_exc()

        await asyncio.sleep(5)


@app.on_event("startup")
async def startup():
    #asyncio.create_task(ai_brain_cycle())
    print("[Aegis AI] Backend online — AI brain cycle started.")


# ──────────────────────────────────────────────────────────────────────
#  Health
# ──────────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"message": "Aegis AI Enterprise Orchestrator Online", "version": "2.0"}


# ──────────────────────────────────────────────────────────────────────
#  Guest Endpoints
# ──────────────────────────────────────────────────────────────────────
@app.post("/guest/sos")
async def guest_sos(req: GuestSosRequest):
    task = engine.create_task(req.floor, req.room, req.guest, req.sos_message, req.lang)
    if task:
        queued = await queue.enqueue(task)
        exit_label, exit_path = engine._best_exit(req.room)
        guest_msg  = alerts.guest_alert("evacuate", req.lang, req.room, req.floor, exit_label)
        await manager.broadcast_gm({"type": "GUEST_SOS", "data": queued})
        await manager.broadcast_guest({
            "type": "ALERT", "room": req.room, "floor": req.floor,
            "message": guest_msg, "exit_route": exit_label,
            "exit_path": exit_path
        })
        return {"status": "SOS_RECEIVED", "task": queued, "message": guest_msg, "exit_path": exit_path}
    return JSONResponse({"status": "ERROR", "message": "Invalid floor/room"}, 400)


# ──────────────────────────────────────────────────────────────────────
#  Staff Endpoints
# ──────────────────────────────────────────────────────────────────────
@app.get("/staff/{staff_id}/next_task")
async def get_task(staff_id: str):
    task = await queue.dequeue_next(staff_id)
    if not task:
        task = engine.get_next_task(staff_id)
    if task:
        task["radio_script"] = alerts.staff_script(task)
        await manager.broadcast_gm({"type": "STAFF_DEPLOYED", "data": task})
        await manager.broadcast_guest({"type": "STAFF_DEPLOYED", "data": task})
        return task
    return {"message": "No pending tasks."}

@app.post("/staff/{staff_id}/reached")
async def staff_reached_guest(staff_id: str):
    task = engine.staff_assignments.get(staff_id)
    if task:
        payload = {"type": "STAFF_REACHED", "staff_id": staff_id, "room": task["room"]}
        await manager.broadcast_gm(payload)
        await manager.broadcast_guest(payload)
        return {"status": "success"}
    return JSONResponse({"status": "error", "message": "No active task"}, 400)

@app.post("/staff/{staff_id}/complete")
async def complete_task(staff_id: str):
    task = await queue.complete(staff_id)
    if not task:
        task = engine.complete_task(staff_id)
    if task:
        stats = engine.get_gm_stats()
        payload = {
            "type": "RESCUE_SUCCESS",
            "task": task, "stats": stats,
            "queue": queue.get_stats(),
        }
        await manager.broadcast_gm(payload)
        await manager.broadcast_guest(payload)
        return {"status": "success", "task": task}
    return JSONResponse({"status": "error", "message": "No active task"}, 400)

class LocationModel(BaseModel):
    floor: int
    room: str

@app.post("/staff/{staff_id}/location")
async def update_staff_location(staff_id: str, loc: LocationModel):
    manager.staff_locations[staff_id] = {"floor": loc.floor, "room": loc.room}
    await manager.broadcast_guest({
        "type": "STAFF_LOCATION",
        "staff_id": staff_id,
        "location": {"floor": loc.floor, "room": loc.room}
    })
    return {"status": "success"}


# ──────────────────────────────────────────────────────────────────────
#  Simulation Endpoint
# ──────────────────────────────────────────────────────────────────────
class CrisisModel(BaseModel):
    floor: int
    room: str
    guest: str
    sos_message: str = ""

@app.get("/simulate")
async def simulate():
    """
    Cloud-compatible simulation endpoint.
    Runs one full AI brain assessment cycle and returns the result as JSON.
    Useful for health-checks, demos, and integration tests on Render / Cloud Run.
    """
    wx_data     = await weather.get_threat()
    camera_data = camera.get_all_feeds(engine.people_tracking)
    hotel_data  = engine.get_full_hotel()
    fire_zones  = engine.get_fire_zones()
    camera.set_crisis_zones(fire_zones)

    assessment = brain.analyze(
        vision_data  = camera_data,
        hotel_data   = hotel_data,
        weather_data = wx_data,
        staff_data   = {"staff_locations": manager.staff_locations},
        sos_events   = engine.get_recent_sos(),
    )
    return JSONResponse({
        "status":     "ok",
        "assessment": assessment,
        "stats":      engine.get_gm_stats(),
        "weather":    wx_data,
        "queue":      queue.get_stats(),
    })


@app.post("/simulate/crisis")
async def simulate_crisis(crisis: CrisisModel):
    # Pass raw message through Gemma AI for language detection and translation
    analysis = gemma.analyze_sos(crisis.sos_message)
    
    task = engine.create_task(
        floor=crisis.floor, 
        room_id=crisis.room, 
        guest_name=crisis.guest, 
        sos_message=crisis.sos_message,
        detected_language=analysis["detected_language"],
        english_translation=analysis["english_translation"],
        sentiment=analysis.get("sentiment", "Urgent"),
        reasoning=analysis.get("reasoning", "")
    )
    if task:
        queued = await queue.enqueue(task)
        await manager.broadcast_gm({"type": "CRISIS_DETECTED", "data": queued})
        return queued
    return JSONResponse({"error": "Could not create task"}, 400)


# ──────────────────────────────────────────────────────────────────────
#  AI Brain Endpoints
# ──────────────────────────────────────────────────────────────────────
@app.get("/ai/assessment")
async def get_assessment():
    wx_data     = await weather.get_threat()
    camera_data = camera.get_all_feeds(engine.people_tracking)
    hotel_data  = engine.get_full_hotel()
    fire_zones  = engine.get_fire_zones()
    camera.set_crisis_zones(fire_zones)
    return brain.analyze(
        vision_data  = camera_data,
        hotel_data   = hotel_data,
        weather_data = wx_data,
        staff_data   = {"staff_locations": manager.staff_locations},
        sos_events   = engine.get_recent_sos(),
    )

@app.get("/ai/evacuation_routes/{floor}")
async def get_evac_routes(floor: int):
    return engine.get_evacuation_routes(floor)

@app.get("/ai/log")
async def get_ai_log():
    return {"log": brain.get_log()}


# ──────────────────────────────────────────────────────────────────────
#  Camera & Weather Endpoints
# ──────────────────────────────────────────────────────────────────────
@app.get("/camera/feeds")
async def get_camera_feeds():
    fire_zones = engine.get_fire_zones()
    camera.set_crisis_zones(fire_zones)
    return camera.get_all_feeds(engine.people_tracking)

@app.get("/camera/floor/{floor_num}")
async def get_floor_camera(floor_num: int):
    return camera.get_floor_feed(floor_num)

@app.get("/weather/threat")
async def get_weather():
    return await weather.get_threat()


# ──────────────────────────────────────────────────────────────────────
#  Floor Layout
# ──────────────────────────────────────────────────────────────────────
@app.get("/floor/{floor_num}/layout")
async def get_floor_layout(floor_num: int):
    return engine.get_floor_layout(floor_num)

@app.get("/hotel/layout")
async def get_hotel_layout():
    return engine.get_full_hotel()


# ──────────────────────────────────────────────────────────────────────
#  Queue Stats
# ──────────────────────────────────────────────────────────────────────
@app.get("/queue/stats")
async def get_queue_stats():
    return queue.get_stats()


# ──────────────────────────────────────────────────────────────────────
#  Multilingual Alerts
# ──────────────────────────────────────────────────────────────────────
@app.get("/alerts/broadcast/{floor}")
async def broadcast_alert(floor: int, alert_type: str = "fire_alert"):
    return alerts.broadcast_message(alert_type, floor)


# ──────────────────────────────────────────────────────────────────────
#  Two-Way Communication Hub
# ──────────────────────────────────────────────────────────────────────
class GuestMessage(BaseModel):
    room: str
    lang: str
    text: str

class StaffMessage(BaseModel):
    staff_id: str
    room: str
    lang: str
    text: str

@app.post("/comms/guest_to_staff")
async def guest_to_staff(msg: GuestMessage):
    # Translate to English
    english_text = gemma.translate_to_english(msg.text, msg.lang)
    
    payload = {
        "type": "GUEST_MESSAGE",
        "room": msg.room,
        "original_text": msg.text,
        "translated_text": english_text,
        "timestamp": datetime.now().isoformat()
    }
    await manager.broadcast_staff(payload)
    await manager.broadcast_gm(payload)
    return {"status": "sent"}

@app.post("/comms/staff_to_guest")
async def staff_to_guest(msg: StaffMessage):
    # Translate to Guest Language
    translated_text = gemma.translate_to_guest(msg.text, msg.lang)
    
    payload = {
        "type": "STAFF_MESSAGE",
        "staff_id": msg.staff_id,
        "room": msg.room,
        "original_text": msg.text,
        "translated_text": translated_text,
        "timestamp": datetime.now().isoformat()
    }
    await manager.broadcast_guest(payload)
    await manager.broadcast_gm(payload)
    return {"status": "sent"}
    
@app.post("/comms/detect_lang")
async def detect_lang(msg: dict):
    text = msg.get("text", "")
    lang = gemma.detect_language(text)
    return {"detected_language": lang}



# ──────────────────────────────────────────────────────────────────────
#  WebSocket Hub
# ──────────────────────────────────────────────────────────────────────
@app.websocket("/ws/{role}")
async def websocket_endpoint(ws: WebSocket, role: str):
    await manager.connect(ws, role)
    try:
        if role == "gm":
            wx = await weather.get_threat()
            await ws.send_text(json.dumps({
                "type": "SYNC",
                "stats":    engine.get_gm_stats(),
                "weather":  wx,
                "queue":    queue.get_stats(),
                "log":      brain.get_log()[:5],
            }))
        while True:
            data = await ws.receive_text()
            msg  = json.loads(data)
            if msg.get("type") == "LOCATION_UPDATE":
                sid = msg["staff_id"]
                manager.staff_locations[sid] = msg["location"]
                await manager.broadcast_gm({
                    "type": "STAFF_LOCATION",
                    "staff_id": sid,
                    "location": msg["location"],
                })
    except WebSocketDisconnect:
        manager.disconnect(ws, role)
