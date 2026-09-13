#!/usr/bin/env python3
"""The Bard — the library of a cosmos.

The problem with generative fiction is slop: prose unmoored from consequence.
The problem with procedural fiction is wallpaper: the same two templates in
rotation. The Bard resolves both with a division of labor the rest of this
project already trusts:

    THE WORLD SUPPLIES THE PLOT   (the Annals: every life, bond, test, deed,
                                   work and teaching, written down as it happens)
    THE MODEL SUPPLIES THE PROSE  (a local LLM as TRANSLATOR, never author)
    A VERIFIER KEEPS IT HONEST    (groundedness lint: no invented facts; the
                                   record appended to every book)

Five genres, each a query over the Annals rendered chapter by chapter:

    epic       one soul across many lives — the road to release (or not)
    novel      one life, in depth — house, youth, bond, tests, turning, death
    history    the chronicle of the ages, by cycle and yuga, with the numbers
    scripture  the Veda: origins, the seers' sūtras, hymns by rasa, deed-songs
    tales      the three short forms: the long road, the fall, the forgotten doer

Wall discipline: the Bard is narration-side — it READS a universe and writes
literature; nothing it produces is ever read by physics, and the Annals roll
their own dice so a seed's measured outcome is unchanged by their existence.

    python3 bard.py                                # seed 11, 500y, all genres
    python3 bard.py --seed 108 --years 800 --genres epic,novel
    python3 bard.py --model none                   # no LLM: chronicler's plain prose
    python3 bard.py --model qwen2.5:7b --limit 3   # quick look: 3 chapters per genre
    python3 bard.py --repair                       # re-render only scrubbed/plain chapters
"""
from __future__ import annotations

import argparse
import os
import time

from soulsim.config import SimConfig, FixedRules
from soulsim.world import Universe
import bardic
from bardic import Renderer, compile_book
from bardic.book import load_prior


def run_cosmos(seed: int, years: int, souls: int, adults: int) -> Universe:
    print(f"running a cosmos (seed {seed}, {years}y, {souls} souls)...", flush=True)
    t = time.time()
    u = Universe(SimConfig(seed=seed, years=years, initial_adults=adults,
                           rules=FixedRules(soul_count=souls)))
    for _ in range(years):
        u.step()
    st = u.annals.stats()
    print(f"  {time.time() - t:.0f}s: {st['lives']} lives, {st['events']} events, "
          f"{len(u.liberated)} liberations, {len(u.arts.library)} works in the canon, "
          f"{len(u.religion.myths)} living myths", flush=True)
    return u


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--years", type=int, default=500)
    ap.add_argument("--souls", type=int, default=800)
    ap.add_argument("--adults", type=int, default=200)
    ap.add_argument("--genres", default="epic,novel,history,scripture,tales")
    ap.add_argument("--model", default="auto",
                    help="ollama model as translator: 'auto' picks the best installed "
                         "(qwen3.6:35b > qwen3.5:9b > qwen2.5:7b); 'none' for plain prose")
    ap.add_argument("--out", default="library")
    ap.add_argument("--limit", type=int, default=0, help="cap chapters per genre (quick look)")
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--repair", action="store_true",
                    help="keep chapters an earlier run rendered cleanly; re-render only "
                         "the scrubbed or plain ones")
    args = ap.parse_args()

    u = run_cosmos(args.seed, args.years, args.souls, args.adults)
    renderer = Renderer(model=args.model, retries=args.retries)
    out_dir = os.path.join(args.out, f"seed_{args.seed}")
    os.makedirs(out_dir, exist_ok=True)
    print(f"renderer: {renderer.model if renderer.available() else 'plain prose (no model)'}")

    for g in [x.strip() for x in args.genres.split(",") if x.strip()]:
        if g not in bardic.GENRES:
            print(f"unknown genre {g!r}; choose from {', '.join(bardic.GENRES)}")
            continue
        book = bardic.GENRES[g](u.annals, u)
        if args.limit:
            book.chapters = book.chapters[: args.limit]
        print(f"\n== {book.title} — {len(book.chapters)} chapters ==", flush=True)
        prior = load_prior(out_dir, book.slug) if args.repair else None
        compile_book(book, renderer, out_dir, prior=prior)

    if renderer.calls:
        print(f"\nmodel calls: {renderer.calls}, {renderer.tokens} tokens, "
              f"{renderer.seconds / 60:.1f} min")
    print(f"library written to {out_dir}/")


if __name__ == "__main__":
    main()
