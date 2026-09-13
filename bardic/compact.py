"""A terser notation for the brief — same facts, fewer tokens.

`render.py` builds THE RECORD out of plain English sentences (see
`common.py`): readable, but wordy — the same handful of templates repeated
for every birth, bond, test and death in a chapter. `encode()` recognizes
those templates by their phrasing and rewrites each line as a short, typed
line instead: `TEST a24 y248 power MASTERED` instead of "At 24, in year 248,
given power, Kavindra saw the impulse rise and mastered it." Every proper
noun and every number in the original survives untouched — the lint checks
the rendered prose against the ORIGINAL brief, not the compact one, so
nothing here may drop or alter a name or a digit that matters.

A line whose phrasing this module doesn't recognize (a genre-specific
sentence built outside `common.py`) is passed through unchanged: correct,
just not shorter.
"""
from __future__ import annotations

import re
from typing import Callable, List, Optional, Tuple

LEGEND = (
    "NOTATION: each line is a compressed fact — expand into vivid prose, "
    "inventing nothing beyond it. y=year, a=age; numbers are exact, never "
    "recomputed. TEST: MASTERED=resisted, CHOSE_WORSE=chose worse, "
    "SWEPT=acted unnoticed, EFFORTLESS=easy right choice, HELD=middle "
    "course. DEATH's -> outcome: unmanifest=awaits rebirth, "
    "FREED(lives=N)=liberated after N lives, dissolved=world's end, "
    "withdrew=a descended one's return, living=record ends first. LEDGER "
    "is tone only, never recite it."
)

_ROLES = ["a mystic", "a teacher", "a reformer", "a caretaker", "a ruler",
          "an opportunist", "a brooder", "a wanderer", "a descended one"]
_ROLE_RE = "(?:" + "|".join(re.escape(r) for r in _ROLES) + ")"

_ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
             "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10}

_COND_ABBR = {"given power": "power", "facing scarcity": "scarcity",
              "struck by loss": "loss", "crowned by success": "success",
              "lost in uncertainty": "uncertainty"}

_KIND_ABBR = {
    "saw the impulse rise and mastered it": "MASTERED",
    "saw the better course and chose the worse": "CHOSE_WORSE",
    "was swept along unseeing, the impulse acting before it was noticed": "SWEPT",
    "did the right thing without any struggle": "EFFORTLESS",
    "held to a middle course, neither the best nor the worst": "HELD",
}

_TOLD_ABBR = {"among a few": "few", "through a household": "household",
              "through a whole village": "village", "across a kingdom": "kingdom",
              "across the world": "world"}

_VIRTUE_ABBR = {
    "the soul rose greatly in virtue": "rose_greatly",
    "the soul rose in virtue": "rose",
    "the soul ended much as it began": "steady",
    "the soul declined": "declined",
    "the soul fell far": "fell_far",
}


def _role_word(role: str) -> str:
    for art in ("an ", "a "):
        if role.startswith(art):
            return role[len(art):]
    return role


def _when_compact(when: str) -> str:
    """'the Treta age of the first cycle' -> 'Treta/1'; unrecognized -> as is."""
    m = re.match(r"^the (\w+) age of the (\w+) cycle$", when)
    if not m:
        return when
    yuga, ordw = m.groups()
    cycle = _ORDINALS.get(ordw)
    if cycle is None:
        m2 = re.match(r"^(\d+)th$", ordw)
        cycle = int(m2.group(1)) if m2 else ordw
    return f"{yuga}/{cycle}"


# ---------------------------------------------------------------------------
# BIRTH
# ---------------------------------------------------------------------------
_BIRTH_FOUNDING = re.compile(
    r"^(?P<name>[A-Z]\w+), a (?P<sex>man|woman) of the house of (?P<house>[A-Z]\w+), "
    r"was among the first, already (?P<age>\d+) years old when the world was made "
    r"manifest in year (?P<year>\d+), in (?P<when>.+)\.$")
_BIRTH_AVATAR = re.compile(
    r"^(?P<name>[A-Z]\w+), a (?P<sex>man|woman) of the house of (?P<house>[A-Z]\w+), "
    r"was not born but descended, already grown, in year (?P<year>\d+), in (?P<when>.+)\.$")
_BIRTH_NORMAL = re.compile(
    r"^(?P<name>[A-Z]\w+), a (?P<sex>man|woman) of the house of (?P<house>[A-Z]\w+), "
    r"was born in year (?P<year>\d+), in (?P<when>.+?), "
    r"(?:to (?P<mother>[A-Z]\w+) \(mother\) and (?P<father>[A-Z]\w+) \(father\)"
    r"|of parents unrecorded)\.$")


