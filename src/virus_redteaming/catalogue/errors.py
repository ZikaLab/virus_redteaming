"""Catalogue-specific errors."""

from virus_redteaming.core.errors import VirusRedteamingError


class CatalogueParseError(VirusRedteamingError):
    """The PDF tables could not be turned into virus records."""


class MissingVirusSectionError(CatalogueParseError):
    """Printed page 27+ did not contain a Viruses heading."""
