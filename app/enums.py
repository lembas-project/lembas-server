"""Application-wide enumerations."""

from enum import StrEnum


class CaseStatus(StrEnum):
    pending = "pending"
    running = "running"
    complete = "complete"
    failed = "failed"
