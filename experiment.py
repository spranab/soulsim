#!/usr/bin/env python3
"""Experiment sweep — the point of the whole thing.

Vary ONE hypothesis knob and watch the metaphysical outcome move. If the outcome
tracks the knob (and not a hard-coded rule), then the simulation is a laboratory
rather than an echo chamber.

Default sweep: `adversity_refines` — how much holding alignment under pressure
builds robustness. The question being asked is literally:

    "Does adversity refine a soul, or does it mostly damage it?"

Low  -> hardship damages faster than it refines -> few souls ever liberate ->
        the reincarnation pool churns forever (samsara persists).
High -> hardship refines -> souls graduate -> the universe empties.

    python3 experiment.py
    python3 experiment.py --knob learning_rate --values 0.02,0.04,0.08
"""
from __future__ import annotations

import argparse
import statistics
from dataclasses import replace

from soulsim.config import SimConfig, FixedRules, Hypotheses
from soulsim.world import Universe


def run_one(knob: str, value: float, seed: int, years: int, souls: int):
    hyp = Hypotheses()
    setattr(hyp, knob, value)
    cfg = SimConfig(seed=seed, years=years, initial_adults=200,
                    rules=FixedRules(soul_count=souls), hyp=hyp)
    log = Universe(cfg).run(verbose=False)
    s = log.summary(souls)
    last = log.records[-1]
    emptied = last.population == 0
    return {
        "fraction_liberated": s["fraction_liberated"],
        "lives_to_moksha": s["avg_lives_to_moksha"] or 0.0,
        "years_survived": s["years"],
        "emptied": 1.0 if emptied else 0.0,
        "final_virtue": s["final_avg_virtue"],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--knob", default="adversity_refines")
    ap.add_argument("--values", default="0.25,0.5,1.0,2.0")
    ap.add_argument("--seeds", default="7,11,23")
    ap.add_argument("--years", type=int, default=2000)
    ap.add_argument("--souls", type=int, default=1000)
    args = ap.parse_args()

    values = [float(v) for v in args.values.split(",")]
    seeds = [int(s) for s in args.seeds.split(",")]

    print(f"sweep knob = {args.knob}   seeds = {seeds}   "
          f"years = {args.years}   souls = {args.souls}\n")
    header = f"{args.knob:>16} | {'frac_liber':>10} {'lives/mokṣa':>12} " \
             f"{'yrs_survived':>13} {'emptied':>8} {'final_virtue':>13}"
    print(header)
    print("-" * len(header))

    for val in values:
        runs = [run_one(args.knob, val, seed, args.years, args.souls) for seed in seeds]

        def avg(key):
            return statistics.mean(r[key] for r in runs)

        print(f"{val:>16.3f} | {avg('fraction_liberated'):>10.3f} "
              f"{avg('lives_to_moksha'):>12.2f} {avg('years_survived'):>13.0f} "
              f"{avg('emptied'):>8.2f} {avg('final_virtue'):>13.3f}")

    print("\n(each row averaged over the seeds; 'emptied' = fraction of seeds "
          "whose universe reached population zero)")


if __name__ == "__main__":
    main()
