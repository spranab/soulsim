"""The second reader — a judge, not an author, checking the translator's work.

`render.py`'s lint catches an invented NAME or an invented NUMBER: cheap,
mechanical, and blind to everything else. It will wave through a sentence
that says a daughter "had married and moved away" when the record never
married her to anyone — no new proper noun, no new digit, just a fact that
does not exist. That is the hole this module closes.

The method is the same division of labor as `render.py`: the model is asked
to grade its own sentence against THE RECORD, one verdict per sentence
(SUPPORTED / TEXTURE / UNSUPPORTED / CONTRADICTED), and anything flagged is
rewritten — or, failing that, deleted — never left standing. Interiority,
weather, the work of hands: all allowed and unpenalized (TEXTURE). A
concrete event, relationship, deed, place or number the record does not
carry: not allowed (UNSUPPORTED), and worse if it conflicts outright
(CONTRADICTED).

If the model can't be reached, nothing here runs — the chapter stands as
rendered, same as it always did.
"""
from __future__ import annotations

import json
import re
import urllib.error
from typing import Dict, Iterable, List, Optional, Tuple
from collections import Counter

from .render import Renderer, groundedness_lint

_VERDICTS = {"SUPPORTED", "TEXTURE", "UNSUPPORTED", "CONTRADICTED"}
_FLAGGED = {"UNSUPPORTED", "CONTRADICTED"}
# the fields the record actually has; a flagged sentence must name one, or it
# is texture by construction (the test applied structurally, not by persuasion)
_FIELDS = {"birth", "death", "bond", "child", "test", "deed", "work", "teaching",
           "place", "number", "reunion", "house", "role", "age", "year", "liberation"}

_ABBR = {"mr", "mrs", "ms", "dr", "st", "sr", "jr", "vs", "etc", "no", "ft", "rev"}
_BOUNDARY = re.compile(r'[.!?]+[\"”’\)\]]*\s+')


# ---------------------------------------------------------------------------
# sentence splitting — cheap, reversible: "".join(tokenize(text)) == text
# ---------------------------------------------------------------------------
def _ends_in_abbr(chunk: str) -> bool:
    m = re.search(r'\b([A-Za-z]+)\.$', chunk.rstrip())
    return bool(m) and m.group(1).lower() in _ABBR


def _tokenize(text: str) -> List[str]:
    """Cut prose into chunks, each a sentence plus the whitespace that
    followed it (a paragraph break included), so the chunks rejoin to the
    exact original text. A trailing abbreviation ("Dr.", "etc.") is merged
    back into its chunk rather than treated as a sentence end."""
    chunks: List[str] = []
    pos = 0
    for m in _BOUNDARY.finditer(text):
        chunks.append(text[pos:m.end()])
        pos = m.end()
    if pos < len(text):
        chunks.append(text[pos:])
    out: List[str] = []
    for c in chunks:
        if out and _ends_in_abbr(out[-1]):
            out[-1] += c
        else:
            out.append(c)
    return out


def split_sentences(text: str) -> List[str]:
    """Prose -> sentences. Verse is not prose: a verse chapter's "sentences"
    are its lines, and the caller (`verify_chapter`) passes those directly
    rather than calling this."""
    if not text or not text.strip():
        return []
    return [c.strip() for c in _tokenize(text) if c.strip()]


def _units_for(text: str, form: str) -> List[str]:
    """The raw, reconstructable pieces of the chapter: lines for verse
    (blank lines are stanza breaks and are kept), sentence-chunks for
    prose."""
    return text.split("\n") if form == "verse" else _tokenize(text)


def _content_positions(units: List[str]) -> List[int]:
    """Which units are non-blank, i.e. which ones classify() actually sees."""
    return [i for i, u in enumerate(units) if u.strip()]


def _sentences_for(text: str, form: str) -> List[str]:
    units = _units_for(text, form)
    return [units[i].strip() for i in _content_positions(units)]


# ---------------------------------------------------------------------------
# loose JSON parsing — the model is a judge here, not a JSON printer
# ---------------------------------------------------------------------------
def _loads_loose(reply: str):
    try:
        return json.loads(reply)
    except ValueError:
        pass
    for pat in (r"\[.*\]", r"\{.*\}"):
        m = re.search(pat, reply, re.S)
        if m:
            try:
                return json.loads(m.group())
            except ValueError:
                continue
    return None


