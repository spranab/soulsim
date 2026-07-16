"""Culture — how deeds become myth (the historical-memory link).

Design hardened in a redteam brainstorm with gpt-5.6-sol (2026-07-16). The
consensus causal chain, and the ONLY one:

    outward event → PublicEventTrace → ClaimUtterance → myth claim-bundle
    → prevalence → stochastic exposure → cultural groove → chariot → new event

Beside it, never feeding back: DeedAuditRecord → fidelity analytics.

THE GOVERNING INVARIANT (sol's phrasing): culture may observe THAT someone held
the line; it may never observe whether doing so was effortless, agonizing,
akratic, avatar-driven, or spiritually decisive. The chariot's inner taxonomy
is exactly what no witness can see. Therefore:
  - traces carry only outward facts (name, condition, act alignment, scale,
    witnesses) — publicness is sampled at event time, never derived from
    spiritual magnitude;
  - soul_id, inner kind, difficulty, avatar status live in the audit record,
    which nothing causal ever reads;
  - myths are recombinant CLAIM BUNDLES (actor / event / doctrine), each claim
    mutating independently — so a false biography can carry a true teaching;
  - exposure lays a CULTURAL GROOVE: a weak, this-life-only samskara acquired
    by hearing (shravana) — amoral by construction, entering the chariot where
    habit already enters. A villain myth grooves the unaligned act exactly as
    a saint myth grooves the aligned one. The noticing gate and the veto still
    stand between availability and act.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

SCALES = ["a few", "a household", "a village", "a kingdom", "the world"]
NAME_SYLL = ["Va", "Su", "Ka", "De", "Mi", "Ra", "Ana", "Ish", "Ta", "Bo",
             "ru", "ni", "va", "sha", "ra", "la", "dev", "mi", "ka", "n"]


@dataclass
class PublicEventTrace:
    """What witnesses could actually see. CAUSAL."""
    tid: int
    year: int
    name_token: str          # the in-world name of the actor's current body
    condition: str
    act_alignment: float     # the outward act (observable)
    scale: int               # index into SCALES
    witnesses: int
    n_actors: int = 1        # collective acts carry their plurality


@dataclass
class DeedAuditRecord:
    """What really happened, inwardly. NONCAUSAL — analytics only."""
    tid: int
    soul_id: str
    inner_kind: str          # veto_won / effortless / akrasia / unseen
    difficulty: float
    was_avatar: bool


@dataclass
class ClaimUtterance:
    """Someone said something happened. Lies have speakers and motives."""
    year: int
    speaker: str             # name token
    actor_claim: str
    condition: str
    align_claim: float
    scale_claim: int
    source_tid: Optional[int]   # None => fabrication (no underlying event)


@dataclass
class StoryClaims:
    actor: str
    condition: str
    align: float
    scale: int
    n_actors: int
    source_tid: Optional[int]
    transformations: List[str] = field(default_factory=list)


class CultureSystem:
    """Owns traces, utterances, and the story side of myths. The doctrine side
    stays in ReligionSystem; story-myths are religion myths that ALSO carry a
    StoryClaims bundle — one tradition, separable claims."""

    MAX_TRACES = 400

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.traces: List[PublicEventTrace] = []
        self.audit: List[DeedAuditRecord] = []     # noncausal
        self.utterances: List[ClaimUtterance] = []
        self._tid = 0
        # analytics-side archive: fidelity must be able to grade a myth against
        # its source even after the world has forgotten the trace (noncausal)
        self.trace_archive: Dict[int, tuple] = {}

    def mint_name(self) -> str:
        return ("".join(self.rng.choice(NAME_SYLL) for _ in range(3))).capitalize()

    # -- 1. the outward event leaves (or doesn't leave) a public trace -------
    # p_public depends on the KIND OF SITUATION (power plays out in court,
    # loss at a burning ground, uncertainty mostly in private) — never on
    # spiritual magnitude.
    P_PUBLIC = {"power": 0.12, "success": 0.12, "loss": 0.08,
                "scarcity": 0.08, "uncertainty": 0.03}

    def maybe_trace(self, person, event_condition: str, act_alignment: float,
                    decision, year: int) -> None:
        if self.rng.random() > self.P_PUBLIC.get(event_condition, 0.2):
            return
        if getattr(person, "name_token", None) is None:
            person.name_token = self.mint_name()
        witnesses = max(1, int(self.rng.gauss(8, 6)))
        scale = min(4, max(0, int(abs(self.rng.gauss(0.8, 0.9)))))
        self._tid += 1
        self.traces.append(PublicEventTrace(
            tid=self._tid, year=year, name_token=person.name_token,
            condition=event_condition, act_alignment=act_alignment,
            scale=scale, witnesses=witnesses,
            n_actors=1 if self.rng.random() > 0.15 else self.rng.randint(2, 20)))
        if len(self.traces) > self.MAX_TRACES:
            self.traces.pop(0)
        # the audit shadow — written here, read only by analytics
        self.audit.append(DeedAuditRecord(
            tid=self._tid, soul_id=str(person.soul.soul_id),
            inner_kind=("veto_won" if decision.veto_won else
                        "effortless" if not decision.veto_needed else
                        "akrasia" if decision.noticed else "unseen"),
            difficulty=0.0, was_avatar=person.is_avatar))
        if len(self.audit) > 4000:
            self.audit.pop(0)

    # -- 2. accounts and lies -------------------------------------------------
    def utter(self, persons, year: int, hyp) -> None:
        # witness accounts: bigger, more-witnessed traces get told
        for t in self.traces[-40:]:
            p_tell = 0.04 + 0.01 * t.witnesses + 0.05 * t.scale
            if self.rng.random() < min(0.5, p_tell * hyp.utterance_rate):
                # a told trace enters the permanent record (analytics archive)
                self.trace_archive[t.tid] = (t.name_token, t.act_alignment,
                                             t.scale, t.n_actors)
                if len(self.trace_archive) > 50000:
                    self.trace_archive.pop(next(iter(self.trace_archive)))
                self.utterances.append(ClaimUtterance(
                    year=year, speaker="a witness", actor_claim=t.name_token,
                    condition=t.condition, align_claim=t.act_alignment,
                    scale_claim=t.scale, source_tid=t.tid))
        # fabrication: lies have speakers, and speakers have vices.
        # mada fabricates glory for itself; matsarya fabricates villainy for another.
        for person in persons:
            if getattr(person, "name_token", None) is None:
                continue
            s = person.soul
            if self.rng.random() < hyp.fabrication_rate * max(0.0, s.mada - 0.55):
                self.utterances.append(ClaimUtterance(
                    year=year, speaker=person.name_token,
                    actor_claim=person.name_token,
                    condition=self.rng.choice(list(self.P_PUBLIC)),
                    align_claim=1.0, scale_claim=min(4, 1 + int(s.mada * 3)),
                    source_tid=None))
            if self.rng.random() < hyp.fabrication_rate * max(0.0, s.matsarya - 0.55):
                victims = [t.name_token for t in self.traces[-30:]]
                if victims:
                    self.utterances.append(ClaimUtterance(
                        year=year, speaker=person.name_token,
                        actor_claim=self.rng.choice(victims),
                        condition=self.rng.choice(list(self.P_PUBLIC)),
                        align_claim=-1.0, scale_claim=2, source_tid=None))
        if len(self.utterances) > 300:
            self.utterances = self.utterances[-300:]

    # -- story mutations (the retelling) --------------------------------------
    def mutate_story(self, sc: StoryClaims, misinformation: float) -> None:
        r = self.rng.random()
        if r < 0.35:   # scale drift, one categorical step, bounded
            step = 1 if self.rng.random() < 0.75 else -1   # inflation more common
            sc.scale = min(4, max(0, sc.scale + step))
            sc.transformations.append("scale")
        elif r < 0.55:  # attribution drift: the deed finds a new owner
            names = [t.name_token for t in self.traces[-40:]] or [self.mint_name()]
            sc.actor = self.rng.choice(names)
            sc.transformations.append("misattribution")
        elif r < 0.70 and sc.n_actors > 1:  # great-man compression
            sc.n_actors = 1
            sc.transformations.append("great_man")
        elif r < 0.80:  # moral inversion: hero becomes villain, villain hero
            sc.align = -sc.align
            sc.transformations.append("inversion")
        # else: the retelling holds

    # -- analytics only (reads audit; feeds nothing) ---------------------------
    def fidelity(self, story_myths) -> float:
        if not story_myths:
            return 0.0
        scores = []
        for m in story_myths:
            sc = m.story
            src = self.trace_archive.get(sc.source_tid) if sc.source_tid else None
            if src is None:
                scores.append(0.0)     # unsupported (incl. fabrications)
                continue
            name, align, scale, n_actors = src
            ok = 0
            ok += 1 if sc.actor == name else 0
            ok += 1 if abs(sc.align - align) < 0.5 else 0
            ok += 1 if abs(sc.scale - scale) <= 1 else 0
            ok += 1 if (sc.n_actors > 1) == (n_actors > 1) else 0
            scores.append(ok / 4)
        return sum(scores) / len(scores)
