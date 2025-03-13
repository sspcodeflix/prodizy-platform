"""
Main application module for the FastAPI backend.
Initializes the FastAPI application and includes routers.
"""

import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv
from backend.api.mlflow_router import router as mlflow_router
from backend.api.invitation_router import router as invitation_router
from backend.core.config import settings
from backend.api.llm_router import router as llm_router

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Prodizy Platform API Services")

# Include routers
app.include_router(mlflow_router, prefix="/chat")
app.include_router(invitation_router, prefix="/invitation")
app.include_router(llm_router, prefix="/llm")

if __name__ == "__main__":
    port = settings.API_PORT
    print(f"Starting FastAPI server on port {port}")
    uvicorn.run(
        "main:app",  # Use relative import when running directly
        host="0.0.0.0", 
        port=port,
        reload=True
    )