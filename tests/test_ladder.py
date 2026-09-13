"""Tests for `ladder.py` and `bardic/compact.py`.

No ollama here: `CompactTest` runs one real cosmos (seed 11, 300 years) in
setUpClass and checks the encoder against real briefs, and `SummaryTest`
feeds `ladder.compute_summary` hand-made per_chapter records — the one
thing the smoke run against ollama is for is whether a real model's prose
from the compact notation is any good.
"""
from __future__ import annotations

import re
import unittest

from soulsim.config import SimConfig, FixedRules
from soulsim.world import Universe

import bardic
from bardic import compact
from bardic.render import COMMON
from ladder import compute_summary

_PROPER = re.compile(r"[A-Z][a-z]{2,}")
_SENTENCE_INITIAL = '.!?:;*"“—\n('


def _real_names(text: str) -> set:
    """Proper nouns as `render.py`'s own groundedness lint sees them: a
    capitalized word, not a stock English/cosmology term (COMMON), and not
    sitting at the start of a sentence — the same two exemptions the lint
    grants, since a capital there is just English, not a name. Using the
    bare `[A-Z][a-z]{2,}` regex without this filter catches "They", "Why",
    "Before" and the like — real words the compact notation rightly drops
    when it throws out the scaffolding around a fact — which would make
    this a test of the scaffolding, not of the names the lint actually
    depends on."""
    names = set()
    for m in _PROPER.finditer(text):
        w = m.group()
        if w in COMMON:
            continue
        before = text[:m.start()].rstrip()
        if not before or before[-1] in _SENTENCE_INITIAL:
            continue
        names.add(w)
    return names


class CompactTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.universe = Universe(SimConfig(seed=11, years=300, initial_adults=200,
                                          rules=FixedRules(soul_count=800)))
        for _ in range(300):
            cls.universe.step()
        cls.epic = bardic.GENRES["epic"](cls.universe.annals, cls.universe)
        cls.novel = bardic.GENRES["novel"](cls.universe.annals, cls.universe)

    def _briefs(self):
        for book in (self.epic, self.novel):
            for ch in book.chapters:
                yield ch.brief

    def test_every_real_name_and_number_survives_encoding(self):
        orig_join = "\n".join("\n".join(b) for b in self._briefs())
        enc_join = "\n".join("\n".join(compact.encode(b)) for b in self._briefs())
        missing_names = _real_names(orig_join) - set(_PROPER.findall(enc_join))
        self.assertEqual(missing_names, set(), "a name the lint depends on was dropped")
        missing_nums = set(re.findall(r"\d+", orig_join)) - set(re.findall(r"\d+", enc_join))
        self.assertEqual(missing_nums, set(), "a number the lint depends on was dropped")

    def test_encoding_shrinks_the_brief(self):
        orig_join = "\n".join("\n".join(b) for b in self._briefs())
        enc_join = "\n".join("\n".join(compact.encode(b)) for b in self._briefs())
        self.assertLess(len(enc_join), 0.7 * len(orig_join),
                        f"only {len(enc_join) / len(orig_join):.0%} of the original length")

    def test_encode_is_line_for_line(self):
        for brief in self._briefs():
            with self.subTest(brief=brief[:1]):
                self.assertEqual(len(compact.encode(brief)), len(brief))

    def test_unrecognized_line_passes_through_unchanged(self):
        line = "A sentence bardic/common.py would never produce, verbatim."
        self.assertEqual(compact.encode([line]), [line])

    def test_legend_is_short(self):
        self.assertLessEqual(len(compact.LEGEND.split()), 60)

    def test_proem_lines_are_compacted(self):
        # the proem's free-text lines are the single biggest source of
        # unencoded tokens in an epic's brief (they open the book and never
        # repeat, so there's no template savings elsewhere to offset them)
        proem = self.epic.chapters[0].brief
        enc = compact.encode(proem)
        unmatched = [o for o, e in zip(proem, enc) if o == e]
        self.assertEqual(unmatched, [], f"proem lines left uncompacted: {unmatched}")


class SummaryTest(unittest.TestCase):
    """`compute_summary` on hand-made records: no ollama, no cosmos."""

    def _chapter(self, **over) -> dict:
        base = dict(seconds=10.0, attempts=1, prompt_tokens=800, gen_tokens=500,
                   prompt_eval_tps=900.0, gen_tps=45.0, lint_ok=True, lint_first_ok=True,
                   source="model", coverage=1.0, words=400, sentences=20, supported=15,
                   texture=4, unsupported=1, contradicted=0)
        base.update(over)
        return base

    def test_empty_per_chapter_is_empty_summary(self):
        self.assertEqual(compute_summary([], size_gb=22.0), {})

    def test_all_clean_chapters(self):
        chapters = [self._chapter() for _ in range(3)]
        s = compute_summary(chapters, size_gb=22.0)
        self.assertEqual(s["sentences"], 60)
        self.assertEqual(s["supported"], 45)
        self.assertEqual(s["texture"], 12)
        self.assertEqual(s["unsupported"], 3)
        self.assertAlmostEqual(s["lint_first_pass_rate"], 1.0)
        self.assertAlmostEqual(s["lint_final_pass_rate"], 1.0)
        self.assertEqual(s["retries"], 0)
        self.assertEqual(s["scrubbed"], 0)
        self.assertAlmostEqual(s["coverage"], 1.0)
        self.assertAlmostEqual(s["seconds_per_chapter"], 10.0)
        self.assertAlmostEqual(s["grounded_rate"], (45 + 12) / 60)
        self.assertAlmostEqual(s["quality"], s["grounded_rate"] * 1.0 * 1.0)
        self.assertAlmostEqual(s["efficiency"], s["quality"] / (10.0 * 22.0))

    def test_retry_and_scrub_are_counted(self):
        chapters = [
            self._chapter(attempts=1, lint_first_ok=True, lint_ok=True, source="model"),
            self._chapter(attempts=3, lint_first_ok=False, lint_ok=True, source="model"),
            self._chapter(attempts=3, lint_first_ok=False, lint_ok=False, source="model+scrub"),
        ]
        s = compute_summary(chapters, size_gb=10.0)
        self.assertEqual(s["retries"], 0 + 2 + 2)
        self.assertEqual(s["scrubbed"], 1)
        self.assertAlmostEqual(s["lint_first_pass_rate"], 1 / 3)
        self.assertAlmostEqual(s["lint_final_pass_rate"], 2 / 3)

    def test_missing_coverage_is_excluded_not_zeroed(self):
        chapters = [self._chapter(coverage=None), self._chapter(coverage=0.5)]
        s = compute_summary(chapters, size_gb=10.0)
        self.assertAlmostEqual(s["coverage"], 0.5)

    def test_zero_sentences_does_not_divide_by_zero(self):
        chapters = [self._chapter(sentences=0, supported=0, texture=0, unsupported=0,
                                  contradicted=0)]
        s = compute_summary(chapters, size_gb=10.0)
        self.assertEqual(s["grounded_rate"], 0.0)

    def test_zero_size_or_seconds_does_not_divide_by_zero(self):
        chapters = [self._chapter(seconds=0.0)]
        s = compute_summary(chapters, size_gb=10.0)
        self.assertEqual(s["efficiency"], 0.0)
        chapters = [self._chapter()]
        s = compute_summary(chapters, size_gb=0.0)
        self.assertEqual(s["efficiency"], 0.0)

    def test_partial_rung_summary_reflects_only_what_ran(self):
        s = compute_summary([self._chapter()], size_gb=22.0)
        self.assertEqual(s["sentences"], 20)


if __name__ == "__main__":
    unittest.main()
