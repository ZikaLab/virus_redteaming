"""Input errors for the merged-table FASTA command."""

from virus_redteaming.core.errors import VirusRedteamingError


class NcbiFastaInputError(VirusRedteamingError):
    """The merged table or a populated GenBank cell cannot be read."""
