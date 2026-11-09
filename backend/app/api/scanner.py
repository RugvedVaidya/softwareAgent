
from fastapi import APIRouter, HTTPException

from app.schemas.environment import EnvironmentResponse
from app.services.environment_scanner import scan_environment

router = APIRouter(
    prefix="/api/scanner",
    tags=["Environment Scanner"]
)


@router.get(
    "/environment",
    response_model=EnvironmentResponse
)
def get_environment():

    try:
        environment = scan_environment()
        return environment

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Environment scan failed: {str(error)}"
        )
