#!/bin/bash
set -e

# Change to script directory
cd "$(dirname "$0")"

echo "Setting up server environment..."
bash setup_server.sh

echo "Deploying backend..."
bash deploy_backend.sh

echo "Deploying MLflow..."
bash deploy_mlflow.sh

echo "Deployment complete!"