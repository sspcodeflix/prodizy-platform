#!/bin/bash

# This script starts all components in separate terminal windows/tabs

# Make all scripts executable
chmod +x scripts/start_mlflow.sh
chmod +x scripts/start_fastapi.sh
chmod +x scripts/start_streamlit.sh

# Display the service configuration
echo "=== Prodizy Platform Configuration ==="
echo "MLflow server:  $(grep MLFLOW_TRACKING_URI .env | cut -d '=' -f2)"
echo "FastAPI server: $(grep BACKEND_API_URL .env | cut -d '=' -f2)"
echo "=================================="

# Detect the operating system and terminal
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "Detected macOS. Starting services in new Terminal tabs..."
    osascript -e 'tell application "Terminal" to do script "cd \"'$PWD'\" && ./scripts/start_mlflow.sh"'
    sleep 2
    osascript -e 'tell application "Terminal" to do script "cd \"'$PWD'\" && ./scripts/start_fastapi.sh"'
    sleep 2
    osascript -e 'tell application "Terminal" to do script "cd \"'$PWD'\" && ./scripts/start_streamlit.sh"'
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v gnome-terminal &>/dev/null; then
        echo "Detected Linux with gnome-terminal. Starting services in new terminal windows..."
        gnome-terminal -- bash -c "cd '$PWD' && ./scripts/start_mlflow.sh; exec bash"
        sleep 2
        gnome-terminal -- bash -c "cd '$PWD' && ./scripts/start_fastapi.sh; exec bash"
        sleep 2
        gnome-terminal -- bash -c "cd '$PWD' && ./scripts/start_streamlit.sh; exec bash"
    elif command -v xterm &>/dev/null; then
        echo "Detected Linux with xterm. Starting services in new terminal windows..."
        xterm -e "cd '$PWD' && ./scripts/start_mlflow.sh" &
        sleep 2
        xterm -e "cd '$PWD' && ./scripts/start_fastapi.sh" &
        sleep 2
        xterm -e "cd '$PWD' && ./scripts/start_streamlit.sh" &
    else
        echo "Unable to detect a supported terminal emulator on Linux."
        echo "Please run each script manually in separate terminals:"
        echo "  ./scripts/start_mlflow.sh"
        echo "  ./scripts/start_fastapi.sh"
        echo "  ./scripts/start_streamlit.sh"
    fi
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows with Git Bash or similar
    echo "Detected Windows. Starting services in new Command Prompt windows..."
    start cmd /k "cd %CD% && bash scripts/start_mlflow.sh"
    sleep 2
    start cmd /k "cd %CD% && bash scripts/start_fastapi.sh"
    sleep 2
    start cmd /k "cd %CD% && bash scripts/start_streamlit.sh"
else
    echo "Unable to detect a supported operating system."
    echo "Please run each script manually in separate terminals:"
    echo "  ./scripts/start_mlflow.sh"
    echo "  ./scripts/start_fastapi.sh"
    echo "  ./scripts/start_streamlit.sh"
fi

echo "All services have been started in separate terminal windows."
echo "To stop the services, close each terminal window or press Ctrl+C in each window."