"""A Person = soul + body + emergent personality for one lifetime.

The person is the join of the persistent soul and the temporary body. Its
*current personality* (self-awareness, impulsiveness) is derived from both and
is NOT the same thing as the deep soul-state — a calm soul in a highly reactive
body can behave impulsively, and vice versa. That gap is where realistic
contradiction lives.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List
from uuid import UUID

from .body import Body
from .soul import SoulState, clamp


@dataclass
class Person:
    soul: SoulState
    body: Body

    # running trace of alignment choices this life, in [-1, +1]
    _alignment_trace: List[float] = field(default_factory=list)
    partner_id: object = None  # body_id of current partner, or None
    is_avatar: bool = False    # a liberated soul that has voluntarily descended

    # v2: veto fatigue — freedom is metabolically expensive. Each veto attempt
    # costs; rest recovers. Bodily, so it resets with each new life.
    fatigue: float = 0.0

    # v3: the bond — years together with the current partner. Conception rises
    # with a settled bond; drifting apart can dissolve it.
    bond_years: int = 0

    # culture: the name the world knows this body by (minted at first public
    # trace), and the grooves laid by hearing stories — weak, this-life-only
    # samskaras acquired by shravana. Amoral: stories groove availability of
    # WHATEVER act they claim, aligned or vile.
    name_token: object = None
    cultural: Dict[str, float] = field(default_factory=dict)

    # v4: the life ledger — what this incarnation did with its choices. At death
    # it consolidates into the soul's history, making the life narratable.
    life_veto: int = 0
    life_akrasia: int = 0
    life_unseen: int = 0
    life_effortless: int = 0
    notable: List[str] = field(default_factory=list)
    start_virtue: float = 0.0
    start_enemy: str = ""

    def snapshot_start(self) -> None:
        from .soul import CORE_VIRTUES, INSTABILITIES
        self.start_virtue = sum(getattr(self.soul, v) for v in CORE_VIRTUES) / len(CORE_VIRTUES)
        self.start_enemy = max(INSTABILITIES, key=lambda x: getattr(self.soul, x))

    @property
    def body_id(self) -> UUID:
        return self.body.body_id

    @property
    def alive(self) -> bool:
        return self.body.alive

    @property
    def age(self) -> int:
        return self.body.age

    def is_adult(self, adult_age: int) -> bool:
        return self.body.alive and self.body.age >= adult_age

    # -- emergent personality (soul x body) --------------------------------
    @property
    def self_awareness(self) -> float:
        """Capacity to notice one's own active parameters and choose among them.
        This is the seat of free will in the model."""
        g = self.body.genome
        intel = g.intelligence_potential if g else 0.5
        base = (0.10
                + 0.45 * self.soul.discernment
                + 0.25 * self.soul.unity_awareness
                + 0.20 * intel)
        # Reflection cannot exceed the ceiling earned on the yoni ladder: a soul
        # freshly arrived at human birth is greener than one long-matured.
        ceiling = 0.5 + 0.5 * self.soul.capacity
        return clamp(base * ceiling)

    @property
    def impulsiveness(self) -> float:
        """Behavioural temperature — how much noise/urge overrides deliberation."""
        g = self.body.genome
        react = g.emotional_sensitivity if g else 0.5
        aggr = g.aggression_tendency if g else 0.5
        return clamp(0.20
                     + 0.35 * react
                     + 0.20 * aggr
                     + 0.30 * self.soul.krodha   # anger fuels impulsive reactivity
                     - 0.30 * self.soul.discernment)

    # -- karmic bookkeeping ------------------------------------------------
    def record_alignment(self, al: float) -> None:
        self._alignment_trace.append(al)

    def alignment_consistency(self) -> float:
        """Running mean alignment mapped to [0,1]. Consistency, not one heroic act,
        is what integrates a lesson."""
        if not self._alignment_trace:
            return 0.5
        m = sum(self._alignment_trace) / len(self._alignment_trace)
        return clamp((m + 1.0) / 2.0)

    # -- v2: the charioteer's effective strength in THIS vessel --------------
    @property
    def buddhi_power(self) -> float:
        """The soul's trained buddhi, expressed through this body's capacity and
        steadied by unity_awareness. This is what enters the veto contest."""
        return clamp(0.6 * self.soul.buddhi
                     + 0.25 * self.soul.unity_awareness
                     + 0.15 * self.soul.capacity)
