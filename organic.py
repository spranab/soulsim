#!/usr/bin/env python3
"""The organic transformer — the world as a network you can prompt.

Nothing here changes the physics. It reads the Universe as if it were a
network and drives it only through the god-ops the world already exposes.
The correspondence is structural, not decorative:

    residual stream   the soul: a state vector carried across lives, each life
                      adding an update (karma) and passing it on
    layer             one life; decision.py is the nonlinearity (a sigmoid veto
                      contest), karma.py the update
    LayerNorm         soul.normalize_gunas(): the simplex normalization run
                      every step
    attention         who hears whom: each hearer attends to living myths and
                      works in proportion to their strength (softmax over the
                      canon); two heads, story and art
    positional enc.   the yuga: the same layer processes a soul differently in
                      Satya and in Kali
    weights           the substrate (liberated souls consolidated into the
                      ground new souls are born from) and the samskara grooves
    learning rule     local, Hebbian: you become what you repeatedly do; no
                      backprop anywhere
    epoch             a day of Brahma: pralaya resets activations (habits,
                      gunas) and keeps the weights (virtues, robustness, buddhi,
                      the substrate)
    tokens in         events the world is given: calamity, grace, avatar,
                      pralaya, rest — applied through god-ops at each block
    logits out        what the world believes about its own rules: a
                      probability per proposition, believer-weighted
    loss              cross-entropy of those beliefs against GROUND_TRUTHS,
                      which only the physics can see

It is organic in the plain sense: units are born, die and are pruned (moksha),
attention re-forms around whatever the canon keeps, and the readout is the
world's own scripture.

    python3 organic.py                       # prompt it two ways, compare
    python3 organic.py --prompt "calamity calamity grace rest avatar"
"""
from __future__ import annotations

import argparse
import math
from typing import Dict, List

from soulsim.config import SimConfig, FixedRules
from soulsim.religion import GROUND_TRUTHS, PROPS
from soulsim.soul import CORE_VIRTUES, INSTABILITIES, ROBUSTNESS
from soulsim.world import Universe

VOCAB = ("rest", "calamity", "grace", "avatar", "pralaya")


class OrganicTransformer:
    def __init__(self, seed: int = 11, souls: int = 800, adults: int = 200,
                 years_per_token: int = 25) -> None:
        self.u = Universe(SimConfig(seed=seed, years=10 ** 6, initial_adults=adults,
                                    rules=FixedRules(soul_count=souls)))
        self.block = years_per_token
        self.trace: List[Dict] = []

    # -- the residual stream ---------------------------------------------------
    def residual(self) -> List[List[float]]:
        """One row per living unit: the soul's state vector (virtues, enemies,
        robustness, gunas, buddhi). This is what a layer reads and updates."""
        dims = CORE_VIRTUES + INSTABILITIES + ROBUSTNESS + ["sattva", "rajas", "tamas", "buddhi"]
        return [[getattr(p.soul, d) for d in dims] for p in self.u.persons.values()]

    # -- attention -------------------------------------------------------------
    def attention(self) -> Dict[str, Dict]:
        """Two heads. Each hearer attends to the living canon in proportion to
        strength — the world's exposure rule, read back as a distribution."""
        out = {}
        for head, items, key in (("story", [m for m in self.u.religion.myths if m.story is not None],
                                  lambda m: m.name),
                                 ("art", self.u.arts.works, lambda w: f"{w.form} of {w.creator}")):
            if not items:
                out[head] = {"entropy": 0.0, "top": [], "n": 0}
                continue
            tot = sum(x.strength for x in items)
            w = [x.strength / tot for x in items]
            ent = -sum(p * math.log(p) for p in w if p > 0)
            top = sorted(zip(w, items), key=lambda t: -t[0])[:3]
            out[head] = {"entropy": ent, "n": len(items),
                         "top": [(round(p, 3), key(x)) for p, x in top]}
        return out

    # -- readout: what the world believes -----------------------------------------
    def logits(self) -> Dict[str, float]:
        """P(the world holds proposition p true), believer-weighted over living
        doctrine. 0.5 where nobody teaches either way."""
        pos = {p: 0.0 for p in PROPS}
        neg = {p: 0.0 for p in PROPS}
        for m in self.u.religion.myths:
            for p, pol in m.props.items():
                (pos if pol else neg)[p] += m.strength
        return {p: (pos[p] / (pos[p] + neg[p]) if pos[p] + neg[p] > 0 else 0.5) for p in PROPS}

    def loss(self) -> float:
        """Cross-entropy of the world's beliefs against the truth it lives in."""
        b = self.logits()
        eps = 1e-6
        return -sum(math.log((b[p] if GROUND_TRUTHS[p] else 1 - b[p]) + eps) for p in PROPS) / len(PROPS)

    # -- one token: an event, then a block of layers ------------------------------
    def step_token(self, tok: str) -> Dict:
        u = self.u
        if tok == "calamity":
            u.god_calamity()
        elif tok == "grace":
            u.god_miracle()
        elif tok == "avatar":
            u.god_avatar()
        elif tok == "pralaya":
            u.god_pralaya()
        elif tok != "rest":
            raise ValueError(f"unknown token {tok!r}; vocab is {VOCAB}")
        born = u.souls_created
        freed = len(u.liberated)
        for _ in range(self.block):
            u.step()
        att = self.attention()
        rec = {"token": tok, "year": u.year, "yuga": u.clock.at(u.year - 1)[0].name,
               "units": len(u.persons), "grown": u.souls_created - born,
               "pruned": len(u.liberated) - freed,
               "residual_mean_virtue": sum(r[:len(CORE_VIRTUES)][i] for r in self.residual()
                                           for i in range(len(CORE_VIRTUES))) / max(1, len(u.persons) * len(CORE_VIRTUES)),
               "weights_substrate": round(u.substrate_virtue(), 3),
               "attention": att, "loss": self.loss(),
               "accuracy": u.religion.doctrine_accuracy()}
        self.trace.append(rec)
        return rec

    def forward(self, prompt: List[str]) -> List[Dict]:
        return [self.step_token(t) for t in prompt]


