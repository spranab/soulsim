"""The Scripture — the canon of a cosmos, arranged as a Veda.

compile_veda.py collected; this arranges and *renders*. Four books:

  I.   Origins    — a hymn of the first dawn, the dissolutions, the descents
  II.  The Seers  — each living teaching as a sūtra with commentary, in the
                    seer's name; every clause the tradition actually holds,
                    true or false, is kept — the world's scripture is honestly
                    wrong where the world was wrong
  III. Hymns      — the canonized works by rasa, each grown into a full hymn
                    from its own true lines
  IV.  Deeds      — the songs of deeds as ballads, with the witness's gloss on
                    who really did the thing

The witness's gloss (which clauses are true, which name is right) stays out
of the rendered text and in the appendix, where the world cannot hear it.
"""
from __future__ import annotations

from collections import Counter
from typing import Dict, List

from soulsim.annals import Annals, SCALE_EN
from soulsim.religion import GROUND_TRUTHS
from .book import Book, Chapter
from .common import (claims_of, glossary_of, lineage_phrase, born_of_phrase, ROLE_EN, RASA_EN,
                     PROP_EN, verse_line)
from .render import ordinal

HYMN_VOICE = ("You are a liturgist of an ancient world rendering a hymn for recitation. "
              "Incantatory, plain, physical; first person or first person plural; a refrain "
              "may return once. Keep every given line of the verse, in order, exactly once, "
              "and grow new lines before, between and after them so the whole reads as one "
              "hymn. Do not name the form, the maker or the year inside the hymn; do not "
              "explain the hymn.")
SUTRA_VOICE = ("You are the compiler of a scripture, setting down one teaching as a sūtra "
               "followed by a short commentary in the voice of the tradition that holds it. "
               "Open with the seer's name and the age. State each clause the teaching holds "
               "as its own terse aphorism, keeping its exact sense (even if it seems wrong — "
               "the tradition holds it), then comment on each as a believer would. Do not "
               "count the believers in the text.")
BALLAD_VOICE = ("You are a village singer rendering a song of a deed, as the song is sung. "
                "Sing what the song claims as if it were so; do not say it was retold or "
                "changed. Plain, rhythmic prose in short sentences; a refrain may recur; "
                "name the doer more than once.")
ORIGIN_VOICE = ("You are the reciter of the oldest hymn of a world: the account of its "
                "beginning and its turnings. Cosmogonic, solemn, in short breath-length "
                "lines. Say it as wonder, not as report: do not recite every date — a hymn "
                "holds a few numbers at most, and names are what it keeps. The houses, the "
                "ages in their order, the ones who descended and who they had been, the "
                "first to be freed.")


