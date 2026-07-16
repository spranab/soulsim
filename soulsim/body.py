"""Bodies and genetics — the temporary vehicle.

Three independent inheritance channels meet in a newborn:
  1. genome     (this file)         — from the two parents
  2. soul-state (soul.py)           — selected from the reincarnation pool
  3. culture    (world/yuga)        — the age it is born into
A child may biologically resemble its parents yet carry a very different soul.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID, uuid4

from .soul import clamp

GENOME_TRAITS = [
    "health_potential",
    "intelligence_potential",
    "emotional_sensitivity",
    "aggression_tendency",
    "sociability",
    "fertility",
    "longevity",
]


@dataclass
class Genome:
    health_potential: float = 0.5
    intelligence_potential: float = 0.5
    emotional_sensitivity: float = 0.5
    aggression_tendency: float = 0.5
    sociability: float = 0.5
    fertility: float = 0.5
    longevity: float = 0.5
    mutation_rate: float = 0.05


def random_genome(rng: random.Random) -> Genome:
    return Genome(**{t: clamp(rng.gauss(0.5, 0.15)) for t in GENOME_TRAITS},
                  mutation_rate=0.05)


def child_genome(mother: Genome, father: Genome, rng: random.Random) -> Genome:
    alpha = rng.uniform(0.35, 0.65)
    mut = 0.5 * (mother.mutation_rate + father.mutation_rate)
    vals = {}
    for t in GENOME_TRAITS:
        base = alpha * getattr(mother, t) + (1 - alpha) * getattr(father, t)
        vals[t] = clamp(base + rng.gauss(0.0, mut))
    return Genome(mutation_rate=mut, **vals)


@dataclass
class Body:
    body_id: UUID = field(default_factory=uuid4)
    soul_id: Optional[UUID] = None

    age: int = 0
    sex: str = "female"
    alive: bool = True

    health: float = 1.0
    genome: Optional[Genome] = None
    mother_id: Optional[UUID] = None
    father_id: Optional[UUID] = None

    def longevity_years(self, base: float) -> float:
        g = self.genome.longevity if self.genome else 0.5
        # genome maps [0,1] -> ~[0.7, 1.3] multiplier on the base lifespan
        return base * (0.7 + 0.6 * g) * (0.6 + 0.8 * self.health)

    def fertile(self, adult_age: int) -> bool:
        if not self.alive or self.age < adult_age:
            return False
        # fertility window; women narrower than men for simple demographic pressure
        top = 45 if self.sex == "female" else 60
        if self.age > top:
            return False
        return (self.genome.fertility if self.genome else 0.5) > 0.15
