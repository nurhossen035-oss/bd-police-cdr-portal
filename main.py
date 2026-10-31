"""Compatibility launcher for the FastAPI application.

Use `uvicorn api:app --host 0.0.0.0 --port $PORT` on Render,
or `python main.py` for local testing.
"""
import os
import uvicorn
from api import app

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=False)
