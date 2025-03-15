#!/bin/bash
set -e

# Navigate to the backend directory
cd /opt/prodizy-platform/backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
  python3.11 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
pip install -r ../requirements.txt

# Copy systemd service
sudo cp /opt/prodizy-platform/deployment/config/systemd/prodizy-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable prodizy-api


# Restart the service
sudo systemctl restart prodizy-api