def _parse_json_items(reply: str) -> List[Dict]:
    """A list of dicts, tolerating a dict that wraps the list under some
    key, a dict keyed by index, a single bare dict, or garbage. Never
    raises; garbage yields an empty list."""
    data = _loads_loose(reply.strip()) if reply else None
    if data is None:
        return []
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                data = v
                break
        else:
            data = [data] if "verdict" in data or "rewrite" in data else list(data.values())
    if not isinstance(data, list):
        return []
    return [d for d in data if isinstance(d, dict)]


# ---------------------------------------------------------------------------
# the judge call — always at low temperature, restored afterward
# ---------------------------------------------------------------------------
# `fmt="json"` sounds like the safer choice for a call that must return JSON,
# and `_generate` supports it, but measured against the real model it back-
# fires: under ollama's grammar-constrained decoding, qwen3.6:35b reliably
# (not occasionally — every retry, same seed-of-temperature) closes the very
# first {"i": 1, ...} object and stops, treating one object as a complete
# answer, on any prompt with enough surrounding instruction to make the
# schema ambiguous — which a careful verdict rubric always is. Freeform text
# with an explicit "return a JSON array" instruction does not have this
# failure mode and reliably returns the whole array; `_parse_json_items`
# already tolerates the odd stray sentence around it. So the default here is
# None, not "json" — a judgment call from measurement, not the spec's first
# guess. `fmt` stays available for a future model where the reverse holds.
def _judge(renderer: Renderer, prompt: str, n_predict: int, fmt: Optional[str] = None) -> str:
    orig = renderer.temperature
    renderer.temperature = 0.1
    try:
        return renderer._generate(prompt, n_predict, fmt)
    except (urllib.error.URLError, TimeoutError, OSError):
        return ""
    finally:
        renderer.temperature = orig


# ---------------------------------------------------------------------------
# classify
# ---------------------------------------------------------------------------
# UNSUPPORTED/CONTRADICTED are for a CHECKABLE FACT OF RECORD TYPE only: a
# named person doing or suffering a dated or specific thing (a birth, death,
# bond, child, deed seen by others, journey, marriage, quarrel with a named
# person), a relationship between named people, a place other than the
# houses, a number, a teaching's content, or the outcome of a test (mastered
# vs chose the worse). Everything else — gesture, drumbeat, weather, an
# imagined voice, a feeling, a hypothetical, a quotation of a line the
# record already gives — is TEXTURE. Getting this line right is the whole
# point: too loose and invented events slip through; too strict and the
# second reader edits the art out of the prose.
_CLASSIFY_RUBRIC = (
    "Grade EVERY sentence with exactly one verdict. UNSUPPORTED and "
    "CONTRADICTED apply ONLY to a CHECKABLE FACT OF RECORD TYPE: a named "
    "person doing or suffering a dated or specific thing (a birth, death, "
    "bond, child, deed seen by others, journey, marriage, quarrel with a "
    "named person), a relationship between named people, a place other "
    "than the houses, a number, a teaching's content, or the outcome of a "
    "test (mastered vs chose the worse). Everything else — a gesture, a "
    "drumbeat, weather, an imagined voice, a feeling, a hypothetical, a "
    "quotation of a line already in the record — is TEXTURE, not "
    "UNSUPPORTED, no matter how specific it sounds.\n"
    "SUPPORTED - states or rephrases a fact in the record.\n"
    "TEXTURE - allowed color, no record-type fact. This includes ordinary, "
    "unremarkable movement or household motion by a named person (walking, "
    "sitting, moving about a room, closing one's eyes) and any statement of "
    "intention, habit, or what someone 'would' do — those are not deeds "
    "seen by others unless the record itself names the deed. Examples: "
    "'She struck the first beat.' -> TEXTURE. 'The rhythm quickened.' -> "
    "TEXTURE. 'They would speak.' -> TEXTURE. 'It felt like love, though "
    "she knew better.' -> TEXTURE. 'Her mother moved about the room, her "
    "footsteps soft.' -> TEXTURE (ordinary motion, not a deed). 'They "
    "would prepare food and mend clothes.' -> TEXTURE (a habit or "
    "intention, not a recorded event).\n"
    "UNSUPPORTED - a record-type fact the record does not contain. "
    "Example: 'Irmumala had married and moved away.' -> UNSUPPORTED (a "
    "marriage and a departure are record-type facts the record has "
    "neither of).\n"
    "CONTRADICTED - conflicts with the record (wrong person did it, wrong "
    "year or age, someone dead is alive, wrong sex, etc). Example: 'Jade, "
    "still living, embraced her.' when the record has Jade dead -> "
    "CONTRADICTED.\n"
    "THE ONE TEST: ask whether the record would have a FIELD for the "
    "sentence's content if it were true. The record keeps only births, "
    "deaths, bonds and how they ended, children, the tests a person faced "
    "and their outcomes, deeds seen by witnesses, works composed, teachings "
    "spoken, houses, years and ages. Appearance, chores, posture, tone of "
    "voice, what a room looked like, what someone felt or wanted — none of "
    "these has a field, so they are TEXTURE even when a named person is "
    "doing them. Examples: 'Lapra's eyes were red-rimmed from years of sun.' "
    "-> TEXTURE. 'Dubha sat by the hearth sharpening a blade.' -> TEXTURE. "
    "'Tapaguni stared at her hands.' -> TEXTURE. 'She refused it.' -> "
    "TEXTURE unless 'it' is a recorded test. UNSUPPORTED only when the "
    "record WOULD have a field for it and does not (a marriage, a death, a "
    "child, a journey to a named place, a deed before witnesses, a teaching, "
    "a quarrel or reunion with a named person, a test outcome).\n"
    "When in doubt, prefer TEXTURE over UNSUPPORTED, and SUPPORTED over "
    "either.\n"
)


