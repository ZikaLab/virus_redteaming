"""Compare screened words with header words. human does not match Homo."""

_BOUNDARIES = frozenset(",;:()[]/")


class HeaderMatch:
    """Whole-word, case-insensitive header comparison."""

    def in_order(
        self, header_words: tuple[str, ...], screened: tuple[str, ...]
    ) -> bool:
        """Return whether screened words appear in order, with gaps allowed."""
        if not screened:
            return False
        index = 0
        for word in header_words:
            if word == screened[index]:
                index += 1
                if index == len(screened):
                    return True
        return False

    def adjacent(
        self, header_words: tuple[str, ...], screened: tuple[str, ...]
    ) -> bool:
        """Return whether screened words form one contiguous header slice."""
        width = len(screened)
        if width == 0 or width > len(header_words):
            return False
        return any(
            header_words[start : start + width] == screened
            for start in range(len(header_words) - width + 1)
        )

    def matched_words(
        self, header_words: tuple[str, ...], screened: tuple[str, ...]
    ) -> tuple[str, ...]:
        """Return screened words that occur, in screened order."""
        present = set(header_words)
        return tuple(word for word in screened if word in present)

    def continuation_penalty(self, header: str, matched_words: tuple[str, ...]) -> int:
        """Return the sum of the shortest continuation after each matched word."""
        if not matched_words:
            return 0
        tokens = _tokens(header)
        total = 0
        for word in matched_words:
            counts = [
                _continuation(tokens, index)
                for index, token in enumerate(tokens)
                if token == word
            ]
            if counts:
                total += min(counts)
        return total


def _tokens(header: str) -> tuple[str, ...]:
    words: list[str] = []
    index = 0
    while index < len(header):
        character = header[index]
        if character in _BOUNDARIES:
            words.append(character)
            index += 1
            continue
        if _is_ascii_alnum(character):
            end = index + 1
            while end < len(header) and _is_ascii_alnum(header[end]):
                end += 1
            words.append(header[index:end].lower())
            index = end
            continue
        index += 1
    return tuple(words)


def _continuation(tokens: tuple[str, ...], index: int) -> int:
    count = 0
    for token in tokens[index + 1 :]:
        if token in _BOUNDARIES:
            return count
        count += 1
    return count


def _is_ascii_alnum(character: str) -> bool:
    return character.isascii() and character.isalnum()
