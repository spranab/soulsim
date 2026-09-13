#!/usr/bin/env python3
"""ladder.py — how small can the translator be?

The Bard's division of labor (`bard.py`) puts every fact in the world's
hands and asks a local model only to phrase it. If that's true, the model's
job is translation, not invention — and translation should scale down hard.
This is the measurement: a fixed chapter set, a fixed judge, a ladder of
writer models from 35B down to 1.5B, each tried under two interfaces —
`english` (the brief as `bard.py` already writes it) and `compact`
(`bardic/compact.py`'s terser notation) — to see where quality falls off
a cliff, and whether the terser notation buys back some of the fall.

Every chapter's result streams to `<out>/results.json` (written atomically)
so a dashboard can watch a run in progress; `--resume` picks a partial run
back up without re-doing finished rungs or finished chapters within one.

    python3 ladder.py                                   # the full ladder
    python3 ladder.py --writers qwen2.5:1.5b --chapters 2 --out /tmp/smoke
    python3 ladder.py --resume                          # pick up where it left off
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import bardic
from bardic import compact
from bardic.render import Renderer
from bardic.verify import classify, split_sentences
from bard import run_cosmos

OLLAMA = "http://localhost:11434"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# machine + model sizes
# ---------------------------------------------------------------------------
def machine_string() -> str:
    """A short, human description of the box the ladder is run on."""
    if sys.platform == "darwin":
        try:
            chip = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"],
                                  capture_output=True, text=True, timeout=5).stdout.strip()
            mem = subprocess.run(["sysctl", "-n", "hw.memsize"],
                                 capture_output=True, text=True, timeout=5).stdout.strip()
            gb = int(mem) / 1e9 if mem.isdigit() else None
            if chip:
                return f"{chip}, {gb:.0f} GB" if gb else chip
        except (OSError, subprocess.SubprocessError):
            pass
    return platform.platform()


def model_sizes() -> Dict[str, float]:
    """name -> installed size in GB, from `ollama list` (the SIZE column);
    falls back to /api/tags' byte-exact `size` if the CLI isn't available."""
    sizes: Dict[str, float] = {}
    try:
        out = subprocess.run(["ollama", "list"], capture_output=True, text=True,
                             timeout=15, check=True).stdout
        for line in out.strip().splitlines()[1:]:
            cols = re.split(r"\s{2,}", line.strip())
            if len(cols) < 3:
                continue
            m = re.match(r"([\d.]+)\s*(GB|MB)", cols[2], re.I)
            if m:
                val, unit = float(m.group(1)), m.group(2).upper()
                sizes[cols[0]] = val / 1024 if unit == "MB" else val
    except (OSError, subprocess.SubprocessError):
        pass
    if not sizes:
        try:
            with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=5) as r:
                for m in json.loads(r.read()).get("models", []):
                    sizes[m["name"]] = m.get("size", 0) / 1e9
        except Exception:  # noqa: BLE001
            pass
    return sizes


def size_for(model: str, sizes: Dict[str, float]) -> float:
    if model in sizes:
        return sizes[model]
    base = model.split(":")[0]
    for name, gb in sizes.items():
        if name.split(":")[0] == base:
            return gb
    return 0.0


# ---------------------------------------------------------------------------
# the fixed chapter set
# ---------------------------------------------------------------------------
_PLAN = (("epic", 5), ("novel", 4), ("tales", 3))


def build_chapter_set(annals, universe, chapters: int) -> List[Dict]:
    """epic[0:5] + novel[0:4] + tales[0:3], truncated to `chapters` in that
    order. Each entry carries everything `Renderer.render` needs, including
    the same per-book continuity (`lead`) and book-wide allowed numbers
    `compile_book` gives a real compile."""
    out: List[Dict] = []
    for genre, n in _PLAN:
        book = bardic.GENRES[genre](annals, universe)
        book_numbers = set(re.findall(r"\d+", "\n".join(l for c in book.chapters for l in c.brief)))
        lead = ""
        for ch in book.chapters[:n]:
            out.append({"genre": genre, "heading": ch.heading, "brief": ch.brief,
                        "voice": ch.voice, "words": ch.words, "must_say": ch.must_say,
                        "form": ch.form, "inside": book.inside, "glossary": book.glossary,
                        "numbers": book_numbers,
                        "lead": lead if ch.form == "prose" else ""})
            lead = " ".join(ch.brief[:3])[:600]
    return out[:chapters]


# ---------------------------------------------------------------------------
# one chapter, one rung: render + judge
# ---------------------------------------------------------------------------
def render_one(writer: Renderer, info: Dict, interface: str) -> Tuple[Dict, Dict, float]:
    """Renders one chapter and returns (render() result, ollama stats for
    every attempt this call made, wall-clock seconds)."""
    kwargs: Dict = dict(voice=info["voice"], brief=info["brief"], words=info["words"],
                        glossary=info["glossary"], must_say=info["must_say"],
                        lead=info["lead"], form=info["form"], inside=info["inside"],
                        numbers=info["numbers"])
    if interface == "compact":
        kwargs["brief_for_prompt"] = compact.encode(info["brief"])
        kwargs["legend"] = compact.LEGEND
    p0, g0 = writer.prompt_tokens, writer.tokens
    ps0, gs0 = writer.prompt_seconds, writer.gen_seconds
    t0 = time.time()
    result = writer.render(**kwargs)
    seconds = time.time() - t0
    stats = {"prompt_tokens": writer.prompt_tokens - p0, "gen_tokens": writer.tokens - g0,
             "prompt_seconds": writer.prompt_seconds - ps0, "gen_seconds": writer.gen_seconds - gs0,
             # the FIRST attempt only — what the writer had to read once,
             # unpadded by any retries this chapter needed
             "prompt_tokens_first": writer.first_call.get("prompt_tokens", 0)}
    return result, stats, seconds


def judge_one(judge: Renderer, text: str, brief: List[str]) -> Tuple[List[str], List[Dict]]:
    sentences = split_sentences(text)
    verdicts = classify(sentences, brief, judge, batch=12)
    return sentences, verdicts


def build_record(info: Dict, result: Dict, stats: Dict, seconds: float,
                 sentences: List[str], verdicts: List[Dict]) -> Dict:
    lint = result.get("lint", {})
    source = result.get("source", "plain")
    attempts = result.get("attempts", 0)
    p_tok, g_tok = stats["prompt_tokens"], stats["gen_tokens"]
    p_sec, g_sec = stats["prompt_seconds"], stats["gen_seconds"]
    tally = {"SUPPORTED": 0, "TEXTURE": 0, "UNSUPPORTED": 0, "CONTRADICTED": 0}
    for v in verdicts:
        tally[v.get("verdict", "SUPPORTED")] = tally.get(v.get("verdict", "SUPPORTED"), 0) + 1
    flags = [{"sentence": sentences[v["i"]], "verdict": v["verdict"], "why": v.get("why", "")}
             for v in verdicts if v.get("verdict") in ("UNSUPPORTED", "CONTRADICTED")]
    parse_failures = sum(1 for v in verdicts if v.get("why") == "unparsed")
    return {
        "genre": info["genre"], "heading": info["heading"], "seconds": seconds,
        "attempts": attempts,
        "prompt_tokens": p_tok, "prompt_tokens_first": stats.get("prompt_tokens_first", 0),
        "gen_tokens": g_tok,
        "prompt_eval_tps": (p_tok / p_sec) if p_sec > 0 else 0.0,
        "gen_tps": (g_tok / g_sec) if g_sec > 0 else 0.0,
        "lint_ok": source == "model", "lint_first_ok": source == "model" and attempts == 1,
        "source": source, "invented": lint.get("invented_names", []) + lint.get("invented_numbers", []),
        "coverage": result.get("coverage"), "words": len(result.get("text", "").split()),
        "sentences": len(sentences), "supported": tally["SUPPORTED"], "texture": tally["TEXTURE"],
        "unsupported": tally["UNSUPPORTED"], "contradicted": tally["CONTRADICTED"],
        "parse_failures": parse_failures, "flags": flags, "text": result.get("text", ""),
    }


# ---------------------------------------------------------------------------
# the summary — recomputed from per_chapter every time (pure, no ollama)
# ---------------------------------------------------------------------------
def compute_summary(per_chapter: List[Dict], size_gb: float) -> Dict:
    """A rung's summary from its (possibly partial) `per_chapter` list.
    Pure and ollama-free so it can be unit-tested on hand-made records."""
    n = len(per_chapter)
    if n == 0:
        return {}

    def avg(key: str) -> float:
        vals = [c[key] for c in per_chapter if c.get(key) is not None]
        return sum(vals) / len(vals) if vals else 0.0

    lint_first_pass_rate = sum(1 for c in per_chapter if c.get("lint_first_ok")) / n
    lint_final_pass_rate = sum(1 for c in per_chapter if c.get("lint_ok")) / n
    retries = sum(max(0, (c.get("attempts") or 0) - 1) for c in per_chapter)
    scrubbed = sum(1 for c in per_chapter if c.get("source") == "model+scrub")
    cov_vals = [c["coverage"] for c in per_chapter if c.get("coverage") is not None]
    coverage = sum(cov_vals) / len(cov_vals) if cov_vals else None
    sentences = sum(c.get("sentences", 0) for c in per_chapter)
    supported = sum(c.get("supported", 0) for c in per_chapter)
    texture = sum(c.get("texture", 0) for c in per_chapter)
    unsupported = sum(c.get("unsupported", 0) for c in per_chapter)
    contradicted = sum(c.get("contradicted", 0) for c in per_chapter)
    seconds_per_chapter = avg("seconds")
    grounded_rate = (supported + texture) / sentences if sentences else 0.0
    quality = grounded_rate * (coverage if coverage is not None else 1.0) * lint_final_pass_rate
    efficiency = (quality / (seconds_per_chapter * size_gb)
                 if seconds_per_chapter > 0 and size_gb > 0 else 0.0)
    return {
        "seconds_per_chapter": seconds_per_chapter,
        "prompt_tokens_per_chapter": avg("prompt_tokens"),
        "prompt_tokens_first_per_chapter": avg("prompt_tokens_first"),
        "gen_tokens_per_chapter": avg("gen_tokens"),
        "prompt_eval_tps": avg("prompt_eval_tps"),
        "gen_tps": avg("gen_tps"),
        "lint_first_pass_rate": lint_first_pass_rate,
        "lint_final_pass_rate": lint_final_pass_rate,
        "retries": retries,
        "scrubbed": scrubbed,
        "coverage": coverage,
        "words_per_chapter": avg("words"),
        "sentences": sentences,
        "supported": supported,
        "texture": texture,
        "unsupported": unsupported,
        "contradicted": contradicted,
        "grounded_rate": grounded_rate,
        "quality": quality,
        "efficiency": efficiency,
    }


# ---------------------------------------------------------------------------
# results.json — loaded for --resume, written atomically after every chapter
# ---------------------------------------------------------------------------
def load_results(path: str) -> Optional[Dict]:
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def atomic_write_json(path: str, data: Dict) -> None:
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".ladder-", suffix=".json.tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=1)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--years", type=int, default=500)
    ap.add_argument("--souls", type=int, default=800)
    ap.add_argument("--adults", type=int, default=200)
    ap.add_argument("--writers", default="qwen3.6:35b,qwen3.5:9b,qwen3.5:4b,qwen2.5:1.5b")
    ap.add_argument("--interfaces", default="english,compact")
    ap.add_argument("--judge", default="qwen3.6:35b")
    ap.add_argument("--out", default="ladder")
    ap.add_argument("--chapters", type=int, default=12)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--machine", default="", help="override the auto-detected machine string")
    args = ap.parse_args()

    writers = [w.strip() for w in args.writers.split(",") if w.strip()]
    interfaces = [i.strip() for i in args.interfaces.split(",") if i.strip()]

    os.makedirs(args.out, exist_ok=True)
    results_path = os.path.join(args.out, "results.json")
    results = load_results(results_path) if args.resume else None
    if results is None:
        results = {"benchmark": {}, "rungs": [], "updated": now_iso()}

    u = run_cosmos(args.seed, args.years, args.souls, args.adults)
    chapter_infos = build_chapter_set(u.annals, u, args.chapters)
    print(f"chapter set: {len(chapter_infos)} chapters -> "
          + ", ".join(f"{g} {sum(1 for c in chapter_infos if c['genre'] == g)}"
                      for g, _ in _PLAN), flush=True)

    started = results.get("benchmark", {}).get("started") or now_iso()
    results["benchmark"] = {
        "seed": args.seed, "years": args.years, "genres": ["epic", "novel", "tales"],
        "chapters": len(chapter_infos),
        "chapter_list": [{"genre": c["genre"], "heading": c["heading"]} for c in chapter_infos],
        "judge": args.judge, "machine": args.machine or machine_string(), "started": started,
    }

    sizes = model_sizes()
    judge = Renderer(model=args.judge, verbose=False)

    rungs_by_id = {r["id"]: r for r in results["rungs"]}

    for interface in interfaces:
        for writer_name in writers:
            rung_id = f"{writer_name}|{interface}"
            rung = rungs_by_id.get(rung_id)
            if rung is None:
                rung = {"id": rung_id, "writer": writer_name, "interface": interface,
                        "size_gb": size_for(writer_name, sizes), "status": "queued",
                        "started": None, "finished": None, "chapters_done": 0,
                        "per_chapter": [], "summary": {}}
                results["rungs"].append(rung)
                rungs_by_id[rung_id] = rung

            if args.resume and rung["status"] == "done":
                print(f"[resume] {rung_id}: done, skipping", flush=True)
                continue

            rung["status"] = "running"
            rung["started"] = rung["started"] or now_iso()
            done = {(c["genre"], c["heading"]) for c in rung["per_chapter"]}
            writer = Renderer(model=writer_name, retries=2, verbose=False)

            for info in chapter_infos:
                key = (info["genre"], info["heading"])
                if key in done:
                    continue
                result, stats, seconds = render_one(writer, info, interface)
                sentences, verdicts = judge_one(judge, result["text"], info["brief"])
                rec = build_record(info, result, stats, seconds, sentences, verdicts)
                rung["per_chapter"].append(rec)
                rung["chapters_done"] = len(rung["per_chapter"])
                rung["summary"] = compute_summary(rung["per_chapter"], rung["size_gb"])
                results["updated"] = now_iso()
                atomic_write_json(results_path, results)
                lint_tag = "ok" if rec["lint_ok"] else rec["source"]
                flagged = rec["unsupported"] + rec["contradicted"]
                print(f"{rung_id}  {info['genre']}/{info['heading']}  {seconds:.1f}s  "
                      f"lint={lint_tag}  flagged={flagged}/{rec['sentences']}", flush=True)

            rung["status"] = "done"
            rung["finished"] = now_iso()
            results["updated"] = now_iso()
            atomic_write_json(results_path, results)
            s = rung["summary"]
            print(f"  == {rung_id} done: {s.get('seconds_per_chapter', 0):.1f}s/ch, "
                  f"grounded={s.get('grounded_rate', 0):.0%}, quality={s.get('quality', 0):.3f}, "
                  f"efficiency={s.get('efficiency', 0):.4f}", flush=True)

    print(f"\nwrote {results_path}")


if __name__ == "__main__":
    main()