def _classify_prompt(brief_text: str, numbered: str) -> str:
    return (
        "THE RECORD (the only facts that are true):\n" + brief_text + "\n\n"
        "Below are numbered sentences from a chapter written from that record.\n"
        + _CLASSIFY_RUBRIC + "\n"
        f"SENTENCES:\n{numbered}\n\n"
        'Return ONLY one JSON object of this exact shape: {"verdicts": '
        '[{"i": 1, "verdict": "SUPPORTED", "field": "none", "why": "five words or fewer"}, '
        '...]}. One entry per sentence above. "field" is the record field the '
        "sentence's fact would live in — one of birth, death, bond, child, test, "
        'deed, work, teaching, place, number, reunion, house, role, age, year, '
        'liberation — or "none" if no field could hold it (then the verdict '
        "cannot be UNSUPPORTED or CONTRADICTED). No text outside the object."
    )


def _classify_batch(renderer: Renderer, brief_text: str, chunk: List[str],
                    positions: List[int]) -> Dict[int, Dict]:
    """One classify call. `chunk[j]` is sentence `positions[j]` in the
    caller's full list; returns {that absolute position: verdict dict}."""
    numbered = "\n".join(f"{j + 1}. {s}" for j, s in enumerate(chunk))
    n_predict = 70 * len(chunk) + 150
    reply = _judge(renderer, _classify_prompt(brief_text, numbered), n_predict, fmt="json")
    found: Dict[int, Dict] = {}
    for item in _parse_json_items(reply):
        idx = item.get("i")
        if not isinstance(idx, int):
            continue
        local = idx - 1
        if not (0 <= local < len(chunk)):
            continue
        verdict = str(item.get("verdict", "")).strip().upper()
        if verdict not in _VERDICTS:
            continue
        raw_field = item.get("field")
        field = str(raw_field).strip().lower() if raw_field is not None else ""
        why = str(item.get("why", ""))[:120]
        if verdict in _FLAGGED and raw_field is not None and field not in _FIELDS:
            # the model named no record field that could hold it: texture by
            # construction (a reply that omits the key altogether is kept as is)
            verdict, why = "TEXTURE", f"no record field ({why})"[:120]
        pos = positions[local]
        found[pos] = {"i": pos, "verdict": verdict, "field": field, "why": why}
    return found


def classify(sentences: List[str], brief: List[str], renderer: Renderer, batch: int = 8) -> List[Dict]:
    """Grade every sentence against THE RECORD. Returns one dict per
    sentence, in order: {"i": <index into `sentences`>, "verdict": ...,
    "why": ...}. A batch that comes back short is re-asked once, for the
    missing indices only; anything still missing after that — a garbled
    index, a reply that never parsed — defaults to SUPPORTED with
    why="unparsed", and the caller counts those as parse failures."""
    out: List[Optional[Dict]] = [None] * len(sentences)
    if sentences and renderer.available():
        brief_text = "\n".join(f"- {line}" for line in brief)
        for start in range(0, len(sentences), max(1, batch)):
            positions = list(range(start, min(start + batch, len(sentences))))
            chunk = [sentences[p] for p in positions]
            for pos, v in _classify_batch(renderer, brief_text, chunk, positions).items():
                out[pos] = v
            missing = [p for p in positions if out[p] is None]
            if missing:
                retry_chunk = [sentences[p] for p in missing]
                for pos, v in _classify_batch(renderer, brief_text, retry_chunk, missing).items():
                    out[pos] = v
    return [out[i] or {"i": i, "verdict": "SUPPORTED", "why": "unparsed"} for i in range(len(sentences))]


