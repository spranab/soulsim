"""Shared brief-writing helpers: true sentences about lives, myths and works.

A brief is a list of plain English facts. Everything a genre compiler hands to
the renderer passes through here, so the phrasing of the world's facts is
consistent across the epic, the novel, the history and the scripture — and so
that the only numbers a bard ever sees are years, ages and counts.
"""
from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Set

from soulsim.annals import (Annals, Life, ENEMY_EN, COND_EN, SCALE_EN, TOLD_EN)
from soulsim.religion import GROUND_TRUTHS

PROP_EN = {
    "rebirth": "the soul returns in new bodies",
    "ages_cycle": "the world moves through recurring ages",
    "dawn_returns": "after dissolution, a golden age dawns again",
    "liberation_exists": "a soul can leave the wheel forever",
    "effort_frees": "restraint, exercised, loosens the wheel's grip",
    "habit_binds": "repeated acts groove the soul",
    "helpers_descend": "when dharma falls, a freed one returns",
    "vice_cascades": "craving breeds anger, and anger breeds delusion",
    "world_ends_forever": "the world will one day end and never return",
    "fate_is_random": "fate is random and no act matters",
    "only_one_life": "you live once only",
    "power_frees": "domination liberates",
}
RASA_EN = {"shanta": "peace", "karuna": "sorrow", "vira": "valor", "raudra": "fury",
           "adbhuta": "wonder", "shringara": "love", "hasya": "laughter",
           "bhayanaka": "dread", "bibhatsa": "refusal"}
ROLE_EN = {"mystic": "a mystic", "teacher": "a teacher", "reformer": "a reformer",
           "caretaker": "a caretaker", "ruler": "a ruler", "opportunist": "an opportunist",
           "brooder": "a brooder", "wanderer": "a wanderer", "avatar": "a descended one",
           "": "a wanderer"}
YUGA_CHARACTER = {
    "Satya": "an age when truth was easy to see and temptation weak",
    "Treta": "an age when truth was still mostly visible and temptation had begun to pull",
    "Dvapara": "an age when truth was half-hidden and temptation strong",
    "Kali": "an age when truth was buried in noise and temptation ruled",
}


def sex_word(life: Life) -> str:
    return "woman" if life.sex == "female" else "man"


def englishify(reason: str) -> str:
    """born_reason strings carry Sanskrit enemy names; render them in English."""
    out = reason or "its turn on the wheel came round"
    for k, v in ENEMY_EN.items():
        out = re.sub(rf"\b{k}\b", v, out)
    out = out.replace("non-attachment", "non-attachment").replace("_", " ")
    return out


def claims_of(myth) -> List[str]:
    out = []
    for p, pol in myth.props.items():
        out.append(PROP_EN[p] if pol else f"it is not so that {PROP_EN[p]}")
    return out


def verse_line(verse: str) -> str:
    return " / ".join(l.strip() for l in verse.split("\n") if l.strip())


# ---------------------------------------------------------------------------
# lines about a life
# ---------------------------------------------------------------------------
def birth_line(life: Life, annals: Annals) -> str:
    when = annals.age_phrase(life.born_year)
    if life.founding:
        return (f"{life.name}, a {sex_word(life)} of the house of {life.house}, was among "
                f"the first, already {life.born_age} years old when the world was made "
                f"manifest in year {life.born_year}, in {when}.")
    if life.is_avatar:
        return (f"{life.name}, a {sex_word(life)} of the house of {life.house}, was not born "
                f"but descended, already grown, in year {life.born_year}, in {when}.")
    return (f"{life.name}, a {sex_word(life)} of the house of {life.house}, was born in "
            f"year {life.born_year}, in {when}, {life.parents_phrase()}.")


def siblings_of(life: Life, annals: Annals, k: int = 4) -> List[str]:
    if not life.mother:
        return []
    m = annals.by_name.get(life.mother)
    if not m:
        return []
    return [c for c in m.children if c != life.name][:k]


def is_child_life(l: Life) -> bool:
    return l.died_age is not None and l.died_age < 16 and not l.moments


def previous_life_line(life: Life, annals: Annals, skip_children: bool = True) -> Optional[str]:
    prev = annals.previous_life(life)
    while prev is not None and skip_children and is_child_life(prev):
        prev = annals.previous_life(prev)
    if prev is None:
        return None
    if is_child_life(prev):
        return (f"Before this body, the soul had worn the body of {prev.name} of "
                f"{prev.house} for {prev.died_age} years only, and died a child.")
    end = ("whose body was unmade in a pralaya" if prev.dissolved else
           f"who died at {prev.died_age}")
    return (f"Before this body, the soul had been {prev.name} of {prev.house}, "
            f"{ROLE_EN.get(prev.role, 'a wanderer')}, {end} in year {prev.died_year}, "
            f"ruled at the end by {ENEMY_EN.get(prev.end_enemy, 'craving')}.")


