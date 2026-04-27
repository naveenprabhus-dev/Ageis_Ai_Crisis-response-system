"""
Weather Module — Aegis AI
Fetches live weather from Open-Meteo (free, no API key).
Coordinates: Vijayawada, Andhra Pradesh (16.51°N, 80.64°E)
Translates WMO code + wind data → Aegis threat level.
"""
import asyncio
import httpx
from datetime import datetime
from typing import Dict

BASE_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=16.51&longitude=80.64"
    "&current_weather=true"
    "&hourly=weathercode,windspeed_10m,precipitation_probability,windgusts_10m"
    "&forecast_days=1"
)

WMO_DESCRIPTIONS = {
    range(0,  1):  "Clear sky",
    range(1,  4):  "Mainly clear / Partly cloudy",
    range(45, 50): "Fog",
    range(51, 56): "Drizzle - Light",
    range(56, 58): "Freezing Drizzle",
    range(61, 66): "Rain - Light to Heavy",
    range(71, 78): "Snow",
    range(80, 83): "Rain Showers",
    range(85, 87): "Snow Showers",
    range(95, 96): "Thunderstorm - Moderate",
    range(96, 100):"Thunderstorm with Hail",
}


def _wmo_description(code: int) -> str:
    for rng, desc in WMO_DESCRIPTIONS.items():
        if code in rng:
            return desc
    return f"Weather code {code}"


def _threat_level(code: int, wind: float, gusts: float, precip: float) -> Dict:
    if code >= 96 or (code >= 95 and gusts > 80):
        level, label, severity = 3, "CRITICAL", 5
    elif code >= 95 or wind > 60:
        level, label, severity = 3, "HIGH", 4
    elif code >= 80 or (code >= 51 and precip > 85):
        level, label, severity = 2, "ELEVATED", 3
    elif code >= 51:
        level, label, severity = 1, "MODERATE", 2
    else:
        level, label, severity = 0, "LOW", 1

    action = {
        3: "PRE-EMPTIVE EVACUATION RECOMMENDED",
        2: "ALERT GUESTS - MONITOR CLOSELY",
        1: "ADVISORY - OUTDOOR ROUTES FLAGGED",
        0: "NORMAL OPERATIONS",
    }[level]

    return {
        "level": level, "label": label, "severity": severity,
        "action": action,
        "cyclone_risk": wind > 60 or gusts > 80,
    }


class WeatherModule:
    def __init__(self):
        self._cache: Dict = {}
        self._last_fetch: float = 0.0
        self.POLL_INTERVAL = 900  # 15 minutes (Open-Meteo interval)

    async def get_threat(self) -> Dict:
        """Fetch from Open-Meteo and return structured threat object."""
        import time
        now = time.time()
        if self._cache and (now - self._last_fetch) < self.POLL_INTERVAL:
            return self._cache

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(BASE_URL)
                data = resp.json()

            cw = data.get("current_weather", {})
            hourly = data.get("hourly", {})
            code = int(cw.get("weathercode", 0))
            wind = float(cw.get("windspeed", 0))
            temp = float(cw.get("temperature", 28))

            # Get first hourly wind gust + precip probability
            gusts = float(hourly.get("windgusts_10m", [wind])[0])
            precip = float(hourly.get("precipitation_probability", [0])[0])

            threat = _threat_level(code, wind, gusts, precip)
            result = {
                "weathercode": code,
                "description": _wmo_description(code),
                "windspeed": wind,
                "windgusts_10m": gusts,
                "precipitation_probability": precip,
                "temperature": temp,
                "timestamp": datetime.now().isoformat(),
                **threat,
            }
            self._cache = result
            self._last_fetch = now
            return result

        except Exception as e:
            # Return last cache or safe fallback
            if self._cache:
                return self._cache
            return {
                "weathercode": 95, "description": "Thunderstorm (simulated)",
                "windspeed": 10.6, "windgusts_10m": 18.0,
                "precipitation_probability": 70, "temperature": 28.8,
                "level": 3, "label": "HIGH", "severity": 4,
                "action": "PRE-EMPTIVE EVACUATION RECOMMENDED",
                "cyclone_risk": False,
                "error": str(e), "timestamp": datetime.now().isoformat(),
            }