# ---------------------------------------------------------------------------
# repair
# ---------------------------------------------------------------------------
def _tidy_rewrite(s: str) -> str:
    s = s.strip()
    s = re.sub(r'^[\"“]+|[\"”]+$', "", s).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _rewrite_prompt(brief_text: str, blocks: str) -> str:
    return (
        "THE RECORD (the only facts that are true):\n" + brief_text + "\n\n"
        "Each SENTENCE below was flagged against the record. Rewrite ONLY the "
        "flagged sentence so it says nothing the record does not say: one or "
        "two plain sentences, no new names, places, relationships, or numbers, "
        "fitting naturally between 'before' and 'after'. Do not mention the "
        "record, the rules, or your task.\n\n" + blocks + "\n"
        'Return ONLY one JSON object of this exact shape: {"rewrites": '
        '[{"i": 3, "rewrite": "..."}, ...]}. One entry per SENTENCE number '
        'above. No text outside the object.'
    )


def _batch_rewrite(flagged: List[Dict], sentences: List[str], brief_text: str,
                   renderer: Renderer) -> Dict[int, str]:
    """One call for the whole chapter's flagged sentences. Sentence numbers
    shown to the model are 1-based (matching `classify`'s prompt); the
    returned dict is keyed back to `sentences`' own 0-based indices."""
    if not renderer.available():
        return {}
    blocks = []
    for item in flagged:
        i = item["i"]
        if not (0 <= i < len(sentences)):
            continue
        before = sentences[i - 1] if i > 0 else "(start of chapter)"
        after = sentences[i + 1] if i + 1 < len(sentences) else "(end of chapter)"
        blocks.append(
            f"SENTENCE {i + 1} [{item.get('verdict')}: {item.get('why', '')}]\n"
            f"before: {before}\nflagged: {sentences[i]}\nafter: {after}\n"
        )
    if not blocks:
        return {}
    n_predict = 120 * len(blocks) + 150
    reply = _judge(renderer, _rewrite_prompt(brief_text, "\n".join(blocks)), n_predict, fmt="json")
    out: Dict[int, str] = {}
    for item in _parse_json_items(reply):
        i, rw = item.get("i"), item.get("rewrite")
        if isinstance(i, int) and isinstance(rw, str) and rw.strip():
            out[i - 1] = rw
    return out


def _single_rewrite(item: Dict, sentence: str, before: str, after: str,
                    brief_text: str, renderer: Renderer) -> str:
    if not renderer.available():
        return ""
    prompt = (
        "THE RECORD (the only facts that are true):\n" + brief_text + "\n\n"
        f"This sentence was flagged {item.get('verdict')} ({item.get('why', '')}):\n"
        f"\"{sentence}\"\n\nIt sits between:\nbefore: {before}\nafter: {after}\n\n"
        "Rewrite ONLY this sentence so it says nothing beyond the record: one or "
        "two plain sentences, no new names, places, relationships, or numbers, "
        "fitting naturally between 'before' and 'after'. Reply with the "
        "rewritten sentence ONLY — no quotes, no preamble, nothing else."
    )
    reply = _judge(renderer, prompt, 150, fmt=None)
    return reply


def repair(text: str, flagged: List[Dict], brief: List[str], renderer: Renderer,
          glossary: Iterable[str] = (), numbers: Iterable[str] = (),
          form: str = "prose") -> str:
    """Rewrite (or, failing the lint, delete) every flagged sentence, in
    place. `flagged` is a list of {"i", "verdict", "why"} — the indices
    `classify()` produced against `split_sentences(text)` (or, for verse,
    against the chapter's lines)."""
    return _repair_detailed(text, flagged, brief, renderer, glossary, numbers, form)[0]


