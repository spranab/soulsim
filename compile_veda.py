#!/usr/bin/env python3
"""Compile the Veda of a cosmos.

A Veda is not a story. It is a civilization's accumulated canon — centuries of
revelation, hymn, and liturgy, collected and arranged. Our world already
produces every ingredient: revelations graded against the ground truth,
doctrines that institutionalized, hymns that survived the endurance test of
the canon. This script only does what Vyasa is said to have done: COLLECT and
ARRANGE. Nothing here is generated; every line was produced inside the world.

    python3 compile_veda.py [seed] [years]   ->  veda_of_seed_N.md
"""
from __future__ import annotations

import sys
from collections import Counter

from soulsim.config import SimConfig, FixedRules
from soulsim.religion import GROUND_TRUTHS
from soulsim.world import Universe

PROP_EN = {
    "rebirth": "The soul returns in new bodies",
    "ages_cycle": "The world moves through recurring ages",
    "dawn_returns": "After dissolution, a golden age dawns again",
    "liberation_exists": "A soul can leave the wheel forever",
    "effort_frees": "Restraint, exercised, loosens the wheel's grip",
    "habit_binds": "Repeated acts groove the soul",
    "helpers_descend": "When dharma falls, a freed one returns",
    "vice_cascades": "Craving breeds anger; anger breeds delusion",
    "world_ends_forever": "The world will one day end, and never return",
    "fate_is_random": "Fate is random; no act matters",
    "only_one_life": "You live once only",
    "power_frees": "Domination liberates",
}
RASA_BOOK = {"shanta": "Peace", "karuna": "Sorrow", "vira": "Valor",
             "raudra": "Fury", "adbhuta": "Wonder", "shringara": "Love",
             "hasya": "Laughter", "bhayanaka": "Dread", "bibhatsa": "Refusal"}


def main() -> None:
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 11
    years = int(sys.argv[2]) if len(sys.argv) > 2 else 500
    print(f"running cosmos (seed {seed}, {years}y)...")
    u = Universe(SimConfig(seed=seed, years=years, initial_adults=200,
                           rules=FixedRules(soul_count=800)))
    for _ in range(years):
        u.step()

    out = [f"# The Veda of the World of Seed {seed}",
           "",
           f"*Compiled after {years} years, {u.year // 500 + 1} cosmic cycle(s), "
           f"{len(u.liberated)} liberations. Every verse below was composed, "
           f"believed, and preserved inside the world itself.*", ""]

    # -- Book I: cosmogony — what the chronicle remembers of beginnings/endings
    out += ["## Book I — Of Beginnings and Endings", ""]
    for y, kind, text in u.chronicle:
        if kind in ("pralaya", "avatar", "moksha"):
            out.append(f"- *Year {y}:* {text}")
    out.append("")

    # -- Book II: the teachings — living doctrine, arranged by how true it is
    out += ["## Book II — The Teachings", "",
            "*What the traditions hold, from clearest to most clouded. "
            "(The world cannot see these gradings; only we can.)*", ""]
    holders = sorted([m for m in u.religion.myths if m.props],
                     key=lambda m: (-m.accuracy(), -m.strength))
    for m in holders[:10]:
        inst = " — an institution" if m.institution else ""
        out.append(f"**{m.name}**{inst} ({int(m.strength)} believers, "
                   f"{m.accuracy():.0%} true):")
        for p, pol in m.props.items():
            claim = PROP_EN[p] if pol else f"It is denied that: {PROP_EN[p].lower()}"
            mark = "◦" if GROUND_TRUTHS[p] == pol else "✗"
            out.append(f"  - {mark} {claim}")
        out.append("")

    # -- Book III..: the hymns — the canon, arranged by rasa into books
    by_rasa = {}
    for w in u.arts.library:
        by_rasa.setdefault(w.rasa, []).append(w)
    book_n = 3
    ROMAN = ["III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"]
    for rasa, works in sorted(by_rasa.items(), key=lambda kv: -len(kv[1])):
        out += [f"## Book {ROMAN[book_n-3]} — The Hymns of {RASA_BOOK.get(rasa, rasa)}",
                f"*{len(works)} canonized; the earliest from year "
                f"{min(w.year for w in works)}.*", ""]
        for w in works[:4]:
            out.append(f"**{w.form} of {w.creator}** (yr {w.year}, {w.age_name}; "
                       f"born of {w.born_of}):")
            out.append("")
            for line in w.verse.split("\n"):
                out.append(f"> {line}")
            out.append("")
        book_n += 1
        if book_n - 3 >= len(ROMAN):
            break

    # -- final book: the songs of deeds (story-myths strong enough to endure)
    stories = sorted([m for m in u.religion.myths if m.story is not None],
                     key=lambda m: -m.strength)[:6]
    if stories:
        out += ["## The Last Book — Songs of Deeds", ""]
        for m in stories:
            sc = m.story
            src = u.culture.trace_archive.get(sc.source_tid) if sc.source_tid else None
            truth = ("" if src is None else
                     f" *(the record says it was {src[0]})*" if src[0] != sc.actor else
                     " *(the record agrees)*")
            deed = "did well" if sc.align > 0 else "did ill"
            scale = ["for a few", "for a household", "for a village",
                     "for a kingdom", "for the world"][sc.scale]
            out.append(f"- **{m.name}** ({int(m.strength)} believers): "
                       f"{sc.actor} {deed} {scale}.{truth}")
        out.append("")

    rasas = Counter(w.rasa for w in u.arts.library)
    out += ["---", f"*Canon: {len(u.arts.library)} works. The world's heart, "
            f"by weight: {', '.join(f'{RASA_BOOK.get(r, r)} ({n})' for r, n in rasas.most_common(3))}.*"]

    path = f"veda_of_seed_{seed}.md"
    open(path, "w").write("\n".join(out))
    print(f"wrote {path}: {len(out)} lines, "
          f"{len(u.arts.library)} hymns, {len(holders)} teaching traditions")


if __name__ == "__main__":
    main()
