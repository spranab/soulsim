"""The Upanishad — teaching set down as dialogue, seer and student, seated near.

An upaniṣad is literally a sitting-down-near: a teaching given to one real
listener, clause by clause. The four strongest living teachings with a named
seer each get one dialogue, with the seer's own real household supplying the
student — a child, failing that a partner, failing that a sibling. The seer
answers as a believer in every clause the teaching holds, true or false; the
witness's gloss on which is which stays out of the dialogues and in the
colophon, exactly as the Veda's does.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from soulsim.annals import Annals, Life
from soulsim.religion import GROUND_TRUTHS
from .book import Book, Chapter
from .common import (birth_line, claims_of, glossary_of, lineage_phrase,
                     moment_lines, siblings_of, PROP_EN, ROLE_EN)

INVOCATION_VOICE = ("You are the compiler's voice, opening a book of dialogues between "
                    "seers and their students. Briefly name the seers and the ages their "
                    "teachings were spoken in. Solemn, brief. Do not explain the teachings "
                    "yet; that is for the dialogues.")

DIALOGUE_VOICE = ("You are staging a scripture's dialogue between a seer and a real student "
                  "of that seer's own household. Write it as a script: each line begins "
                  "with the speaker's name and a colon, alternating between the two "
                  "speakers, each in first person. The student asks about each clause the "
                  "teaching holds, one at a time, in the order given; the seer answers as a "
                  "believer in that very clause, with full conviction, sometimes drawing on "
                  "a moment from the seer's own life as an example. Do not add narration "
                  "outside the dialogue lines, and do not summarize.")


def _interlocutor(seer: Life, annals: Annals) -> Optional[Tuple[str, str]]:
    if seer.children:
        return seer.children[0], "child"
    if seer.bonds:
        return seer.bonds[0].partner, "partner"
    sibs = siblings_of(seer, annals)
    if sibs:
        return sibs[0], "sibling"
    return None


def _relation_line(seer: Life, student: str, relation: str) -> str:
    if relation == "child":
        return f"{student} was the first child of {seer.name}."
    if relation == "partner":
        return f"{student} was bonded to {seer.name}."
    return f"{student} was a sibling of {seer.name}, another child of {seer.mother}."


def build(annals: Annals, universe) -> Book:
    R = universe.religion
    holders = sorted([m for m in R.myths if m.props and m.seer], key=lambda m: -m.strength)
    chosen = []
    for m in holders:
        seer = annals.by_name.get(m.seer)
        if seer is None:
            continue
        who = _interlocutor(seer, annals)
        if who is None:
            continue
        chosen.append((m, seer, who[0], who[1]))
        if len(chosen) == 4:
            break

    chapters: List[Chapter] = []

    # -- invocation ---------------------------------------------------------
    b = [f"This book holds {len(chosen)} dialogue"
         + ("s" if len(chosen) != 1 else "")
         + ", each a seer teaching a real listener of the seer's own household."]
    for m, seer, student, relation in chosen:
        b.append(f"'{m.name}' was spoken by {seer.name} of {seer.house} in "
                 f"{annals.age_phrase(m.born_year)}.")
    must = [seer.name for _, seer, _, _ in chosen][:4]
    chapters.append(Chapter(heading="Invocation", brief=b, voice=INVOCATION_VOICE,
                            words=(60, 120), must_say=must))

    gloss: List[str] = []
    for m, seer, student, relation in chosen:
        age_seer = m.born_year - seer.born_year + seer.born_age
        b = [birth_line(seer, annals),
             (f"{seer.name} was {ROLE_EN.get(seer.role, 'a wanderer')} of the house of "
              f"{seer.house}." if seer.role else
              f"{seer.name} of the house of {seer.house} was still living when the "
              f"record closed, so the world had not yet named what {seer.pronoun[0]} was."),
             f"{seer.name} was {age_seer} years old, in year {m.born_year}, in "
             f"{annals.age_phrase(m.born_year)}, when {seer.pronoun[0]} spoke the teaching "
             f"the world came to call '{m.name}'.",
             _relation_line(seer, student, relation)]
        student_life = annals.by_name.get(student)
        if student_life is not None:
            b.append(birth_line(student_life, annals))
        for c in claims_of(m):
            b.append(f"The teaching holds that {c}.")
        lp = lineage_phrase(m).strip()
        if lp:
            b.append(lp)
        b += moment_lines(seer, seer.dramatic_moments(3))
        must_say = [seer.name, student, m.name]
        chapters.append(Chapter(heading=f"{m.name}: {seer.name} and {student}", brief=b,
                                voice=DIALOGUE_VOICE, words=(260, 400),
                                must_say=must_say))
        truths = [f"{'true' if GROUND_TRUTHS[p] == pol else 'FALSE'}: "
                  f"{PROP_EN[p] if pol else 'denies that ' + PROP_EN[p]}"
                  for p, pol in m.props.items()]
        gloss.append(f"- **{m.name}** ({m.accuracy():.0%} true): " + "; ".join(truths))

    colophon = ("**The Witness's Gloss** — what the world cannot see.\n\n"
                "On the teachings:\n" + "\n".join(gloss)) if gloss else ""

    lives = [seer for _, seer, _, _ in chosen]
    for _, _, student, _ in chosen:
        sl = annals.by_name.get(student)
        if sl is not None:
            lives.append(sl)
    myth_words = set()
    for m, *_ in chosen:
        myth_words.update(re.findall(r"[A-Z][a-z]+", m.name))
    return Book(title=f"The Upanishad of the World of Seed {universe.cfg.seed}",
               subtitle=(f"{len(chosen)} teachings, each set down as the seer spoke it to "
                         "one real listener of the household. World of seed "
                         f"{universe.cfg.seed}."),
               epigraph="Sit down near; what is spoken to a crowd is a sermon, what is "
                        "spoken to one who will ask again is a teaching.",
               chapters=chapters,
               glossary=glossary_of(annals, lives) | myth_words,
               slug="upanishad", colophon=colophon, inside=True)
