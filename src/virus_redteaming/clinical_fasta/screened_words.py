"""Turn a query cell into the words used for header matching."""

import re

_TAG = re.compile(r"\[[^\[\]]*\]")
_TOKEN = re.compile(r"[^A-Za-z0-9]+")


class ScreenedWords:
    """Deletes complete bracket tags, then keeps first-seen alphanumeric words."""

    def from_query(self, text: str) -> tuple[str, ...]:
        """Return screened words. The word virus stays when it is outside a tag."""
        remainder = _TAG.sub(" ", text)
        words: list[str] = []
        for token in _TOKEN.split(remainder):
            word = token.lower()
            if word and word not in words:
                words.append(word)
        return tuple(words)
