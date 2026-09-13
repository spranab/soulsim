"""The Saga — a house across the ages.

Every life belongs to a house; the Annals never forget which. Where the epic
follows one soul and the novel follows one life, the saga follows one lineage
of stone and name: the house that carried the most weight in the record —
its rulers, its seers, its deeds seen across a kingdom, its works taken into
canon, its souls freed, its reunions. A prologue at the founding, a chapter
per age the house lived through, an epilogue at the record's close.
"""
from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional

from soulsim.annals import Annals, Life
from .book import Book, Chapter
from .common import glossary_of, notable_dead_line, teaching_lines, RASA_EN
from .render import ordinal

PROLOGUE_VOICE = ("You are the chronicler of a single house of an ancient world, opening "
                  "the saga of its line. Grave, proud but exact — a family chronicler, not "
                  "a flatterer. Past tense. Say what the house is, how it began, and how "
                  "much of the record it has held.")

AGE_VOICE = ("You are the chronicler of a single house, telling what that house did in one "
             "age of the world: its dead worth naming, its deeds seen across a kingdom or "
             "the world, its seers and what they taught, its works taken into the canon, "
             "any of its bonds that were a reunion of souls, any of its members freed from "
             "the wheel or descended as an avatar. Proud but exact, past tense. Only the "
             "house's own record matters here; do not moralize about other houses.")

EPILOGUE_VOICE = ("You are the chronicler of a single house, closing its saga at the record's "
                  "end. Say plainly what the house is when the record closes, and — since "
                  "you are the chronicler and can see the whole record — what the songs sung "
                  "about the house get wrong, if anything. Grave, exact, past tense.")


def house_score(annals: Annals, members: List[Life]) -> float:
    deeds3 = sum(1 for l in members for d in l.deeds if d.scale >= 3)
    rulers_died = sum(1 for l in members if l.role == "ruler" and l.died_year is not None)
    seers = sum(1 for l in members if l.revelations)
    works_ct = sum(len(l.works) for l in members)
    liberated_ct = sum(1 for l in members if l.liberated)
    reunions_ct = sum(1 for l in members for b in l.bonds if b.reunion)
    return (3 * deeds3 + 2 * rulers_died + 2 * seers + works_ct + liberated_ct + reunions_ct)


def choose_house(annals: Annals) -> str:
    by_house: Dict[str, List[Life]] = {h: [] for h in annals.houses}
    for l in annals.lives.values():
        by_house.setdefault(l.house, []).append(l)
    return max(annals.houses, key=lambda h: house_score(annals, by_house[h]))


def _member_of(annals: Annals, name: str, house: str) -> bool:
    l = annals.by_name.get(name)
    return l is not None and l.house == house


def _canon_line(annals: Annals, e) -> Optional[str]:
    w = annals.works.get(e.data.get("aid"))
    if w is None:
        return None
    creator = e.who[0] if e.who else w.creator
    return (f"In year {e.year}, the {w.form} of {RASA_EN.get(w.rasa, w.rasa)} that "
            f"{creator} composed was taken into the world's canon.")


