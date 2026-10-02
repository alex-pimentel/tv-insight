"""The ``StoredInsight`` entity: an insight we generated and kept.

Persisting the insight (and *why* it is still valid) is what turns the AI feature
from "call an API every time" into a cost-controlled, always-available capability:

* cost, because a stored insight is served without touching the LLM;
* availability, because the last stored insight can be shown even when the
  provider is unreachable;
* traceability, because we keep which provider produced it.

Freshness is expressed as ``based_on_comment_count``: the number of comments that
were fed to the model. Summary and genres change rarely, so comments are the only
input worth watching for staleness.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from tv_insight.domain.exceptions import InvalidValue
from tv_insight.domain.value_objects import ContentTarget


@dataclass(frozen=True, slots=True)
class StoredInsight:
    """An insight about a series or an episode, plus its provenance."""

    target: ContentTarget
    target_id: int
    text: str
    provider: str
    degraded: bool
    based_on_comment_count: int
    generated_at: datetime

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise InvalidValue("StoredInsight.text must not be empty")
        if not self.provider.strip():
            raise InvalidValue("StoredInsight.provider must not be empty")
        if self.target_id <= 0:
            raise InvalidValue("StoredInsight.target_id must be positive")
        if self.based_on_comment_count < 0:
            raise InvalidValue("StoredInsight.based_on_comment_count must not be negative")
        if self.generated_at.tzinfo is None:
            raise InvalidValue("StoredInsight.generated_at must be timezone aware")

    def is_fresh_for(self, current_comment_count: int, *, threshold: int = 1) -> bool:
        """Whether this insight can still be served without regenerating.

        ``threshold`` is how many *new* comments make the insight stale. ``0``
        disables reuse entirely: the caller regenerates on every request, which is
        the behaviour the product wants by default. A positive value restores the
        cost-control rule agreed with the client ("1 comment is enough").

        The count is monotonic (comments are only ever added), so an insight can
        never become "fresh again", which keeps the rule free of clock logic.
        """
        if threshold <= 0:
            return False
        if current_comment_count < self.based_on_comment_count:
            # Defensive: only reachable if comments were deleted out of band.
            return False
        return current_comment_count - self.based_on_comment_count < threshold
