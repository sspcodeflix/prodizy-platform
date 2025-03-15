#!/bin/bash
set -e

# Define MLflow directories
MLFLOW_DIR="/opt/mlflow"
LOG_DIR="/var/log/mlflow"
ARTIFACT_DIR="/var/artifacts"
SYSTEMD_SERVICE="/etc/systemd/system/prodizy-mlflow.service"

# Create required directories
sudo mkdir -p $MLFLOW_DIR $MLFLOW_DIR/artifacts $LOG_DIR $ARTIFACT_DIR /tmp

# Set correct permissions
sudo chown -R www-data:www-data $LOG_DIR $ARTIFACT_DIR /tmp
sudo chmod -R 755 $LOG_DIR $ARTIFACT_DIR /tmp

# Create virtual environment if not exists
if [ ! -d "$MLFLOW_DIR/venv" ]; then
  python3.11 -m venv $MLFLOW_DIR/venv
fi

# Activate virtual environment
source $MLFLOW_DIR/venv/bin/activate

# Install MLflow and Gunicorn
pip install --upgrade pip
pip install mlflow==2.4.0 gunicorn

# Copy and enable systemd service
sudo cp /opt/prodizy-platform/deployment/config/systemd/prodizy-mlflow.service $SYSTEMD_SERVICE
sudo systemctl daemon-reload
sudo systemctl enable prodizy-mlflow

# Restart MLflow service
sudo systemctl restart prodizy-mlflow

# Check service status
sudo systemctl status prodizy-mlflow --no-pager
