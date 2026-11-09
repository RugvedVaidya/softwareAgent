
from app.services.environment_scanner import scan_environment

from app.services.docker_desktop_diagnostics import (
    get_docker_diagnostics
)

from app.services.docker_desktop_engine import (
    evaluate_docker_desktop
)


def check_docker_desktop_compatibility():
    # Step 1: Collect the machine profile.
    profile = scan_environment()

    # Step 2: Collect Docker-specific diagnostics.
    diagnostics = get_docker_diagnostics(profile)

    # Step 3: Evaluate compatibility.
    report = evaluate_docker_desktop(
        profile,
        diagnostics
    )

    return report
