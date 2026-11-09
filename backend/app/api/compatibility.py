
from fastapi import APIRouter, HTTPException

from app.schemas.compatibility import CompatibilityReport

from app.services.docker_desktop_service import (
    check_docker_desktop_compatibility
)


router = APIRouter(
    prefix="/api/compatibility",
    tags=["Compatibility Engine"]
)


@router.get(
    "/docker-desktop",
    response_model=CompatibilityReport
)
def check_docker_desktop():

    try:
        return check_docker_desktop_compatibility()

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Docker compatibility evaluation failed: {str(error)}"
        )
