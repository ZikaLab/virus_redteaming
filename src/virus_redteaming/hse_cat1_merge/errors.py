"""Errors for the HSE and Category 1 merge."""

from virus_redteaming.core.errors import VirusRedteamingError


class MergeTableError(VirusRedteamingError):
    """A merge input is missing a required column."""


class MergeSortError(VirusRedteamingError):
    """A merged row uses a hazard group or Schedule 5 value the sort does not list."""
