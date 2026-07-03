#!/bin/bash

# Run the FastAPI server with uvicorn
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
