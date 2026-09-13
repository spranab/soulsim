"""The Epic — one soul, many lives, the ages turning around it.

An itihāsa needs a hero who is the same person across bodies; the simulation
has exactly that: the persistent soul. The epic follows the soul with the
hardest recorded road to liberation (or, if no soul was freed, the one that
carried the most lives). Each life is a canto; the world's turnings between
its deaths and births are interludes; recognition — meeting a soul known
from another life — is the thread the whole poem pulls on.
"""
from __future__ import annotations

from typing import List

from soulsim.annals import Annals, Life, ENEMY_EN
from .book import Book, Chapter
from .common import (birth_line, bond_lines, canon_years, death_line, englishify,
                     glossary_of, ledger_line, moment_lines, previous_life_line,
                     teaching_lines, work_lines, world_between, ROLE_EN, sex_word)
from .render import ordinal

PROEM_VOICE = ("You are the bard of an ancient world, speaking the proem — the invocation "
               "— that opens a long epic about one soul's road across many lives. Address "
               "the listener directly; name what the song will hold and how it ends. Voice: "
               "grave, concrete, unhurried, like a modern prose translation of an old poem. "
               "Do not tell the whole story; promise it.")

CANTO_VOICE = ("You are the bard of an ancient world, composing one canto of a long epic that "
               "follows a single soul across many lives. Voice: grave, concrete, unhurried — a "
               "modern prose translation of an old poem. Third person, past tense. Call the "
               "soul 'the soul' and the body by its recorded name. The listener already knows "
               "the earlier cantos; carry them, do not repeat them.")


def choose_soul(annals: Annals) -> int:
    def road(serial: int) -> float:
        lives = annals.lives_of_soul(serial)
        real = [l for l in lives if l.moments]
        falls = sum(1 for l in lives if l.dv < -0.02)
        betrayed = sum(l.ledger[1] for l in lives)
        reunions = sum(1 for l in lives for b in l.bonds if b.reunion)
        return len(real) * 3 + 2 * falls + 0.1 * betrayed + 2 * reunions
    freed = {l.soul_serial for l in annals.lives.values() if l.liberated}
    pool = freed or set(annals.soul_lives)
    return max(pool, key=road)


def build(annals: Annals, universe) -> Book:
    serial = choose_soul(annals)
    lives = annals.lives_of_soul(serial)
    cy = canon_years(annals)
    real = [l for l in lives if l.moments or (l.died_age or 0) >= 16]
    first, last = lives[0], lives[-1]
    freed = last.liberated
    title_name = (max(real, key=lambda l: len(l.moments)) if real else last).name
    ages: List[str] = []
    for l in lives:
        a = annals.age_phrase(l.born_year)
        if a not in ages:
            ages.append(a)

    chapters: List[Chapter] = []

    # -- proem ---------------------------------------------------------------
    proem = [
        f"This epic follows one soul through {len(lives)} lives, from year {first.born_year} "
        f"to year {last.died_year if last.died_year is not None else universe.year}.",
        "The ages it passed through: " + "; ".join(ages) + ".",
        "The houses of the world: " + ", ".join(annals.houses) + ".",
        "The soul's bodies, in order: " + "; ".join(
            f"{l.name} of {l.house} ({'a child only' if (l.died_age or 0) < 16 and not l.moments else ROLE_EN.get(l.role, 'a wanderer')}, "
            f"years {l.born_year}–{l.died_year if l.died_year is not None else 'the close of the record'})"
            for l in lives) + ".",
        (f"In the end the soul was freed: in year {last.died_year}, with the death of "
         f"{last.name}, it left the wheel forever." if freed else
         "In the end the soul was not freed; when the record closes it is still on the wheel."),
        f"Across that span the world saw {sum(1 for e in annals.events if e.kind == 'pralaya')} "
        f"dissolutions of the manifest world and {sum(1 for e in annals.events if e.kind == 'avatar')} "
        f"descents of liberated ones.",
    ]
    chapters.append(Chapter(heading="Proem", brief=proem, voice=PROEM_VOICE, words=(160, 240),
                            must_say=[first.name, last.name]))

    # -- cantos ----------------------------------------------------------------
    n = 0
    pending_children: List[str] = []
    prev_death_year = None
    for life in lives:
        childish = (life.died_age or 0) < 16 and not life.moments
        if childish and life.died_year is not None:
            pending_children.append(
                f"Between those lives the soul wore the body of {life.name} of {life.house} "
                f"for {life.died_age} years only, born in year {life.born_year}, and died a "
                f"child, having faced no test.")
            continue
        n += 1
        b: List[str] = []
        b.append(f"This is the {ordinal(life.life_n)} life of the soul.")
        if prev_death_year is not None:
            b += world_between(annals, prev_death_year, life.born_year)
        b += pending_children
        pending_children = []
        pl = previous_life_line(life, annals)
        if pl:
            b.append(pl)
        b.append(birth_line(life, annals))
        if not life.founding:
            b.append(f"Why this birth: {englishify(life.born_reason)}.")
        b.append(f"The soul came into this body ruled by {ENEMY_EN.get(life.start_enemy, 'craving')}.")
        b += bond_lines(life, annals)
        b += moment_lines(life, life.dramatic_moments(6))
        b += work_lines(life, annals, cy)
        b += teaching_lines(life, annals)
        b.append(ledger_line(life))
        b.append(death_line(life, annals))
        must = [life.name, life.house] + [bd.partner for bd in life.bonds][:2] + life.children[:2]
        heading = f"Canto {n}: {life.name} of {life.house}"
        if life.liberated:
            heading += " — the Release"
        chapters.append(Chapter(heading=heading, brief=b, voice=CANTO_VOICE,
                                words=(330, 480), must_say=must))
        prev_death_year = life.died_year

    if pending_children:
        chapters[-1].brief = chapters[-1].brief[:-1] + pending_children + [chapters[-1].brief[-1]]

    subtitle = (f"The road of one soul across {len(lives)} lives, from year {first.born_year} "
                f"to year {last.died_year if last.died_year is not None else universe.year}; "
                f"{'freed at the last' if freed else 'still bound when the record closes'}. "
                f"World of seed {universe.cfg.seed}.")
    return Book(title=f"The {title_name}-ayana",
                subtitle=subtitle,
                epigraph="Out of thousands, scarcely one strives; and of those who strive, "
                         "scarcely one knows the road. This is the road.",
                chapters=chapters, glossary=glossary_of(annals, lives), slug="epic")
