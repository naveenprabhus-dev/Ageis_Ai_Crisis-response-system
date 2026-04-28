import os
import sys

# Ensure the backend directory is in the path
_backend_dir = os.path.join(os.path.dirname(__file__), "backend")
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from main import app  # noqa: F401

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Aegis AI Backend is alive and reachable"}

@app.get("/")
async def root_check():
    return {"message": "Aegis AI Enterprise Orchestrator Online", "status": "active"}