def _birth(line: str) -> Optional[str]:
    sex = {"man": "m", "woman": "f"}
    if m := _BIRTH_FOUNDING.match(line):
        g = m.groupdict()
        return (f"BIRTH {g['name']} {sex[g['sex']]} house={g['house']} y{g['year']} "
                f"founding when={_when_compact(g['when'])}")
    if m := _BIRTH_AVATAR.match(line):
        g = m.groupdict()
        return (f"BIRTH {g['name']} {sex[g['sex']]} house={g['house']} y{g['year']} "
                f"avatar when={_when_compact(g['when'])}")
    if m := _BIRTH_NORMAL.match(line):
        g = m.groupdict()
        out = (f"BIRTH {g['name']} {sex[g['sex']]} house={g['house']} y{g['year']} "
               f"when={_when_compact(g['when'])}")
        if g["mother"]:
            out += f" mother={g['mother']} father={g['father']}"
        return out
    return None


# ---------------------------------------------------------------------------
# WHY
# ---------------------------------------------------------------------------
_WHY_RE = re.compile(r"^Why (?:this birth|the soul came to this house): (?P<reason>.+)\.$")


def _why(line: str) -> Optional[str]:
    if m := _WHY_RE.match(line):
        return f"WHY {m.group('reason')}"
    return None


# ---------------------------------------------------------------------------
# BOND + CHILDREN
# ---------------------------------------------------------------------------
_BOND_RE = re.compile(
    r"^At (?P<age>\d+), in year (?P<year>\d+), (?P<name>[A-Z]\w+) bonded with (?P<partner>[A-Z]\w+)"
    r"(?:, a soul known from another life\. In an earlier life that soul had been "
    r"(?P<rname>[A-Z]\w+) of (?P<rhouse>[A-Z]\w+), " + _ROLE_RE +
    r"(?:, bonded then to (?P<runfin>[A-Z]\w+) — the two had left something unfinished)?)?"
    r"\."
    r"(?: They stayed together (?P<years>\d+) years, until (?P<how>.+?)\.)?$")

_HOW_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"^(?P<who>[A-Z]\w+) died in year (?P<endyear>\d+)$"), "death"),
    (re.compile(r"^(?P<who>[A-Z]\w+)'s own death in year (?P<endyear>\d+)$"), "death_self"),
    (re.compile(r"^both died in year (?P<endyear>\d+)$"), "death_both"),
    (re.compile(r"^they drifted apart in year (?P<endyear>\d+)$"), "drift"),
    (re.compile(r"^the world itself dissolved in year (?P<endyear>\d+)$"), "pralaya"),
]

_CHILDREN_RE = re.compile(r"^Children born to (?P<name>[A-Z]\w+): (?P<rest>.+)\.$")
_CHILD_ITEM_RE = re.compile(r"^(?P<kid>[A-Z]\w+)(?: \(born year (?P<year>\d+)\))?$")


def _bond(line: str) -> Optional[str]:
    m = _BOND_RE.match(line)
    if not m:
        return None
    g = m.groupdict()
    out = f"BOND y{g['year']} a{g['age']} with={g['partner']}"
    if g["rname"]:
        out += f" reunion(was={g['rname']}/{g['rhouse']})"
        if g["runfin"]:
            out += f"+prior_bond={g['runfin']}"
    if g["how"]:
        for pat, kind in _HOW_PATTERNS:
            hm = pat.match(g["how"])
            if hm:
                who = "both" if kind == "death_both" else hm.group("who")
                out += (f" until={'death' if kind.startswith('death') else kind}"
                        f"({who}) y{hm.group('endyear')} years={g['years']}")
                break
        else:
            out += f" until=({g['how']}) years={g['years']}"
    return out


def _children(line: str) -> Optional[str]:
    m = _CHILDREN_RE.match(line)
    if not m:
        return None
    kids = []
    for item in m.group("rest").split(", "):
        km = _CHILD_ITEM_RE.match(item.strip())
        if not km:
            return None
        kids.append(f"{km.group('kid')}(y{km.group('year')})" if km.group("year") else km.group("kid"))
    return f"CHILDREN " + " ".join(kids)


# ---------------------------------------------------------------------------
# TEST (moment_lines)
# ---------------------------------------------------------------------------
_TEST_RE = re.compile(
    r"^At (?P<age>\d+), in year (?P<year>\d+), (?P<cond>" +
    "|".join(re.escape(c) for c in _COND_ABBR) + r"), (?P<name>[A-Z]\w+) "
    r"(?P<kind>" + "|".join(re.escape(k) for k in _KIND_ABBR) + r")\."
    r"(?: This was done in public, before (?P<wit>a single witness|\d+ witnesses); "
    r"the deed was seen as (?P<align>good|ill), and the story of it was told "
    r"(?P<told>" + "|".join(re.escape(t) for t in _TOLD_ABBR) + r")"
    r"(?:; (?P<actors>\d+) others were part of it)?\.)?$")


