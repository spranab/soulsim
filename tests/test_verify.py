"""Tests for the second reader (bardic/verify.py).

No ollama here: a scripted fake renderer plays the model's part, returning
one canned reply per call in order regardless of the prompt. That's enough
to test the JSON parsing, the rewrite-or-delete repair logic, and the
classify -> repair -> reclassify wiring in `verify_chapter` — the one thing
it can't test is whether a real model's answers are any good, which is what
the smoke run against ollama is for.
"""
import json
import unittest

from bardic.verify import classify, repair, split_sentences, verify_chapter


class FakeRenderer:
    """Just enough of Renderer's surface for verify.py to work with:
    `.available()`, a mutable `.temperature` (verify.py sets it to 0.1
    around a call and restores it), and `._generate` returning the next
    canned reply."""

    def __init__(self, replies=(), available=True):
        self.replies = list(replies)
        self._available = available
        self.temperature = 0.8
        self.model = "fake"

    def available(self):
        return self._available

    def _generate(self, prompt, n_predict, fmt=None):
        if not self.replies:
            return ""
        return self.replies.pop(0)


BRIEF = [
    "Arbhani sat by the fire.",
    "Bachak is Arbhani's son.",
    "The house was quiet.",
]
# the middle sentence is exactly the kind of invention the groundedness lint
# can't see: no new name, no new number, just an event the record never had.
TEXT = "Arbhani sat by the fire. Bachak had married and moved away. The house was quiet."


class SplitSentencesTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(split_sentences(TEXT), [
            "Arbhani sat by the fire.",
            "Bachak had married and moved away.",
            "The house was quiet.",
        ])

    def test_empty(self):
        self.assertEqual(split_sentences(""), [])
        self.assertEqual(split_sentences("   "), [])

    def test_abbreviation_is_not_a_sentence_break(self):
        text = "Dr. Rao arrived. He left soon after."
        self.assertEqual(split_sentences(text),
                         ["Dr. Rao arrived.", "He left soon after."])


class ClassifyTest(unittest.TestCase):
    def test_dict_wrapping_the_list(self):
        renderer = FakeRenderer(replies=[json.dumps({"results": [
            {"i": 1, "verdict": "SUPPORTED", "why": "matches record"},
            {"i": 2, "verdict": "UNSUPPORTED", "why": "invented marriage"},
            {"i": 3, "verdict": "SUPPORTED", "why": "matches record"},
        ]})])
        verdicts = classify(split_sentences(TEXT), BRIEF, renderer)
        self.assertEqual([v["verdict"] for v in verdicts],
                         ["SUPPORTED", "UNSUPPORTED", "SUPPORTED"])
        self.assertEqual(verdicts[1]["why"], "invented marriage")

    def test_garbage_reply_defaults_to_supported_unparsed(self):
        renderer = FakeRenderer(replies=["not json at all, sorry about that"])
        verdicts = classify(split_sentences(TEXT), BRIEF, renderer)
        self.assertTrue(all(v["verdict"] == "SUPPORTED" for v in verdicts))
        self.assertTrue(all(v["why"] == "unparsed" for v in verdicts))

    def test_item_missing_its_index_only_defaults_that_one(self):
        renderer = FakeRenderer(replies=[json.dumps([
            {"i": 1, "verdict": "TEXTURE", "why": "just weather"},
            {"verdict": "CONTRADICTED", "why": "no index at all"},
        ])])
        verdicts = classify(split_sentences(TEXT), BRIEF, renderer)
        self.assertEqual(verdicts[0]["verdict"], "TEXTURE")
        self.assertEqual(verdicts[1]["why"], "unparsed")
        self.assertEqual(verdicts[2]["why"], "unparsed")


class RepairTest(unittest.TestCase):
    def test_contradicted_sentence_rewritten_in_place(self):
        renderer = FakeRenderer(replies=[json.dumps(
            [{"i": 2, "rewrite": "Bachak stayed home."}]
        )])
        flagged = [{"i": 1, "verdict": "CONTRADICTED", "why": "invented marriage"}]
        new_text = repair(TEXT, flagged, BRIEF, renderer)
        self.assertNotIn("married and moved away", new_text)
        self.assertIn("Bachak stayed home.", new_text)
        self.assertIn("Arbhani sat by the fire.", new_text)
        self.assertIn("The house was quiet.", new_text)

    def test_rewrite_failing_lint_falls_back_to_deletion(self):
        renderer = FakeRenderer(replies=[json.dumps(
            [{"i": 2, "rewrite": "She then met Zorblex by the river."}]
        )])
        flagged = [{"i": 1, "verdict": "CONTRADICTED", "why": "invented marriage"}]
        new_text = repair(TEXT, flagged, BRIEF, renderer)
        self.assertNotIn("married and moved away", new_text)
        self.assertNotIn("Zorblex", new_text)
        self.assertIn("Arbhani sat by the fire.", new_text)
        self.assertIn("The house was quiet.", new_text)


class VerifyChapterTest(unittest.TestCase):
    def test_skips_when_renderer_unavailable(self):
        renderer = FakeRenderer(available=False)
        result = verify_chapter(TEXT, BRIEF, renderer)
        self.assertEqual(result["text"], TEXT)
        self.assertEqual(result["checked"], 0)
        self.assertEqual(result["flags"], [])

    def test_end_to_end_flags_rewrites_and_clears(self):
        renderer = FakeRenderer(replies=[
            json.dumps([
                {"i": 1, "verdict": "SUPPORTED", "why": "matches record"},
                {"i": 2, "verdict": "CONTRADICTED", "why": "invented marriage"},
                {"i": 3, "verdict": "SUPPORTED", "why": "matches record"},
            ]),
            json.dumps([{"i": 2, "rewrite": "Bachak stayed home."}]),
            json.dumps([{"i": 1, "verdict": "SUPPORTED", "why": "now matches"}]),
        ])
        result = verify_chapter(TEXT, BRIEF, renderer)
        self.assertEqual(result["checked"], 3)
        self.assertEqual(result["contradicted"], 1)
        self.assertEqual(result["rewritten"], 1)
        self.assertEqual(result["deleted"], 0)
        self.assertEqual(result["remaining"], 0)
        self.assertEqual(result["parse_failures"], 0)
        self.assertIn("Bachak stayed home.", result["text"])
        self.assertNotIn("married and moved away", result["text"])
        self.assertEqual(len(result["flags"]), 1)
        self.assertEqual(result["flags"][0]["verdict"], "CONTRADICTED")


if __name__ == "__main__":
    unittest.main()
