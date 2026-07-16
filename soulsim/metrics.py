"""The measured layer — observation only.

Nothing here is ever read back by a rule, a hypothesis, or a decision. Metrics
flow one way: out of the simulation and into a report/CSV. That one-way flow is
the whole point of the three-layer wall — it is what lets a result count as a
finding instead of an echo of the code.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class YearRecord:
    year: int
    cosmic_cycle: int
    yuga: str
    population: int
    births: int
    deaths: int
    liberated_this_year: int
    liberated_total: int
    avg_virtue: float
    avg_instability: float
    avg_robustness: float
    cooperation_rate: float
    violence_rate: float
    # yoni ladder snapshot
    pool_mineral: int = 0
    pool_plant: int = 0
    pool_animal: int = 0
    pool_human_waiting: int = 0   # human-stage souls awaiting birth
    yoni_arrivals: int = 0        # souls that reached human birth this year
    pralaya: int = 0              # 1 if the world dissolved & re-manifested this year
    souls_total: int = 0          # total jivas ever manifested (grows with creation)
    # per-vice population averages (the ariṣaḍvarga)
    vice_kama: float = 0.0
    vice_krodha: float = 0.0
    vice_lobha: float = 0.0
    vice_moha: float = 0.0
    vice_mada: float = 0.0
    vice_matsarya: float = 0.0
    # avatars & the substrate (where the liberated go)
    avatar: int = 0              # 1 if an avatar descended this year
    avatars_alive: int = 0
    avatar_total: int = 0        # cumulative descents
    substrate_virtue: float = 0.0  # mean virtue of the enriched ground
    returnable: int = 0          # liberated individuals available to return
    # v2 — the inner life (chariot / gunas / habits)
    avg_buddhi: float = 0.0        # strength of the charioteer, population mean
    avg_sattva: float = 0.0
    avg_rajas: float = 0.0
    avg_tamas: float = 0.0
    avg_compulsion: float = 0.0    # mean compulsion EWMA (low = effortless souls)
    noticing_rate: float = 0.0     # fraction of choices where the impulse was seen
    effortless_rate: float = 0.0   # fraction where the FIRST impulse was aligned
    veto_rate: float = 0.0         # veto attempts / choices
    veto_win_rate: float = 0.0     # wins / attempts (0 if none)
    # the meta-loop — this world's own scriptures, graded by its physics
    myths_alive: int = 0
    institutions: int = 0
    doctrine_accuracy: float = 0.0  # strength-weighted truth of living doctrine
    doctrine_coverage: float = 0.0  # fraction of ground truths anyone still teaches
    historical_fidelity: float = 0.0  # story-claims vs the audit (analytics only)
    story_myths: int = 0
    # arts — the world's emotional weather and its growing library
    artworks_alive: int = 0
    classics: int = 0


@dataclass
class MetricsLog:
    records: List[YearRecord] = field(default_factory=list)
    # lifetimes each liberated soul needed — reported at the end
    lives_to_moksha: List[int] = field(default_factory=list)

    def add(self, rec: YearRecord) -> None:
        self.records.append(rec)

    def record_liberation(self, lifetime_count: int) -> None:
        self.lives_to_moksha.append(lifetime_count)

    # -- reporting ---------------------------------------------------------
    def avg_lives_to_moksha(self) -> Optional[float]:
        if not self.lives_to_moksha:
            return None
        return sum(self.lives_to_moksha) / len(self.lives_to_moksha)

    def write_csv(self, path: str) -> None:
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow([
                "year", "cosmic_cycle", "yuga", "population", "births", "deaths",
                "liberated_this_year", "liberated_total",
                "avg_virtue", "avg_instability", "avg_robustness",
                "cooperation_rate", "violence_rate",
            ])
            for r in self.records:
                w.writerow([
                    r.year, r.cosmic_cycle, r.yuga, r.population, r.births, r.deaths,
                    r.liberated_this_year, r.liberated_total,
                    round(r.avg_virtue, 4), round(r.avg_instability, 4),
                    round(r.avg_robustness, 4),
                    round(r.cooperation_rate, 4), round(r.violence_rate, 4),
                ])

    def summary(self, soul_count: int) -> Dict[str, object]:
        if not self.records:
            return {}
        last = self.records[-1]
        peak_pop = max(r.population for r in self.records)
        total_births = sum(r.births for r in self.records)
        total_deaths = sum(r.deaths for r in self.records)
        pralaya_count = sum(r.pralaya for r in self.records)
        souls_ever = max(last.souls_total, soul_count)
        return {
            "years": self.records[-1].year + 1,
            "cosmic_cycles": last.cosmic_cycle + 1,
            "pralayas": pralaya_count,
            "avatar_descents": last.avatar_total,
            "substrate_virtue": round(last.substrate_virtue, 4),
            "peak_population": peak_pop,
            "final_population": last.population,
            "souls_ever_created": souls_ever,
            "total_births": total_births,
            "total_deaths": total_deaths,
            "souls_liberated": last.liberated_total,
            "fraction_liberated": round(last.liberated_total / souls_ever, 4),
            "avg_lives_to_moksha": (round(self.avg_lives_to_moksha(), 2)
                                    if self.avg_lives_to_moksha() is not None else None),
            "final_avg_virtue": round(last.avg_virtue, 4),
            "final_avg_instability": round(last.avg_instability, 4),
            "final_avg_robustness": round(last.avg_robustness, 4),
        }
