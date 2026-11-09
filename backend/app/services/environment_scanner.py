
import os
import platform
import shutil
import subprocess

import psutil

from app.services.windows_inspector import (
    get_gpu_information,
    get_dotnet_information,
    get_visual_cpp_information,
    get_directx_information,
    get_installed_applications,
)



def get_operating_system():
    from app.services.windows_inspector import run_powershell

    command = """
    Get-CimInstance Win32_OperatingSystem |
    Select-Object Caption, Version, BuildNumber, OSArchitecture |
    ConvertTo-Json -Compress
    """

    data = run_powershell(command)

    if data:
        return {
            "name": data.get("Caption", "Windows"),
            "version": data.get("Version", "Unknown"),
            "build": data.get("BuildNumber", "Unknown"),
            "architecture": data.get("OSArchitecture", "Unknown")
        }

    return {
        "name": "Windows",
        "version": platform.version(),
        "build": platform.version(),
        "architecture": platform.machine()
    }


def get_hardware_info():
    from app.services.windows_inspector import run_powershell

    command = """
    Get-CimInstance Win32_Processor |
    Select-Object -First 1 Name, NumberOfCores, NumberOfLogicalProcessors |
    ConvertTo-Json -Compress
    """

    cpu = run_powershell(command) or {}

    return {
        "processor": cpu.get("Name") or platform.processor() or "Unknown",
        "logical_cores": (
            cpu.get("NumberOfLogicalProcessors")
            or psutil.cpu_count(logical=True)
            or 0
        ),
        "physical_cores": (
            cpu.get("NumberOfCores")
            or psutil.cpu_count(logical=False)
        ),
        "total_ram_gb": round(
            psutil.virtual_memory().total / (1024 ** 3), 2
        )
    }


def get_storage_info():
    system_drive = os.environ.get("SystemDrive", "C:")
    drive_path = system_drive + "\\"

    disk = psutil.disk_usage(drive_path)

    return {
        "system_drive": system_drive,
        "total_gb": round(disk.total / (1024 ** 3), 2),
        "free_gb": round(disk.free / (1024 ** 3), 2)
    }


def get_command_info(command, version_args):
    executable_path = shutil.which(command)

    if not executable_path:
        return {
            "installed": False,
            "version": None,
            "path": None
        }

    try:
        result = subprocess.run(
            [executable_path, *version_args],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            shell=False
        )

        output = result.stdout.strip() or result.stderr.strip()
        version = output.splitlines()[0] if output else "Unknown"

        return {
            "installed": True,
            "version": version,
            "path": executable_path
        }

    except (subprocess.TimeoutExpired, OSError):
        return {
            "installed": True,
            "version": "Could not retrieve version",
            "path": executable_path
        }


def get_development_tools():
    return {
        "python": get_command_info("python", ["--version"]),
        "node": get_command_info("node", ["--version"]),
        "npm": get_command_info("npm", ["--version"]),
        "java": get_command_info("java", ["-version"]),
        "git": get_command_info("git", ["--version"]),
        "vscode": get_command_info("code", ["--version"]),
        "winget": get_winget_info()
    }


def get_advanced_system_info():
    applications, truncated = get_installed_applications()

    return {
        "gpus": get_gpu_information(),
        "dotnet": get_dotnet_information(),
        "visual_cpp": get_visual_cpp_information(),
        "directx": get_directx_information(),
        "installed_applications": applications,
        "applications_truncated": truncated
    }


def scan_environment():
    return {
        "operating_system": get_operating_system(),
        "hardware": get_hardware_info(),
        "storage": get_storage_info(),
        "development_tools": get_development_tools(),
        "advanced_system": get_advanced_system_info()
    }


def get_winget_info():
    from app.services.windows_inspector import run_powershell

    command = """
    Get-AppxPackage -Name Microsoft.DesktopAppInstaller |
    Select-Object -First 1 Version, InstallLocation |
    ConvertTo-Json -Compress
    """

    data = run_powershell(command)

    executable = shutil.which("winget")

    if data:
        return {
            "installed": True,
            "version": data.get("Version", "Unknown"),
            "path": executable
        }

    return {
        "installed": bool(executable),
        "version": None,
        "path": executable
    }
