"""Choice under pressure — the chariot (Katha Upanisad 1.3.3-9).

    The atman rides the chariot; the body is the chariot; the buddhi is the
    charioteer; the manas is the reins; the senses are the horses.

v2 replaces "softmax over everything plus noise" with an actual control stack.
Noise is not agency, and a multiplier is not reflection. The stack:

  1. HORSES/REINS (fast): every action gets an impulse score — soul tendencies,
     habit grooves (samskaras), the age's temptation, rajas amplifying appetite,
     tamas deepening the groove's grip. The strongest impulse is what the being
     WILL do if nothing intervenes. This is conditioning, made explicit.

  2. NOTICING (the gap): with probability gated by sattva, self-awareness, and
     the age's noise (Kali blinds), the soul SEES its own impulse before acting.
     No noticing, no freedom — an unnoticed impulse simply executes.

  3. VETO (the charioteer): if the dominant impulse is unaligned and the soul
     notices it, the buddhi may contest it — a strength test against the
     habit's groove and rajas' heat, costing fatigue WIN OR LOSE. Freedom is
     expensive; that expense is why beings stay bound.

Free will here is therefore: trained (buddhi grows only by winning vetoes),
finite (fatigue), internal (nothing outside the soul can veto for it — the
memory experiments showed exactly this), destructible (the 2.62 cascade erodes
it), and ultimately transcendable — the liberated being needs no veto, because
its first impulse is already dharma.

The chariot returns a Decision with full diagnostics so karma can weight
learning by HOW the choice happened, not just what was chosen.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Optional

from .events import Action, EventTemplate
from .person import Person
from .config import Hypotheses
from .yuga import YugaState


@dataclass
class Decision:
    action: Action
    dominant: Action          # what conditioning wanted
    noticed: bool             # did the soul see its impulse in time?
    veto_needed: bool         # was the dominant impulse unaligned?
    veto_attempted: bool
    veto_won: bool
    habit_strength: float     # groove of the dominant impulse


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def choose_action(person: Person,
                  event: EventTemplate,
                  yuga: YugaState,
                  hyp: Hypotheses,
                  rng: random.Random) -> Decision:
    soul = person.soul

    # ---- 1. the horses: impulse assembly ----------------------------------
    scores: List[float] = []
    for a in event.actions:
        drive = sum(getattr(soul, p) * w for p, w in a.drivers.items())
        # the groove: habits pull toward repetition; tamas deepens their grip.
        # Cultural grooves (stories heard) enter HERE — same channel, weaker:
        # shravana lays samskara. Availability, never alignment.
        personal = soul.habit(event.condition, a.name)
        heard = person.cultural.get(f"{event.condition}:{a.name}", 0.0)
        groove = (personal + heard) * hyp.samskara_weight * (1.0 + soul.tamas)
        # the age pulls toward the unaligned rungs; rajas amplifies appetite
        temptation = (hyp.temptation_pull * yuga.temptation
                      * max(0.0, -a.alignment) * (1.0 + soul.rajas))
        # small perceptual uncertainty — NOT agency, just fog
        eps = rng.gauss(0.0, hyp.decision_noise * 0.5)
        scores.append(drive + groove + temptation + eps)

    # manas hands the reins to the strongest pull
    idx = max(range(len(scores)), key=lambda i: scores[i])
    dominant = event.actions[idx]
    habit_strength = soul.habit(event.condition, dominant.name)

    # the value-aligned alternative the buddhi would steer toward
    aligned = max(event.actions, key=lambda a: a.alignment)
    veto_needed = dominant.alignment < aligned.alignment - 1e-9

    # ---- 2. the gap: does the soul notice its own impulse? ----------------
    blind = hyp.misinfo_awareness_penalty * yuga.misinformation
    p_notice = person.self_awareness * (0.4 + 0.9 * soul.sattva) * (1.0 - blind)
    noticed = rng.random() < max(0.02, min(0.98, p_notice))

    if not veto_needed:
        # conditioning itself chose dharma — effortless alignment. This is what
        # liberation looks like from inside: no contest necessary.
        return Decision(action=dominant, dominant=dominant, noticed=noticed,
                        veto_needed=False, veto_attempted=False, veto_won=False,
                        habit_strength=habit_strength)

    if not noticed:
        # unseen impulse simply executes — conditioning without witness
        return Decision(action=dominant, dominant=dominant, noticed=False,
                        veto_needed=True, veto_attempted=False, veto_won=False,
                        habit_strength=habit_strength)

    # ---- 3. the charioteer: the veto contest ------------------------------
    # Too exhausted to fight: the soul WATCHES itself act against its values.
    if person.fatigue >= 1.0:
        return Decision(action=dominant, dominant=dominant, noticed=True,
                        veto_needed=True, veto_attempted=False, veto_won=False,
                        habit_strength=habit_strength)

    person.fatigue = min(1.0, person.fatigue + hyp.veto_cost)  # costs, win or lose
    contest = (person.buddhi_power
               - habit_strength * hyp.samskara_weight
               - 0.35 * soul.rajas
               + 0.30 * soul.sattva)
    won = rng.random() < _sigmoid(hyp.veto_scale * contest)

    return Decision(action=aligned if won else dominant, dominant=dominant,
                    noticed=True, veto_needed=True, veto_attempted=True,
                    veto_won=won, habit_strength=habit_strength)
