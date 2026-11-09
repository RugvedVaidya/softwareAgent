
from fastapi import FastAPI

from app.api.scanner import router as scanner_router
from app.api.compatibility import router as compatibility_router


app = FastAPI(
    title="Software Agent API",
    description=(
        "AI-powered software installation, "
        "compatibility and repair agent"
    ),
    version="0.2.0"
)


@app.get("/")
def root():
    return {
        "message": "Software Agent API is running",
        "version": "0.2.0"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


app.include_router(scanner_router)
app.include_router(compatibility_router)
