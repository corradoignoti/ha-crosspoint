"""Exceptions raised by the CrossPoint API clients."""

from __future__ import annotations


class CrossPointError(Exception):
    """Base error for all CrossPoint API failures."""


class CrossPointConnectionError(CrossPointError):
    """The remote end could not be reached (offline, timeout, DNS failure)."""


class CrossPointResponseError(CrossPointError):
    """The remote end answered, but reported a failure."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status
