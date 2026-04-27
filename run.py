"""
╔══════════════════════════════════════════════════════════╗
║            AEGIS AI — Master Launcher (run.py)           ║
║  Starts the FastAPI backend + Unified Simulator in one   ║
╚══════════════════════════════════════════════════════════╝

Usage:
    python run.py              # Start backend only (open browser manually)
    python run.py --sim        # Start backend + auto simulation
    python run.py --sim --mode staff   # Backend + only staff tracker
    python run.py --sim --mode crisis  # Backend + only crisis injector
    python run.py --sim --mode load    # Backend + load test
"""
import subprocess
import asyncio
import sys
import os
import time
import argparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

APPS = {
    "GM Command Hub":       "http://localhost:8000/static/gm-app/index.html",
    "Guest Safety Portal":  "http://localhost:8000/static/guest-app/index.html",
    "Staff Operations":     "http://localhost:8000/static/staff-app/tasks.html",
}

def banner():
    print("+----------------------------------------------------------+")
    print("|               AEGIS AI -- MASTER LAUNCHER                |")
    print("+----------------------------------------------------------+")
    print("  App URLs:")
    for name, url in APPS.items():
        print(f"   [LINK] {name}")
        print(f"      {url}")
    print()

def start_backend():
    """Start the uvicorn backend server as a subprocess."""
    print("\033[92m[LAUNCHER] Starting Aegis AI Backend...\033[0m")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app",
         "--reload", "--port", "8000", "--host", "0.0.0.0"],
        cwd=BASE_DIR,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    return proc

def wait_for_backend(timeout=30):
    """Poll until the backend is accepting connections."""
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen("http://localhost:8000/", timeout=2)
            return True
        except Exception:
            time.sleep(1)
    return False

def start_simulator(mode=None):
    """Launch the unified simulator as a subprocess."""
    cmd = [sys.executable, "unified_simulator.py", "--auto"]
    print(f"\033[96m[LAUNCHER] Starting Unified Simulator: {' '.join(cmd)}\033[0m")
    return subprocess.Popen(cmd, cwd=BASE_DIR)

def main():
    parser = argparse.ArgumentParser(description="Aegis AI Master Launcher")
    parser.add_argument("--sim",   action="store_true", help="Also run the unified simulator")
    parser.add_argument("--mode",  choices=["crisis", "staff", "load", "auto"], default="auto",
                        help="Simulator mode (default: auto)")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser tabs")
    args = parser.parse_args()

    banner()
    
    # Start backend
    backend_proc = start_backend()

    # Wait for backend to be ready
    print("[LAUNCHER] Waiting for backend to come online...")
    if not wait_for_backend(timeout=40):
        print("\033[91m[LAUNCHER] Backend failed to start within 40s. Check for errors above.\033[0m")
        backend_proc.terminate()
        sys.exit(1)

    print("[LAUNCHER] [OK] Backend is online!\n")

    # Open browser
    if not args.no_browser:
        import webbrowser
        for name, url in APPS.items():
            print(f"  Opening {name}...")
            webbrowser.open(url)
            time.sleep(0.5)

    sim_proc = None
    if args.sim:
        time.sleep(2)  # Small delay to let backend fully settle
        mode = None if args.mode == "auto" else args.mode
        sim_proc = start_simulator(mode)

    print("\n\033[93m[LAUNCHER] All systems running. Press Ctrl+C to stop.\033[0m")
    try:
        backend_proc.wait()
    except KeyboardInterrupt:
        print("\n\033[93m[LAUNCHER] Shutting down all processes...\033[0m")
        backend_proc.terminate()
        if sim_proc:
            sim_proc.terminate()
        print("[LAUNCHER] [OK] Shutdown complete.")

if __name__ == "__main__":
    main()
