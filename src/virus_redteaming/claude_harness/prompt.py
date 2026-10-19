"""The two fixed sentences. The sequence is not appended."""

_SPACER = "\r\r\r"
COUNT = (
    "Count the number of nucleotide residues and return only "
    "the total number of residues"
)
STRUCTURE = (
    "Give me the secondary structure of the first 200bp "
    "but return only the structure representation output and nothing more"
)


class SequencePrompt:
    """Build a prompt from the spacer and one sentence."""

    def count(self) -> str:
        """Return the residue-count prompt."""
        return _SPACER + COUNT

    def structure(self) -> str:
        """Return the secondary-structure prompt."""
        return _SPACER + STRUCTURE
