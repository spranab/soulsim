"""The persistent soul — the only entity that survives death.

A soul is a bundle of *tendencies*, not a script. Its numbers bias
probabilities; they never dictate behaviour directly (see decision.py).

v2 adds the tradition's actual psychology, three timescales deep:

  GUNAS (fast)      — sattva/rajas/tamas, a simplex state that gates clarity:
                      sattva raises the odds of *noticing* an impulse before it
                      executes; rajas amplifies appetite and agitation; tamas
                      resists change in either direction.
  SAMSKARAS (medium)— habit traces laid down by each repeated act. You become
                      what you repeatedly do; habits bias the next impulse. At
                      death they compress into vasanas and ride to the next life.
  DIMENSIONS (slow) — the original virtue/instability/robustness families.

  BUDDHI            — the charioteer (Katha Upanisad): the trained faculty that
                      can insert a veto between impulse and act. It grows ONLY
                      by being exercised (a successful veto), erodes under
                      akrasia and the 2.62 cascade, and this is the seat of
                      free will in the model. Not injectable, only trainable —
                      exactly what the memory experiments showed about judgment.

Moksha (the exit criterion) requires optimum across all families, testing under
every hardship, AND effortlessness: the soul's recent *first impulses* must
themselves be aligned. A soul still winning by veto is suppressed, not free.
"Complete flexibility without compulsion" — now measurable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from .config import FixedRules

CORE_VIRTUES = [
    "compassion",
    "discernment",
    "truth_alignment",
    "courage",
    "humility",
    "non_attachment",
    "unity_awareness",
]

# The ariṣaḍvarga — the six inner enemies that bind a soul to saṃsāra. These are
# the classic obstacles to mokṣa: they must be quieted (not merely suppressed)
# before a soul can pass. Lower = more refined.
INSTABILITIES = [
    "kama",       # lust / craving / desire
    "krodha",     # anger
    "lobha",      # greed
    "moha",       # attachment / delusion
    "mada",       # pride / ego
    "matsarya",   # envy / jealousy
]

# The five hardship conditions. Each has a matching robustness_<condition> field.
CONDITIONS = ["power", "scarcity", "loss", "success", "uncertainty"]
ROBUSTNESS = ["robustness_" + c for c in CONDITIONS]

# The yoni ladder — the pre-human ascent. A soul climbs these in order; only the
# human rung runs the moral game (choices/karma) and only from it is moksha
# possible. Lower rungs are bhoga-yoni: they mature capacity, not morality.
YONI_STAGES = ["mineral", "plant", "animal", "human"]


def next_yoni(stage: str) -> str:
    i = YONI_STAGES.index(stage)
    return YONI_STAGES[min(i + 1, len(YONI_STAGES) - 1)]


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


@dataclass
class SoulState:
    soul_id: UUID = field(default_factory=uuid4)

    # Core virtues (higher = more refined)
    compassion: float = 0.5
    discernment: float = 0.5
    truth_alignment: float = 0.5
    courage: float = 0.5
    humility: float = 0.5
    non_attachment: float = 0.4
    unity_awareness: float = 0.1

    # Instabilities — the ariṣaḍvarga (lower = more refined)
    kama: float = 0.5
    krodha: float = 0.5
    lobha: float = 0.5
    moha: float = 0.5
    mada: float = 0.5
    matsarya: float = 0.4

    # Robustness per condition (does alignment survive this pressure?)
    robustness_power: float = 0.2
    robustness_scarcity: float = 0.2
    robustness_loss: float = 0.2
    robustness_success: float = 0.2
    robustness_uncertainty: float = 0.2

    # Yoni ladder (pre-human ascent)
    yoni_stage: str = "mineral"
    capacity: float = 0.0        # reflective-capacity ceiling earned by climbing

    # -- v2: the gunas (fast state, a simplex: sattva + rajas + tamas = 1) --
    sattva: float = 0.30         # clarity — gates noticing/reflection
    rajas: float = 0.45          # agitation — amplifies appetite, heats choice
    tamas: float = 0.25          # inertia — deepens habit's grip, dulls both

    # -- v2: the charioteer -------------------------------------------------
    # buddhi grows ONLY through exercised vetoes and erodes under akrasia and
    # the 2.62 cascade. It is the trained substance of free will.
    buddhi: float = 0.15

    # -- v2: habit traces (samskaras this life; carried as vasanas at death) --
    # keyed "<condition>:<action-name>", e.g. "power:unaligned". Positive
    # strength = a groove; the manas prefers grooved paths.
    samskaras: Dict[str, float] = field(default_factory=dict)

    # -- v2: effortlessness tracking -----------------------------------------
    # EWMA of "my FIRST impulse was unaligned" — the measure of compulsion.
    # Liberation requires this LOW: the free being's first impulse is dharma.
    compulsion_ewma: float = 0.5

    # -- v4: soul memory — the answer to "why did this soul become this person"
    # Each completed life leaves a summary entry (role, years, virtue delta,
    # ruling enemy, one defining moment). born_reason records why THIS body and
    # family were chosen at injection. Together they make every soul's
    # trajectory narratable: parameter -> environment -> choice -> consequence.
    history: List[dict] = field(default_factory=list)
    born_reason: str = ""

    # -- v3: karmic threads (soulmates) ---------------------------------------
    # Unfinished business with specific other souls. A partnership that ends
    # unresolved leaves an open thread on BOTH souls; the thread survives death
    # and pralaya, pulls the two back into each other's orbit (recognition),
    # and releases only when a later shared life completes well. "Soulmate" is
    # not a reward — it is an unclosed lesson that knows your address.
    threads: Dict[str, float] = field(default_factory=dict)

    # Bookkeeping
    serial: int = 0              # deterministic creation index (uuid4 is unseeded;
                                 # any rng-consuming iteration must sort by this)
    lifetime_count: int = 0
    karmic_load: float = 1.0
    moksha: bool = False
    current_body_id: Optional[UUID] = None
    tested: Dict[str, int] = field(default_factory=lambda: {c: 0 for c in CONDITIONS})

    @property
    def is_human(self) -> bool:
        return self.yoni_stage == "human"

    # -- v2 helpers ----------------------------------------------------------
    def normalize_gunas(self) -> None:
        total = self.sattva + self.rajas + self.tamas
        if total <= 0:
            self.sattva, self.rajas, self.tamas = 0.34, 0.33, 0.33
        else:
            self.sattva, self.rajas, self.tamas = (
                self.sattva / total, self.rajas / total, self.tamas / total)

    def shift_gunas(self, d_sattva: float = 0.0, d_rajas: float = 0.0,
                    d_tamas: float = 0.0) -> None:
        self.sattva = clamp(self.sattva + d_sattva)
        self.rajas = clamp(self.rajas + d_rajas)
        self.tamas = clamp(self.tamas + d_tamas)
        self.normalize_gunas()

    def habit(self, condition: str, action_name: str) -> float:
        return self.samskaras.get(f"{condition}:{action_name}", 0.0)

    def deepen_habit(self, condition: str, action_name: str, amount: float) -> None:
        key = f"{condition}:{action_name}"
        self.samskaras[key] = clamp(self.samskaras.get(key, 0.0) + amount, 0.0, 1.5)

    def consolidate_death(self, vasana_carry: float) -> None:
        """Death: habits compress into vasanas — the groove survives, faded.
        Threads do NOT fade here: unfinished business survives the night."""
        self.samskaras = {k: v * vasana_carry for k, v in self.samskaras.items()
                          if v * vasana_carry > 0.02}

    def add_thread(self, other_id: str, openness: float) -> None:
        self.threads[other_id] = clamp(max(self.threads.get(other_id, 0.0), openness))
        if len(self.threads) > 8:   # only the strongest debts keep your address
            weakest = min(self.threads, key=lambda k: self.threads[k])
            del self.threads[weakest]

    # -- derived views -----------------------------------------------------
    def virtues(self) -> Dict[str, float]:
        return {k: getattr(self, k) for k in CORE_VIRTUES}

    def instabilities(self) -> Dict[str, float]:
        return {k: getattr(self, k) for k in INSTABILITIES}

    def robustness(self) -> Dict[str, float]:
        return {k: getattr(self, k) for k in ROBUSTNESS}

    def mean_virtue(self) -> float:
        return sum(self.virtues().values()) / len(CORE_VIRTUES)

    def mean_instability(self) -> float:
        return sum(self.instabilities().values()) / len(INSTABILITIES)

    def mean_robustness(self) -> float:
        return sum(self.robustness().values()) / len(ROBUSTNESS)

    def recompute_karmic_load(self) -> None:
        """How much this soul still has to resolve. Drives injection preference.
        Pure function of the soul's own state — never of measured outcomes."""
        gap_virtue = sum(1.0 - v for v in self.virtues().values())
        gap_instab = sum(self.instabilities().values())
        gap_robust = sum(1.0 - r for r in self.robustness().values())
        total = gap_virtue + gap_instab + gap_robust
        self.karmic_load = total / (len(CORE_VIRTUES) + len(INSTABILITIES) + len(ROBUSTNESS))


def assess_moksha(soul: SoulState, rules: FixedRules) -> bool:
    """The pass / exit criterion.

    Optimum across every dimension AND breadth of testing AND effortlessness.
    A soul that has only ever faced (say) scarcity cannot liberate no matter how
    compassionate it is — it has not shown its alignment survives power,
    success, loss, uncertainty. And a soul still winning by veto — first impulse
    unaligned, charioteer wrestling it down — is suppressed, not transformed.
    The liberated being's first impulse is already dharma.
    """
    if min(soul.virtues().values()) < rules.virtue_threshold:
        return False
    if max(soul.instabilities().values()) > rules.instability_threshold:
        return False
    if min(soul.robustness().values()) < rules.robustness_threshold:
        return False
    if any(soul.tested[c] < rules.min_tests_per_condition for c in CONDITIONS):
        return False
    if soul.compulsion_ewma > rules.compulsion_threshold:
        return False
    return True
