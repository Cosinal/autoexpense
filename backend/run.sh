#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Run FastAPI with hot reload
uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