def reunion_context(life: Life, partner_name: str, annals: Annals) -> str:
    """Who the partner's soul was before — the recognition an epic turns on."""
    p = annals.by_name.get(partner_name)
    if p is None:
        return ""
    pprev = annals.previous_life(p)
    mine = annals.previous_life(life)
    if pprev is None:
        return ""
    s = f" In an earlier life that soul had been {pprev.name} of {pprev.house}, {ROLE_EN.get(pprev.role, 'a wanderer')}"
    if mine is not None and any(b.partner == pprev.name for b in mine.bonds):
        s += f", bonded then to {mine.name} — the two had left something unfinished"
    return s + "."


def bond_lines(life: Life, annals: Annals) -> List[str]:
    out = []
    for b in life.bonds:
        age = b.year - life.born_year + life.born_age
        s = f"At {age}, in year {b.year}, {life.name} bonded with {b.partner}"
        if b.reunion:
            s += ", a soul known from another life." + reunion_context(life, b.partner, annals)
        else:
            s += "."
        if b.ended is not None:
            p = annals.by_name.get(b.partner)
            if b.how == "death":
                if p is not None and p.died_year == b.ended and life.died_year != b.ended:
                    how = f"until {b.partner} died in year {b.ended}"
                elif life.died_year == b.ended and not (p is not None and p.died_year == b.ended):
                    how = f"until {life.name}'s own death in year {b.ended}"
                else:
                    how = f"until both died in year {b.ended}"
            elif b.how == "drift":
                how = f"until they drifted apart in year {b.ended}"
            else:
                how = f"until the world itself dissolved in year {b.ended}"
            s += f" They stayed together {max(b.years, 0)} years, {how}."
        out.append(s)
    if life.children:
        kids = []
        for c in life.children[:8]:
            cl = annals.by_name.get(c)
            kids.append(f"{c} (born year {cl.born_year})" if cl else c)
        out.append(f"Children born to {life.name}: " + ", ".join(kids) + ".")
    return out


def deed_for(life: Life, moment) -> Optional[object]:
    for d in life.deeds:
        if d.year == moment.year and d.condition == moment.condition:
            return d
    return None


def moment_lines(life: Life, moments: Iterable, with_public: bool = True) -> List[str]:
    out = []
    for m in moments:
        s = f"At {m.age}, in year {m.year}, {COND_EN[m.condition]}, {life.name} " \
            f"{_kind_phrase(m.kind)}."
        d = deed_for(life, m) if with_public else None
        if d is not None:
            what = "the deed was seen as good" if d.alignment > 0 else "the deed was seen as ill"
            crowd = "" if d.n_actors <= 1 else f"; {d.n_actors} others were part of it"
            wit = "a single witness" if d.witnesses == 1 else f"{d.witnesses} witnesses"
            s += (f" This was done in public, before {wit}; {what}, "
                  f"and the story of it was told {TOLD_EN[d.scale]}{crowd}.")
        out.append(s)
    return out


def _kind_phrase(kind: str) -> str:
    return {"mastered": "saw the impulse rise and mastered it",
            "betrayed": "saw the better course and chose the worse",
            "swept": "was swept along unseeing, the impulse acting before it was noticed",
            "effortless": "did the right thing without any struggle",
            "held": "held to a middle course, neither the best nor the worst"}[kind]


def work_lines(life: Life, annals: Annals, canon_year: Dict[int, int],
               years: Optional[tuple] = None) -> List[str]:
    out = []
    for aid in life.works:
        w = annals.works.get(aid)
        if w is None:
            continue
        if years and not (years[0] <= w.year < years[1]):
            continue
        age = w.year - life.born_year + life.born_age
        s = (f"In year {w.year}, at {age}, {life.name} composed a {w.form} of "
             f"{RASA_EN.get(w.rasa, w.rasa)}, born of this: {born_of_phrase(w.born_of)}. "
             f"Its words: \"{verse_line(w.verse)}\".")
        if aid in canon_year:
            s += f" The world took it into its canon in year {canon_year[aid]}."
        out.append(s)
    return out


def teaching_lines(life: Life, annals: Annals, years: Optional[tuple] = None) -> List[str]:
    out = []
    for mn in life.revelations:
        m = annals.myths.get(mn)
        if m is None:
            continue
        if years and not (years[0] <= m.born_year < years[1]):
            continue
        age = m.born_year - life.born_year + life.born_age
        s = f"In year {m.born_year}, at {age}, {life.name} spoke a teaching the world came to call '{m.name}'"
        if m.props:
            s += ", holding that: " + "; ".join(claims_of(m)) + "."
        else:
            s += "; what it held has since been lost in the retelling."
        s += lineage_phrase(m)
        out.append(s)
    return out


