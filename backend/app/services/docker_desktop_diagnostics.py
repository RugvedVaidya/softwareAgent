
import os
import re
import shutil
import subprocess

from app.services.windows_inspector import run_powershell


def run_command(args, timeout=12):
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False
        )

        if result.returncode != 0:
            return None

        return result.stdout.strip()

    except (subprocess.TimeoutExpired, OSError):
        return None


def find_executable(command, fallback_paths=None):
    path = shutil.which(command)

    if path:
        return path

    for candidate in fallback_paths or []:
        if candidate and os.path.isfile(candidate):
            return candidate

    return None


def get_wsl_executable():
    system_root = os.environ.get("SystemRoot", r"C:\Windows")

    return find_executable(
        "wsl.exe",
        [
            os.path.join(system_root, "System32", "wsl.exe")
        ]
    )


def get_docker_executable():
    program_files = os.environ.get(
        "ProgramFiles", r"C:\Program Files"
    )

    local_app_data = os.environ.get("LOCALAPPDATA", "")

    return find_executable(
        "docker.exe",
        [
            os.path.join(
                program_files,
                "Docker",
                "Docker",
                "resources",
                "bin",
                "docker.exe"
            ),
            os.path.join(
                local_app_data,
                "Programs",
                "DockerDesktop",
                "resources",
                "bin",
                "docker.exe"
            )
        ]
    )


def get_wsl_version():
    executable = get_wsl_executable()

    if not executable:
        return None

    output = run_command([executable, "--version"])

    if not output:
        return None

    match = re.search(
        r"WSL version:\s*([0-9.]+)",
        output,
        re.IGNORECASE
    )

    if match:
        return match.group(1)

    # Older WSL command implementations may not support
    # the --version option.
    return None


def get_hardware_diagnostics():
    command = """
    $cs = Get-CimInstance Win32_ComputerSystem
    $cpu = Get-CimInstance Win32_Processor |
        Select-Object -First 1
    $ram = (
        Get-CimInstance Win32_PhysicalMemory |
        Measure-Object -Property Capacity -Sum
    ).Sum

    [PSCustomObject]@{
        HypervisorPresent = $cs.HypervisorPresent
        FirmwareVirtualization = $cpu.VirtualizationFirmwareEnabled
        SLAT = $cpu.SecondLevelAddressTranslationExtensions
        InstalledMemoryBytes = $ram
    } | ConvertTo-Json -Compress
    """

    return run_powershell(command) or {}


def get_windows_diagnostics():
    command = """
    $os = Get-CimInstance Win32_OperatingSystem

    [PSCustomObject]@{
        Caption = $os.Caption
        BuildNumber = $os.BuildNumber
        Architecture = $os.OSArchitecture
    } | ConvertTo-Json -Compress
    """

    return run_powershell(command) or {}


def get_windows_feature_states():
    command = """
    $names = @(
        'Microsoft-Windows-Subsystem-Linux',
        'VirtualMachinePlatform'
    )

    $result = foreach ($name in $names) {
        try {
            $feature = Get-WindowsOptionalFeature `
                -Online `
                -FeatureName $name `
                -ErrorAction Stop

            [PSCustomObject]@{
                Name = $name
                State = [string]$feature.State
            }
        }
        catch {
            [PSCustomObject]@{
                Name = $name
                State = 'Unknown'
            }
        }
    }

    $result | ConvertTo-Json -Compress
    """

    data = run_powershell(command)

    if not data:
        return {}

    if isinstance(data, dict):
        data = [data]

    return {
        item.get("Name"): item.get("State")
        for item in data
    }


def get_server_service():
    command = """
    Get-CimInstance Win32_Service `
        -Filter "Name='LanmanServer'" |
    Select-Object State, StartMode |
    ConvertTo-Json -Compress
    """

    return run_powershell(command) or {}


def get_docker_engine_health():
    executable = get_docker_executable()

    if not executable:
        return {
            "cli_found": False,
            "engine_running": None,
            "client_version": None,
            "server_version": None
        }

    client_version = run_command(
        [
            executable,
            "version",
            "--format",
            "{{.Client.Version}}"
        ]
    )

    server_version = run_command(
        [
            executable,
            "info",
            "--format",
            "{{.ServerVersion}}"
        ],
        timeout=15
    )

    return {
        "cli_found": True,
        "engine_running": bool(server_version),
        "client_version": client_version,
        "server_version": server_version
    }


def get_docker_diagnostics(profile):
    hardware = get_hardware_diagnostics()
    windows = get_windows_diagnostics()

    applications = (
        profile.get("advanced_system", {})
        .get("installed_applications", [])
    )

    docker_app = next(
        (
            app for app in applications
            if "docker desktop" in app.get("name", "").lower()
        ),
        None
    )

    wsl_app = next(
        (
            app for app in applications
            if app.get("name", "").strip().lower()
            == "windows subsystem for linux"
        ),
        None
    )

    wsl_cli_version = get_wsl_version()

    registered_wsl_version = (
        wsl_app.get("version") if wsl_app else None
    )

    memory_bytes = hardware.get("InstalledMemoryBytes")

    try:
        installed_ram_gb = (
            int(memory_bytes) / (1024 ** 3)
            if memory_bytes else None
        )
    except (ValueError, TypeError):
        installed_ram_gb = None

    engine = get_docker_engine_health()

    return {
        "windows_caption": windows.get("Caption"),
        "windows_build": windows.get("BuildNumber"),
        "windows_architecture": windows.get("Architecture"),

        "hypervisor_present": hardware.get("HypervisorPresent"),
        "firmware_virtualization": hardware.get(
            "FirmwareVirtualization"
        ),
        "slat_supported": hardware.get("SLAT"),

        "installed_ram_gb": installed_ram_gb,

        "wsl_version": wsl_cli_version,
        "registered_wsl_version": registered_wsl_version,

        "windows_features": get_windows_feature_states(),
        "server_service": get_server_service(),

        "docker_installed": docker_app is not None,
        "docker_version": (
            docker_app.get("version") if docker_app else None
        ),

        "docker_cli_found": engine["cli_found"],
        "docker_engine_running": engine["engine_running"],
        "docker_client_version": engine["client_version"],
        "docker_server_version": engine["server_version"]
    }
