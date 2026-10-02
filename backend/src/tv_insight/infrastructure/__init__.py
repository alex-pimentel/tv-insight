"""Infrastructure layer.

Adapters that implement the ports declared by the inner layers:
HTTP clients, AI providers, SQLAlchemy persistence and the composition root.
This is the only place allowed to import third-party libraries.
"""
