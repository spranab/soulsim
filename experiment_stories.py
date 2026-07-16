#!/usr/bin/env python3
"""E1 — Can stories change conduct? (sol's dose-response battery)

The only mechanism difference between arms is the shravana-samskara channel
(exemplar_pull): stories heard lay weak cultural grooves in the chariot's
habit slot. Culture rolls its own rng stream, so arms differ by the channel
alone, not by dice consumption.

Finding (seeds 7/11/23, 350y, 800 souls, last-120y means):
  pull=0.0   coop .512  violence .488  effortless .486  liberated  98
  pull=0.5   coop .511  violence .489  effortless .485  liberated  98   (null)
  pull=1.0   coop .531  violence .468  effortless .506  liberated 107

At full strength the story-channel is measurably PRO-SOCIAL (+1.9pp
cooperation, +2pp effortlessness, +9% liberation) even though villain-tales
slightly dominate the myth pool by believers (hero share ~.46). Working
hypothesis for the asymmetry, consistent with the chariot mechanics: villain
tales groove actions the unrefined were already taking (redundant at the
argmax), while hero tales can FLIP marginal souls to the aligned action
(pivotal). The devil's stories are wasted on those already his; the saint's
stories rescue the borderline. At pull=0.5 the groove increments sit below
the flip threshold — narrative influence is nonlinear.

Honest caveats: n=3 seeds, small effects, one parameterization; the
per-myth surgical deletion test needs more seeds to beat chaos and is left
as future work.
"""
import statistics as st
from soulsim.config import SimConfig, FixedRules, Hypotheses
from soulsim.world import Universe


def run(pull, seed, years=350, souls=800):
    hyp = Hypotheses(); hyp.exemplar_pull = pull
    u = Universe(SimConfig(seed=seed, years=years, initial_adults=200,
                           rules=FixedRules(soul_count=souls), hyp=hyp))
    for _ in range(years):
        u.step()
    R = u.metrics.records[-120:]
    stories = [m for m in u.religion.myths if m.story is not None]
    hero = sum(m.strength for m in stories if m.story.align > 0)
    vill = sum(m.strength for m in stories if m.story.align < 0)
    return dict(coop=st.mean(r.cooperation_rate for r in R),
                viol=st.mean(r.violence_rate for r in R),
                eff=st.mean(r.effortless_rate for r in R),
                lib=len(u.liberated),
                hero_share=hero / (hero + vill) if hero + vill else 0.5)


if __name__ == "__main__":
    for pull in (0.0, 0.5, 1.0):
        rs = [run(pull, s) for s in (7, 11, 23)]
        avg = lambda k: st.mean(r[k] for r in rs)
        print(f"pull={pull:.1f}  coop={avg('coop'):.3f}  viol={avg('viol'):.3f}  "
              f"eff={avg('eff'):.3f}  lib={avg('lib'):.0f}  hero_share={avg('hero_share'):.2f}")