def report(name: str, net: OrganicTransformer) -> None:
    print(f"\n== prompt: {name}")
    print(f"{'tok':<9}{'year':>5} {'yuga':<8}{'units':>6}{'grown':>6}{'pruned':>7}"
          f"{'virtue':>8}{'subst':>7}{'H(att)':>8}{'loss':>7}{'acc':>6}")
    for r in net.trace:
        print(f"{r['token']:<9}{r['year']:>5} {r['yuga']:<8}{r['units']:>6}{r['grown']:>6}"
              f"{r['pruned']:>7}{r['residual_mean_virtue']:>8.3f}{r['weights_substrate']:>7.3f}"
              f"{r['attention']['story']['entropy']:>8.2f}{r['loss']:>7.3f}{r['accuracy']:>6.2f}")
    b = net.logits()
    print("  beliefs (P true) vs truth:")
    for p in PROPS:
        mark = "ok" if (b[p] >= 0.5) == GROUND_TRUTHS[p] else "WRONG"
        print(f"    {p:<20} {b[p]:.2f}  truth={str(GROUND_TRUTHS[p]):<5} {mark}")
    a = net.attention()
    for head in ("story", "art"):
        print(f"  attention[{head}]: {a[head]['n']} keys, entropy {a[head]['entropy']:.2f}, "
              f"top: " + "; ".join(f"{p} {k}" for p, k in a[head]["top"]))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--block", type=int, default=25, help="years per token (layers per block)")
    ap.add_argument("--prompt", default=None, help="space-separated tokens from " + " ".join(VOCAB))
    args = ap.parse_args()
    if args.prompt:
        net = OrganicTransformer(seed=args.seed, years_per_token=args.block)
        net.forward(args.prompt.split())
        report(args.prompt, net)
        return
    # the control: does the readout depend on the input? Same seed, same length,
    # two prompts; the difference is the network's response to the tokens.
    quiet = "rest " * 12
    loud = "calamity calamity grace rest rest calamity grace grace rest calamity rest grace"
    for name in (quiet.strip(), loud):
        net = OrganicTransformer(seed=args.seed, years_per_token=args.block)
        net.forward(name.split())
        report(name, net)


if __name__ == "__main__":
    main()
