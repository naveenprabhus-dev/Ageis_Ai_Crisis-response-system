import sys
sys.path.append('.')
from ai_brain import AiBrain
from task_engine import TaskEngine

te = TaskEngine()
# Mock some events to set the stage
te.process_timeline_events(0)

# trigger SOS for room 108
te.create_task(floor=1, room_id='108', guest_name='Healthy Guest', sos_message='Help')

hotel_data = te.get_full_hotel()
brain = AiBrain()

# We need some dummy data to pass to brain.analyze
# Simulate fire in room 101, making floor 1 high risk
vision_data = {'detections': [{'zone': '101', 'label': 'fire', 'confidence': 0.9}]}
weather_data = {}
staff_data = {'staff_locations': {'S1': {'floor': 1, 'room': '001'}, 'S2': {'floor': 1, 'room': '002'}}}
sos_events = te.get_recent_sos()

res = brain.analyze(vision_data, hotel_data, weather_data, staff_data, sos_events)

print("\n--- Rescue Decisions ---")
for dec in res.get('rescue_decisions', []):
    if dec['room'] in ('101', '105', '108'):
        print(f"Room {dec['room']}: {dec['rescue_mode']} (Rationale: {dec['rationale'][:50]}...)")

print("\n--- Risk Scores ---")
print(f"Floor 1 Risk: {res['zone_risk_scores'].get(1)}")
