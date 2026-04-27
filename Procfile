# Render / Railway / Heroku process file
# Uses Gunicorn with Uvicorn workers for async FastAPI support.
# PORT is automatically injected by Render as an environment variable.
web: gunicorn run:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --workers 2 --timeout 120
