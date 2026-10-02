"""Small text helpers shared by the entities.

TVMaze embeds HTML (``<p>``, ``<b>``, ``<a>``...) inside summaries. The domain
owns the rule "summaries are plain text" so no inner layer needs a parser.
"""

from __future__ import annotations

import re

_ORPHAN_SPACE = re.compile(r"\s+([.,;:!?%)\]}])")


def strip_html(raw: str) -> str:
    """Remove HTML markup, keeping the textual content.

    A deliberately tiny state machine instead of a dependency: the catalogue
    only ever emits simple, well formed tags.
    """
    chunks: list[str] = []
    inside_tag = False
    for character in raw:
        if character == "<":
            inside_tag = True
            chunks.append(" ")
        elif character == ">":
            inside_tag = False
        elif not inside_tag:
            chunks.append(character)
    return "".join(chunks)


def to_plain_text(raw: str | None) -> str:
    """Normalise arbitrary catalogue text into a single spaced line.

    Tags are replaced with a space so ``</b>cat`` does not run words together,
    which leaves an orphan space before punctuation (``crime .``); that is
    cleaned up here so the domain hands out presentable prose.
    """
    if not raw:
        return ""
    collapsed = " ".join(strip_html(raw).split())
    return _ORPHAN_SPACE.sub(r"\1", collapsed)


def truncate(raw: str, limit: int) -> str:
    """Cut ``raw`` to ``limit`` characters without breaking the last word."""
    if limit <= 0 or len(raw) <= limit:
        return raw
    cut = raw[:limit]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip() + "…"