def _test(line: str) -> Optional[str]:
    m = _TEST_RE.match(line)
    if not m:
        return None
    g = m.groupdict()
    out = f"TEST a{g['age']} y{g['year']} {_COND_ABBR[g['cond']]} {_KIND_ABBR[g['kind']]}"
    if g["wit"]:
        w = 1 if g["wit"] == "a single witness" else int(g["wit"].split()[0])
        out += f" public={w}w {g['align']} told={_TOLD_ABBR[g['told']]}"
        if g["actors"]:
            out += f" actors={g['actors']}"
    return out


# ---------------------------------------------------------------------------
# WORK
# ---------------------------------------------------------------------------
_WORK_RE = re.compile(
    r'^In year (?P<year>\d+), at (?P<age>\d+), (?P<name>[A-Z]\w+) composed a '
    r'(?P<form>[\w-]+) of (?P<rasa>\w+), born of this: (?P<bornof>.+?)\. '
    r'Its words: "(?P<verse>.+?)"\.'
    r'(?: The world took it into its canon in year (?P<canon>\d+)\.)?$', re.S)


def _work(line: str) -> Optional[str]:
    m = _WORK_RE.match(line)
    if not m:
        return None
    g = m.groupdict()
    out = (f'WORK y{g["year"]} a{g["age"]} form={g["form"]} rasa={g["rasa"]} '
           f'of="{g["bornof"]}" text="{g["verse"]}"')
    if g["canon"]:
        out += f" canon=y{g['canon']}"
    return out


# ---------------------------------------------------------------------------
# TEACHING
# ---------------------------------------------------------------------------
_TEACH_RE = re.compile(
    r"^In year (?P<year>\d+), at (?P<age>\d+), (?P<name>[A-Z]\w+) spoke a teaching "
    r"the world came to call '(?P<myth>[^']+)'"
    r"(?:, holding that: (?P<claims>.+?)\."
    r"|; what it held has since been lost in the retelling\.)"
    r"(?P<lineage> .+)?$", re.S)


def _teaching(line: str) -> Optional[str]:
    m = _TEACH_RE.match(line)
    if not m:
        return None
    g = m.groupdict()
    holds = g["claims"] if g["claims"] else "lost"
    out = f"TEACHING y{g['year']} a{g['age']} name='{g['myth']}' holds: {holds}"
    if g["lineage"]:
        out += f" | lineage: {g['lineage'].strip()}"
    return out


# ---------------------------------------------------------------------------
# DEATH
# ---------------------------------------------------------------------------
_DEATH_LIVING = re.compile(r"^(?P<name>[A-Z]\w+) was still living when the record closed\.$")
_DEATH_AVATAR = re.compile(
    r"^In year (?P<year>\d+), at (?P<age>\d+), (?P<name>[A-Z]\w+) laid the body down and "
    r"withdrew, the walk of a descended one being finished\.$")
_DEATH_RE = re.compile(
    r"^(?:In year (?P<year1>\d+), at (?P<age1>\d+), the body of (?P<name1>[A-Z]\w+) was "
    r"unmade with the whole manifest world in the pralaya\. "
    r"|(?P<name2>[A-Z]\w+) died in year (?P<year2>\d+), at (?P<age2>\d+), in (?P<when>.+?)\. )"
    r"The world would call \w+ (?P<role>" + _ROLE_RE + r")\. Over this life "
    r"(?P<virtue>" + "|".join(re.escape(v) for v in _VIRTUE_ABBR) + r"); the ruling enemy "
    r"at the end was (?P<enemy>\w+)\."
    r"(?P<lib> And with this death the soul left the wheel forever — liberation, "
    r"after (?P<lives>\d+) lives\.)?"
    r"(?P<ret> The soul returned to the unmanifest, to wait for another body\.)?$")