def build(annals: Annals, universe) -> Book:
    house = choose_house(annals)
    members = [l for l in annals.lives.values() if l.house == house]
    chapters: List[Chapter] = []

    # -- prologue -------------------------------------------------------------
    founders = sorted(l.name for l in members if l.founding and l.born_year == 0)
    roles = Counter(l.role for l in members if l.role)
    b = [f"The house of {house} is one of the nine houses of the world: "
         + ", ".join(annals.houses) + "."]
    if founders:
        b.append(f"At the founding, in year 0, the house of {house} began with these "
                 "members: " + ", ".join(founders) + ".")
    b.append(f"Over the whole run of the record the house of {house} held "
             f"{len(members)} lives.")
    if roles:
        b.append(f"Of these the world called {roles.get('ruler', 0)} rulers, "
                 f"{roles.get('mystic', 0)} mystics, and {roles.get('teacher', 0)} "
                 "teachers.")
    must = [house] + founders[:3]
    chapters.append(Chapter(heading=f"Prologue: The House of {house}", brief=b,
                            voice=PROLOGUE_VOICE, words=(180, 260), must_say=must[:4]))

    # -- one chapter per age ----------------------------------------------------
    for a in annals.ages(universe.year):
        y0, y1 = a["start"], a["end"]
        lines: List[str] = []
        named: List[str] = []

        died = [l for l in members if l.died_year is not None and y0 <= l.died_year < y1]
        scored = sorted(died, key=lambda l: -(len(l.deeds) + len(l.works)
                                              + len(l.revelations) + int(l.liberated)))
        notable = [l for l in scored if notable_dead_line(l)][:4]
        if notable:
            lines.append("Notable dead of the house in this age:")
            for l in notable:
                lines.append(notable_dead_line(l))
                named.append(l.name)

        deeds = [e for e in annals.events_between(y0, y1, kinds={"deed"})
                if e.who and _member_of(annals, e.who[0], house)]
        deeds.sort(key=lambda e: (-e.data["scale"], -e.data["n_actors"], e.year))
        deeds = sorted(deeds[:5], key=lambda e: e.year)
        if deeds:
            lines.append("The house's deeds most talked of in this age:")
            for e in deeds:
                lines.append(f"Year {e.year}: {e.text}.")
                named.append(e.who[0])

        # teachings: the house's own seers, capped to the strongest few so an
        # age chapter stays a chapter and not a ledger
        candidates = []
        for l in members:
            for mn in l.revelations:
                m = annals.myths.get(mn)
                if m is not None and y0 <= m.born_year < y1:
                    candidates.append((m.strength, l, m))
        candidates.sort(key=lambda t: -t[0])
        seer_lines: List[str] = []
        for _, l, m in candidates[:4]:
            tl = teaching_lines(l, annals, years=(m.born_year, m.born_year + 1))
            line = next((x for x in tl if f"'{m.name}'" in x), None)
            if line:
                seer_lines.append(line)
                named.append(l.name)
        if seer_lines:
            lines.append("Teachings spoken by the house's own seers in this age:")
            lines += seer_lines

        canon_lines = []
        for e in annals.events_between(y0, y1, kinds={"canon"}):
            if e.who and _member_of(annals, e.who[0], house):
                cl = _canon_line(annals, e)
                if cl:
                    canon_lines.append(cl)
                    named.append(e.who[0])
        if canon_lines:
            lines.append("Works of the house canonized in this age:")
            lines += canon_lines[:4]

        reunion_lines = []
        for e in annals.events_between(y0, y1, kinds={"reunion"}):
            if any(_member_of(annals, n, house) for n in e.who):
                reunion_lines.append(f"Year {e.year}: {e.text}.")
                named += list(e.who)
        if reunion_lines:
            lines.append("Bonds of the house that were reunions of souls, in this age:")
            lines += reunion_lines

        moksha_lines = []
        for e in annals.events_between(y0, y1, kinds={"moksha"}):
            if e.who and _member_of(annals, e.who[0], house):
                moksha_lines.append(f"Year {e.year}: {e.text}.")
                named.append(e.who[0])
        if moksha_lines:
            total = len(moksha_lines)
            kept = moksha_lines[:5]
            lines.append("Members of the house freed from the wheel in this age"
                         + (f" ({total} in all; the first 5 named)" if total > 5 else "")
                         + ":")
            lines += kept

        avatar_lines = []
        for e in annals.events_between(y0, y1, kinds={"avatar"}):
            if e.who and _member_of(annals, e.who[0], house):
                avatar_lines.append(f"Year {e.year}: {e.text}.")
                named.append(e.who[0])
        if avatar_lines:
            lines.append("Members of the house who descended as avatars in this age:")
            lines += avatar_lines

        if not lines:
            continue  # the house has nothing in this age; skip it

        heading = f"The {a['yuga']} Age of the {ordinal(a['cycle'] + 1).capitalize()} Cycle"
        seen: List[str] = []
        for n in named:
            if n not in seen:
                seen.append(n)
        must = ([house] + seen[:3])[:4]
        chapters.append(Chapter(heading=heading, brief=lines, voice=AGE_VOICE,
                                words=(300, 450), must_say=must))

    # -- epilogue ---------------------------------------------------------------
    living = [l for l in members if l.died_year is None]
    b = [f"When the record closes, in year {universe.year}, the house of {house} has "
         f"{len(living)} living members."]
    candidates = sorted(
        (m for m in universe.religion.myths
         if m.story is not None and _member_of(annals, m.story.actor, house)),
        key=lambda m: -m.strength)
    must = [house]
    if candidates:
        m = candidates[0]
        deed = "did well" if m.story.align > 0 else "did ill"
        b.append(f"The most-sung name of the house is {m.story.actor}, in a song called "
                 f"'{m.name}' with {int(m.strength)} believers, which says {m.story.actor} "
                 f"{deed}.")
        src = universe.culture.trace_archive.get(m.story.source_tid) if m.story.source_tid else None
        if src is None:
            b.append("The record knows no such deed; the song was made up.")
        elif src[0] != m.story.actor:
            b.append(f"The record says the deed was {src[0]}'s, not {m.story.actor}'s.")
        else:
            b.append(f"The record agrees: the deed was {m.story.actor}'s own.")
        must.append(m.story.actor)
        if src is not None and src[0] != m.story.actor:
            must.append(src[0])
    chapters.append(Chapter(heading=f"Epilogue: The House of {house} at the Record's Close",
                            brief=b, voice=EPILOGUE_VOICE, words=(180, 280),
                            must_say=must[:4]))

    subtitle = (f"The house of {house} among the nine houses of the world, across "
                f"{len(members)} lives, to year {universe.year}. World of seed "
                f"{universe.cfg.seed}.")
    return Book(title=f"The Saga of the House of {house}", subtitle=subtitle,
               epigraph="A house is not its stones; it is who was born there, and what "
                        "they did with the years they were given.",
               chapters=chapters, glossary=glossary_of(annals, members), slug="saga")
