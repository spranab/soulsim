#!/usr/bin/env python3
"""Run the soulsim MVP and print a report.

    python3 run.py                 # default: seed 7, 2000 years, 1000 souls
    python3 run.py --years 500 --seed 3 --csv out.csv
    python3 run.py --experiment intelligence_vs_compassion   # (placeholder hook)

The run is fully deterministic in the seed.
"""
from __future__ import annotations

import argparse

from soulsim.config import SimConfig
from soulsim.world import Universe


def _sparkline(values, width=60):
    if not values:
        return ""
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        hi = lo + 1e-9
    ramp = " .:-=+*#%@"
    # sample `width` evenly spaced points
    step = max(len(values) // width, 1)
    sampled = values[::step][:width]
    out = []
    for v in sampled:
        idx = int((v - lo) / (hi - lo) * (len(ramp) - 1))
        out.append(ramp[idx])
    return "".join(out), lo, hi


def _line(label, values):
    spark = _sparkline(values)
    if not spark:
        print(f"  {label:<22} (no data)")
        return
    s, lo, hi = spark
    print(f"  {label:<22} {s}  [{lo:.3f}..{hi:.3f}]")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--souls", type=int, default=1000)
    ap.add_argument("--adults", type=int, default=200)
    ap.add_argument("--csv", type=str, default=None)
    ap.add_argument("--json", type=str, default=None,
                    help="dump per-year records + summary to JSON for the dashboard")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    from soulsim.config import FixedRules
    cfg = SimConfig(seed=args.seed, years=args.years, initial_adults=args.adults,
                    rules=FixedRules(soul_count=args.souls))

    print(f"soulsim — seed={args.seed} years={args.years} souls={args.souls} "
          f"initial_adults={args.adults}")
    print("running...")
    uni = Universe(cfg)
    log = uni.run(verbose=not args.quiet)

    summary = log.summary(cfg.rules.soul_count)
    print("\n=== SUMMARY ===")
    for k, v in summary.items():
        print(f"  {k:<22} {v}")

    print("\n=== TRAJECTORIES (time -> right) ===")
    _line("population", [r.population for r in log.records])
    _line("avg virtue", [r.avg_virtue for r in log.records])
    _line("avg instability", [r.avg_instability for r in log.records])
    _line("avg robustness", [r.avg_robustness for r in log.records])
    _line("cooperation rate", [r.cooperation_rate for r in log.records])
    _line("violence rate", [r.violence_rate for r in log.records])
    _line("liberated (cumul.)", [float(r.liberated_total) for r in log.records])

    print("\n=== THE INNER LIFE (chariot / gunas / habits) ===")
    _line("avg buddhi", [r.avg_buddhi for r in log.records])
    _line("avg sattva", [r.avg_sattva for r in log.records])
    _line("avg compulsion", [r.avg_compulsion for r in log.records])
    _line("effortless choice", [r.effortless_rate for r in log.records])
    _line("veto attempts/choice", [r.veto_rate for r in log.records])
    _line("veto win rate", [r.veto_win_rate for r in log.records])

    print("\n=== THE META-LOOP (this world's own scriptures) ===")
    _line("doctrine accuracy", [r.doctrine_accuracy for r in log.records])
    _line("myths alive", [float(r.myths_alive) for r in log.records])
    _line("institutions", [float(r.institutions) for r in log.records])

    print("\n=== YONI LADDER (pre-human reservoir draining upward) ===")
    _line("mineral pool", [float(r.pool_mineral) for r in log.records])
    _line("plant pool", [float(r.pool_plant) for r in log.records])
    _line("animal pool", [float(r.pool_animal) for r in log.records])
    _line("human (awaiting birth)", [float(r.pool_human_waiting) for r in log.records])
    total_arrivals = sum(r.yoni_arrivals for r in log.records)
    print(f"  souls reaching human birth over the run: {total_arrivals}")

    # cooperation by yuga — does a hostile age suppress aligned choice?
    # NOTE: naive averaging is confounded by souls refining over time (early
    # Satya looks bad only because souls start raw). We burn in past the first
    # cosmic cycle so the comparison is between ages at comparable refinement.
    burn_in = None
    for r in log.records:
        if r.cosmic_cycle >= 1:
            burn_in = r.year
            break
    print("\n=== COOPERATION & VIRTUE BY YUGA "
          f"(burn-in: years >= {burn_in}) ===")
    coop, virt = {}, {}
    for r in log.records:
        if burn_in is not None and r.year < burn_in:
            continue
        coop.setdefault(r.yuga, []).append(r.cooperation_rate)
        virt.setdefault(r.yuga, []).append(r.avg_virtue)
    print(f"  {'yuga':<8} {'coop':>6} {'virtue':>8}   years")
    for name in ["Satya", "Treta", "Dvapara", "Kali"]:
        c = coop.get(name)
        if c:
            v = virt.get(name)
            print(f"  {name:<8} {sum(c)/len(c):>6.3f} {sum(v)/len(v):>8.3f}   (n={len(c)})")

    if args.csv:
        log.write_csv(args.csv)
        print(f"\nwrote {args.csv}")

    if args.json:
        import json
        from dataclasses import asdict
        payload = {
            "meta": {"seed": args.seed, "years": args.years,
                     "souls": cfg.rules.soul_count, "initial_adults": args.adults,
                     "mahayuga_years": __import__("soulsim.yuga", fromlist=["MAHAYUGA_YEARS"]).MAHAYUGA_YEARS},
            "summary": summary,
            "records": [asdict(r) for r in log.records],
        }
        with open(args.json, "w") as f:
            json.dump(payload, f)
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
