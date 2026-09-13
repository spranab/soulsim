"""Tales — the three short forms the Bard began with, now told from the Annals.

  the long road    — the redemption tale: a liberated soul's hardest climb
  the fall         — the tragedy: a soul still bound whose lives decline
  the forgotten doer — the injustice: a living song that credits the wrong name
"""
from __future__ import annotations

from typing import List, Optional

from soulsim.annals import Annals, ENEMY_EN, SCALE_EN
from .book import Book, Chapter
from .common import glossary_of, ROLE_EN, englishify

VOICE = ("You are the court poet of an ancient world, telling a short tale from the "
         "chronicle in a timeless, spare, mythic voice. Refer to the soul as 'the soul' and "
         "to bodies by their recorded names. End with a single italicized line, like a moral "
         "a village might repeat.")


def _life_line(l, annals: Annals) -> str:
    m = l.dramatic_moments(1)
    moment = f"; at {m[0].age}, {m[0].phrase().split(', ', 1)[1]}" if m else ""
    who = "a woman" if l.sex == "female" else "a man"
    return (f"Life {l.life_n}: {l.name} of {l.house}, {who}, {ROLE_EN.get(l.role, 'a wanderer')}, "
            f"years {l.born_year}–{l.died_year}, {l.virtue_phrase()}, ruled by "
            f"{ENEMY_EN.get(l.end_enemy, 'craving')}{moment}.")


def long_road(annals: Annals) -> Optional[Chapter]:
    freed = {l.soul_serial for l in annals.lives.values() if l.liberated}
    if not freed:
        return None
    serial = max(freed, key=lambda s: sum(1 for l in annals.lives_of_soul(s) if l.moments)
                 + 2 * sum(1 for l in annals.lives_of_soul(s) if l.dv < -0.02))
    lives = [l for l in annals.lives_of_soul(serial) if l.moments]
    b = [f"The soul took {len(annals.lives_of_soul(serial))} lives to be freed."]
    b += [_life_line(l, annals) for l in lives[-7:]]
    b.append(f"With the death of {lives[-1].name} in year {lives[-1].died_year}, the soul left the wheel forever.")
    return Chapter(heading="The Long Road", brief=b, voice=VOICE, words=(220, 330),
                   must_say=[lives[-1].name])


def the_fall(annals: Annals) -> Optional[Chapter]:
    best, worst = None, 1.0
    for serial, lives in annals.soul_lives.items():
        real = [l for l in lives if l.moments and l.died_year is not None]
        if len(real) < 3 or any(l.liberated for l in lives):
            continue
        dv = sum(l.dv for l in real[-3:])
        if dv < worst:
            best, worst = real, dv
    if not best:
        return None
    b = ["The soul is still on the wheel; its last lives went downward."]
    b += [_life_line(l, annals) for l in best[-4:]]
    b.append(f"When the record closes the soul waits in the unmanifest, ruled by "
             f"{ENEMY_EN.get(best[-1].end_enemy, 'craving')}.")
    return Chapter(heading="The Fall", brief=b, voice=VOICE, words=(220, 330),
                   must_say=[best[-1].name])


def forgotten_doer(annals: Annals, universe) -> Optional[Chapter]:
    for m in sorted(universe.religion.myths, key=lambda m: -m.strength):
        if m.story is None or m.story.source_tid is None:
            continue
        src = universe.culture.trace_archive.get(m.story.source_tid)
        if src and m.story.actor != src[0] and m.strength > 8:
            true_l, cred_l = annals.by_name.get(src[0]), annals.by_name.get(m.story.actor)
            b = [f"A song called '{m.name}' is sung by {int(m.strength)} people.",
                 f"The song says {m.story.actor}"
                 + (f" of {cred_l.house}" if cred_l else "")
                 + f" {'did well' if m.story.align > 0 else 'did ill'} {SCALE_EN[m.story.scale]}.",
                 f"The record says the deed was done by {src[0]}"
                 + (f" of {true_l.house}, {ROLE_EN.get(true_l.role, 'a wanderer')}, years {true_l.born_year}–{true_l.died_year}" if true_l else "")
                 + f", and that it was {'a kindness' if src[1] > 0 else 'a harm'} {SCALE_EN[src[2]]}.",
                 f"The song changed {len(m.story.transformations)} times in the retelling; among its changes: "
                 + ", ".join(sorted(set(m.story.transformations))).replace("_", " ") + "."]
            if cred_l:
                b.append(f"{m.story.actor} lived years {cred_l.born_year}–{cred_l.died_year}, "
                         f"{ROLE_EN.get(cred_l.role, 'a wanderer')} of {cred_l.house}.")
            return Chapter(heading="The Forgotten Doer", brief=b, voice=VOICE, words=(220, 330),
                           must_say=[src[0], m.story.actor])
    return None


def build(annals: Annals, universe) -> Book:
    chapters = [c for c in (long_road(annals), the_fall(annals), forgotten_doer(annals, universe)) if c]
    return Book(title=f"Three Tales from the World of Seed {universe.cfg.seed}",
                subtitle="The long road, the fall, and the forgotten doer.",
                epigraph="", chapters=chapters,
                glossary=glossary_of(annals, annals.lives.values()), slug="tales")
