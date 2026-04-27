import asyncio
import websockets
import json

async def test():
    async with websockets.connect('ws://localhost:8000/ws/gm') as ws:
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            if data.get('type') == 'AI_ASSESSMENT':
                zones = data.get('assessment', {}).get('high_alert_zones', [])
                print(f"HIGH_ALERT_ZONES: {zones}")
                break

asyncio.run(test())
