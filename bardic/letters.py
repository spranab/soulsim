"""Letters Across the Wheel — two souls, a thread left open, then picked up again.

An unresolved bond leaves a "thread" on both souls (soul.py); when a later
body of each meets again, the Annals mark it a reunion. This book finds the
strongest such case and writes it from the inside, twice over: the two
earlier bodies, each not yet knowing what is to come, and the two later
bodies, each carrying a recognition neither can fully name. A witness closes
it, saying what the record shows of both souls afterward.
"""
from __future__ import annotations

from typing import List, Optional

from soulsim.annals import Annals, Life
from .book import Book, Chapter
from .common import (birth_line, bond_lines, canon_years, glossary_of, moment_lines,
                     teaching_lines, work_lines)

LETTER_VOICE = ("You are writing a private letter, one soul's body to another, first "
                "person, intimate and plain. No titles, no epithets — use names exactly as "
                "given. Past or present tense, whichever the moment calls for. Say only "
                "what this body could know; do not reach for anything from a later time "
                "this body never lived to see.")

AFTERWORD_VOICE = ("You are the witness who watches every life, speaking now in your own "
                   "voice at the close of this book of letters. Address the reader "
                   "plainly, past tense, grave and spare. Say what became of both souls "
                   "afterward — their later lives, if any, and whether each found release "
                   "from the wheel or is still bound.")


def _find_pair(annals: Annals):
    """The strongest reunion: (a, b, pa, pb, strict) — a, b the two later bodies;
    pa, pb their earlier bodies (None if none exists); strict True if pa and pb
    were themselves bonded to each other."""
    reunions = [e for e in annals.events if e.kind == "reunion" and len(e.who) == 2]
    strict, loose = [], []
    for e in reunions:
        a, b = annals.by_name.get(e.who[0]), annals.by_name.get(e.who[1])
        if a is None or b is None:
            continue
        pa, pb = annals.previous_life(a), annals.previous_life(b)
        if pa is not None and pb is not None and (
                any(bd.partner == pb.name for bd in pa.bonds)
                or any(bd.partner == pa.name for bd in pb.bonds)):
            strict.append((a, b, pa, pb))
        elif pa is not None or pb is not None:
            loose.append((a, b, pa, pb))

    def weight(item) -> int:
        a, b, pa, pb = item
        return (len(a.moments) + len(b.moments) + (len(pa.moments) if pa else 0)
                + (len(pb.moments) if pb else 0))

    if strict:
        a, b, pa, pb = max(strict, key=weight)
        return a, b, pa, pb, True
    if loose:
        # prefer a case with both earlier bodies present, even if not proven
        # bonded to each other, so Part I can still be written
        both = [it for it in loose if it[2] is not None and it[3] is not None]
        pool = both or loose
        a, b, pa, pb = max(pool, key=weight)
        return a, b, pa, pb, False
    return None


def _bond_line_with(life: Life, other: str, annals: Annals) -> Optional[str]:
    marker = f"bonded with {other}"
    for l in bond_lines(life, annals):
        if marker in l:
            return l
    return None


def _later_lives_lines(life: Life, annals: Annals) -> List[str]:
    ls = annals.lives_of_soul(life.soul_serial)
    if life not in ls:
        return []
    later = ls[ls.index(life) + 1:]
    lines = []
    for l in later:
        if l.died_year is not None:
            if l.liberated:
                status = f"was freed from the wheel in year {l.died_year}, at {l.died_age}"
            elif l.dissolved:
                status = f"had its body unmade in a pralaya in year {l.died_year}"
            else:
                status = f"died in year {l.died_year}, at {l.died_age}"
            lines.append(f"After that, the soul that had been {life.name} was born as "
                        f"{l.name} of {l.house} in year {l.born_year}, and {status}.")
        else:
            lines.append(f"After that, the soul that had been {life.name} was born as "
                        f"{l.name} of {l.house} in year {l.born_year}, and was still "
                        "living when the record closed.")
    if not later:
        if life.liberated:
            lines.append(f"{life.name} was the last body that soul wore: it was freed "
                        f"from the wheel at death, after {life.life_n} lives.")
        elif life.died_year is not None:
            lines.append(f"{life.name} was the last body that soul wore when the record "
                        "closed; the soul was not freed from the wheel.")
        else:
            lines.append(f"{life.name} was still living, in that body, when the record "
                        "closed.")
    return lines


