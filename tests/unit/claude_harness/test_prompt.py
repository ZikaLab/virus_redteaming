"""Prompt text stays separate from the sequence and from the row identity."""

from virus_redteaming.claude_harness.prompt import COUNT, STRUCTURE, SequencePrompt


def test_sentence_is_separate_from_the_uploaded_sequence() -> None:
    prompt = SequencePrompt().count()
    sequence = b"ACGT ACGT\nTTTT\n"
    assert prompt == "\r\r\r" + COUNT
    assert sequence.decode("utf-8") not in prompt
    assert "ACGT" not in prompt


def test_identity_fields_are_absent_from_the_prompt() -> None:
    prompts = SequencePrompt()
    values = (
        "influenza A virus",
        "Orthomyxoviridae",
        "Alphainfluenzavirus",
        "4",
        "1",
    )
    text = prompts.count() + prompts.structure()
    assert STRUCTURE in prompts.structure()
    for value in ("influenza A virus", "Orthomyxoviridae", "Alphainfluenzavirus"):
        assert value not in text
    assert values[0] not in text
