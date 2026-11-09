
import re
from datetime import datetime, timezone

from app.schemas.compatibility import (
    CompatibilityCheck,
    CompatibilityReport
)


DOCKER_WINDOWS_DOCS = (
    "https://docs.docker.com/desktop/setup/install/windows-install/"
)

DOCKER_WSL_DOCS = (
    "https://docs.docker.com/desktop/features/wsl/"
)


def parse_version(value):
    """
    Convert a version string into a comparable tuple.
    Example: 2.4.13.0 -> (2, 4, 13, 0)
    """

    if not value:
        return None

    match = re.search(r"\d+(?:\.\d+)+", str(value))

    if not match:
        return None

    return tuple(
        int(part) for part in match.group().split(".")
    )


def add_check(
    checks,
    key,
    title,
    status,
    observed=None,
    expected=None,
    explanation="",
    recommendation=None,
    source_url=None
):
    checks.append(
        CompatibilityCheck(
            key=key,
            title=title,
            status=status,
            observed=(
                str(observed) if observed is not None else None
            ),
            expected=expected,
            explanation=explanation,
            recommendation=recommendation,
            source_url=source_url
        )
    )


def evaluate_docker_desktop(profile, diagnostics):
    checks = []

    os_info = profile.get("operating_system", {})
    hardware = profile.get("hardware", {})
    storage = profile.get("storage", {})
    advanced = profile.get("advanced_system", {})

    # --------------------------------------------------
    # 1. Windows version and build
    # --------------------------------------------------

    build = diagnostics.get("windows_build")

    try:
        build_number = int(build) if build else None
    except (ValueError, TypeError):
        build_number = None

    if build_number is None:
        add_check(
            checks,
            "windows_build",
            "Windows build",
            "unknown",
            observed=os_info.get("build"),
            expected="Windows 11 build 22631 or later",
            explanation="Could not verify the Windows build."
        )

    elif build_number >= 22631:
        add_check(
            checks,
            "windows_build",
            "Windows build",
            "pass",
            observed=build_number,
            expected="22631 or later",
            explanation="The detected Windows build meets the documented minimum.",
            source_url=DOCKER_WINDOWS_DOCS
        )

    else:
        add_check(
            checks,
            "windows_build",
            "Windows build",
            "fail",
            observed=build_number,
            expected="22631 or later",
            explanation="The detected build is below Docker's documented Windows 11 minimum.",
            recommendation="Update Windows to a supported build.",
            source_url=DOCKER_WINDOWS_DOCS
        )

    # --------------------------------------------------
    # 2. Windows edition
    # --------------------------------------------------

    edition = diagnostics.get("windows_caption") or "Unknown"
    edition_lower = edition.lower()

    if "home" in edition_lower:
        add_check(
            checks,
            "windows_edition",
            "Windows edition",
            "warning",
            observed=edition,
            expected="Supported Windows edition",
            explanation=(
                "Docker Desktop can be used for Linux containers "
                "on Windows Home, but Windows containers are not supported."
            ),
            recommendation=(
                "Use the WSL 2 backend and Linux containers."
            ),
            source_url=DOCKER_WINDOWS_DOCS
        )

    elif "education" in edition_lower:
        add_check(
            checks,
            "windows_edition",
            "Windows edition",
            "warning",
            observed=edition,
            expected="Supported Windows edition",
            explanation=(
                "Docker Desktop supports Linux containers on Education; "
                "Windows containers are not supported."
            ),
            source_url=DOCKER_WINDOWS_DOCS
        )

    elif any(
        item in edition_lower
        for item in ["professional", "pro", "enterprise"]
    ):
        add_check(
            checks,
            "windows_edition",
            "Windows edition",
            "pass",
            observed=edition,
            expected="Pro, Enterprise or supported edition",
            explanation="Detected a supported Windows edition.",
            source_url=DOCKER_WINDOWS_DOCS
        )

    else:
        add_check(
            checks,
            "windows_edition",
            "Windows edition",
            "unknown",
            observed=edition,
            expected="Supported Windows edition",
            explanation="Windows edition could not be classified."
        )

    # --------------------------------------------------
    # 3. Architecture
    # --------------------------------------------------

    architecture = (
        diagnostics.get("windows_architecture")
        or os_info.get("architecture", "")
    )

    if str(architecture).lower() in [
        "amd64", "x64", "64-bit"
    ]:
        add_check(
            checks,
            "architecture",
            "CPU architecture",
            "pass",
            observed=architecture,
            expected="64-bit x86",
            explanation="The system uses a supported x64 architecture."
        )

    else:
        add_check(
            checks,
            "architecture",
            "CPU architecture",
            "fail",
            observed=architecture,
            expected="64-bit x86",
            explanation="The detected architecture does not match this x64 evaluation.",
            source_url=DOCKER_WINDOWS_DOCS
        )

    # --------------------------------------------------
    # 4. CPU virtualization capabilities
    # --------------------------------------------------

    slat = diagnostics.get("slat_supported")

    if slat is True:
        add_check(
            checks,
            "slat",
            "Second Level Address Translation",
            "pass",
            observed="Supported",
            expected="SLAT supported",
            explanation="The processor reports SLAT support."
        )

    elif slat is False:
        add_check(
            checks,
            "slat",
            "Second Level Address Translation",
            "fail",
            observed="Not supported",
            expected="SLAT supported",
            explanation="The processor reports no SLAT support.",
            recommendation="Check CPU and virtualization compatibility."
        )

    else:
        add_check(
            checks,
            "slat",
            "Second Level Address Translation",
            "unknown",
            observed="Unknown",
            expected="SLAT supported",
            explanation="Could not verify processor SLAT support."
        )

    # --------------------------------------------------
    # 5. BIOS/UEFI virtualization
    # --------------------------------------------------

    virtualization = diagnostics.get(
        "firmware_virtualization"
    )

    if virtualization is True:
        add_check(
            checks,
            "firmware_virtualization",
            "Hardware virtualization",
            "pass",
            observed="Enabled",
            expected="Enabled in BIOS/UEFI",
            explanation="Windows reports firmware virtualization enabled."
        )

    elif virtualization is False:
        add_check(
            checks,
            "firmware_virtualization",
            "Hardware virtualization",
            "fail",
            observed="Disabled",
            expected="Enabled in BIOS/UEFI",
            explanation="Hardware virtualization is disabled.",
            recommendation=(
                "Enable AMD SVM or Intel VT-x in BIOS/UEFI, "
                "then restart Windows."
            )
        )

    else:
        add_check(
            checks,
            "firmware_virtualization",
            "Hardware virtualization",
            "unknown",
            observed="Unknown",
            expected="Enabled in BIOS/UEFI",
            explanation="Could not verify firmware virtualization."
        )

    # --------------------------------------------------
    # 6. Windows hypervisor
    # --------------------------------------------------

    hypervisor = diagnostics.get("hypervisor_present")

    if hypervisor is True:
        add_check(
            checks,
            "hypervisor",
            "Windows hypervisor",
            "pass",
            observed="Detected",
            expected="Available for WSL 2",
            explanation="A Windows hypervisor is currently detected."
        )

    elif hypervisor is False:
        add_check(
            checks,
            "hypervisor",
            "Windows hypervisor",
            "warning",
            observed="Not detected",
            expected="Available for WSL 2",
            explanation=(
                "A hypervisor is not currently detected. "
                "This does not by itself prove BIOS virtualization is disabled."
            ),
            recommendation=(
                "Verify Virtual Machine Platform and hypervisor startup settings."
            )
        )

    else:
        add_check(
            checks,
            "hypervisor",
            "Windows hypervisor",
            "unknown",
            expected="Available for WSL 2",
            explanation="Could not inspect hypervisor state."
        )

    # --------------------------------------------------
    # 7. WSL version
    # --------------------------------------------------

    wsl_version = diagnostics.get("wsl_version")

    if not wsl_version:
        wsl_version = diagnostics.get(
            "registered_wsl_version"
        )

    current_wsl = parse_version(wsl_version)
    minimum_wsl = (2, 1, 5)

    if current_wsl is None:
        add_check(
            checks,
            "wsl_version",
            "WSL version",
            "unknown",
            observed=wsl_version,
            expected="2.1.5 or later",
            explanation="Could not verify the WSL version."
        )

    elif current_wsl >= minimum_wsl:
        add_check(
            checks,
            "wsl_version",
            "WSL version",
            "pass",
            observed=wsl_version,
            expected="2.1.5 or later",
            explanation="The detected WSL version meets the minimum.",
            source_url=DOCKER_WSL_DOCS
        )

    else:
        add_check(
            checks,
            "wsl_version",
            "WSL version",
            "fail",
            observed=wsl_version,
            expected="2.1.5 or later",
            explanation="The detected WSL version is below the minimum.",
            recommendation="Update WSL using wsl --update.",
            source_url=DOCKER_WSL_DOCS
        )

    # --------------------------------------------------
    # 8. Windows optional features
    # --------------------------------------------------

    features = diagnostics.get("windows_features", {})

    for feature_key, feature_name in [
        ("Microsoft-Windows-Subsystem-Linux", "WSL"),
        ("VirtualMachinePlatform", "Virtual Machine Platform")
    ]:
        state = features.get(feature_key)

        if state == "Enabled":
            status = "pass"
            explanation = f"{feature_name} is enabled."

        elif state == "Disabled":
            status = "fail"
            explanation = f"{feature_name} is disabled."

        else:
            status = "unknown"
            explanation = f"Could not verify {feature_name} state."

        add_check(
            checks,
            feature_key,
            feature_name,
            status,
            observed=state,
            expected="Enabled",
            explanation=explanation,
            recommendation=(
                f"Enable the {feature_name} Windows feature if disabled."
            )
        )

    # --------------------------------------------------
    # 9. Memory
    # --------------------------------------------------

    installed_memory_gb = diagnostics.get(
        "installed_ram_gb"
    )

    reported_memory_gb = hardware.get("total_ram_gb")

    if installed_memory_gb is not None:
        memory = float(installed_memory_gb)

        if memory >= 8:
            status = "pass"
            explanation = "Installed physical RAM meets the 8 GB baseline."

        else:
            status = "fail"
            explanation = "Installed physical RAM is below the 8 GB baseline."

        add_check(
            checks,
            "memory",
            "Installed system RAM",
            status,
            observed=f"{memory:.2f} GB",
            expected="At least 8 GB",
            explanation=explanation,
            source_url=DOCKER_WINDOWS_DOCS
        )

    else:
        add_check(
            checks,
            "memory",
            "Installed system RAM",
            "unknown",
            observed=f"{reported_memory_gb} GiB reported by OS",
            expected="At least 8 GB installed",
            explanation=(
                "The scanner's OS-visible memory value cannot reliably "
                "establish the installed physical RAM capacity."
            ),
            recommendation=(
                "Verify installed memory using Windows Task Manager "
                "or inspect the physical memory modules."
            ),
            source_url=DOCKER_WINDOWS_DOCS
        )

    # --------------------------------------------------
    # 10. Disk space
    # --------------------------------------------------

    free_disk = storage.get("free_gb")

    add_check(
        checks,
        "disk_space",
        "Available system disk space",
        "info",
        observed=(
            f"{free_disk} GB free"
            if free_disk is not None else "Unknown"
        ),
        expected="No fixed minimum encoded",
        explanation=(
            "Docker's Windows installation requirements do not specify "
            "a universal minimum free-disk threshold. Check actual image "
            "and container storage needs before large workloads."
        )
    )

    # --------------------------------------------------
    # 11. Windows Server service
    # --------------------------------------------------

    service = diagnostics.get("server_service", {})
    start_mode = service.get("start_mode")
    service_state = service.get("state")

    if start_mode == "Disabled":
        status = "fail"
        explanation = "The Windows Server service is disabled."

    elif start_mode == "Auto":
        status = "pass"
        explanation = "The Windows Server service is configured for automatic startup."

    elif start_mode:
        status = "warning"
        explanation = (
            f"The Windows Server service start mode is {start_mode}."
        )

    else:
        status = "unknown"
        explanation = "Could not verify the Windows Server service."

    if service_state == "Stopped" and status == "pass":
        status = "warning"
        explanation += " It is currently stopped."

    add_check(
        checks,
        "server_service",
        "Windows Server service",
        status,
        observed=f"{service_state}, start mode: {start_mode}",
        expected="Enabled and Automatic",
        explanation=explanation,
        source_url=DOCKER_WINDOWS_DOCS
    )

    # --------------------------------------------------
    # 12. Existing Docker Desktop installation
    # --------------------------------------------------

    installed = diagnostics.get("docker_installed", False)
    installed_version = diagnostics.get("docker_version")

    add_check(
        checks,
        "docker_installed",
        "Docker Desktop installation",
        "pass" if installed else "info",
        observed=installed_version if installed else "Not detected",
        expected="Docker Desktop installed",
        explanation=(
            "Docker Desktop is already registered as installed."
            if installed else
            "Docker Desktop is not detected as installed."
        )
    )

    # --------------------------------------------------
    # 13. Docker engine health
    # --------------------------------------------------

    engine_running = diagnostics.get("docker_engine_running")

    if engine_running is True:
        status = "pass"
        explanation = "The Docker Engine responded successfully."

    elif engine_running is False:
        status = "warning"
        explanation = (
            "Docker Desktop is installed, but the Docker Engine "
            "did not respond to the health check."
        )

    else:
        status = "unknown"
        explanation = "Docker Engine health could not be verified."

    add_check(
        checks,
        "docker_engine",
        "Docker Engine health",
        status,
        observed=(
            "Running" if engine_running is True
            else "Not responding" if engine_running is False
            else "Unknown"
        ),
        expected="Docker Engine responds to docker info",
        explanation=explanation,
        recommendation=(
            "Start Docker Desktop and retry the health check."
            if engine_running is False else None
        )
    )

    # --------------------------------------------------
    # 14. Overall result
    # --------------------------------------------------

    passed = sum(c.status == "pass" for c in checks)
    failed = sum(c.status == "fail" for c in checks)
    warnings = sum(c.status == "warning" for c in checks)
    unknown = sum(c.status == "unknown" for c in checks)

    if failed:
        overall = "fail"
        summary = (
            f"{failed} required compatibility check(s) failed. "
            "Resolve these before relying on Docker Desktop."
        )

    elif warnings or unknown:
        overall = "warning"
        summary = (
            "No confirmed hard failure was found, but some checks "
            "need attention or could not be verified."
        )

    else:
        overall = "pass"
        summary = (
            "All evaluated compatibility checks passed."
        )

    return CompatibilityReport(
        software_name="Docker Desktop",
        evaluation_type="installation_and_runtime_compatibility",
        overall_status=overall,
        summary=summary,
        installed=installed,
        installed_version=installed_version,
        evaluated_at=datetime.now(timezone.utc),
        checks=checks,
        passed_count=passed,
        failed_count=failed,
        warning_count=warnings,
        unknown_count=unknown
    )
