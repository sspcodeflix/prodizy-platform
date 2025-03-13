#!/bin/bash

# Display the FastAPI configuration
echo "=== Starting FastAPI Backend ==="
echo "FastAPI server: $(grep BACKEND_API_URL .env | cut -d '=' -f2)"
echo "==========================="

# Check if any process is already using the FastAPI port
API_PORT=$(grep API_PORT .env | cut -d '=' -f2 || echo "5003")
if lsof -i:"$API_PORT" > /dev/null; then
    echo "⚠️  Warning: Port $API_PORT is already in use!"
    echo "Please choose a different port in .env or terminate the process using this port."
    echo "To find the process: lsof -i:$API_PORT"
    echo "To kill the process: kill \$(lsof -t -i:$API_PORT)"
    exit 1
fi

# Set PYTHONPATH to include project root
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Start the backend
echo "Starting FastAPI backend on port $API_PORT..."
cd backend
python main.py

# Note: This script will keep running until FastAPI is stopped with Ctrl+C