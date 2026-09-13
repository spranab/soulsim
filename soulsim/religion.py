"""The meta-loop — emergent religion.

The original question (the alien-visitor thread) was whether myth is *lossy
compression of real mechanics*: civilizations encoding truths about their world
in stories, which drift, ossify into institutions, corrupt, and reform. This
module closes the loop: the souls of THIS world now generate scriptures about
THIS world — and because we are the world's physics, we can grade them.

Mechanics:

  REVELATION — a clear soul (high unity_awareness x sattva, steadied by buddhi)
    occasionally perceives the world's actual workings. What it "sees" is drawn
    from GROUND_TRUTHS — the simulation's real fixed rules — with accuracy
    proportional to its clarity. Cloudy seers produce inverted doctrine.
    Perception is biased by lived experience: an age that just saw an avatar
    speaks of helpers descending; old souls speak of return.

  TRANSMISSION — a myth spreads through the population (logistic competition
    for finite attention) and MUTATES in the retelling: each proposition can
    flip or vanish, at a rate scaled by the age's misinformation. Kali corrupts
    scripture measurably.

  INSTITUTION — a myth crossing a believer threshold ossifies: canon freezes
    (mutation drops sharply), reach grows — but in dark ages power occasionally
    rewrites a true clause to false (corruption), and a later clear revelation
    within the lineage can restore it (reform).

  MEASUREMENT — doctrine_accuracy: the strength-weighted fraction of living
    propositions that match ground truth. THE question the meta-loop asks:
    when a world's own inhabitants write its scriptures through noisy ages,
    does truth survive?

Wall discipline: proposition truth values come from FIXED ontology; perception,
mutation, spread and thresholds are HYPOTHESES; accuracy is MEASURED and feeds
nothing back.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional


def W_MYTHW(universe):
    # theme myth-words if the visual layer set them; engine-neutral fallback
    return getattr(universe, "myth_words", ["Song", "Tale", "Ballad", "Saying"])

# ---------------------------------------------------------------------------
# Ground truths — statements about how THIS world actually works (fixed rules),
# paired with seductive falsehoods. Polarity True = the world really is so.
# ---------------------------------------------------------------------------
GROUND_TRUTHS: Dict[str, bool] = {
    "rebirth":            True,   # souls return in new bodies
    "ages_cycle":         True,   # the world moves through recurring ages
    "dawn_returns":       True,   # after dissolution, a golden age dawns again
    "liberation_exists":  True,   # a soul can leave the wheel forever
    "effort_frees":       True,   # exercised restraint (vetoes) loosens the wheel
    "habit_binds":        True,   # repeated acts groove the soul
    "helpers_descend":    True,   # when dharma falls, a freed one returns
    "vice_cascades":      True,   # craving breeds anger breeds delusion
    "world_ends_forever": False,  # the wheel does not stop
    "fate_is_random":     False,  # karma exists; acts matter
    "only_one_life":      False,  # there is rebirth
    "power_frees":        False,  # domination does not liberate
}
PROPS = list(GROUND_TRUTHS.keys())

MYTH_NAMES = ["Song", "Wheel", "Ember", "River", "Lotus", "Mirror", "Ladder",
              "Flame", "Veil", "Seed", "Bridge", "Bell", "Root", "Star", "Path"]


@dataclass
class Myth:
    myth_id: int
    name: str
    props: Dict[str, bool]        # proposition -> asserted polarity (doctrine claims)
    strength: float               # believers (soft count)
    born_year: int
    born_yuga: str
    institution: bool = False
    retellings: int = 0
    # narration-side: who spoke it, and what happened to it since
    seer: str = ""
    seer_role: str = ""
    seer_house: str = ""
    institution_year: object = None
    lineage: list = field(default_factory=list)   # (year, kind) events
    # story side (deeds-become-myth): an optional claim bundle about WHO did
    # WHAT at what scale. Mutates independently of the doctrine props — a false
    # biography can carry a true teaching, and vice versa.
    story: object = None          # culture.StoryClaims or None

    def accuracy(self) -> float:
        if not self.props:
            return 0.0
        good = sum(1 for p, pol in self.props.items() if GROUND_TRUTHS[p] == pol)
        return good / len(self.props)


class ReligionSystem:
    MAX_MYTHS = 150

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.myths: List[Myth] = []
        self._next_id = 0

    # -- revelation ----------------------------------------------------------
    def _clarity(self, soul) -> float:
        return min(1.0, 0.45 * soul.unity_awareness + 0.35 * soul.sattva
                   + 0.20 * soul.buddhi)

    def reveal(self, soul, year: int, yuga, context: dict, person=None,
               universe=None) -> Optional[Myth]:
        """A soul perceives the mechanics of its world — through its own clarity."""
        clarity = self._clarity(soul)
        n_props = self.rng.randint(3, 6)
        # experience biases WHICH truths present themselves
        pool = list(PROPS)
        weights = [1.0] * len(pool)
        for i, p in enumerate(pool):
            if p == "helpers_descend" and context.get("avatar_recent"):
                weights[i] = 4.0
            if p in ("rebirth", "only_one_life") and soul.lifetime_count >= 3:
                weights[i] = 3.0
            if p == "dawn_returns" and context.get("post_pralaya"):
                weights[i] = 4.0
            if p in ("habit_binds", "effort_frees") and soul.buddhi > 0.3:
                weights[i] = 2.5
        chosen: List[str] = []
        for _ in range(n_props):
            total = sum(w for j, w in enumerate(weights) if pool[j] not in chosen)
            r = self.rng.uniform(0, total)
            acc = 0.0
            for j, p in enumerate(pool):
                if p in chosen:
                    continue
                acc += weights[j]
                if r <= acc:
                    chosen.append(p)
                    break
        # clarity decides whether each clause is seen truly or inverted
        props = {}
        for p in chosen:
            seen_true = self.rng.random() < (0.35 + 0.6 * clarity)
            props[p] = GROUND_TRUTHS[p] if seen_true else (not GROUND_TRUTHS[p])
        name = f"{self.rng.choice(MYTH_NAMES)} of {self.rng.choice(MYTH_NAMES)}"
        myth = Myth(myth_id=self._next_id, name=name, props=props, strength=5.0,
                    born_year=year, born_yuga=yuga.name)
        self._next_id += 1
        self.myths.append(myth)
        if person is not None and universe is not None:
            myth.seer = getattr(person, "name", "") or "an unnamed seer"
            myth.seer_house = getattr(person, "house", "")
            myth.seer_role = universe._derive_role(soul)
            universe.annals.revelation(person, myth)
        return myth

    # -- the yearly turn ------------------------------------------------------
    def step(self, universe, yuga) -> List[tuple]:
        """Returns chronicle events [(kind, text), ...]."""
        hyp = universe.cfg.hyp
        rng = self.rng
        events: List[tuple] = []
        pop = max(len(universe.persons), 1)

        # 1. revelations — clear adults occasionally see
        context = {
            "avatar_recent": universe._avatars_alive() > 0 or universe._avatar_this_year,
            "post_pralaya": universe._pralaya_this_year == 1,
        }
        adults = [p for p in universe.persons.values()
                  if p.is_adult(universe.cfg.rules.adult_age)]
        for person in adults:
            clarity = self._clarity(person.soul)
            if rng.random() < hyp.revelation_rate * clarity:
                m = self.reveal(person.soul, universe.year, yuga, context,
                                person=person, universe=universe)
                if m and m.accuracy() >= 0.99:
                    events.append(("revelation",
                                   f"A seer speaks: '{m.name}' is born, and every word of it is true"))
                elif m and rng.random() < 0.08:
                    events.append(("revelation", f"A new teaching arises: '{m.name}'"))

        # 2. spread — logistic competition for finite attention
        total = sum(m.strength for m in self.myths)
        room = max(0.0, 1.0 - total / (0.8 * pop + 1))
        for m in self.myths:
            reach = hyp.myth_spread * (1.6 if m.institution else 1.0)
            m.strength += reach * m.strength * room
            m.strength *= 0.985  # forgetting

        # 3. mutation — the retelling corrupts, worse in noisy ages
        for m in self.myths:
            p_mut = hyp.myth_mutation * (0.4 + 1.2 * yuga.misinformation)
            if m.institution:
                p_mut *= 0.15  # canon is frozen
            if rng.random() < p_mut and m.props:
                m.retellings += 1
                p = rng.choice(list(m.props.keys()))
                if rng.random() < 0.6:
                    m.props[p] = not m.props[p]
                else:
                    del m.props[p]

        # 4. institutionalization, corruption, reform
        for m in self.myths:
            if not m.institution and m.strength > hyp.institution_threshold * pop:
                m.institution = True
                m.institution_year = universe.year
                m.lineage.append((universe.year, "institution"))
                events.append(("institution",
                               f"'{m.name}' becomes an institution ({m.accuracy():.0%} true at canonization)"))
            if m.institution and yuga.name in ("Dvapara", "Kali"):
                # power rewrites doctrine in the dark ages
                if rng.random() < 0.02 * yuga.misinformation and m.props:
                    true_props = [p for p, pol in m.props.items() if GROUND_TRUTHS[p] == pol]
                    if true_props:
                        p = rng.choice(true_props)
                        m.props[p] = not m.props[p]
                        m.lineage.append((universe.year, "corruption"))
                        events.append(("corruption", f"The canon of '{m.name}' is corrupted"))
            if m.institution and yuga.name in ("Satya", "Treta"):
                # reform: a clear age restores a broken clause
                if rng.random() < 0.02:
                    false_props = [p for p, pol in m.props.items() if GROUND_TRUTHS[p] != pol]
                    if false_props:
                        p = rng.choice(false_props)
                        m.props[p] = GROUND_TRUTHS[p]
                        m.lineage.append((universe.year, "reform"))
                        events.append(("reform", f"'{m.name}' is reformed; a truth is restored"))

        # 4.5 the story side: birth from utterances, retelling mutations,
        #     doctrinal smuggling, adaptive retention
        culture = getattr(universe, "culture", None)
        if culture is not None:
            from .culture import StoryClaims
            # utterances become story-myths (a told account enters tradition)
            for utt in culture.utterances[-12:]:
                if rng.random() < 0.04:
                    nm = f"The {rng.choice(W_MYTHW(universe))} of {utt.actor_claim}"
                    self.myths.append(Myth(
                        myth_id=self._next_id, name=nm, props={},
                        strength=3.0 + 0.8 * utt.scale_claim,
                        born_year=universe.year, born_yuga=yuga.name,
                        story=StoryClaims(actor=utt.actor_claim,
                                          condition=utt.condition,
                                          align=utt.align_claim,
                                          scale=utt.scale_claim, n_actors=1,
                                          source_tid=utt.source_tid)))
                    self._next_id += 1
            for m in self.myths:
                if m.story is None:
                    continue
                # stories about persons travel better (hypothesis knob)
                m.strength *= 1.0 + 0.004 * (hyp.story_spread_bonus - 1.0)
                # the retelling corrupts the story side independently
                if rng.random() < 0.35 * hyp.myth_mutation * (0.4 + 1.2 * yuga.misinformation) * (0.15 if m.institution else 1.0):
                    culture.mutate_story(m.story, yuga.misinformation)
                    m.retellings += 1
                # doctrinal smuggling: a popular tale annexes a teaching
                if not m.props and rng.random() < 0.03:
                    donors = [d for d in self.myths if d.props and d is not m]
                    if donors:
                        donor = rng.choice(donors)
                        p = rng.choice(list(donor.props.keys()))
                        m.props[p] = donor.props[p]
                        m.story.transformations.append("doctrine_annexed")
                # adaptive retention: hard ages keep tales of loss and power alive
                if yuga.hardness >= 0.7 and m.story.condition in ("loss", "power"):
                    m.strength *= 1.005

        # 5. extinction & cap
        survivors = []
        for m in self.myths:
            if m.strength < 1.0 or (not m.props and m.story is None):
                if m.institution:
                    m.lineage.append((universe.year, "extinction"))
                    events.append(("extinction", f"The way of '{m.name}' is forgotten"))
            else:
                survivors.append(m)
        survivors.sort(key=lambda m: m.strength, reverse=True)
        self.myths = survivors[: self.MAX_MYTHS]
        return events

    # -- measurement (read-only) ----------------------------------------------
    def doctrine_accuracy(self) -> float:
        holders = [m for m in self.myths if m.props]
        total = sum(m.strength for m in holders)
        if total <= 0:
            return 0.0
        return sum(m.accuracy() * m.strength for m in holders) / total

    def counts(self) -> tuple:
        return len(self.myths), sum(1 for m in self.myths if m.institution)

    def doctrine_coverage(self) -> float:
        """How much of the ground truth is represented correctly by living,
        believed myths — accuracy tells you truth-per-claim; coverage tells you
        whether anyone still teaches each truth at all."""
        covered = 0
        for p, truth in GROUND_TRUTHS.items():
            if any(m.props.get(p) == truth and m.strength >= 5 for m in self.myths):
                covered += 1
        return covered / len(GROUND_TRUTHS)

    def accuracy_by_birth_age(self) -> Dict[str, float]:
        out: Dict[str, List[float]] = {}
        for m in self.myths:
            out.setdefault(m.born_yuga, []).append(m.accuracy())
        return {k: sum(v) / len(v) for k, v in out.items()}
