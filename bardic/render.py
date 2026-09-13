"""The renderer — a local model as TRANSLATOR, never author; a linter as judge.

Every chapter of every work in the library is produced the same way:

    brief   : a fact-sheet of true sentences mined from the Annals
    voice   : the register the genre asks for (epic, novel, chronicle, hymn)
    render  : the model turns the brief into prose under absolute rules
    lint    : invented numbers or proper nouns -> reject and retry
    plain   : if no model is available (or every retry fails the lint), the
              chronicler's plain prose — the brief itself, made readable —
              stands in. The library is never empty and never ungrounded.

The lint is deliberately cheap and deliberately strict: a capitalized word in
mid-sentence that is not in the brief (or the document's glossary) is an
invented person, place or god; a numeral not in the brief is an invented
fact. Coverage — how many of the brief's must-say facts made it into the
prose — is reported, not enforced.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from typing import Dict, Iterable, List, Optional, Tuple

OLLAMA = "http://localhost:11434"

# `--model auto`: the best installed translator, in order of preference. The
# 35B mixture (3B active) writes better than the 9B and is no slower here.
PREFERRED = ["qwen3.6:35b", "qwen3.6:latest", "qwen3.6:27b", "qwen3.5:9b", "qwen2.5:7b"]


def installed_models() -> List[str]:
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=5) as r:
            return [m["name"] for m in json.loads(r.read()).get("models", [])]
    except Exception:  # noqa: BLE001
        return []


def resolve_model(model: str) -> str:
    """'auto' -> the first PREFERRED model that is installed (else 'none')."""
    if model != "auto":
        return model
    have = installed_models()
    for m in PREFERRED:
        if m in have:
            return m
    return "none"

# capitalized words that are English, titles or cosmology — not inventions
COMMON = set("""
The And But When Then That For His Her She They Their One Now Yet There Not All
What Once Each From Until With Some This These Those Who Whom Whose Where Why
How Here Nor Only Even Still Though Although Because Before After While Into
Onto Over Under Above Below Between Among Through Around Again Never Always
Perhaps Maybe Indeed Thus Hence Therefore However Whatever Whenever Wherever
Nothing Something Everything Anything Nobody Someone Everyone Anyone Let Yes
No Oh Ah Lo Behold Hear Listen Remember Know See Say Sing Come Go Hold Stand
King Queen Lord Lady Mother Father Brother Sister Son Daughter Child Children
Sage Seer Elder Teacher Master Servant Witness Chronicler Bard Poet Singer
Ruler Caretaker Mystic Reformer Opportunist Brooder Wanderer Avatar
Wheel Age Ages Cycle Cycles Dawn Dusk Night Day Year Years Spring Summer
Autumn Winter Sun Moon Star Stars Earth Sky Sea River Mountain Fire Water
Wind Stone Road Path House Houses Hearth Lamp Door Wall Gate Field Village
Kingdom World Canon Song Tale Ballad Saying Hymn Lament Poem Dance Carving
Mural Book Record Annals Chronicle Satya Treta Dvapara Kali Pralaya Yuga
Dharma Karma Moksha Samsara Peace Sorrow Valor Fury Wonder Love Laughter
Dread Refusal Craving Anger Greed Attachment Pride Envy Truth Courage
Humility Compassion Discernment Unity Life Death Birth Time Fate Memory
Silence Power Scarcity Loss Success Uncertainty Grief Joy Hope Fear Shame
First Second Third Fourth Fifth Sixth Seventh Eighth Ninth Tenth Last
One Two Three Four Five Six Seven Eight Nine Ten Eleven Twelve Twenty Thirty
Forty Fifty Sixty Seventy Eighty Ninety Hundred Thousand
""".split())

_NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
              "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
              "twelve": 12}


class Renderer:
    def __init__(self, model: str = "auto", temperature: float = 0.8,
                 retries: int = 2, num_ctx: int = 8192, verbose: bool = True) -> None:
        self.model = resolve_model(model)
        self.temperature = temperature
        self.retries = retries
        self.num_ctx = num_ctx
        self.verbose = verbose
        self.calls = 0
        self.seconds = 0.0
        self.tokens = 0
        self.prompt_tokens = 0
        self.prompt_seconds = 0.0
        self.gen_seconds = 0.0
        self.last: Dict = {}
        self.first_call: Dict = {}   # this render()'s FIRST attempt only — what
                                     # the writer had to read, unpadded by retries
        self._ok: Optional[bool] = None

    # -- availability ---------------------------------------------------------
    def available(self) -> bool:
        if self.model in ("none", "plain", ""):
            return False
        if self._ok is not None:
            return self._ok
        try:
            with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=5) as r:
                names = [m["name"] for m in json.loads(r.read()).get("models", [])]
            self._ok = any(n == self.model or n.split(":")[0] == self.model.split(":")[0]
                           for n in names)
            if not self._ok and self.verbose:
                print(f"[renderer] model {self.model!r} not found in ollama; "
                      f"available: {', '.join(names)}; falling back to plain prose")
        except Exception as e:  # noqa: BLE001
            if self.verbose:
                print(f"[renderer] ollama unreachable ({e}); falling back to plain prose")
            self._ok = False
        return self._ok

    def _generate(self, prompt: str, n_predict: int, fmt: Optional[str] = None) -> str:
        payload = {"model": self.model, "prompt": prompt, "stream": False,
                  "think": False,
                  "options": {"num_predict": n_predict,
                              "temperature": self.temperature,
                              "num_ctx": self.num_ctx}}
        if fmt:
            payload["format"] = fmt   # e.g. "json" — the second reader asks for a verdict, not prose
        body = json.dumps(payload).encode()
        req = urllib.request.Request(f"{OLLAMA}/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
        t = time.time()
        with urllib.request.urlopen(req, timeout=900) as r:
            d = json.loads(r.read())
        wall = time.time() - t
        self.calls += 1
        self.seconds += wall
        self.tokens += int(d.get("eval_count") or 0)
        # ollama reports durations in nanoseconds; convert to seconds
        p_tokens = int(d.get("prompt_eval_count") or 0)
        p_seconds = (d.get("prompt_eval_duration") or 0) / 1e9
        g_seconds = (d.get("eval_duration") or 0) / 1e9
        self.prompt_tokens += p_tokens
        self.prompt_seconds += p_seconds
        self.gen_seconds += g_seconds
        self.last = {"wall_seconds": wall, "prompt_tokens": p_tokens,
                    "gen_tokens": int(d.get("eval_count") or 0),
                    "prompt_seconds": p_seconds, "gen_seconds": g_seconds}
        text = d.get("response") or ""
        if not text.strip():
            text = d.get("thinking") or ""   # some models answer in the wrong field
        return text.strip()

    # -- the contract -----------------------------------------------------------
    def render(self, voice: str, brief: List[str], words: Tuple[int, int] = (300, 450),
               glossary: Iterable[str] = (), must_say: Iterable[str] = (),
               lead: str = "", form: str = "prose", inside: bool = True,
               numbers: Iterable[str] = (), brief_for_prompt: Optional[List[str]] = None,
               legend: str = "") -> Dict:
        """Returns {text, lint, coverage, source} where source is 'model' or 'plain'.
        `glossary` and `numbers` widen the allowed sets to the whole book's record:
        a name or a number that is true anywhere in the book is not an invention.

        `brief_for_prompt` lets a caller show the model a DIFFERENT (e.g.
        terser) rendering of the same facts than the one the lint checks
        against: the prompt is built from `brief_for_prompt` (with `legend`
        inserted just before THE RECORD), but `allowed_names`/`allowed_nums`
        — and so what counts as an invention — still come from `brief`."""
        brief_text = "\n".join(f"- {line}" for line in brief)
        allowed_names = set(_proper_nouns(brief_text)) | set(glossary)
        allowed_nums = set(re.findall(r"\d+", brief_text)) | set(numbers)
        prompt_brief_text = ("\n".join(f"- {line}" for line in brief_for_prompt)
                             if brief_for_prompt is not None else brief_text)
        n_predict = int(words[1] * 1.9) + 80 if form == "prose" else int(words[1] * 16) + 80
        length = (f"Length: {words[0]}-{words[1]} words of prose. No verse, no rhyme, no "
                  "headings, no bullet points." if form == "prose" else
                  f"Form: free verse in {words[0]}-{words[1]} short lines. No rhyme, no meter, "
                  "no title, no headings.")
        prompt = (f"{voice}\n\n{length}\n\n"
                  "ABSOLUTE RULES:\n"
                  "- Every event, person, place, teaching and number MUST come from "
                  "THE RECORD below. Invent NO new events, names, places, gods, "
                  "or numbers. Do not compute new numbers from the record.\n"
                  "- You may render inner life and texture freely — what a "
                  "temptation felt like, what mastery cost, the light, the weather, "
                  "the work of hands — so long as it adds no person, place, event "
                  "or number.\n"
                  "- Use the names exactly as written. Do not add titles or epithets "
                  "that name new things.\n"
                  "- Write years, ages and counts above twelve as numerals (year 470; "
                  "at 36; 205 souls), never as words.\n"
                  "- Do not mention these rules or your task anywhere in the text.\n"
                  "- You need not use every fact; choose what this passage turns on. "
                  "But never contradict a fact, and never recite the facts as a list.\n"
                  + ("- You are inside the story. Never mention 'the record', 'the "
                     "annals', 'the tally' or 'the chronicle', and never address the "
                     "reader as a reader.\n" if inside else "")
                  + "\n"
                  + (f"WHAT CAME BEFORE (for continuity only):\n{lead}\n\n" if lead else "")
                  + (f"{legend}\n\n" if legend else "")
                  + f"THE RECORD:\n{prompt_brief_text}\n\nTHE TEXT:")
        best = None
        self.first_call = {}
        if self.available():
            for attempt in range(self.retries + 1):
                try:
                    text = self._generate(prompt, n_predict)
                except (urllib.error.URLError, TimeoutError, OSError) as e:
                    if self.verbose:
                        print(f"[renderer] call failed: {e}")
                    break
                if attempt == 0:
                    self.first_call = dict(self.last)
                text = words_to_digits(_tidy(text))
                lint = groundedness_lint(text, allowed_names, allowed_nums)
                cov = coverage(text, must_say)
                cand = {"text": text, "lint": lint, "coverage": cov, "source": "model",
                        "attempts": attempt + 1}
                if lint["ok"]:
                    return cand
                if best is None or _badness(lint) < _badness(best["lint"]):
                    best = cand
                if self.verbose:
                    print(f"[renderer] lint failed (attempt {attempt + 1}): "
                          f"names={lint['invented_names']} nums={lint['invented_numbers']}")
        if best is not None:
            # a near miss is still ungrounded: scrub the offending tokens rather
            # than publish an invention, and say so
            best["text"] = _scrub(best["text"], best["lint"])
            best["lint"] = groundedness_lint(best["text"], allowed_names, allowed_nums)
            best["source"] = "model+scrub"
            return best
        text = plain_verse(brief) if form == "verse" else plain_prose(brief)
        return {"text": text, "lint": groundedness_lint(text, allowed_names, allowed_nums),
                "coverage": coverage(text, must_say), "source": "plain", "attempts": 0}


# ---------------------------------------------------------------------------
# lint
# ---------------------------------------------------------------------------
def _proper_nouns(text: str) -> List[str]:
    return re.findall(r"[A-Z][a-z]{2,}", text)


_UNITS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
          "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
          "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
          "nineteen": 19}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
         "seventy": 70, "eighty": 80, "ninety": 90}
_NUMTOK = r"(?:" + "|".join(list(_UNITS) + list(_TENS) + ["hundred", "thousand"]) + r")"
_SPELLED = re.compile(rf"\b{_NUMTOK}(?:(?:[-\s]|\s+and\s+){_NUMTOK})*\b", re.I)


def _value(words: List[str]) -> int:
    total = cur = 0
    for w in words:
        if w in _UNITS:
            cur += _UNITS[w]
        elif w in _TENS:
            cur += _TENS[w]
        elif w == "hundred":
            cur = max(cur, 1) * 100
        elif w == "thousand":
            total += max(cur, 1) * 1000
            cur = 0
    return total + cur


def words_to_digits(text: str) -> str:
    """'thirty-one times' -> '31 times'. A number written out in words escapes a
    numeral check and is, in practice, where the arithmetic goes wrong
    ('twenty-five souls' for 205); so every spelled number above twelve is
    normalized to digits before the lint looks. Small numbers stay words."""
    def sub(m):
        words = re.split(r"[-\s]+", m.group().lower())
        words = [w for w in words if w != "and"]
        v = _value(words)
        return str(v) if v > 12 else m.group()
    return _SPELLED.sub(sub, text)


def groundedness_lint(text: str, allowed_names: set, allowed_nums: set) -> Dict:
    used_nums = set(re.findall(r"\d+", text))
    bad_nums = used_nums - allowed_nums
    bad_names = set()
    for m in re.finditer(r"[A-Z][a-z]{2,}", text):
        w = m.group()
        if w in allowed_names or w in COMMON:
            continue
        before = text[:m.start()].rstrip()
        # sentence-initial capitals are just English (also after quotes/dashes)
        if not before or before[-1] in '.!?:;*"“—\n(':
            continue
        # a possessive/plural of an allowed name is fine ("Kavindra's")
        if w.endswith("s") and w[:-1] in allowed_names:
            continue
        bad_names.add(w)
    return {"ok": not bad_nums and not bad_names,
            "invented_numbers": sorted(bad_nums), "invented_names": sorted(bad_names)}


def _badness(lint: Dict) -> int:
    return len(lint["invented_numbers"]) + len(lint["invented_names"])


def _scrub(text: str, lint: Dict) -> str:
    for w in lint["invented_names"]:
        text = re.sub(rf"\b{re.escape(w)}('s)?\b", "one whose name the record does not keep", text)
    for n in lint["invented_numbers"]:
        text = re.sub(rf"\b{n}\b", "some", text)
    return text


def coverage(text: str, must_say: Iterable[str]) -> Optional[float]:
    keys = [k for k in must_say if k]
    if not keys:
        return None
    low = text.lower()
    hit = 0
    for k in keys:
        k = k.lower()
        if k in low:
            hit += 1
        elif k.isdigit() and int(k) in _NUM_WORDS.values():
            word = next(w for w, v in _NUM_WORDS.items() if v == int(k))
            hit += 1 if re.search(rf"\b{word}\b", low) else 0
    return hit / len(keys)


def _tidy(text: str) -> str:
    text = re.sub(r"^\s*(THE (TEXT|CANTO|CHAPTER|TALE|HYMN)|Canto|Chapter)\s*[:\-—]?\s*\n", "", text)
    text = re.sub(r"^#+.*\n", "", text)                 # a heading the model added
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# the chronicler's plain prose — the fallback that is always available
# ---------------------------------------------------------------------------
def plain_verse(brief: List[str]) -> str:
    """No model: the world's own quoted lines, one per line; else the brief."""
    quoted = [l.strip().strip('"') for l in brief if l.strip().startswith('"')]
    return "\n".join(quoted) if quoted else "\n".join(brief)


def plain_prose(brief: List[str]) -> str:
    """The brief, made readable: each fact a sentence, joined into paragraphs."""
    paras, cur = [], []
    for line in brief:
        s = line.strip()
        if not s:
            continue
        if s.endswith(":"):
            if cur:
                paras.append(" ".join(cur))
                cur = []
            cur.append(s[:-1] + ".")
            continue
        s = s[0].upper() + s[1:]
        if s[-1] not in ".!?\"”":
            s += "."
        cur.append(s)
        if len(cur) >= 4:
            paras.append(" ".join(cur))
            cur = []
    if cur:
        paras.append(" ".join(cur))
    return "\n\n".join(paras)


def ordinal(n: int) -> str:
    words = ["zeroth", "first", "second", "third", "fourth", "fifth", "sixth",
             "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth"]
    return words[n] if 0 <= n < len(words) else f"{n}th"
