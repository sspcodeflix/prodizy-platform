#!/bin/bash

# Display the Streamlit configuration
echo "=== Starting Streamlit Frontend ==="
echo "Backend API URL: $(grep BACKEND_API_URL .env | cut -d '=' -f2)"
echo "============================"

# Set PYTHONPATH to include project root (needed for any imports)
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Start the Streamlit frontend
echo "Starting Streamlit frontend..."
cd frontend
streamlit run app.py

# Note: This script will keep running until Streamlit is stopped with Ctrl+C