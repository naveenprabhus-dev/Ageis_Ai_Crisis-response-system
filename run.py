"""
╔══════════════════════════════════════════════════════════╗
║          AEGIS AI — Cloud Entrypoint (run.py)            ║
║  Exposes the FastAPI app for Gunicorn / Uvicorn to use   ║
║                                                          ║
║  Cloud deployment (Render, Cloud Run, Railway …):        ║
║    gunicorn run:app -k uvicorn.workers.UvicornWorker     ║
║                                                          ║
║  Local development:                                      ║
║    uvicorn run:app --reload --port 8000                  ║
║    python run.py   (dev convenience wrapper)             ║
╚══════════════════════════════════════════════════════════╝
"""
import os
import sys

# ── Re-export the FastAPI app so Gunicorn can find it as `run:app` ──────────
# Gunicorn / Uvicorn expects a module-level `app` object.
from backend.main import app  # noqa: F401  (re-export)

# ── Health-check convenience endpoint (already defined in backend/main.py) ──
# GET /  →  {"message": "Aegis AI Enterprise Orchestrator Online", "version": "2.0"}
# GET /simulate  →  wraps existing /ai/assessment as a named simulate endpoint
# Both are defined in backend/main.py; nothing extra needed here.


# ── Dev convenience: `python run.py` starts the server directly ─────────────
if __name__ == "__main__":
    import uvicorn

    # Read PORT from environment (Render / Cloud Run inject this)
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")

    # Detect if we are running locally (not inside a container / cloud env)
    is_local = not os.environ.get("RENDER") and not os.environ.get("K_SERVICE")

    print("+----------------------------------------------------------+")
    print("|               AEGIS AI -- CLOUD ENTRYPOINT               |")
    print("+----------------------------------------------------------+")
    print(f"  Host : {host}")
    print(f"  Port : {port}")
    print(f"  Mode : {'local-dev (reload on)' if is_local else 'production'}")
    print()

    uvicorn.run(
        "run:app",
        host=host,
        port=port,
        reload=is_local,   # --reload only in local dev, never in production
        log_level="info",
    )
