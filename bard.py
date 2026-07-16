#!/usr/bin/env python3
"""The Bard — grounded narrative rendering for soulsim.

The problem with generative fiction is slop: prose unmoored from consequence.
The problem with procedural fiction is wallpaper: the same two templates in
rotation. The Bard resolves both with a division of labor the rest of this
project already trusts:

    THE WORLD SUPPLIES THE PLOT   (true events — mined from soul histories,
                                   the chronicle, the myth record)
    THE MODEL SUPPLIES THE PROSE  (a local LLM as TRANSLATOR, never author)
    A VERIFIER KEEPS IT HONEST    (groundedness lint: no invented facts)

Wall discipline: the Bard is narration-side — it READS a universe and writes
literature; nothing it produces is ever read by physics.

    python3 bard.py            # run a fresh cosmos, mine it, render its stories
"""
from __future__ import annotations

import json
import re
import urllib.request

from soulsim.config import SimConfig, FixedRules
from soulsim.soul import CORE_VIRTUES, INSTABILITIES
from soulsim.world import Universe

OLLAMA = "http://localhost:11434/api/generate"
ENEMY_EN = {"kama": "craving", "krodha": "anger", "lobha": "greed",
            "moha": "attachment", "mada": "pride", "matsarya": "envy"}


def ollama(prompt: str, model="qwen2.5:7b", n=900) -> str:
    body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                       "options": {"num_predict": n, "temperature": 0.85,
                                   "num_ctx": 8192}}).encode()
    req = urllib.request.Request(OLLAMA, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read()).get("response", "")


# ---------------------------------------------------------------------------
# STORY MINERS — dramatic structure is a query over data the world already keeps
# ---------------------------------------------------------------------------
def mine_long_road(u: Universe):
    """The redemption epic: a liberated soul with the hardest recorded climb."""
    best, score = None, -1
    for sid in u.liberated:
        s = u.souls[sid]
        if len(s.history) < 4:
            continue
        falls = sum(1 for h in s.history if h["dv"] < -0.02)
        akrasia = sum(h["ledger"][1] for h in s.history if "ledger" in h)
        sc = len(s.history) + 2 * falls + 0.1 * akrasia
        if sc > score:
            best, score = s, sc
    if not best:
        return None
    return {"kind": "the long road", "lives": best.lifetime_count,
            "arc": [{"life": h["n"], "role": h["role"], "years": h["years"],
                     "virtue_change": h["dv"], "ruling_enemy": ENEMY_EN[h["enemy"]],
                     "born_because": h["born"], "defining_moment": h["note"]}
                    for h in best.history],
            "ending": "attained liberation; left the wheel forever"}


def mine_the_fall(u: Universe):
    """The tragedy: a soul still bound whose recorded lives show decline."""
    best, worst_dv = None, 1
    for s in u.souls.values():
        if s.moksha or len(s.history) < 3:
            continue
        dv = sum(h["dv"] for h in s.history[-3:])
        if dv < worst_dv:
            best, worst_dv = s, dv
    if not best:
        return None
    return {"kind": "the fall", "lives": best.lifetime_count,
            "arc": [{"life": h["n"], "role": h["role"], "years": h["years"],
                     "virtue_change": h["dv"], "ruling_enemy": ENEMY_EN[h["enemy"]],
                     "defining_moment": h["note"]} for h in best.history[-4:]],
            "now": {"ruling_enemy": ENEMY_EN[max(INSTABILITIES, key=lambda v: getattr(best, v))],
                    "still_bound": True},
            "ending": "still on the wheel"}


def mine_forgotten_doer(u: Universe):
    """The injustice: a real deed whose living legend names the wrong person."""
    for m in u.religion.myths:
        if m.story is None or m.story.source_tid is None:
            continue
        src = u.culture.trace_archive.get(m.story.source_tid)
        if src and m.story.actor != src[0] and m.strength > 8:
            return {"kind": "the forgotten doer",
                    "true_actor": src[0], "credited_actor": m.story.actor,
                    "what_was_done": f"an act of {'kindness' if src[1] > 0 else 'harm'} "
                                     f"under {m.story.condition}",
                    "how_the_song_grew": m.story.transformations,
                    "believers_now": int(m.strength),
                    "song_name": m.name}
    return None


# ---------------------------------------------------------------------------
# RENDERER — the model is a translator; the brief is the only truth it has
# ---------------------------------------------------------------------------
RENDER_PROMPT = """You are the court poet of an ancient world. Below is a TRUE \
record from the chronicle — real lives, real years, real failures. Write a short \
story (200-320 words) in a timeless, spare, mythic voice telling this record as \
a tale.

ABSOLUTE RULES:
- Every event you narrate MUST come from the record. Invent NO new events, \
names, places, or numbers.
- You may render inner life (what anger feels like, what a long climb costs) \
freely — that is your art — but deeds, lives, roles and endings are fixed.
- Refer to the soul as "the soul" or by role; lives by their number if useful.
- End with a single italicized line, like a moral a village might repeat.

THE RECORD:
{brief}

THE TALE:"""


def groundedness_lint(text: str, brief: dict) -> dict:
    """No invented numerals or proper nouns: the cheapest honesty check."""
    allowed_nums = set(re.findall(r"\d+", json.dumps(brief)))
    used_nums = set(re.findall(r"\d+", text))
    bad_nums = used_nums - allowed_nums
    allowed_names = {w for w in re.findall(r"[A-Z][a-z]{2,}", json.dumps(brief))}
    story_words = re.findall(r"[A-Z][a-z]{2,}", text)
    common = {"The", "And", "But", "When", "Then", "That", "For", "His", "Her",
              "She", "They", "Their", "One", "Now", "Yet", "There", "Not", "All",
              "What", "Once", "Each", "From", "Until", "With", "Some", "This"}
    bad_names = {w for w in story_words if w not in allowed_names and w not in common}
    return {"ok": not bad_nums and not bad_names,
            "invented_numbers": sorted(bad_nums), "invented_names": sorted(bad_names)}


def render(brief: dict, retries=2) -> tuple:
    for _ in range(retries + 1):
        tale = ollama(RENDER_PROMPT.format(brief=json.dumps(brief, indent=1))).strip()
        lint = groundedness_lint(tale, brief)
        if lint["ok"]:
            return tale, lint
    return tale, lint


if __name__ == "__main__":
    print("running a cosmos (400y)...")
    u = Universe(SimConfig(seed=11, years=400, initial_adults=200,
                           rules=FixedRules(soul_count=800)))
    for _ in range(400):
        u.step()
    for miner in (mine_long_road, mine_the_fall, mine_forgotten_doer):
        brief = miner(u)
        if not brief:
            print(f"\n[{miner.__name__}: no instance found in this cosmos]")
            continue
        print("\n" + "=" * 72)
        print(f"STORY BRIEF ({brief['kind']}):")
        print(json.dumps(brief, indent=1)[:900])
        tale, lint = render(brief)
        print(f"\nGROUNDEDNESS: {'PASS' if lint['ok'] else 'FAIL ' + str(lint)}")
        print("\nTHE TALE:\n")
        print(tale)
