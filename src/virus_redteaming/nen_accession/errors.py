"""Errors for the nen accession copy."""

from virus_redteaming.core.errors import VirusRedteamingError


class NenAccessionError(VirusRedteamingError):
    """A nen accession input could not be read."""


class NenTableError(NenAccessionError):
    """output/nen_viruses.csv is missing a required column."""


class VmrTableError(NenAccessionError):
    """The VMR CSV is missing a required column."""