def build(annals: Annals, universe) -> Book:
    found = _find_pair(annals)
    cy = canon_years(annals)
    chapters: List[Chapter] = []

    if found is None:
        b = [f"By year {universe.year}, no reunion between two souls — a bond formed "
             "again after an earlier, unfinished one — had been recorded."]
        return Book(title="Letters Across the Wheel",
                   subtitle=f"World of seed {universe.cfg.seed}; no reunion yet recorded.",
                   epigraph="Some threads are still being spun.",
                   chapters=[Chapter(heading="Note", brief=b, voice=AFTERWORD_VOICE,
                                     words=(60, 150), must_say=[])],
                   glossary=glossary_of(annals, []), slug="letters")

    a, b, pa, pb, strict = found
    lives_for_glossary = [l for l in (a, b, pa, pb) if l is not None]

    # -- Part I: the earlier life -----------------------------------------------
    # Each letter opens on who it is from and to — true of the compiled
    # document itself even in the (more common) case the record never shows
    # these two earlier bodies having met.
    if pa is not None and pb is not None:
        brief_pa = [f"This is a letter from {pa.name} of {pa.house} to {pb.name} of "
                   f"{pb.house}.", birth_line(pa, annals)]
        bl = _bond_line_with(pa, pb.name, annals)
        if bl:
            brief_pa.append(bl)
        brief_pa += moment_lines(pa, pa.dramatic_moments(4))
        brief_pa += work_lines(pa, annals, cy)
        brief_pa += teaching_lines(pa, annals)

        brief_pb = [f"This is a letter from {pb.name} of {pb.house} to {pa.name} of "
                   f"{pa.house}.", birth_line(pb, annals)]
        bl = _bond_line_with(pb, pa.name, annals)
        if bl:
            brief_pb.append(bl)
        brief_pb += moment_lines(pb, pb.dramatic_moments(4))
        brief_pb += work_lines(pb, annals, cy)
        brief_pb += teaching_lines(pb, annals)

        chapters.append(Chapter(heading=f"{pa.name} to {pb.name}", brief=brief_pa,
                                voice=LETTER_VOICE, words=(250, 380),
                                must_say=[pa.name, pb.name],
                                part="Part I — The Earlier Life"))
        chapters.append(Chapter(heading=f"{pb.name} to {pa.name}", brief=brief_pb,
                                voice=LETTER_VOICE, words=(250, 380),
                                must_say=[pb.name, pa.name]))

    # -- Part II: the reunion life ------------------------------------------------
    brief_a = [f"This is a letter from {a.name} of {a.house} to {b.name} of {b.house}.",
              birth_line(a, annals)]
    bl = _bond_line_with(a, b.name, annals)
    if bl:
        brief_a.append(bl)
    brief_a += moment_lines(a, a.dramatic_moments(4))
    brief_a += work_lines(a, annals, cy)
    brief_a += teaching_lines(a, annals)

    brief_b = [f"This is a letter from {b.name} of {b.house} to {a.name} of {a.house}.",
              birth_line(b, annals)]
    bl = _bond_line_with(b, a.name, annals)
    if bl:
        brief_b.append(bl)
    brief_b += moment_lines(b, b.dramatic_moments(4))
    brief_b += work_lines(b, annals, cy)
    brief_b += teaching_lines(b, annals)

    chapters.append(Chapter(heading=f"{a.name} to {b.name}", brief=brief_a,
                            voice=LETTER_VOICE, words=(250, 380),
                            must_say=[a.name, b.name],
                            part="Part II — The Reunion Life"))
    chapters.append(Chapter(heading=f"{b.name} to {a.name}", brief=brief_b,
                            voice=LETTER_VOICE, words=(250, 380),
                            must_say=[b.name, a.name]))

    # -- Part III: afterword ---------------------------------------------------
    after = []
    after += _later_lives_lines(a, annals)
    after += _later_lives_lines(b, annals)
    must_after = [a.name, b.name]
    chapters.append(Chapter(heading="Afterword", brief=after, voice=AFTERWORD_VOICE,
                            words=(150, 250), must_say=must_after,
                            part="Part III — Afterword"))

    subtitle = (f"{a.name} and {b.name}, reunited" +
               (f", once {pa.name} and {pb.name}" if pa is not None and pb is not None else "")
               + f". World of seed {universe.cfg.seed}.")
    return Book(title="Letters Across the Wheel", subtitle=subtitle,
               epigraph="A thread left open does not vanish; it waits for a hand to "
                        "pick it up again.",
               chapters=chapters, glossary=glossary_of(annals, lives_for_glossary),
               slug="letters")
