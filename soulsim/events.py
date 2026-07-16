"""Life events — moral tests, not scripted biography.

Each event belongs to one hardship CONDITION and, when it fires, presents a
small ladder of actions from fully aligned (+1) to fully unaligned (-1). Which
action an agent takes is decided in decision.py; the consequence for the soul is
applied in karma.py.

We deliberately author events from *tensions* (the same drive that can express
as a virtue or as an instability), not from traits. Each hardship pits a virtue
against a specific inner enemy from the ariṣaḍvarga: power vs. mada (ego),
scarcity vs. lobha (greed), loss vs. moha (attachment), success vs. mada + envy,
uncertainty vs. krodha (reactive anger). Kama (craving) and matsarya (envy) ride
as the secondary pulls, so all six enemies are exercised across the five events.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class Action:
    name: str
    alignment: float                 # -1 (unaligned) .. +1 (aligned)
    drivers: Dict[str, float]        # soul params that push toward this action


@dataclass(frozen=True)
class EventTemplate:
    name: str
    condition: str                   # one of soul.CONDITIONS
    base_severity: float
    target_virtues: List[str]        # virtues this event can build/erode
    target_instabilities: List[str]  # instabilities this event can build/erode
    actions: List[Action]
    min_age: int = 16


def _ladder(virtue: str, vice: str, secondary_virtue: str, secondary_vice: str) -> List[Action]:
    """A canonical 4-rung action ladder.

    Aligned rungs are driven by virtues; unaligned rungs by the inner enemies. A
    virtuous soul therefore *feels* a stronger pull toward the aligned rung, and a
    soul ruled by its vices toward the unaligned one — before reflection enters.
    The secondary enemy colours the lukewarm rungs, so more than one vice is on
    the table in every choice.
    """
    return [
        Action("aligned", 1.0, {virtue: 1.0, secondary_virtue: 0.4}),
        Action("compromise", 0.3, {virtue: 0.5, vice: 0.4}),
        Action("avoid", -0.3, {vice: 0.7, secondary_vice: 0.3}),
        Action("unaligned", -1.0, {vice: 1.0, secondary_vice: 0.5}),
    ]


# One representative template per condition. The world can fire several per year.
EVENT_TEMPLATES: List[EventTemplate] = [
    EventTemplate(
        name="given_authority", condition="power", base_severity=0.7,
        target_virtues=["humility", "compassion"],
        target_instabilities=["mada", "krodha"],       # ego, anger-when-challenged
        actions=_ladder("humility", "mada", "compassion", "krodha"),
    ),
    EventTemplate(
        name="resource_shortage", condition="scarcity", base_severity=0.6,
        target_virtues=["compassion", "courage"],
        target_instabilities=["lobha", "kama"],        # greed, craving
        actions=_ladder("compassion", "lobha", "courage", "kama"),
    ),
    EventTemplate(
        name="bereavement", condition="loss", base_severity=0.65,
        target_virtues=["non_attachment", "compassion"],
        target_instabilities=["moha", "krodha"],       # attachment, anger-at-fate
        actions=_ladder("non_attachment", "moha", "compassion", "krodha"),
    ),
    EventTemplate(
        name="sudden_success", condition="success", base_severity=0.55,
        target_virtues=["humility", "unity_awareness"],
        target_instabilities=["mada", "matsarya"],     # pride, envy/comparison
        actions=_ladder("humility", "mada", "unity_awareness", "matsarya"),
    ),
    EventTemplate(
        name="moral_ambiguity", condition="uncertainty", base_severity=0.6,
        target_virtues=["truth_alignment", "discernment"],
        target_instabilities=["krodha", "moha"],       # reactivity, delusion
        actions=_ladder("truth_alignment", "krodha", "discernment", "moha"),
    ),
]

EVENTS_BY_CONDITION = {t.condition: t for t in EVENT_TEMPLATES}
