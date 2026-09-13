"""A book: chapters of (heading, brief) rendered into one markdown document.

The document carries its own audit: every chapter's fact-sheet is appended in
'The Record', and a groundedness table says for each chapter whether the model
wrote it, whether the lint passed, and what fraction of the must-say facts
made it into the prose. A reader can check any sentence against the record.
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .render import Renderer


@dataclass
class Chapter:
    heading: str
    brief: List[str]
    voice: str
    words: Tuple[int, int] = (300, 450)
    must_say: List[str] = field(default_factory=list)
    form: str = "prose"          # prose | verse
    part: Optional[str] = None   # a part/book heading emitted before this chapter
    table: Optional[str] = None  # markdown appended after the prose (numbers live here)
    result: Optional[Dict] = None


@dataclass
class Book:
    title: str
    subtitle: str
    epigraph: str
    chapters: List[Chapter]
    glossary: Set[str] = field(default_factory=set)
    slug: str = "book"
    colophon: str = ""
    inside: bool = True          # the narrator is inside the world (not the witness)


def load_prior(out_dir: str, slug: str) -> Dict[str, Dict]:
    """Results of an earlier compile of the same book, keyed by chapter heading."""
    path = os.path.join(out_dir, f"{slug}.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return {c["heading"]: c for c in json.load(f).get("chapters", [])}
    except (OSError, ValueError, KeyError):
        return {}


def compile_book(book: Book, renderer: Renderer, out_dir: str, verbose: bool = True,
                 prior: Optional[Dict[str, Dict]] = None) -> str:
    """Render every chapter and write the book. With `prior` (a load_prior()
    result), chapters the model already wrote cleanly are kept and only the
    scrubbed or plain ones are rendered again — a repair pass."""
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    lead = ""
    # any number true anywhere in this book's record is not an invention
    book_numbers = set(re.findall(r"\d+", "\n".join(l for c in book.chapters for l in c.brief)))
    for i, ch in enumerate(book.chapters):
        old = (prior or {}).get(ch.heading)
        if old and old.get("brief") == ch.brief and old.get("result", {}).get("source") == "model" \
                and old["result"].get("lint", {}).get("ok"):
            ch.result = old["result"]
            if verbose:
                print(f"  [{book.slug}] {i + 1}/{len(book.chapters)} {ch.heading} (kept)", flush=True)
        else:
            if verbose:
                print(f"  [{book.slug}] {i + 1}/{len(book.chapters)} {ch.heading} ...", flush=True)
            ch.result = renderer.render(ch.voice, ch.brief, words=ch.words, glossary=book.glossary,
                                        must_say=ch.must_say, form=ch.form, inside=book.inside,
                                        lead=lead if ch.form == "prose" else "",
                                        numbers=book_numbers)
        # continuity for the next chapter: this chapter's facts, compressed
        lead = " ".join(ch.brief[:3])[:600]
    md = render_markdown(book)
    path = os.path.join(out_dir, f"{book.slug}.md")
    with open(path, "w") as f:
        f.write(md)
    with open(os.path.join(out_dir, f"{book.slug}.json"), "w") as f:
        json.dump({"title": book.title, "chapters": [
            {"heading": c.heading, "brief": c.brief, "must_say": c.must_say,
             "result": c.result} for c in book.chapters]}, f, indent=1)
    if verbose:
        print(f"  wrote {path} ({len(md) // 1024} KB, {time.time() - t0:.0f}s)")
    return path


def render_markdown(book: Book) -> str:
    out = [f"# {book.title}", "", f"*{book.subtitle}*", ""]
    if book.epigraph:
        out += [f"> {book.epigraph}", ""]
    out += ["## Contents", ""]
    for c in book.chapters:
        if c.part:
            out.append(f"- **{c.part}**")
        out.append(f"  - {c.heading}" if c.part is not None or True else f"- {c.heading}")
    out.append("")
    for c in book.chapters:
        if c.part:
            out += [f"# {c.part}", ""]
        out += [f"## {c.heading}", ""]
        text = c.result["text"] if c.result else ""
        if c.form == "verse":
            out += ["> " + l if l.strip() else ">" for l in text.split("\n")]
        else:
            out.append(text)
        out.append("")
        if c.table:
            out += [c.table, ""]
    if book.colophon:
        out += ["---", "", book.colophon, ""]
    # -- the audit ---------------------------------------------------------
    out += ["---", "", "## The Record", "",
            "*Every chapter above was rendered from the fact-sheet below and nothing "
            "else. Where the model's prose failed the groundedness lint after every "
            "retry, the offending names or numbers were scrubbed; where no model was "
            "available, the chronicler's plain prose stands in.*", ""]
    for c in book.chapters:
        out += [f"<details><summary><b>{c.heading}</b></summary>", ""]
        out += [f"- {line}" for line in c.brief]
        out += ["", "</details>", ""]
    out += ["## Groundedness", "", "| chapter | written by | lint | facts kept |", "|---|---|---|---|"]
    for c in book.chapters:
        r = c.result or {}
        lint = r.get("lint", {})
        flag = "pass" if lint.get("ok") else ("scrubbed: " + ", ".join(
            lint.get("invented_names", []) + lint.get("invented_numbers", [])) or "fail")
        cov = r.get("coverage")
        cov_s = "—" if cov is None else f"{cov:.0%}"
        out.append(f"| {c.heading} | {r.get('source', '—')} | {flag} | {cov_s} |")
    out.append("")
    return "\n".join(out)
