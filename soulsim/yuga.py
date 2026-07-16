"""The yuga cycle — the changing global difficulty distribution.

The four ages are not a moral calendar; they are four training distributions.
Satya is supervised-learning-easy (truth visible, temptation low); Kali is the
adversarial regime (truth buried in noise, temptation high, impulsiveness
amplified). The same soul faces the same kinds of test in every age, but the
*difficulty* of holding alignment differs — which is why passage through the
hard ages is what actually builds robustness.

A full mahayuga runs S:T:D:K in the classical 4:3:2:1 proportion, then a
pralaya resets into the next cosmic cycle.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class YugaState:
    name: str
    hardness: float          # multiplies event difficulty
    temptation: float        # environmental pull toward unaligned rungs
    misinformation: float    # blinds reflection (truth hard to see)
    truth_visibility: float  # inverse-ish of misinformation, kept for metrics/flavour
    # v2: each age has an ambient guna climate that souls drift toward.
    # Satya is sattvic (clarity is cheap); Kali is rajas+tamas heavy (agitation
    # and inertia are the weather, and the charioteer works uphill).
    ambient_sattva: float = 0.34
    ambient_rajas: float = 0.33
    ambient_tamas: float = 0.33


SATYA = YugaState("Satya", hardness=0.35, temptation=0.10, misinformation=0.10, truth_visibility=0.95,
                  ambient_sattva=0.62, ambient_rajas=0.23, ambient_tamas=0.15)
TRETA = YugaState("Treta", hardness=0.55, temptation=0.30, misinformation=0.30, truth_visibility=0.75,
                  ambient_sattva=0.48, ambient_rajas=0.32, ambient_tamas=0.20)
DVAPARA = YugaState("Dvapara", hardness=0.75, temptation=0.55, misinformation=0.55, truth_visibility=0.50,
                    ambient_sattva=0.34, ambient_rajas=0.40, ambient_tamas=0.26)
KALI = YugaState("Kali", hardness=1.00, temptation=0.85, misinformation=0.85, truth_visibility=0.22,
                 ambient_sattva=0.20, ambient_rajas=0.45, ambient_tamas=0.35)

# Classical 4:3:2:1 proportions, scaled down so several cycles fit a 2000y run.
_SEQUENCE: List[tuple] = [
    (SATYA, 200),
    (TRETA, 150),
    (DVAPARA, 100),
    (KALI, 50),
]
MAHAYUGA_YEARS = sum(length for _, length in _SEQUENCE)


class YugaClock:
    """Maps an absolute year to the current yuga and cosmic-cycle index."""

    def __init__(self) -> None:
        self.sequence = _SEQUENCE
        self.period = MAHAYUGA_YEARS

    def at(self, year: int):
        cosmic_cycle = year // self.period
        offset = year % self.period
        for yuga, length in self.sequence:
            if offset < length:
                return yuga, cosmic_cycle
            offset -= length
        # Shouldn't happen, but fall back to Kali.
        return KALI, cosmic_cycle
