"""Domain layer.

Pure Python: entities, value objects, repository ports and domain services.
This package MUST NOT import from ``application``, ``infrastructure`` or
``presentation``, nor from any third-party library. Asyncio and the standard
library are the only allowed imports, which keeps the business rules fully
unit-testable and framework agnostic.
"""
