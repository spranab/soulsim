"""The Annals — the witness's record of everything narratable.

The Bard's rule is that the world supplies the plot. But a plot needs more
than the physics keeps: names, houses, parents, partners, children, the age
a life was lived in, every test a life faced and how it went, the deeds that
were seen, the works composed, the teachings spoken, the death and what came
after. The Annals write all of that down AS IT HAPPENS, so that later a
compiler can assemble an epic, a novel, a history or a scripture out of
nothing but true sentences.

Wall discipline, twice over:
  - narration-side: nothing here is ever read by physics (soul/decision/karma/
    reproduction). The Annals only listen.
  - dice discipline: names and any other narrative choice roll on their OWN
    stream (`nrng`), so the physics stream and the culture stream consume
    exactly the dice they consumed before the Annals existed. A seed's
    measured outcome is byte-identical with or without this record.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Names — Sanskritic syllable grammar, unique for the life of a cosmos
# ---------------------------------------------------------------------------
_SYL = ["ka", "ki", "ku", "ke", "ga", "gi", "gu", "cha", "chi", "ja", "ji",
        "ta", "ti", "tu", "te", "da", "di", "du", "de", "na", "ni", "nu",
        "pa", "pi", "pu", "ba", "bi", "bha", "ma", "mi", "mu", "me", "ya",
        "ra", "ri", "ru", "la", "li", "lu", "va", "vi", "ve", "sha", "shi",
        "shu", "sa", "si", "su", "ha", "hi", "dha", "dhi", "tra", "pra",
        "kri", "sva", "dra", "sri", "ja", "ya"]
_SYL_FIRST = _SYL + ["ar", "an", "ish", "ut", "in", "am", "ud", "ir"]
_END_M = ["", "", "", "n", "sh", "t", "k", "deva", "sen", "dat", "raj", "vat", "nath"]
_END_F = ["", "", "ni", "ini", "ika", "vati", "la", "mala", "shri", "ta"]
_END_SHORT = ["", "", "n", "t", "k", "sh", "la", "ni"]
_HOUSE_SUFFIX = ["pura", "vati", "grama", "kota", "nagara", "giri", "tirtha",
                 "kshetra", "desha"]

ENEMY_EN = {"kama": "craving", "krodha": "anger", "lobha": "greed",
            "moha": "attachment", "mada": "pride", "matsarya": "envy"}
VIRTUE_EN = {"compassion": "compassion", "discernment": "discernment",
             "truth_alignment": "truthfulness", "courage": "courage",
             "humility": "humility", "non_attachment": "non-attachment",
             "unity_awareness": "sense of unity"}
COND_EN = {"power": "given power", "scarcity": "facing scarcity",
           "loss": "struck by loss", "success": "crowned by success",
           "uncertainty": "lost in uncertainty"}
KIND_EN = {"mastered": "saw the impulse and mastered it",
           "betrayed": "saw the better and chose the worse",
           "swept": "was swept along unseeing",
           "effortless": "did the right thing without effort",
           "held": "held the line, though it cost something"}
SCALE_EN = ["for a few", "for a household", "for a village", "for a kingdom",
            "for the world"]
TOLD_EN = ["among a few", "through a household", "through a whole village",
           "across a kingdom", "across the world"]


class Namer:
    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.used = set()
        # narration-side only: which syllable/ending tokens built each minted
        # name, so a tokenizer (train/vani.py) can emit and re-join them
        # without re-drawing dice. Recorded, never consumed: every value
        # stored here was already produced by the calls below.
        self.parts: Dict[str, List[str]] = {}
        self._last_syllables: List[str] = []

    def _syllables(self, n: int) -> str:
        parts = [self.rng.choice(_SYL_FIRST)]
        while len(parts) < n:
            s = self.rng.choice(_SYL)
            if s != parts[-1]:
                parts.append(s)
        self._last_syllables = list(parts)
        return "".join(parts)

    def person(self, sex: str) -> str:
        ends = _END_F if sex == "female" else _END_M
        for _ in range(200):
            n = 2 if self.rng.random() < 0.7 else 3
            end = self.rng.choice(ends if n == 2 else _END_SHORT)
            syl = self._syllables(n)
            name = (syl + end).capitalize()
            if name not in self.used and 4 <= len(name) <= 10:
                self.used.add(name)
                self.parts[name] = self._last_syllables + ([end] if end else [])
                return name
        syl = self._syllables(3)
        name = syl.capitalize() + str(len(self.used))
        self.used.add(name)
        self.parts[name] = self._last_syllables + [str(len(self.used) - 1)]
        return name

    def house(self) -> str:
        for _ in range(200):
            syl = self._syllables(2)
            suffix = self.rng.choice(_HOUSE_SUFFIX)
            name = (syl + suffix).capitalize()
            if name not in self.used:
                self.used.add(name)
                self.parts[name] = self._last_syllables + [suffix]
                return name
        syl = self._syllables(3)
        name = syl.capitalize() + "pura"
        self.parts[name] = self._last_syllables + ["pura"]
        return name


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------
@dataclass
class Moment:
    age: int
    year: int
    condition: str
    kind: str          # mastered | betrayed | swept | effortless | held
    alignment: float
    difficulty: float
    public: bool = False

    def phrase(self) -> str:
        return f"at {self.age}, {COND_EN[self.condition]}, {KIND_EN[self.kind]}"


@dataclass
class Deed:
    tid: int
    year: int
    age: int
    condition: str
    alignment: float
    scale: int
    witnesses: int
    n_actors: int

    def phrase(self) -> str:
        what = "did well" if self.alignment > 0 else "did ill"
        crowd = "" if self.n_actors <= 1 else f", and {self.n_actors} stood with them"
        wit = "a single witness" if self.witnesses == 1 else f"{self.witnesses} witnesses"
        return (f"{COND_EN[self.condition]}, {what} {SCALE_EN[self.scale]} before "
                f"{wit}{crowd}")


@dataclass
class Bond:
    partner: str
    year: int
    reunion: bool = False
    ended: Optional[int] = None
    how: str = ""              # death | drift | pralaya
    years: int = 0


@dataclass
class Life:
    pid: str
    name: str
    sex: str
    house: str
    soul_serial: int
    life_n: int
    born_year: int
    born_age: int
    mother: Optional[str]
    father: Optional[str]
    born_reason: str
    is_avatar: bool = False
    founding: bool = False
    start_enemy: str = ""
    start_role: str = ""
    bonds: List[Bond] = field(default_factory=list)
    children: List[str] = field(default_factory=list)
    moments: List[Moment] = field(default_factory=list)
    deeds: List[Deed] = field(default_factory=list)
    works: List[int] = field(default_factory=list)
    revelations: List[str] = field(default_factory=list)
    died_year: Optional[int] = None
    died_age: Optional[int] = None
    role: str = ""
    dv: float = 0.0
    end_enemy: str = ""
    liberated: bool = False
    dissolved: bool = False        # the body dissolved in pralaya
    ledger: Tuple[int, int, int, int] = (0, 0, 0, 0)

    # -- derived phrasing ------------------------------------------------
    @property
    def pronoun(self) -> Tuple[str, str, str]:
        return ("she", "her", "her") if self.sex == "female" else ("he", "him", "his")

    def title(self) -> str:
        return f"{self.name} of {self.house}"

    def parents_phrase(self) -> str:
        if self.founding:
            return "among the first, at the founding of the world"
        if self.is_avatar:
            return "not born, but descended"
        if self.mother and self.father:
            return f"to {self.mother} (mother) and {self.father} (father)"
        return "of parents unrecorded"

    def virtue_phrase(self) -> str:
        d = self.dv
        if d >= 0.15:
            return "the soul rose greatly in virtue"
        if d >= 0.05:
            return "the soul rose in virtue"
        if d > -0.05:
            return "the soul ended much as it began"
        if d > -0.15:
            return "the soul declined"
        return "the soul fell far"

    def dramatic_moments(self, k: int = 6) -> List[Moment]:
        """The tests a bard would keep: mastery, betrayal, being swept —
        weighted by difficulty; effortless rightness only if nothing else."""
        rank = {"mastered": 3, "betrayed": 3, "swept": 2, "held": 1, "effortless": 0}
        ms = sorted(self.moments, key=lambda m: (-(rank[m.kind] + m.difficulty), m.age))
        keep = [m for m in ms if m.kind != "effortless"][:k]
        if not keep and ms:
            keep = ms[:2]
        return sorted(keep, key=lambda m: m.age)

    def counts(self) -> Dict[str, int]:
        out = {"mastered": 0, "betrayed": 0, "swept": 0, "effortless": 0, "held": 0}
        for m in self.moments:
            out[m.kind] += 1
        return out


@dataclass
class Event:
    year: int
    kind: str
    text: str
    who: List[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# The Annals
# ---------------------------------------------------------------------------
class Annals:
    N_HOUSES = 9

    def __init__(self, seed: int) -> None:
        self.nrng = random.Random(seed ^ 0xBA5D)   # narration dice, nothing else
        self.namer = Namer(self.nrng)
        self.houses: List[str] = [self.namer.house() for _ in range(self.N_HOUSES)]
        self.lives: Dict[str, Life] = {}            # pid -> Life
        self.by_name: Dict[str, Life] = {}
        self.soul_lives: Dict[int, List[Life]] = {}  # soul serial -> lives in order
        self.events: List[Event] = []
        self.clock = None                            # set by the world
        self.works: Dict[int, object] = {}           # aid -> Artwork (narration copies)
        self.myths: Dict[str, object] = {}           # myth name -> Myth (live refs)

    # -- helpers ------------------------------------------------------------
    def age_at(self, year: int) -> Tuple[str, int]:
        if self.clock is None:
            return ("?", 0)
        yuga, cycle = self.clock.at(year)
        return yuga.name, cycle

    def age_phrase(self, year: int) -> str:
        yuga, cycle = self.age_at(year)
        ordinal = ["first", "second", "third", "fourth", "fifth", "sixth",
                   "seventh", "eighth", "ninth", "tenth"]
        c = ordinal[cycle] if cycle < len(ordinal) else f"{cycle + 1}th"
        return f"the {yuga} age of the {c} cycle"

    def life_of(self, person) -> Optional[Life]:
        return self.lives.get(str(person.body_id))

    # -- births -------------------------------------------------------------
    def new_life(self, person, year: int, mother=None, father=None,
                 founding: bool = False, avatar: bool = False,
                 role_fn=None) -> Life:
        soul = person.soul
        name = self.namer.person(person.body.sex)
        person.name = name
        if father is not None and getattr(father, "house", ""):
            house = father.house
        elif mother is not None and getattr(mother, "house", ""):
            house = mother.house
        else:
            house = self.nrng.choice(self.houses)
        person.house = house
        from .soul import INSTABILITIES
        life = Life(
            pid=str(person.body_id), name=name, sex=person.body.sex, house=house,
            soul_serial=soul.serial, life_n=soul.lifetime_count + 1,
            born_year=year, born_age=person.body.age,
            mother=getattr(mother, "name", None) if mother is not None else None,
            father=getattr(father, "name", None) if father is not None else None,
            born_reason=soul.born_reason, is_avatar=avatar, founding=founding,
            start_enemy=max(INSTABILITIES, key=lambda v: getattr(soul, v)),
            start_role=role_fn(soul) if role_fn else "")
        self.lives[life.pid] = life
        self.by_name[name] = life
        self.soul_lives.setdefault(soul.serial, []).append(life)
        if mother is not None:
            ml = self.life_of(mother)
            if ml:
                ml.children.append(name)
        if father is not None:
            fl = self.life_of(father)
            if fl:
                fl.children.append(name)
        return life

    # -- the life as it is lived ---------------------------------------------
    def moment(self, person, year: int, condition: str, decision, difficulty: float,
               public: bool = False) -> None:
        life = self.life_of(person)
        if life is None or len(life.moments) >= 80:
            return
        if decision.veto_won:
            kind = "mastered"
        elif decision.veto_needed and decision.noticed:
            kind = "betrayed"
        elif decision.veto_needed:
            kind = "swept"
        elif decision.action.alignment > 0.9:
            kind = "effortless"
        else:
            kind = "held"
        life.moments.append(Moment(age=person.body.age, year=year, condition=condition,
                                   kind=kind, alignment=decision.action.alignment,
                                   difficulty=difficulty, public=public))

    def deed(self, person, trace) -> None:
        life = self.life_of(person)
        if life is None:
            return
        life.deeds.append(Deed(tid=trace.tid, year=trace.year, age=person.body.age,
                               condition=trace.condition, alignment=trace.act_alignment,
                               scale=trace.scale, witnesses=trace.witnesses,
                               n_actors=trace.n_actors))
        if life.moments:
            life.moments[-1].public = True
        if trace.scale >= 3:
            what = "did well" if trace.act_alignment > 0 else "did ill"
            self.event(trace.year, "deed",
                       f"{life.name} of {life.house}, {COND_EN[trace.condition]}, "
                       f"{what} {SCALE_EN[trace.scale]}",
                       who=[life.name], scale=trace.scale, align=trace.act_alignment,
                       condition=trace.condition, n_actors=trace.n_actors)

    def bond(self, a, b, year: int, reunion: bool) -> None:
        la, lb = self.life_of(a), self.life_of(b)
        if la is None or lb is None:
            return
        la.bonds.append(Bond(partner=lb.name, year=year, reunion=reunion))
        lb.bonds.append(Bond(partner=la.name, year=year, reunion=reunion))
        if reunion:
            self.event(year, "reunion",
                       f"{la.name} and {lb.name} find each other again, "
                       f"souls long entangled", who=[la.name, lb.name])

    def unbond(self, a, b, year: int, how: str) -> None:
        for x, y in ((a, b), (b, a)):
            lx, ly = self.life_of(x), self.life_of(y)
            if lx is None or ly is None:
                continue
            for bd in reversed(lx.bonds):
                if bd.partner == ly.name and bd.ended is None:
                    bd.ended, bd.how, bd.years = year, how, year - bd.year
                    break

    def work(self, person, artwork) -> None:
        life = self.life_of(person)
        if life is None:
            return
        life.works.append(artwork.aid)
        self.works[artwork.aid] = artwork

    def revelation(self, person, myth) -> None:
        life = self.life_of(person)
        if life is None:
            return
        life.revelations.append(myth.name)
        self.myths[myth.name] = myth

    # -- endings --------------------------------------------------------------
    def death(self, person, year: int, role: str, dv: float, end_enemy: str,
              liberated: bool, ledger=(0, 0, 0, 0), dissolved: bool = False) -> None:
        life = self.life_of(person)
        if life is None:
            return
        life.died_year, life.died_age = year, person.body.age
        life.role, life.dv, life.end_enemy = role, dv, end_enemy
        life.liberated, life.dissolved, life.ledger = liberated, dissolved, tuple(ledger)
        for bd in life.bonds:
            if bd.ended is None:
                bd.ended, bd.how, bd.years = year, ("pralaya" if dissolved else "death"), year - bd.year
        if liberated:
            self.event(year, "moksha",
                       f"{life.name} of {life.house} died at {life.died_age}, and the soul "
                       f"that wore that body left the wheel after {life.life_n} lives",
                       who=[life.name], lives=life.life_n, serial=life.soul_serial)

    def event(self, year: int, kind: str, text: str, who=None, **data) -> None:
        self.events.append(Event(year=year, kind=kind, text=text, who=list(who or []),
                                 data=data))

    # -- queries ----------------------------------------------------------------
    def lives_of_soul(self, serial: int) -> List[Life]:
        return self.soul_lives.get(serial, [])

    def previous_life(self, life: Life) -> Optional[Life]:
        ls = self.lives_of_soul(life.soul_serial)
        i = ls.index(life) if life in ls else -1
        return ls[i - 1] if i > 0 else None

    def events_between(self, y0: int, y1: int, kinds=None) -> List[Event]:
        return [e for e in self.events if y0 <= e.year < y1
                and (kinds is None or e.kind in kinds)]

    def lives_in(self, y0: int, y1: int) -> List[Life]:
        """Lives that were adult at some point in [y0, y1)."""
        out = []
        for l in self.lives.values():
            end = l.died_year if l.died_year is not None else 10 ** 9
            if l.born_year < y1 and end >= y0:
                out.append(l)
        return out

    def ages(self, until_year: int) -> List[dict]:
        """The sequence of (cycle, yuga, start, end) that the run passed through."""
        if self.clock is None:
            return []
        out, y = [], 0
        while y < until_year:
            yuga, cycle = self.clock.at(y)
            start = y
            while y < until_year and self.clock.at(y)[0].name == yuga.name \
                    and self.clock.at(y)[1] == cycle:
                y += 1
            out.append({"cycle": cycle, "yuga": yuga.name, "start": start, "end": y,
                        "hardness": yuga.hardness, "temptation": yuga.temptation,
                        "misinformation": yuga.misinformation})
        return out

    def stats(self) -> dict:
        return {"lives": len(self.lives), "souls_with_lives": len(self.soul_lives),
                "events": len(self.events), "houses": list(self.houses)}
