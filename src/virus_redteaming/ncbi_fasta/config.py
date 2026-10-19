"""Entrez identity for this command. The clinical tool name stays unchanged."""

import os

from virus_redteaming.clinical_fasta.config import NcbiEntrezConfig

TOOL = "virus_redteaming_ncbi_fasta"


def entrez_config_from_environment() -> NcbiEntrezConfig:
    """Read ``NCBI_EMAIL`` and the optional ``NCBI_API_KEY``."""
    email = os.environ.get("NCBI_EMAIL", "")
    raw_key = os.environ.get("NCBI_API_KEY", "")
    api_key = raw_key if raw_key else None
    return NcbiEntrezConfig(email=email, tool=TOOL, api_key=api_key)