def _death(line: str) -> Optional[str]:
    if m := _DEATH_LIVING.match(line):
        return f"DEATH {m.group('name')} living"
    if m := _DEATH_AVATAR.match(line):
        g = m.groupdict()
        return f"DEATH {g['name']} y{g['year']} a{g['age']} avatar withdrew"
    m = _DEATH_RE.match(line)
    if not m:
        return None
    g = m.groupdict()
    dissolved = g["name1"] is not None
    name = g["name1"] or g["name2"]
    year = g["year1"] or g["year2"]
    age = g["age1"] or g["age2"]
    out = f"DEATH {name} y{year} a{age}"
    out += " dissolved" if dissolved else f" age={_when_compact(g['when'])}"
    out += f" role={_role_word(g['role'])} virtue={_VIRTUE_ABBR[g['virtue']]} enemy={g['enemy']}"
    if g["lib"]:
        out += f" -> FREED(lives={g['lives']})"
    elif g["ret"]:
        out += " -> unmanifest"
    elif dissolved:
        out += " -> dissolved"
    return out


# ---------------------------------------------------------------------------
# LEDGER
# ---------------------------------------------------------------------------
_LEDGER_NONE = re.compile(
    r"^Background for tone, not to be recited: this life faced no test at all\.$")
_LEDGER_RE = re.compile(
    r"^Background for tone, not to be recited: (?P<shape>.+?) — over the whole life, "
    r"(?P<parts>.+)\.$")
_LEDGER_PARTS = [
    (re.compile(r"(\d+) times the impulse was seen and mastered"), "mastered"),
    (re.compile(r"(\d+) times the better was seen and the worse chosen"), "worse"),
    (re.compile(r"(\d+) times the impulse acted unseen"), "unseen"),
    (re.compile(r"(\d+) times the right thing was done without struggle"), "effortless"),
]


def _ledger(line: str) -> Optional[str]:
    if _LEDGER_NONE.match(line):
        return "LEDGER none"
    m = _LEDGER_RE.match(line)
    if not m:
        return None
    counts = {"mastered": 0, "worse": 0, "unseen": 0, "effortless": 0}
    for pat, key in _LEDGER_PARTS:
        pm = pat.search(m.group("parts"))
        if pm:
            counts[key] = int(pm.group(1))
    return (f"LEDGER mastered={counts['mastered']} worse={counts['worse']} "
            f"unseen={counts['unseen']} effortless={counts['effortless']} "
            f'shape="{m.group("shape")}"')


# ---------------------------------------------------------------------------
# PREV
# ---------------------------------------------------------------------------
_PREV_CHILD = re.compile(
    r"^Before this body, the soul had worn the body of (?P<name>[A-Z]\w+) of "
    r"(?P<house>[A-Z]\w+) for (?P<years>\d+) years only, and died a child\.$")
_PREV_RE = re.compile(
    r"^Before this body, the soul had been (?P<name>[A-Z]\w+) of (?P<house>[A-Z]\w+), "
    r"(?P<role>" + _ROLE_RE + r"), "
    r"(?:whose body was unmade in a pralaya|who died at (?P<age>\d+)) in year (?P<year>\d+), "
    r"ruled at the end by (?P<enemy>\w+)\.$")


def _prev(line: str) -> Optional[str]:
    if m := _PREV_CHILD.match(line):
        g = m.groupdict()
        return f"PREV {g['name']} house={g['house']} child died_after={g['years']}y"
    m = _PREV_RE.match(line)
    if not m:
        return None
    g = m.groupdict()
    died = f"a{g['age']}" if g["age"] else "dissolved"
    return (f"PREV {g['name']} house={g['house']} role={_role_word(g['role'])} "
            f"died={died} y{g['year']} enemy={g['enemy']}")


# ---------------------------------------------------------------------------
# WORLD
# ---------------------------------------------------------------------------
_WORLD_RE = re.compile(r"^Year (?P<year>\d+): (?P<text>.+)\.$")


def _world(line: str) -> Optional[str]:
    if m := _WORLD_RE.match(line):
        return f"WORLD y{m.group('year')}: {m.group('text')}"
    return None


# ---------------------------------------------------------------------------
# PROEM (epic.py) — long free-text lines that, unencoded, are the single
# biggest source of wasted tokens in a compact brief (they open every epic
# and never repeat, so there's no template savings elsewhere to offset them)
# ---------------------------------------------------------------------------
_SPAN_RE = re.compile(
    r"^This epic follows one soul through (?P<n>\d+) lives, from year "
    r"(?P<y0>\d+) to year (?P<y1>\d+)\.$")
_AGES_RE = re.compile(r"^The ages it passed through: (?P<ages>.+)\.$")
_HOUSES_RE = re.compile(r"^The houses of the world: (?P<houses>.+)\.$")
_BODIES_RE = re.compile(r"^The soul's bodies, in order: (?P<bodies>.+)\.$")
_BODY_ITEM_RE = re.compile(
    r"^(?P<name>[A-Z]\w+) of (?P<house>[A-Z]\w+) \((?P<role>a child only|" + _ROLE_RE +
    r"), years (?P<y0>\d+)[–-](?P<y1>\d+|the close of the record)\)$")
