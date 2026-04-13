from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

def add_cors_middleware(app: FastAPI) -> None:
    """
    Configures CORS to only allow requests from our specified frontend origins.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )