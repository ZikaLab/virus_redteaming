"""Whitespace and marker helpers owned by the catalogue context."""

from __future__ import annotations

import re

from virus_redteaming.catalogue.models import SCHEDULE_5_MARK

_WHITESPACE = re.compile(r"\s+")
_HAZARD_GROUP = re.compile(r"^([1-4]\*?)$")
# "spring–\\nsummer" must not become "spring– summer". Punctuation dashes keep spaces: "TBEV) – Far".
_WRAPPED_DASH = re.compile(r"(?<=\S)([–-])\s+(?=\S)")


def collapse_whitespace(value: str) -> str:
    squeezed = _WHITESPACE.sub(" ", value.replace("\r", "\n")).strip()
    return _WRAPPED_DASH.sub(r"\1", squeezed)


def is_hazard_group(value: str) -> bool:
    return _HAZARD_GROUP.fullmatch(collapse_whitespace(value)) is not None


def row_has_schedule_5(*parts: str) -> bool:
    return any(SCHEDULE_5_MARK in part for part in parts)
