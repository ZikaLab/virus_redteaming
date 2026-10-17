"""Errors for clinical nucleotide retrieval."""

from virus_redteaming.core.errors import VirusRedteamingError


class ClinicalFastaError(VirusRedteamingError):
    """Base error for the clinical FASTA package."""


class NcbiInputError(ClinicalFastaError):
    """A local CSV, search term, or accession text is unusable."""


class NcbiConfigError(ClinicalFastaError):
    """NCBI email configuration is missing or contains whitespace."""


class NcbiSearchMiss(ClinicalFastaError):  # noqa: N818
    """Every query cell missed, or an IdList item was not a non-empty string."""


class NcbiFetchError(ClinicalFastaError):
    """NCBI transport failed or an esearch body could not be read."""


class NcbiRecordRejected(ClinicalFastaError):  # noqa: N818
    """A FASTA record failed validation, or every record was shorter than the cutoff."""


class FastaWriteError(ClinicalFastaError):
    """An accession table or FASTA file could not be replaced atomically."""
