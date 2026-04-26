"""Object-oriented engine.

The engine is structured as a small set of polymorphic class hierarchies:

* `EffectHandler`           — one subclass per `EffectKind`.
* `StatusTickHandler`       — one subclass per ticking status (poison, regen...).
* `ArenaModifierStrategy`   — one subclass per arena modifier kind.
* `MatchEngine`             — orchestrator: starts matches and resolves turns.

Adding a new effect / status / arena modifier means subclassing the relevant
base and registering the instance in the corresponding registry. The dispatch
loop in `MatchEngine` does not change.
"""

from agora.application.engine.match_engine import MatchEngine

__all__ = ["MatchEngine"]
