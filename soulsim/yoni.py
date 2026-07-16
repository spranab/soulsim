"""The yoni ladder — the pre-human ascent (bhoga, not karma).

Souls climb mineral -> plant -> animal -> human. Lower rungs do NOT make moral
choices and accrue no virtue/instability change; they only *mature capacity* —
the reflective ceiling that human life later needs in order for reflection (free
will) to function at all. The ascent is one-way: a soul never falls back down.

This subsystem is the supply chain of the whole world: it is the only source of
human souls eligible for birth. As humans liberate and leave, the ladder keeps
feeding new (greener) human souls up from below — until the reservoir drains.
"""
from __future__ import annotations

import random

from .soul import SoulState, next_yoni, clamp

# Capacity needed to promote OUT of each pre-human stage into the next.
PROMOTE_AT = {
    "mineral": 0.25,
    "plant": 0.50,
    "animal": 0.80,   # crossing this arrives at "human"
}


def mature(soul: SoulState, rate: float, rng: random.Random) -> bool:
    """Advance one pre-human soul by a year of bhoga. Returns True iff it has
    just reached the human stage this step."""
    if soul.is_human:
        return False
    soul.capacity = clamp(soul.capacity + max(0.0, rng.gauss(rate, rate * 0.4)))
    threshold = PROMOTE_AT[soul.yoni_stage]
    if soul.capacity >= threshold:
        soul.yoni_stage = next_yoni(soul.yoni_stage)
        return soul.is_human
    return False
