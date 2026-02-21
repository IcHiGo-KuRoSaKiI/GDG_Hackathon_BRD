#!/bin/bash
# Startup script for BRD Generator backend
#
# Usage: ./run.sh

# Activate virtual environment
source venv/bin/activate

# Run FastAPI with uvicorn
# Note: Must run from parent directory to fix relative imports
cd ..
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8080
