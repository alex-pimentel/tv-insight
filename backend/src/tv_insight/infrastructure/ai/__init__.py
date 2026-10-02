"""AI provider adapters.

Every provider implements the same port, so the use case that generates an
insight never learns which vendor answered. The chain that decides *who* gets
asked lives in ``factory.py``.
"""

from tv_insight.infrastructure.ai.caching import CachingInsightProvider
from tv_insight.infrastructure.ai.fallback import FallbackInsightProvider
from tv_insight.infrastructure.ai.heuristic import HeuristicInsightProvider
from tv_insight.infrastructure.ai.huggingface import HuggingFaceInsightProvider
from tv_insight.infrastructure.ai.openrouter import OpenRouterInsightProvider

__all__ = [
    "CachingInsightProvider",
    "FallbackInsightProvider",
    "HeuristicInsightProvider",
    "HuggingFaceInsightProvider",
    "OpenRouterInsightProvider",
]