def build(annals: Annals, universe) -> Book:
    seed = universe.cfg.seed
    chapters: List[Chapter] = []
    R = universe.religion

    # -- Book I: origins ----------------------------------------------------------
    b = [f"In year 0 the world was made manifest, with these houses: " + ", ".join(annals.houses) + "."]
    for a in annals.ages(universe.year):
        b.append(f"The {a['yuga']} age of the {ordinal(a['cycle'] + 1)} cycle: years "
                 f"{a['start']} to {a['end'] - 1}.")
    for e in annals.events:
        if e.kind in ("pralaya", "dawn", "avatar", "withdrawal") and e.year > 0:
            b.append(f"Year {e.year}: {e.text}.")
    first = next((e for e in annals.events if e.kind == "moksha"), None)
    if first:
        b.append(f"The first soul freed from the wheel: year {first.year}, {first.text}.")
    b.append(f"By year {universe.year}, {len(universe.liberated)} souls had left the wheel.")
    chapters.append(Chapter(heading="Hymn of the First Dawn", brief=b, voice=ORIGIN_VOICE,
                            words=(18, 34), form="verse", part="Book I — Origins",
                            must_say=annals.houses[:1]))

    # -- Book II: the seers -------------------------------------------------------
    holders = sorted([m for m in R.myths if m.props and m.seer],
                     key=lambda m: -m.strength)[:8]
    gloss: List[str] = []
    for i, m in enumerate(holders):
        seer_life = annals.by_name.get(m.seer)
        seer_age = (f", then {m.born_year - seer_life.born_year + seer_life.born_age} years old"
                    if seer_life else "")
        seer_who = ("a woman" if seer_life and seer_life.sex == "female" else "a man") if seer_life else ""
        b = [f"The teaching is called '{m.name}'.",
             f"It was first spoken in year {m.born_year}, in the {m.born_yuga} age, by "
             f"{m.seer} of the house of {m.seer_house}, {seer_who}{seer_age}, whom the world "
             f"called {ROLE_EN.get(m.seer_role, 'a wanderer')}.",
             f"When the record closes it has {int(m.strength)} believers"
             + (" and is an institution." if m.institution else "."),
             "The clauses it holds:"]
        b += [f"{c}." for c in claims_of(m)]
        lp = lineage_phrase(m)
        if lp:
            b.append(lp.strip())
        truths = [f"{'true' if GROUND_TRUTHS[p] == pol else 'FALSE'}: {PROP_EN[p] if pol else 'denies that ' + PROP_EN[p]}"
                  for p, pol in m.props.items()]
        gloss.append(f"- **{m.name}** ({m.accuracy():.0%} true): " + "; ".join(truths))
        chapters.append(Chapter(heading=f"Sūtra {i + 1}: {m.name}", brief=b, voice=SUTRA_VOICE,
                                words=(150, 240), must_say=[m.seer] + [c.split(",")[0][:24] for c in claims_of(m)][:3],
                                part="Book II — The Seers" if i == 0 else None))

    # -- Book III: hymns by rasa ---------------------------------------------------
    by_rasa: Dict[str, list] = {}
    for w in universe.arts.library:
        by_rasa.setdefault(w.rasa, []).append(w)
    book_n = 0
    for rasa, works in sorted(by_rasa.items(), key=lambda kv: -len(kv[1]))[:5]:
        seen, picked = set(), []
        for w in sorted(works, key=lambda w: w.year):
            key = w.verse.split("\n")[1] if "\n" in w.verse else w.verse
            if key in seen:
                continue
            seen.add(key)
            picked.append(w)
            if len(picked) == 3:
                break
        for j, w in enumerate(picked):
            maker = annals.by_name.get(w.creator)
            b = [f"A {w.form} of {RASA_EN.get(rasa, rasa)}, composed by {w.creator}"
                 + (f" of the house of {maker.house}" if maker else "")
                 + f" in year {w.year}, in the {w.age_name} age.",
                 f"It was born of this: {born_of_phrase(w.born_of)}.",
                 "Its lines, which must all be kept, in order:"]
            b += [f"\"{l.strip()}\"" for l in w.verse.split("\n") if l.strip()]
            chapters.append(Chapter(
                heading=f"{RASA_EN.get(rasa, rasa).capitalize()} — the {w.form} of {w.creator}",
                brief=b, voice=HYMN_VOICE, words=(10, 18), form="verse",
                must_say=[" ".join(l.strip().split(" ")[:3]).strip(",;—:") for l in w.verse.split("\n") if l.strip()][:3],
                part=(f"Book III — Hymns ({len(universe.arts.library)} in the canon; "
                      f"by feeling: " + ", ".join(f"{RASA_EN.get(r, r)} {n}" for r, n in
                      Counter(x.rasa for x in universe.arts.library).most_common(4)) + ")")
                if book_n == 0 and j == 0 else None))
            book_n += 1

    # -- Book IV: deeds ---------------------------------------------------------------
    stories = sorted([m for m in R.myths if m.story is not None], key=lambda m: -m.strength)[:6]
    deed_gloss: List[str] = []
    for i, m in enumerate(stories):
        sc = m.story
        deed = "did a good thing" if sc.align > 0 else "did a wicked thing"
        b = [f"The song is called '{m.name}'; when the record closes {int(m.strength)} people sing it.",
             f"The song says: {sc.actor}, {dict(power='given power', scarcity='facing scarcity', loss='struck by loss', success='crowned by success', uncertainty='lost in uncertainty')[sc.condition]}, {deed} {SCALE_EN[sc.scale]}"
             + (f", and {sc.n_actors} stood with {sc.actor}." if sc.n_actors > 1 else ".")]
        if m.props:
            b.append("The song also teaches: " + "; ".join(claims_of(m)) + ".")
        src = universe.culture.trace_archive.get(sc.source_tid) if sc.source_tid else None
        if src is None:
            deed_gloss.append(f"- **{m.name}**: the record knows no such deed — a fabrication.")
        elif src[0] != sc.actor:
            deed_gloss.append(f"- **{m.name}**: the deed was {src[0]}'s; the song gives it to {sc.actor}"
                              + (" and has also inverted its moral" if (src[1] > 0) != (sc.align > 0) else "") + ".")
        else:
            deed_gloss.append(f"- **{m.name}**: the record agrees on the doer"
                              + ("; the moral was inverted in the retelling" if (src[1] > 0) != (sc.align > 0) else "") + ".")
        chapters.append(Chapter(heading=f"{m.name}", brief=b, voice=BALLAD_VOICE, words=(90, 150),
                                must_say=[sc.actor], part="Book IV — Songs of Deeds" if i == 0 else None))

    rasas = Counter(w.rasa for w in universe.arts.library)
    colophon = ("**The Witness's Gloss** — what the world cannot see.\n\n"
                "On the teachings:\n" + "\n".join(gloss) +
                "\n\nOn the songs of deeds:\n" + "\n".join(deed_gloss) +
                f"\n\nCanon: {len(universe.arts.library)} works; the world's heart by weight: "
                + ", ".join(f"{RASA_EN.get(r, r)} ({n})" for r, n in rasas.most_common(3)) + ".")
    return Book(title=f"The Veda of the World of Seed {seed}",
                subtitle=(f"Compiled after {universe.year} years and {len(universe.liberated)} "
                          f"liberations. Every clause below was spoken, believed and preserved "
                          f"inside the world; the rendering is a translation, not an authorship."),
                epigraph="What the seers saw, they saw through their own clearness or "
                         "cloud; what the singers sang, they sang as it was told to them.",
                chapters=chapters, glossary=glossary_of(annals, []) | {m.seer for m in holders}
                | {w.creator for w in universe.arts.library} | {s.story.actor for s in stories},
                slug="veda", colophon=colophon)
