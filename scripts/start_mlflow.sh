#!/bin/bash

# Load MLflow server port from .env file
MLFLOW_PORT=5000
MLFLOW_URI=$(grep MLFLOW_TRACKING_URI .env | cut -d '=' -f2 || echo "http://127.0.0.1:5000")
MLFLOW_PORT=$(echo $MLFLOW_URI | grep -oE '[0-9]+' | tail -1)

echo "=== Starting MLflow Tracking Server ==="
echo "MLflow URI: $MLFLOW_URI"
echo "MLflow Port: $MLFLOW_PORT"
echo "==================================="

# Check if MLflow port is already in use
if lsof -i:"$MLFLOW_PORT" > /dev/null; then
    echo "⚠️  Warning: Port $MLFLOW_PORT is already in use!"
    echo "This might mean MLflow is already running, or another process is using this port."
    echo "To find the process: lsof -i:$MLFLOW_PORT"
    echo "To kill the process: kill \$(lsof -t -i:$MLFLOW_PORT)"
    exit 1
fi

# Start MLflow server
echo "Starting MLflow server on port $MLFLOW_PORT..."
mlflow server --host 127.0.0.1 --port $MLFLOW_PORT

# Note: This script will keep running until MLflow is stopped with Ctrl+C