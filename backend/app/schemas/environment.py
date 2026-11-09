
from typing import Optional
from pydantic import BaseModel


class OperatingSystemInfo(BaseModel):
    name: str
    version: str
    build: str
    architecture: str


class HardwareInfo(BaseModel):
    processor: str
    logical_cores: int
    physical_cores: Optional[int]
    total_ram_gb: float


class StorageInfo(BaseModel):
    system_drive: str
    total_gb: float
    free_gb: float


class ToolInfo(BaseModel):
    installed: bool
    version: Optional[str] = None
    path: Optional[str] = None


class DevelopmentTools(BaseModel):
    python: ToolInfo
    node: ToolInfo
    npm: ToolInfo
    java: ToolInfo
    git: ToolInfo
    vscode: ToolInfo
    winget: ToolInfo


class GPUInfo(BaseModel):
    name: str
    driver_version: Optional[str] = None
    driver_date: Optional[str] = None
    adapter_ram_gb: Optional[float] = None


class DotNetInfo(BaseModel):
    installed: bool
    runtimes: list[str]
    framework_release: Optional[int] = None


class VisualCppInfo(BaseModel):
    installed: bool
    redistributables: list[str]


class DirectXInfo(BaseModel):
    version: Optional[str] = None


class InstalledApplication(BaseModel):
    name: str
    version: Optional[str] = None
    publisher: Optional[str] = None


class AdvancedSystemInfo(BaseModel):
    gpus: list[GPUInfo]
    dotnet: DotNetInfo
    visual_cpp: VisualCppInfo
    directx: DirectXInfo
    installed_applications: list[InstalledApplication]
    applications_truncated: bool = False


class EnvironmentResponse(BaseModel):
    operating_system: OperatingSystemInfo
    hardware: HardwareInfo
    storage: StorageInfo
    development_tools: DevelopmentTools
    advanced_system: AdvancedSystemInfo
