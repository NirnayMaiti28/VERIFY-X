from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio

from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler

from text_verification.api.verify_route import router, limiter
from text_verification.pipeline.verify_pipeline import VerificationPipeline


# Create FastAPI app
app = FastAPI(title="Fact Verification API")


# Attach rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# Enable CORS (frontend access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # replace with explicit frontend origin in production
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register API routes
app.include_router(router)


@app.on_event("startup")
async def startup_event():
    # Create a single shared pipeline instance for warm starts and stable latency.
    app.state.pipeline = VerificationPipeline()
    app.state.pipeline_lock = asyncio.Lock()


# Health check endpoint
@app.get("/")
def home():
    return {"message": "Fact Verification API is running"}


def run_terminal_mode():
    """Interactive terminal mode for manual claim verification."""
    pipeline = VerificationPipeline()

    print("Fact Verification Terminal")
    print("Type a news headline and press Enter.")
    print("Type 'exit' to quit.\n")

    while True:
        claim = input("Enter news headline: ").strip()

        if not claim:
            print("Please enter a non-empty headline.\n")
            continue

        if claim.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        result = pipeline.verify_claim(claim)
        print(json.dumps(result, indent=2))
        print()


if __name__ == "__main__":
    run_terminal_mode()