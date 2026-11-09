
import json
import os
import subprocess
import winreg
import shutil

from app.schemas.environment import (
    GPUInfo,
    DotNetInfo,
    VisualCppInfo,
    DirectXInfo,
    InstalledApplication,
)


def run_powershell(command: str):
    """
    Run a fixed, read-only PowerShell query.
    No user-provided command is accepted.
    """

    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                command
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            shell=False
        )

        if result.returncode != 0:
            return None

        output = result.stdout.strip()

        if not output:
            return None

        return json.loads(output)

    except (
        subprocess.TimeoutExpired,
        OSError,
        json.JSONDecodeError
    ):
        return None


def get_gpu_information():
    # Prefer NVIDIA's own utility for NVIDIA hardware.
    nvidia_gpus = get_nvidia_gpu_information()

    # CIM provides fallback and detects other GPU vendors.
    command = """
    Get-CimInstance Win32_VideoController |
    Select-Object Name, DriverVersion, DriverDate, AdapterRAM |
    ConvertTo-Json -Depth 3 -Compress
    """

    data = run_powershell(command)

    if not data:
        return nvidia_gpus

    if isinstance(data, dict):
        data = [data]

    gpus = []

    for item in data:
        name = item.get("Name") or "Unknown"

        # Use NVIDIA's more reliable memory and driver information
        # when its utility detected this GPU.
        nvidia_match = next(
            (
                gpu for gpu in nvidia_gpus
                if gpu.name.lower() == name.lower()
            ),
            None
        )

        if nvidia_match:
            gpus.append(nvidia_match)
            continue

        try:
            memory = item.get("AdapterRAM")
            memory_gb = (
                round(int(memory) / (1024 ** 3), 2)
                if memory else None
            )
        except (ValueError, TypeError):
            memory_gb = None

        gpus.append(
            GPUInfo(
                name=name,
                driver_version=item.get("DriverVersion"),
                driver_date=item.get("DriverDate"),
                adapter_ram_gb=memory_gb
            )
        )

    return gpus

def get_dotnet_information():
    runtimes = []

    dotnet_path = shutil_which("dotnet")

    if dotnet_path:
        try:
            result = subprocess.run(
                [dotnet_path, "--list-runtimes"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                shell=False
            )

            if result.returncode == 0:
                runtimes = [
                    line.strip()
                    for line in result.stdout.splitlines()
                    if line.strip()
                ]

        except (subprocess.TimeoutExpired, OSError):
            pass

    framework_release = None

    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full"
        ) as key:
            framework_release, _ = winreg.QueryValueEx(
                key, "Release"
            )
    except OSError:
        pass

    return DotNetInfo(
        installed=bool(runtimes or framework_release),
        runtimes=runtimes,
        framework_release=framework_release
    )


def shutil_which(command):
    import shutil
    return shutil.which(command)


def get_visual_cpp_information():
    uninstall_paths = [
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
        ),
        (
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
        )
    ]

    found = set()

    for root, path in uninstall_paths:
        try:
            with winreg.OpenKey(root, path) as parent:
                count = winreg.QueryInfoKey(parent)[0]

                for index in range(count):
                    try:
                        subkey_name = winreg.EnumKey(parent, index)

                        with winreg.OpenKey(
                            parent, subkey_name
                        ) as subkey:
                            try:
                                name, _ = winreg.QueryValueEx(
                                    subkey, "DisplayName"
                                )
                            except OSError:
                                continue

                            if (
                                "Microsoft Visual C++" in name
                                and "Redistributable" in name
                            ):
                                found.add(name)

                    except OSError:
                        continue

        except OSError:
            continue

    redistributables = sorted(found)

    return VisualCppInfo(
        installed=bool(redistributables),
        redistributables=redistributables
    )


def get_directx_information():
    version = None

    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\DirectX"
        ) as key:
            version, _ = winreg.QueryValueEx(key, "Version")
    except OSError:
        pass

    return DirectXInfo(version=version)


def get_installed_applications(limit=500):
    uninstall_paths = [
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
        ),
        (
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
        )
    ]

    applications = {}
    truncated = False

    for root, path in uninstall_paths:
        try:
            with winreg.OpenKey(root, path) as parent:
                count = winreg.QueryInfoKey(parent)[0]

                for index in range(count):
                    try:
                        subkey_name = winreg.EnumKey(parent, index)

                        with winreg.OpenKey(
                            parent, subkey_name
                        ) as subkey:
                            try:
                                name, _ = winreg.QueryValueEx(
                                    subkey, "DisplayName"
                                )
                            except OSError:
                                continue

                            if not name or not name.strip():
                                continue

                            try:
                                version, _ = winreg.QueryValueEx(
                                    subkey, "DisplayVersion"
                                )
                            except OSError:
                                version = None

                            try:
                                publisher, _ = winreg.QueryValueEx(
                                    subkey, "Publisher"
                                )
                            except OSError:
                                publisher = None

                            # Use name as a simple de-duplication key.
                            applications[name.lower()] = (
                                name, version, publisher
                            )

                    except OSError:
                        continue

        except OSError:
            continue

    all_apps = sorted(
        applications.values(),
        key=lambda item: item[0].lower()
    )

    if len(all_apps) > limit:
        truncated = True
        all_apps = all_apps[:limit]

    result = [
        InstalledApplication(
            name=name,
            version=version,
            publisher=publisher
        )
        for name, version, publisher in all_apps
    ]

    return result, truncated

def get_nvidia_gpu_information():
    executable = shutil.which("nvidia-smi")

    if not executable:
        return []

    try:
        result = subprocess.run(
            [
                executable,
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader,nounits"
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            shell=False
        )

        if result.returncode != 0:
            return []

        gpus = []

        for line in result.stdout.splitlines():
            parts = [part.strip() for part in line.split(",")]

            if len(parts) != 3:
                continue

            name, memory, driver = parts

            try:
                memory_gb = round(float(memory) / 1024, 2)
            except ValueError:
                memory_gb = None

            gpus.append(
                GPUInfo(
                    name=name,
                    driver_version=driver,
                    driver_date=None,
                    adapter_ram_gb=memory_gb
                )
            )

        return gpus

    except (subprocess.TimeoutExpired, OSError):
        return []