def born_of_phrase(born_of: str) -> str:
    b = englishify(born_of)
    if b.startswith("a life of "):
        return b.replace("a life of ", "a life steeped in ").replace(
            "raudra", "fury").replace("shanta", "peace").replace("karuna", "sorrow").replace(
            "vira", "valor").replace("adbhuta", "wonder").replace("shringara", "love").replace(
            "hasya", "laughter").replace("bhayanaka", "dread").replace("bibhatsa", "refusal")
    return "a moment when, " + b


def lineage_phrase(m) -> str:
    parts = []
    for y, kind in m.lineage:
        parts.append({"institution": f"in year {y} it became an institution",
                      "corruption": f"in year {y} its canon was corrupted by power",
                      "reform": f"in year {y} a reformer restored a lost truth to it",
                      "extinction": f"in year {y} its way was forgotten"}[kind])
    return (" " + "; ".join(parts).capitalize() + ".") if parts else ""


def death_line(life: Life, annals: Annals) -> str:
    he, him, his = life.pronoun
    when = annals.age_phrase(life.died_year) if life.died_year is not None else ""
    if life.died_year is None:
        return f"{life.name} was still living when the record closed."
    if life.is_avatar:
        return (f"In year {life.died_year}, at {life.died_age}, {life.name} laid the body "
                f"down and withdrew, the walk of a descended one being finished.")
    if life.dissolved:
        s = (f"In year {life.died_year}, at {life.died_age}, the body of {life.name} was "
             f"unmade with the whole manifest world in the pralaya. ")
    else:
        s = (f"{life.name} died in year {life.died_year}, at {life.died_age}, in {when}. ")
    s += (f"The world would call {him} {ROLE_EN.get(life.role, 'a wanderer')}. "
          f"Over this life {life.virtue_phrase()}; the ruling enemy at the end was "
          f"{ENEMY_EN.get(life.end_enemy, 'craving')}.")
    if life.liberated:
        s += (f" And with this death the soul left the wheel forever — liberation, "
              f"after {life.life_n} lives.")
    elif not life.dissolved:
        s += " The soul returned to the unmanifest, to wait for another body."
    return s


def ledger_line(life: Life) -> str:
    v, a, u, e = life.ledger
    parts = []
    if v:
        parts.append(f"{v} times the impulse was seen and mastered")
    if a:
        parts.append(f"{a} times the better was seen and the worse chosen")
    if u:
        parts.append(f"{u} times the impulse acted unseen")
    if e:
        parts.append(f"{e} times the right thing was done without struggle")
    if not parts:
        return "Background for tone, not to be recited: this life faced no test at all."
    shape = ("a life that never once had to fight its own impulse" if not v and not a else
             "a life more often swept than steering" if u > v + a + e else
             "a life of open struggle" if v + a >= e else "a life mostly at ease")
    return ("Background for tone, not to be recited: " + shape + " — over the whole life, "
            + "; ".join(parts) + ".")


def canon_years(annals: Annals) -> Dict[int, int]:
    return {e.data["aid"]: e.year for e in annals.events if e.kind == "canon"}


def world_between(annals: Annals, y0: int, y1: int, k: int = 3) -> List[str]:
    """What the world did while a soul waited between bodies."""
    evs = annals.events_between(y0, y1, kinds={"pralaya", "dawn", "avatar", "institution",
                                                "withdrawal"})
    return [f"Year {e.year}: {in_world(e.text)}." for e in evs[:k]]


def in_world(text: str) -> str:
    """Strip the witness's gradings (e.g. '(100% true at canonization)') from
    chronicle text that inhabitants are supposed to be able to say."""
    return re.sub(r"\s*\([^)]*true[^)]*\)", "", text).rstrip(".")


def glossary_of(annals: Annals, lives: Iterable[Life]) -> Set[str]:
    g = set(annals.houses) | {"Satya", "Treta", "Dvapara", "Kali"}
    for l in lives:
        g.add(l.name)
        g.update(l.children)
        g.update(b.partner for b in l.bonds)
        if l.mother:
            g.add(l.mother)
        if l.father:
            g.add(l.father)
        for mn in l.revelations:
            g.update(w for w in re.findall(r"[A-Z][a-z]+", mn))
    return g


def life_score(life: Life) -> float:
    """How much novel there is in a life."""
    c = life.counts()
    if life.died_age is None or life.died_age < 40:
        return -1
    return (len(life.dramatic_moments(8)) + 3 * bool(life.bonds) + min(len(life.children), 4)
            + 2 * min(len(life.deeds), 3) + 2 * len(life.works) + 2 * len(life.revelations)
            + 3 * (c["mastered"] > 0 and c["betrayed"] > 0)
            + 3 * any(b.reunion for b in life.bonds) + 2 * life.liberated)
