
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


CheckStatus = Literal[
    "pass",
    "fail",
    "warning",
    "unknown",
    "info"
]


class CompatibilityCheck(BaseModel):
    key: str
    title: str
    status: CheckStatus

    observed: Optional[str] = None
    expected: Optional[str] = None

    explanation: str
    recommendation: Optional[str] = None
    source_url: Optional[str] = None


class CompatibilityReport(BaseModel):
    software_name: str
    evaluation_type: str

    overall_status: CheckStatus
    summary: str

    installed: bool
    installed_version: Optional[str] = None

    evaluated_at: datetime

    checks: list[CompatibilityCheck]

    passed_count: int
    failed_count: int
    warning_count: int
    unknown_count: int
