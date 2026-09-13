"""The Novel — one life, in depth.

Where the epic spends a canto on a life, the novel spends a book on one. It
chooses the life with the most novel in it: a long adult span, a bond, children,
tests won and tests failed, something done in public, something composed or
taught. Chapters follow the shape of a life; the last chapter is what the
world kept of it — including, when it happens, the wrong name.
"""
from __future__ import annotations

from typing import List, Optional

from soulsim.annals import Annals, Life, ENEMY_EN, SCALE_EN
from .book import Book, Chapter
from .common import (birth_line, bond_lines, canon_years, death_line, englishify,
                     glossary_of, ledger_line, life_score, moment_lines,
                     previous_life_line, siblings_of, teaching_lines, work_lines,
                     ROLE_EN, RASA_EN, sex_word, verse_line)

VOICE = ("You are a literary novelist writing one chapter of a novel set in an ancient "
         "world. Close third person, past tense. Interiority and texture are your art: what "
         "a room felt like, what a temptation felt like from inside, the weight of a "
         "choice before and after. Brief dialogue is allowed but must not state anything "
         "the record does not. Do not moralize. Do not explain the world's rules; live "
         "inside them.")


def choose_life(annals: Annals) -> Life:
    return max(annals.lives.values(), key=life_score)


def build(annals: Annals, universe) -> Book:
    life = choose_life(annals)
    cy = canon_years(annals)
    he, him, his = life.pronoun
    born, died = life.born_year, life.died_year or universe.year
    mid_end = max(born + 30, died - 15)
    chapters: List[Chapter] = []
    who = (f"{life.name} is a {sex_word(life)} of the house of {life.house}, born in year "
           f"{born}; every age below is {'hers' if life.sex == 'female' else 'his'}.")

    # 1. the house
    b = [birth_line(life, annals)]
    sibs = siblings_of(life, annals)
    if sibs:
        b.append(f"{life.name} had these siblings: " + ", ".join(sibs) + ".")
    if not life.founding:
        b.append(f"Why the soul came to this house: {englishify(life.born_reason)}.")
    pl = previous_life_line(life, annals)
    if pl:
        b.append(pl + " Nothing of that was remembered, but something of it was carried.")
    b.append(f"The soul's ruling enemy from birth was {ENEMY_EN.get(life.start_enemy, 'craving')}.")
    b.append(f"The age: {annals.age_phrase(born)}.")
    early = [m for m in life.dramatic_moments(8) if m.age < 22][:2]
    b += moment_lines(life, early)
    chapters.append(Chapter(heading=f"1. The House of {life.house}", brief=b, voice=VOICE,
                            words=(380, 520), must_say=[life.name, life.house] + sibs[:1]))

    # 2. youth
    youth = [m for m in life.dramatic_moments(10) if 22 <= m.age < 30][:4]
    if youth:
        b = [who, f"{life.name} in {his} twenties."] + moment_lines(life, youth)
        b += work_lines(life, annals, cy, years=(born + 22, born + 30))
        chapters.append(Chapter(heading="2. Youth", brief=b, voice=VOICE, words=(380, 520),
                                must_say=[life.name]))

    # 3. the bond
    if life.bonds:
        b = [who] + bond_lines(life, annals)
        for bd in life.bonds:
            p = annals.by_name.get(bd.partner)
            if p and p.role:
                b.append(f"{bd.partner} was of the house of {p.house}, and the world would "
                         f"one day call {'her' if p.sex == 'female' else 'him'} "
                         f"{ROLE_EN.get(p.role, 'a wanderer')}.")
        chapters.append(Chapter(heading="3. The Bond", brief=b, voice=VOICE, words=(380, 520),
                                must_say=[bd.partner for bd in life.bonds][:2] + life.children[:2]))

    # 4. the tests
    middle = [m for m in life.dramatic_moments(12) if 30 <= m.age < mid_end - born][:5]
    b = [who, f"{life.name} from age 30 to age {mid_end - born}."] + moment_lines(life, middle)
    b += work_lines(life, annals, cy, years=(born + 30, mid_end))
    b += teaching_lines(life, annals, years=(born + 30, mid_end))
    if len(b) > 2:
        chapters.append(Chapter(heading="4. The Tests", brief=b, voice=VOICE, words=(420, 560),
                                must_say=[life.name]))

    # 5. the turning
    late = [m for m in life.dramatic_moments(12) if m.age >= mid_end - born][:4]
    b = [who, f"{life.name} in the last {died - mid_end} years of {his} life."]
    b += moment_lines(life, late)
    b += work_lines(life, annals, cy, years=(mid_end, died + 1))
    b += teaching_lines(life, annals, years=(mid_end, died + 1))
    for bd in life.bonds:
        if bd.how == "death" and bd.ended is not None and bd.ended < died:
            b.append(f"In year {bd.ended}, when {life.name} was {bd.ended - born}, "
                     f"{bd.partner} died, after {bd.years} years together.")
    buried = []
    for c in life.children:
        cl = annals.by_name.get(c)
        if cl and cl.died_year is not None and cl.died_year < died:
            buried.append(f"{c} (died in year {cl.died_year}, at {cl.died_age})")
    if buried:
        b.append(f"{life.name} outlived these children: " + ", ".join(buried) + ".")
    if len(b) > 2:
        chapters.append(Chapter(heading="5. The Turning", brief=b, voice=VOICE, words=(380, 520),
                                must_say=[life.name]))

    # 6. the last year
    b = [who, death_line(life, annals), ledger_line(life)]
    nxt = None
    ls = annals.lives_of_soul(life.soul_serial)
    if life in ls and ls.index(life) + 1 < len(ls):
        nxt = ls[ls.index(life) + 1]
    if nxt:
        b.append(f"The soul that had been {life.name} was born again in year {nxt.born_year} "
                 f"as {nxt.name} of {nxt.house}, because {englishify(nxt.born_reason)}.")
    chapters.append(Chapter(heading="6. The Last Year", brief=b, voice=VOICE, words=(330, 460),
                            must_say=[life.name]))

    # 7. what the world kept
    b = []
    for m in universe.religion.myths:
        if m.story is not None and m.story.actor == life.name:
            src = universe.culture.trace_archive.get(m.story.source_tid) if m.story.source_tid else None
            deed = "did well" if m.story.align > 0 else "did ill"
            s = (f"A song called '{m.name}', with {int(m.strength)} believers, says that "
                 f"{life.name} {deed} {SCALE_EN[m.story.scale]}.")
            if src is not None and src[0] != life.name:
                s += f" The record says the deed was {src[0]}'s, not {life.name}'s."
            elif src is None:
                s += " The record knows no such deed; the song was made up."
            b.append(s)
    for aid in life.works:
        if aid in cy:
            w = annals.works[aid]
            b.append(f"The {w.form} of {RASA_EN.get(w.rasa, w.rasa)} that {life.name} composed "
                     f"in year {w.year} was taken into the canon in year {cy[aid]}; its words: "
                     f"\"{verse_line(w.verse)}\".")
    for c in life.children[:6]:
        cl = annals.by_name.get(c)
        if cl and cl.role and cl.died_year is not None:
            b.append(f"{c} died in year {cl.died_year} at {cl.died_age}; the world called "
                     f"{'her' if cl.sex == 'female' else 'him'} {ROLE_EN.get(cl.role, 'a wanderer')}.")
    if b:
        chapters.append(Chapter(heading="7. What the World Kept", brief=b, voice=VOICE,
                                words=(260, 400), must_say=[life.name]))

    return Book(title=f"{life.name}",
                subtitle=(f"A life in the house of {life.house}, years {born}–{died}, "
                          f"{annals.age_phrase(born)}. World of seed {universe.cfg.seed}."),
                epigraph="A person is a soul, a body, and the weather between them.",
                chapters=chapters, glossary=glossary_of(annals, [life]), slug="novel")
