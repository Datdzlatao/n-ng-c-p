"""
run.py — Entry point for development and production.
Usage:
  Development:   python run.py
  Production:    gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,   # Set to False in production
        log_level="info",
    )