def _repair_detailed(text: str, flagged: List[Dict], brief: List[str], renderer: Renderer,
                     glossary: Iterable[str] = (), numbers: Iterable[str] = (),
                     form: str = "prose") -> Tuple[str, List[Dict]]:
    # defense in depth: TEXTURE is allowed color, never grounds for a
    # rewrite or a deletion, even if something upstream mislabels a
    # sentence as "flagged" without checking its verdict first.
    flagged = [f for f in flagged if f.get("verdict") in _FLAGGED]
    if not flagged:
        return text, []
    units = _units_for(text, form)
    positions = _content_positions(units)
    sentences = [units[p].strip() for p in positions]
    brief_text = "\n".join(f"- {line}" for line in brief)
    allowed_names = set(re.findall(r"[A-Z][a-z]{2,}", brief_text)) | set(glossary)
    allowed_nums = set(re.findall(r"\d+", brief_text)) | set(numbers)

    rewrites = _batch_rewrite(flagged, sentences, brief_text, renderer)
    for item in flagged:
        i = item["i"]
        if i in rewrites or not (0 <= i < len(sentences)):
            continue
        before = sentences[i - 1] if i > 0 else "(start of chapter)"
        after = sentences[i + 1] if i + 1 < len(sentences) else "(end of chapter)"
        rw = _single_rewrite(item, sentences[i], before, after, brief_text, renderer)
        if rw.strip():
            rewrites[i] = rw

    live: List[Optional[str]] = list(units)
    outcomes: List[Dict] = []
    for item in flagged:
        i = item["i"]
        if not (0 <= i < len(sentences)):
            continue
        pos = positions[i]
        original = sentences[i]
        new_text = _tidy_rewrite(rewrites.get(i, ""))
        ok = bool(new_text) and groundedness_lint(new_text, allowed_names, allowed_nums)["ok"]
        if ok:
            if form == "verse":
                live[pos] = new_text
            else:
                unit = units[pos]
                lead = unit[:len(unit) - len(unit.lstrip())]
                trail = unit[len(unit.rstrip()):]
                live[pos] = lead + new_text + trail
            outcomes.append({"i": i, "sentence": original, "verdict": item.get("verdict"),
                             "why": item.get("why"), "outcome": "rewritten", "text": new_text})
        else:
            live[pos] = None
            outcomes.append({"i": i, "sentence": original, "verdict": item.get("verdict"),
                             "why": item.get("why"), "outcome": "deleted", "text": ""})
    kept = [u for u in live if u is not None]
    new_text = "\n".join(kept) if form == "verse" else "".join(kept)
    return new_text, outcomes


# ---------------------------------------------------------------------------
# verify_chapter — the entry point book.py calls
# ---------------------------------------------------------------------------
def verify_chapter(text: str, brief: List[str], renderer: Renderer, form: str = "prose",
                   glossary: Iterable[str] = (), numbers: Iterable[str] = (),
                   max_rounds: int = 1) -> Dict:
    """Read every sentence against the record; rewrite or delete what
    doesn't belong; read the rewrites once more to see what still doesn't.
    No model available -> nothing happens, text passes through unchanged."""
    empty = {"text": text, "checked": 0, "supported": 0, "texture": 0, "unsupported": 0,
            "contradicted": 0, "rewritten": 0, "deleted": 0, "remaining": 0,
            "parse_failures": 0, "flags": []}
    if not renderer.available():
        return empty

    current = text
    checked = supported = texture = unsupported = contradicted = 0
    rewritten = deleted = remaining = parse_failures = 0
    flags_report: List[Dict] = []

    for round_i in range(max(1, max_rounds)):
        sentences = _sentences_for(current, form)
        if not sentences:
            break
        verdicts = classify(sentences, brief, renderer)
        parse_failures += sum(1 for v in verdicts if v["why"] == "unparsed")
        if round_i == 0:
            checked = len(sentences)
            tally = Counter(v["verdict"] for v in verdicts)
            supported, texture = tally.get("SUPPORTED", 0), tally.get("TEXTURE", 0)
            unsupported, contradicted = tally.get("UNSUPPORTED", 0), tally.get("CONTRADICTED", 0)
        flagged = [dict(v, sentence=sentences[v["i"]]) for v in verdicts if v["verdict"] in _FLAGGED]
        if not flagged:
            remaining = 0
            break
        if round_i == 0:
            flags_report = [{"sentence": f["sentence"], "verdict": f["verdict"],
                             "why": f.get("why", "")} for f in flagged]

        new_text, outcomes = _repair_detailed(current, flagged, brief, renderer,
                                              glossary=glossary, numbers=numbers, form=form)
        rewritten += sum(1 for o in outcomes if o["outcome"] == "rewritten")
        deleted += sum(1 for o in outcomes if o["outcome"] == "deleted")
        current = new_text

        redo = [o["text"] for o in outcomes if o["outcome"] == "rewritten"]
        if not redo:
            remaining = 0
            break
        re_verdicts = classify(redo, brief, renderer)
        parse_failures += sum(1 for v in re_verdicts if v["why"] == "unparsed")
        remaining = sum(1 for v in re_verdicts if v["verdict"] in _FLAGGED)
        if remaining == 0:
            break

    return {"text": current, "checked": checked, "supported": supported, "texture": texture,
            "unsupported": unsupported, "contradicted": contradicted, "rewritten": rewritten,
            "deleted": deleted, "remaining": remaining, "parse_failures": parse_failures,
            "flags": flags_report}
