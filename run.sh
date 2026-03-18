#!/bin/bash
# Launch Peter Brand Draft Planner

cd "$(dirname "$0")"
source .venv/bin/activate
streamlit run app/main.py --server.port 8501
