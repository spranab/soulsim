"""The History — the chronicle of the ages, written by the witness.

A book per cosmic cycle, a chapter per age. The historian stands outside the
world (it is the sākṣī, the physics itself), so it may say what no inhabitant
could: how many were freed, how true the age's teachings were, which deeds
were seen and which names the songs later got wrong. Numbers go in tables;
prose gets the names.
"""
from __future__ import annotations

from collections import Counter
from typing import Dict, List

from soulsim.annals import Annals, Life, COND_EN, SCALE_EN
from .book import Book, Chapter
from .common import (claims_of, glossary_of, lineage_phrase, ROLE_EN, RASA_EN,
                     YUGA_CHARACTER, verse_line)
from .render import ordinal

VOICE = ("You are the chronicler of an ancient world, writing one chapter of its history: "
         "a dry, exact, humane annalist setting down an age, in the manner of an old court "
         "historian. Past tense. You may generalize from the record's counts ('many', 'few', "
         "'more than before'), but every name, deed, teaching, work and number must be the "
         "record's. Give the age a shape: how it opened, what it was known for, how it closed.")


def build(annals: Annals, universe) -> Book:
    ages = annals.ages(universe.year)
    recs = universe.metrics.records
    rec_by_year = {r.year: r for r in recs}
    chapters: List[Chapter] = []
    all_lives: List[Life] = []

    # prologue: the founding
    founders = sum(1 for l in annals.lives.values() if l.founding and l.born_year == 0)
    b = [f"In year 0 the world was made manifest. Its houses: " + ", ".join(annals.houses) + ".",
         f"{founders} souls took bodies at the founding, already grown.",
         "The ages run in a fixed proportion: 200 years of Satya, 150 of Treta, 100 of "
         "Dvapara, 50 of Kali, and then the manifest world dissolves and a new Satya dawns.",
         "Satya is " + YUGA_CHARACTER["Satya"] + "; Kali is " + YUGA_CHARACTER["Kali"] + ".",
         f"The record closes in year {universe.year}."]
    chapters.append(Chapter(heading="Prologue: The Founding", brief=b, voice=VOICE,
                            words=(180, 260), must_say=annals.houses[:2]))

    last_cycle = None
    for a in ages:
        y0, y1 = a["start"], a["end"]
        part = None
        if a["cycle"] != last_cycle:
            part = f"Book {a['cycle'] + 1}: The {ordinal(a['cycle'] + 1).capitalize()} Cycle"
            last_cycle = a["cycle"]
        span = [r for r in recs if y0 <= r.year < y1]
        if not span:
            continue
        lives = annals.lives_in(y0, y1)
        died = [l for l in lives if l.died_year is not None and y0 <= l.died_year < y1]
        all_lives += died
        b = []
        b.append(f"The {a['yuga']} age of the {ordinal(a['cycle'] + 1)} cycle ran from year "
                 f"{y0} to year {y1 - 1}, {y1 - y0} years: {YUGA_CHARACTER[a['yuga']]}.")
        b.append(f"The living numbered {span[0].population} when it opened and "
                 f"{span[-1].population} when it closed; {sum(r.births for r in span)} were born "
                 f"and {sum(r.deaths for r in span)} died.")
        freed = span[-1].liberated_total - (rec_by_year[y0 - 1].liberated_total if y0 > 0 else 0)
        b.append(f"{freed} souls were freed from the wheel in this age." if freed else
                 "No soul was freed from the wheel in this age.")
        if not any(r.liberated_total for r in recs[:y0]) and freed:
            first = next(e for e in annals.events if e.kind == "moksha")
            b.append(f"The first liberation the world ever saw: year {first.year}, {first.text}.")
        # avatars
        for e in annals.events_between(y0, y1, kinds={"avatar"}):
            b.append(f"Year {e.year}: {e.text}.")
        for e in annals.events_between(y0, y1, kinds={"withdrawal"}):
            b.append(f"Year {e.year}: {e.text}.")
        # great deeds
        deeds = [e for e in annals.events_between(y0, y1, kinds={"deed"})]
        deeds.sort(key=lambda e: (-e.data["scale"], -e.data["n_actors"], e.year))
        deeds = sorted(deeds[:5], key=lambda e: e.year)
        if deeds:
            b.append("The deeds most talked of:")
            for e in deeds:
                crowd = f" ({e.data['n_actors']} acted together)" if e.data["n_actors"] > 1 else ""
                b.append(f"Year {e.year}: {e.text}{crowd}.")
        # teachings
        born_myths = [m for m in universe.religion.myths
                      if y0 <= m.born_year < y1 and m.seer and m.props]
        born_myths.sort(key=lambda m: -m.strength)
        if born_myths:
            b.append("Teachings first spoken in this age, and still alive when the record closes:")
            for m in born_myths[:4]:
                b.append(f"'{m.name}', spoken in year {m.born_year} by {m.seer} of {m.seer_house}, "
                         f"{ROLE_EN.get(m.seer_role, 'a wanderer')}, holding that "
                         + "; ".join(claims_of(m)) + "." + lineage_phrase(m))
        for kind, label in (("institution", "became institutions"), ("corruption", "were corrupted"),
                            ("reform", "were reformed"), ("extinction", "were forgotten")):
            evs = annals.events_between(y0, y1, kinds={kind})
            if evs:
                names = []
                for e in evs[:4]:
                    q = e.text.split("'")
                    names.append(f"'{q[1]}' (year {e.year})" if len(q) > 2 else f"year {e.year}")
                b.append(f"Teachings that {label} in this age: " + ", ".join(names) + ".")
        # arts
        canon = [e for e in annals.events_between(y0, y1, kinds={"canon"})]
        if canon:
            rasas = Counter(RASA_EN.get(e.data["rasa"], e.data["rasa"]) for e in canon)
            b.append(f"{len(canon)} works entered the canon in this age; by feeling they were "
                     + ", ".join(f"{n} of {r}" for r, n in rasas.most_common(3)) + ".")
            for e in canon[:2]:
                w = annals.works.get(e.data["aid"])
                if w:
                    b.append(f"Among them the {w.form} of {w.creator}, composed in year {w.year} "
                             f"and taken into the canon in year {e.year}: \"{verse_line(w.verse)}\".")
        # houses and roles
        roles = Counter(l.role for l in died if l.role and not l.is_avatar and (l.died_age or 0) >= 16)
        if roles:
            top = roles.most_common(2)
            b.append("Of the grown who died in this age the world called most of them "
                     + " and ".join(f"{ROLE_EN.get(r, r).split(' ', 1)[1]}s ({n})" for r, n in top) + ".")
        by_house = Counter(l.house for l in died if l.role == "ruler")
        if by_house:
            h, n = by_house.most_common(1)[0]
            b.append(f"The house of {h} gave the age the most rulers ({n}).")
        # notable dead
        notable = sorted(died, key=lambda l: -(len(l.deeds) + 2 * len(l.works)
                                               + 2 * len(l.revelations) + 2 * l.liberated))[:3]
        for l in notable:
            if not (l.deeds or l.works or l.revelations or l.liberated):
                continue
            bits = []
            if l.deeds:
                d = max(l.deeds, key=lambda d: d.scale)
                bits.append(f"seen {d.phrase()}")
            if l.works:
                bits.append(f"composed {len(l.works)} work{'s' if len(l.works) > 1 else ''}")
            if l.revelations:
                bits.append(f"spoke the teaching '{l.revelations[0]}'")
            if l.liberated:
                bits.append(f"freed from the wheel at death after {l.life_n} lives")
            b.append(f"{l.name} of {l.house}, {ROLE_EN.get(l.role, 'a wanderer')}, "
                     f"born in year {l.born_year} and dead in year {l.died_year}: " + "; ".join(bits) + ".")
        # closing
        nxt = next((x for x in ages if x["start"] == y1), None)
        if nxt and nxt["cycle"] != a["cycle"]:
            b.append(f"The age ended in pralaya: in year {y1} the manifest world dissolved, "
                     f"every living body was unmade, and a new Satya dawned.")
        elif nxt:
            b.append(f"The age gave way to {nxt['yuga']} in year {y1}.")
        else:
            b.append(f"The record closes in this age, in year {universe.year}.")

        coop = sum(r.cooperation_rate for r in span) / len(span)
        acc = sum(r.doctrine_accuracy for r in span) / len(span)
        fid = sum(r.historical_fidelity for r in span) / len(span)
        table = ("| measure | value |\n|---|---|\n"
                 f"| aligned choice (mean) | {coop:.3f} |\n"
                 f"| truth of living doctrine (mean) | {acc:.3f} |\n"
                 f"| fidelity of deed-songs to the record (mean) | {fid:.3f} |\n"
                 f"| institutions at close | {span[-1].institutions} |\n"
                 f"| works in the canon at close | {span[-1].classics} |")
        must = [m.seer for m in born_myths[:2]] + [l.name for l in notable[:2]]
        chapters.append(Chapter(heading=f"The {a['yuga']} Age (years {y0}–{y1 - 1})", brief=b,
                                voice=VOICE, words=(380, 560), must_say=must, part=part,
                                table=table))

    n_ages = len(ages)
    return Book(title=f"The Chronicle of the World of Seed {universe.cfg.seed}",
                subtitle=(f"{universe.year} years, {n_ages} ages, {len(annals.lives)} lives "
                          f"recorded, {len(universe.liberated)} souls freed. Set down by the "
                          f"witness, who sees what no inhabitant can."),
                epigraph="What the songs remember and what the record says are two "
                         "histories; this is the second.",
                chapters=chapters, glossary=glossary_of(annals, all_lives), slug="history",
                inside=False)
