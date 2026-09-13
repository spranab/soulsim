"""Tests for the three new genre compilers: saga, upanishad, letters.

Two cosmoi are run once in setUpClass: a modest one (seed 11, 300 years) big
enough to exercise every selection rule, and a tiny one (seed 3, 120 years)
meant only to prove the fallback paths don't raise when the record is thin —
few or no reunions, few or no seers with a real household to teach.

No ollama here and none needed: these tests are about the BRIEFS the
compilers hand to the renderer, not the prose a model would make of them.
"""
from __future__ import annotations

import re
import unittest

from soulsim.config import SimConfig, FixedRules
from soulsim.world import Universe

import bardic
from bardic.book import Book

DECIMAL_RE = re.compile(r"\d\.\d")
SANSKRIT_RE = re.compile(
    r"\b(?:kama|krodha|lobha|moha|mada|matsarya|raudra|karuna|shanta|vira|"
    r"adbhuta|shringara|hasya|bhayanaka|bibhatsa)\b", re.IGNORECASE)

GENRES = ("saga", "upanishad", "letters")


def _run(seed: int, years: int, adults: int, souls: int) -> Universe:
    u = Universe(SimConfig(seed=seed, years=years, initial_adults=adults,
                           rules=FixedRules(soul_count=souls)))
    for _ in range(years):
        u.step()
    return u


class GenresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.universe = _run(seed=11, years=300, adults=200, souls=800)
        cls.tiny = _run(seed=3, years=120, adults=120, souls=400)

    # -- shape and groundedness, on the real cosmos --------------------------
    def _book_for(self, genre: str) -> Book:
        return bardic.GENRES[genre](self.universe.annals, self.universe)

    def test_books_have_at_least_three_chapters(self):
        for genre in GENRES:
            with self.subTest(genre=genre):
                book = self._book_for(genre)
                self.assertGreaterEqual(len(book.chapters), 3,
                                        f"{genre}: too few chapters")

    def test_every_brief_is_non_empty(self):
        for genre in GENRES:
            book = self._book_for(genre)
            for ch in book.chapters:
                with self.subTest(genre=genre, chapter=ch.heading):
                    self.assertTrue(ch.brief, "empty brief")
                    for line in ch.brief:
                        self.assertTrue(line and line.strip(), "blank brief line")

    def test_no_decimal_numbers_in_briefs(self):
        for genre in GENRES:
            book = self._book_for(genre)
            for ch in book.chapters:
                for line in ch.brief:
                    with self.subTest(genre=genre, chapter=ch.heading, line=line):
                        self.assertIsNone(DECIMAL_RE.search(line),
                                          f"decimal number leaked into brief: {line!r}")

    def test_no_raw_sanskrit_enemy_or_rasa_tokens_in_briefs(self):
        for genre in GENRES:
            book = self._book_for(genre)
            for ch in book.chapters:
                for line in ch.brief:
                    with self.subTest(genre=genre, chapter=ch.heading, line=line):
                        self.assertIsNone(SANSKRIT_RE.search(line),
                                          f"raw Sanskrit token leaked into brief: {line!r}")

    def test_every_must_say_appears_in_its_own_brief(self):
        for genre in GENRES:
            book = self._book_for(genre)
            for ch in book.chapters:
                joined = "\n".join(ch.brief)
                for word in ch.must_say:
                    with self.subTest(genre=genre, chapter=ch.heading, must_say=word):
                        self.assertIn(word, joined)

    def test_letters_part_one_letters_name_each_other(self):
        book = self._book_for("letters")
        idx = [i for i, c in enumerate(book.chapters)
              if c.part == "Part I — The Earlier Life"]
        # Part I is written only when both earlier bodies are known; if the
        # strongest reunion found didn't have both, there is none — the rest
        # of the book (Part II, Part III) still stands on its own.
        if not idx:
            self.skipTest("no Part I in this record (no reunion with both earlier lives)")
        letter_1, letter_2 = book.chapters[idx[0]], book.chapters[idx[0] + 1]
        name_1, name_2 = letter_1.must_say[0], letter_1.must_say[1]
        self.assertIn(name_2, "\n".join(letter_1.brief),
                     f"{name_1}'s letter never names {name_2}")
        self.assertIn(name_1, "\n".join(letter_2.brief),
                     f"{name_2}'s letter never names {name_1}")

    # -- fallback paths: must not raise on a thin record ----------------------
    def test_builders_do_not_raise_on_tiny_cosmos(self):
        for genre in GENRES:
            with self.subTest(genre=genre):
                book = bardic.GENRES[genre](self.tiny.annals, self.tiny)
                self.assertIsInstance(book, Book)
                self.assertIsInstance(book.chapters, list)


if __name__ == "__main__":
    unittest.main()
