#!/usr/bin/env python3
"""Export a full run for the playback viewer.

Two passes, same seed (runs are deterministic, so pass 2 is a perfect replay):
  pass 1 — run to the end, then choose the souls worth following:
           the first to liberate, the longest road to moksha, the most bound,
           the sage (highest buddhi still on the wheel), the first avatar.
  pass 2 — replay, snapshotting the chosen souls every year, plus the full
           chronicle and yearly records.

    python3 export_viewer.py [--years 1500] [--seed 7] [--out viewer_data.json]
"""
from __future__ import annotations

import argparse
import json

from soulsim.config import SimConfig, FixedRules
from soulsim.soul import YONI_STAGES, CORE_VIRTUES
from soulsim.world import Universe

NAMES = ["Aruni", "Kavya", "Bodhi", "Tara", "Ishan"]


def r3(x):
    return round(float(x), 3)


def pick_souls(cfg: SimConfig):
    """Pass 1: run and choose the cast."""
    u = Universe(cfg)
    lib_year = {}
    avatar_sid = None
    for _ in range(cfg.years):
        prev = set(u.liberated)
        u.step()
        for sid in u.liberated - prev:
            lib_year.setdefault(sid, u.year - 1)
        if avatar_sid is None:
            for p in u.persons.values():
                if p.is_avatar:
                    avatar_sid = p.soul.soul_id
                    break

    cast = []
    if lib_year:
        first = min(lib_year, key=lambda s: lib_year[s])
        cast.append((first, "the first to walk free", lib_year[first]))
        long_road = max(lib_year, key=lambda s: u.souls[s].lifetime_count)
        if long_road != first:
            cast.append((long_road, "the long road", lib_year[long_road]))
    bound = [s for s in u.souls.values() if not s.moksha and s.lifetime_count > 0]
    if bound:
        trapped = max(bound, key=lambda s: s.lifetime_count)
        cast.append((trapped.soul_id, "still on the wheel", None))
        sage = max(bound, key=lambda s: s.buddhi)
        if sage.soul_id != trapped.soul_id:
            cast.append((sage.soul_id, "the sage, not yet free", None))
    if avatar_sid and avatar_sid not in [c[0] for c in cast]:
        cast.append((avatar_sid, "the one who returns", None))
    return cast[:5]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="viewer_data.json")
    args = ap.parse_args()

    cfg = SimConfig(seed=args.seed, years=args.years, initial_adults=200,
                    rules=FixedRules(soul_count=1000))
    print("pass 1: choosing the cast...")
    cast = pick_souls(cfg)
    for sid, role, ly in cast:
        print(f"  {role:24} {str(sid)[:8]}  {'liberated yr '+str(ly) if ly else ''}")

    print("pass 2: replaying with shadows...")
    cfg2 = SimConfig(seed=args.seed, years=args.years, initial_adults=200,
                     rules=FixedRules(soul_count=1000))
    u = Universe(cfg2)
    ids = [c[0] for c in cast]
    shadows = {str(sid): [] for sid in ids}
    for _ in range(cfg2.years):
        u.step()
        for sid in ids:
            soul = u.souls.get(sid)
            if soul is None:
                shadows[str(sid)].append(None)
                continue
            person = u.persons.get(soul.current_body_id) if soul.current_body_id else None
            if soul.moksha and person is None:
                status = 3          # liberated, beyond
            elif person is not None and person.is_avatar:
                status = 4          # walking as avatar
            elif person is not None:
                status = 2          # embodied
            elif soul.is_human:
                status = 1          # between lives
            else:
                status = 0          # climbing the ladder
            virtue = sum(getattr(soul, v) for v in CORE_VIRTUES) / len(CORE_VIRTUES)
            shadows[str(sid)].append([
                status, soul.lifetime_count, YONI_STAGES.index(soul.yoni_stage),
                r3(virtue), r3(soul.buddhi), r3(soul.compulsion_ewma),
            ])

    R = u.metrics.records
    ycode = {"Satya": "S", "Treta": "T", "Dvapara": "D", "Kali": "K"}
    data = {
        "meta": {"seed": args.seed, "years": args.years, "souls": 1000,
                 "mahayuga": 500},
        "records": {
            "year": [r.year for r in R],
            "yuga": [ycode[r.yuga] for r in R],
            "cc": [r.cosmic_cycle for r in R],
            "pop": [r.population for r in R],
            "lib": [r.liberated_total for r in R],
            "virtue": [r3(r.avg_virtue) for r in R],
            "coop": [r3(r.cooperation_rate) for r in R],
            "buddhi": [r3(r.avg_buddhi) for r in R],
            "sattva": [r3(r.avg_sattva) for r in R],
            "effortless": [r3(r.effortless_rate) for r in R],
            "compulsion": [r3(r.avg_compulsion) for r in R],
            "vetoRate": [r3(r.veto_rate) for r in R],
            "doctrine": [r3(r.doctrine_accuracy) for r in R],
            "myths": [r.myths_alive for r in R],
            "institutions": [r.institutions for r in R],
            "avatars": [r.avatars_alive for r in R],
            "pralaya": [r.year for r in R if r.pralaya],
            "descents": [r.year for r in R if r.avatar],
        },
        "cast": [{"id": str(sid), "name": NAMES[i], "role": role,
                  "liberated_year": ly}
                 for i, (sid, role, ly) in enumerate(cast)],
        "shadows": shadows,
        "chronicle": [{"y": y, "k": k, "t": t} for (y, k, t) in u.chronicle],
    }
    with open(args.out, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    import os
    print(f"wrote {args.out} ({os.path.getsize(args.out)//1024} KB, "
          f"{len(u.chronicle)} chronicle events)")


if __name__ == "__main__":
    main()
