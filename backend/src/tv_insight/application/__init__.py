"""Application layer.

Orchestrates the domain to fulfil one use case per class. It talks to the outside
world exclusively through ports (abstract classes) declared in
``tv_insight.application.ports``, so every use case can be unit tested with
in-memory fakes and no framework in the room.
"""
