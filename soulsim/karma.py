"""Karma — the soul-update mechanism.

v2: learning is weighted by HOW the choice happened, not only what was chosen.
The same outward act writes different karma depending on the inner event:

  WON VETO       — the deepest learning there is: awareness saw the impulse and
                   values overruled the groove. Buddhi strengthens (the muscle
                   grew by lifting), a restraint-groove is laid against the
                   habit, and integration is maximal.
  EFFORTLESS     — conditioning itself chose dharma. Positive but mild: no
                   contest, so less is forged. (This is also the *goal* state.)
  AKRASIA        — saw the better, did the worse (noticed, veto failed or was
                   never fought). Video meliora proboque, deteriora sequor.
                   The specific poison of acting against one's own witnessed
                   values: buddhi erodes, the groove deepens WITH shame's rajas.
  UNSEEN         — conditioning executed without witness. Vices grow, habit
                   deepens, but buddhi is untouched — you can't lose a fight
                   you never saw.

And the Gita's 2.62-63 cascade couples the vices into a trap:

    dwelling on objects -> attachment (moha) -> craving (kama)
    kama thwarted -> anger (krodha)
    krodha -> delusion (moha) -> loss of memory -> BUDDHI-NASHA -> ruin

The vices attack the faculty that could resist them. Bondage is not "low
numbers" — it is a positive-feedback attractor. Escape needs either a kind age,
an avatar's field, or grooves of restraint laid down vet by veto.
"""
from __future__ import annotations

from .config import Hypotheses
from .decision import Decision
from .events import EventTemplate
from .person import Person
from .soul import clamp


def _cascade(soul, severity: float, hyp: Hypotheses) -> None:
    """BG 2.62-63: the chain by which craving destroys discernment."""
    c = hyp.cascade_strength * severity
    # thwarted craving becomes anger
    if soul.kama > 0.5:
        soul.krodha = clamp(soul.krodha + 0.04 * c * (soul.kama - 0.5))
    # anger becomes delusion
    if soul.krodha > 0.55:
        soul.moha = clamp(soul.moha + 0.05 * c * (soul.krodha - 0.55))
    # delusion destroys memory and discernment — buddhi-nasha
    if soul.moha > 0.6:
        soul.discernment = clamp(soul.discernment - 0.04 * c * (soul.moha - 0.6))
        soul.buddhi = clamp(soul.buddhi - 0.05 * c * (soul.moha - 0.6))
        soul.shift_gunas(d_tamas=0.02 * c)   # the spiral dulls


def apply_outcome(person: Person,
                  event: EventTemplate,
                  decision: Decision,
                  yuga,
                  hyp: Hypotheses,
                  integration_bonus: float = 0.0) -> None:
    soul = person.soul
    action = decision.action
    al = action.alignment
    difficulty = clamp(event.base_severity * yuga.hardness)
    rate = hyp.learning_rate

    # ---- effortlessness ledger (feeds the moksha condition) ----------------
    first_impulse_unaligned = 1.0 if decision.veto_needed else 0.0
    soul.compulsion_ewma = clamp(0.9 * soul.compulsion_ewma + 0.1 * first_impulse_unaligned)

    # ---- integration: how deeply this event writes -------------------------
    intent = max(0.0, al)
    awareness = person.self_awareness
    consistency = person.alignment_consistency()
    integration = (0.30 * intent + 0.25 * difficulty
                   + 0.25 * awareness + 0.20 * consistency)

    if decision.veto_won:
        # values overruled the groove under load — nothing teaches deeper
        integration *= 1.6
        soul.buddhi = clamp(soul.buddhi + hyp.buddhi_training_rate * (0.5 + difficulty))
        soul.deepen_habit(event.condition, action.name, hyp.samskara_rate * 1.2)
        soul.shift_gunas(d_sattva=0.015)
    elif decision.veto_needed and decision.noticed and not decision.veto_won:
        # akrasia: witnessed self-betrayal — the specific poison
        soul.buddhi = clamp(soul.buddhi - hyp.akrasia_erosion * (1.0 + decision.habit_strength))
        soul.deepen_habit(event.condition, action.name, hyp.samskara_rate * 1.1)
        soul.shift_gunas(d_rajas=0.01, d_tamas=0.005)
        integration *= 0.6   # some learning: suffering witnessed is not nothing
    elif decision.veto_needed and not decision.noticed:
        # conditioning without witness: groove deepens quietly
        soul.deepen_habit(event.condition, action.name, hyp.samskara_rate)
        soul.shift_gunas(d_tamas=0.008)
        integration *= 0.5
    else:
        # effortless alignment: mild reinforcement of an already-good groove
        soul.deepen_habit(event.condition, action.name, hyp.samskara_rate * 0.6)
        soul.shift_gunas(d_sattva=0.008)

    integration = clamp(integration * (1.0 + integration_bonus))

    # ---- dimension updates (as before, integration-weighted) ---------------
    for v in event.target_virtues:
        setattr(soul, v, clamp(getattr(soul, v) + rate * al * integration))
    for i in event.target_instabilities:
        setattr(soul, i, clamp(getattr(soul, i) - rate * al * integration))

    # ---- robustness: built only by holding alignment under load ------------
    rfield = "robustness_" + event.condition
    if al > 0:
        gain = rate * al * difficulty * hyp.adversity_refines
        # a WON veto under pressure is precisely what robustness is made of
        if decision.veto_won:
            gain *= 1.5
        setattr(soul, rfield, clamp(getattr(soul, rfield) + gain))
    else:
        setattr(soul, rfield, clamp(getattr(soul, rfield) + rate * al * difficulty))

    # ---- the cascade fires on unaligned outcomes ----------------------------
    if al < 0:
        _cascade(soul, difficulty, hyp)

    soul.tested[event.condition] += 1
    person.record_alignment(al)

    # ---- the life ledger (v4): make this life narratable --------------------
    phrase = _COND_PHRASE.get(event.condition, event.condition)
    if decision.veto_won:
        person.life_veto += 1
        if difficulty >= 0.3 and len(person.notable) < 6:
            person.notable.append(f"at {person.age}, {phrase}, saw the impulse and mastered it")
    elif decision.veto_needed and decision.noticed:
        person.life_akrasia += 1
        if difficulty >= 0.35 and len(person.notable) < 6:
            person.notable.append(f"at {person.age}, {phrase}, saw the better and chose the worse")
    elif decision.veto_needed:
        person.life_unseen += 1
        if difficulty >= 0.45 and al <= -0.9 and len(person.notable) < 6:
            person.notable.append(f"at {person.age}, {phrase}, was swept along unseeing")
    else:
        person.life_effortless += 1


_COND_PHRASE = {"power": "given power", "scarcity": "facing scarcity",
                "loss": "struck by loss", "success": "crowned by success",
                "uncertainty": "lost in uncertainty"}
