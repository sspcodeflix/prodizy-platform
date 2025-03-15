# Prodizy Platform

The Prodizy Platform is an enterprise-grade LLM connector system designed to bridge the gap between large language models and enterprise tools, databases, and knowledge sources. It enables natural language interaction with organizational data and systems, allowing users to query information and execute actions across various enterprise tools through simple, conversational interfaces.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
- [Running the Application](#running-the-application)
  - [Option 1: Using Component Scripts](#option-1-using-component-scripts)
  - [Option 2: Starting All Services](#option-2-starting-all-services)
  - [Option 3: Manual Execution](#option-3-manual-execution)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

This repository contains a FastAPI backend and a Streamlit frontend for managing and interacting with MLflow. The application aims to:

- Provide a simple interface for logging experiments, models, and runs to MLflow.
- Offer a conversational interface powered by OpenAI for guided MLflow operations.
- Manage sessions to maintain continuity in user interactions.
- Understands user's queries/issues and directs them to the right resource.

---

## Architecture

The application consists of three core components:

1. **MLflow Tracking Server**: Stores experiments, runs, parameters, and metrics (runs on port 5000)
2. **FastAPI Backend**: Processes natural language requests and connects to MLflow (runs on port 5003)
3. **Streamlit Frontend**: User-facing interface for interacting with the system (runs on default port 8501)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Streamlit  │     │   FastAPI   │     │   MLflow    │
│             │────▶│             │────▶│             │
│  (UI/UX)    │     │ (NL Service)│     │ (Tracking)  │
└─────────────┘     └─────────────┘     └─────────────┘
     Port:               Port:              Port:
     8501               5003               5000
```

---

## Features

- **MLflow Integration**: Interact with MLflow for experiment tracking and logging.
- **OpenAI Integration**: Get AI-driven suggestions and conversational support.
- **Streamlit UI**: A user-friendly interface to visualize and manage experiments.
- **Session Management**: Maintains user session data for improved interaction continuity.
- **Service Status Monitoring**: Real-time monitoring of backend and MLflow server status.

---

## Project Structure

```plaintext
prodizy/
├── README.md                   # Project documentation
├── requirements.txt            # Project dependencies
├── .env.example                # Template for environment variables
│
├── backend/                    # Backend application code
│   ├── __init__.py
│   ├── main.py                 # Main FastAPI application entry point
│   │
│   ├── api/                    # API routes
│   │   ├── __init__.py
│   │   └── mlflow_router.py    # MLflow chat endpoint
│   │
│   ├── core/                   # Core functionality
│   │   ├── __init__.py
│   │   ├── config.py           # Configuration settings
│   │   │
│   │   └── services/           # Service modules
│   │       ├── __init__.py
│   │       ├── mlflow_service.py  # MLflow API interactions
│   │       └── openai_service.py  # OpenAI API interactions
│   │
│   ├── models/                 # Data models
│   │   ├── __init__.py
│   │   └── chat.py             # Request/response models
│   │
│   └── utils/                  # Utility modules
│       ├── __init__.py
│       └── session_store.py    # Session management
│
├── frontend/                   # Streamlit frontend
│   ├── __init__.py
│   ├── app.py                  # Main Streamlit application
│   └── utils/                  # Frontend utilities
│       ├── __init__.py
│       └── api.py              # API client for backend
│
└── scripts/                    # Utility scripts
    ├── start_mlflow.sh         # Script to start MLflow server
    ├── start_fastapi.sh        # Script to start FastAPI backend
    ├── start_streamlit.sh      # Script to start Streamlit frontend
    └── start_all.sh            # Script to start all components
```

---

## Getting Started

### Prerequisites

- Python 3.8+
- MLflow
- OpenAI API key

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/sspcodeflix/prodizy-platform.git
   cd prodizy-platform
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

1. Create a `.env` file in the project root based on the provided `.env.example`:

   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file to add your OpenAI API key and configure service ports:

   ```
   # OpenAI API Key (Required)
   OPENAI_API_KEY=your_openai_api_key_here

   # Service Ports and URLs (Required)
   # MLflow tracking server URL
   MLFLOW_TRACKING_URI=http://127.0.0.1:5000

   # FastAPI backend port and URL
   API_PORT=5003
   BACKEND_API_URL=http://127.0.0.1:5003/

   # Optional Configuration
   REQUEST_TIMEOUT=30
   MAX_REQUESTS_PER_SESSION=10
   INVITATION_EXPIRY_SECONDS=3600
   ```

---

## Running the Application

### Option 1: Using Component Scripts

The application is divided into three components, each with its own startup script. This approach allows you to start, stop, or restart individual components as needed.

First, make the scripts executable:

```bash
chmod +x scripts/*.sh
```

1. **Start the MLflow Tracking Server**:

   ```bash
   ./scripts/start_mlflow.sh
   ```

2. **Start the FastAPI Backend** (in a new terminal):

   ```bash
   ./scripts/start_fastapi.sh
   ```

3. **Start the Streamlit Frontend** (in a new terminal):
   ```bash
   ./scripts/start_streamlit.sh
   ```

Each script will run in the foreground and can be stopped with Ctrl+C.

### Option 2: Starting All Services

To start all components at once in separate terminal windows:

```bash
chmod +x scripts/start_all.sh
./scripts/start_all.sh
```

This script:

- Detects your operating system (macOS, Linux, or Windows)
- Opens appropriate terminal windows for each component
- Starts all three services with appropriate delays

### Option 3: Manual Execution

If you prefer to run commands directly:

1. Start the MLflow tracking server:

   ```bash
   mlflow server --host 127.0.0.1 --port 5000
   ```

2. In a new terminal, set the Python path and start the backend:

   ```bash
   export PYTHONPATH=$PYTHONPATH:$(pwd)  # On Windows: set PYTHONPATH=%PYTHONPATH%;%cd%
   cd backend
   python main.py
   ```

3. In another terminal, start the Streamlit frontend:
   ```bash
   cd frontend
   streamlit run app.py
   ```

---

## Usage

1. Access the Streamlit frontend at http://localhost:8501
2. The sidebar displays the status of both the FastAPI backend and MLflow server
3. Enter natural language commands in the chat to interact with MLflow, such as:
   - "Create a new experiment called my_experiment"
   - "Start a run in my_experiment"
   - "Log a parameter called learning_rate with value 0.01"
   - "Log accuracy metric of 0.95"

---

## Troubleshooting

If you encounter issues with the application, here are some common problems and solutions:

### Common Issues

1. **"Cannot connect to backend" error**:

   - Ensure the FastAPI backend is running on the correct port
   - Check the BACKEND_API_URL in your .env file
   - Verify that no other process is using the same port

2. **"Cannot connect to MLflow server" error**:

   - Verify the MLflow server is running on port 5000
   - Check the MLFLOW_TRACKING_URI in your .env file
   - Ensure MLflow is properly installed

3. **"Address already in use" error**:

   - Change the API_PORT in your .env file to an available port
   - Kill the process using the port: `kill $(lsof -t -i:5003)`

4. **UI Getting Stuck**:

   - Increase the REQUEST_TIMEOUT value in your .env file
   - Check the backend logs for any errors or stuck processes
   - Restart the services in the correct order: MLflow first, then backend, then frontend

5. **OpenAI API Issues**:

   - Verify your API key is correct in the .env file
   - Check if you have remaining API credits/quota
   - Check for any rate limiting in the backend logs

6. **PYTHONPATH Issues**:
   - Ensure PYTHONPATH includes the project root directory
   - Use the provided scripts which set PYTHONPATH automatically

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.
