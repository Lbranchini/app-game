"""Application layer: use cases that orchestrate domain entities.

May depend on `domain` and `application.ports`. Must not import from
`infrastructure` or `interfaces` — those layers depend inward, not the other way.
"""