_OUTCOME_FREED = re.compile(
    r"^In the end the soul was freed: in year (?P<year>\d+), with the death of "
    r"(?P<name>[A-Z]\w+), it left the wheel forever\.$")
_OUTCOME_BOUND = re.compile(
    r"^In the end the soul was not freed; when the record closes it is still "
    r"on the wheel\.$")
_WORLD_SPAN_RE = re.compile(
    r"^Across that span the world saw (?P<diss>\d+) dissolutions of the "
    r"manifest world and (?P<desc>\d+) descents of liberated ones\.$")


def _proem(line: str) -> Optional[str]:
    if m := _SPAN_RE.match(line):
        g = m.groupdict()
        return f"SPAN lives={g['n']} y{g['y0']}-y{g['y1']}"
    if m := _AGES_RE.match(line):
        ages = "; ".join(_when_compact(a.strip()) for a in m.group("ages").split("; "))
        return f"AGES {ages}"
    if m := _HOUSES_RE.match(line):
        return "HOUSES " + " ".join(h.strip() for h in m.group("houses").split(", "))
    if m := _BODIES_RE.match(line):
        items = []
        for item in m.group("bodies").split("; "):
            bm = _BODY_ITEM_RE.match(item.strip())
            if not bm:
                return None
            b = bm.groupdict()
            role = "child" if b["role"] == "a child only" else _role_word(b["role"])
            y1 = "open" if b["y1"] == "the close of the record" else f"y{b['y1']}"
            items.append(f"{b['name']}/{b['house']}/{role}/y{b['y0']}-{y1}")
        return "BODIES " + "; ".join(items)
    if m := _OUTCOME_FREED.match(line):
        g = m.groupdict()
        return f"OUTCOME FREED y{g['year']} name={g['name']}"
    if _OUTCOME_BOUND.match(line):
        return "OUTCOME BOUND"
    if m := _WORLD_SPAN_RE.match(line):
        g = m.groupdict()
        return f"WORLD_SPAN dissolutions={g['diss']} descents={g['desc']}"
    return None


# ---------------------------------------------------------------------------
# per-life lines built inline by epic.py / novel.py (not in common.py, but
# repeated once per life and worth the same treatment)
# ---------------------------------------------------------------------------
_LIFE_ORDINALS = {"zeroth": 0, "first": 1, "second": 2, "third": 3, "fourth": 4,
                  "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9,
                  "tenth": 10, "eleventh": 11, "twelfth": 12}
_LIFE_N_RE = re.compile(r"^This is the (?P<ord>\w+) life of the soul\.$")
_START_ENEMY_RE = re.compile(
    r"^The soul came into this body ruled by (?P<enemy>\w+)\.$|"
    r"^The soul's ruling enemy from birth was (?P<enemy2>\w+)\.$")
_CHILD_INTERLUDE_RE = re.compile(
    r"^Between those lives the soul wore the body of (?P<name>[A-Z]\w+) of "
    r"(?P<house>[A-Z]\w+) for (?P<years>\d+) years only, born in year "
    r"(?P<year>\d+), and died a child, having faced no test\.$")


def _life_extras(line: str) -> Optional[str]:
    if m := _LIFE_N_RE.match(line):
        word = m.group("ord")
        n = _LIFE_ORDINALS.get(word)
        if n is None:
            nm = re.match(r"^(\d+)th$", word)
            n = nm.group(1) if nm else word
        return f"LIFE_N {n}"
    if m := _START_ENEMY_RE.match(line):
        return f"START_ENEMY {m.group('enemy') or m.group('enemy2')}"
    if m := _CHILD_INTERLUDE_RE.match(line):
        g = m.groupdict()
        return f"CHILD_INTERLUDE {g['name']} house={g['house']} y{g['year']} years={g['years']}"
    return None


# ---------------------------------------------------------------------------
# encode
# ---------------------------------------------------------------------------
_ENCODERS: List[Callable[[str], Optional[str]]] = [
    _birth, _why, _bond, _children, _test, _work, _teaching, _death, _ledger,
    _prev, _world, _proem, _life_extras,
]


def encode(brief: List[str]) -> List[str]:
    """Every line rewritten to the compact notation where its phrasing is
    recognized, else passed through unchanged. Names and numbers are never
    dropped — only the English scaffolding around them is."""
    out = []
    for line in brief:
        s = line.strip()
        compact = None
        for enc in _ENCODERS:
            compact = enc(s)
            if compact is not None:
                break
        out.append(compact if compact is not None else line)
    return out
