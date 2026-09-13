"""bardic — the library of a cosmos: epic, novel, history, scripture, tales.

    THE WORLD SUPPLIES THE PLOT    (the Annals: names, houses, lives, deeds)
    THE MODEL SUPPLIES THE PROSE   (a local LLM as translator, never author)
    A VERIFIER KEEPS IT HONEST     (groundedness lint; the record appended)

Nothing here is ever read by physics.
"""
from . import epic, novel, history, scripture, tales  # noqa: F401
from . import saga, upanishad, letters  # noqa: F401
from .book import Book, Chapter, compile_book  # noqa: F401
from .render import Renderer  # noqa: F401

GENRES = {"epic": epic.build, "novel": novel.build, "history": history.build,
          "scripture": scripture.build, "tales": tales.build,
          "saga": saga.build, "upanishad": upanishad.build, "letters": letters.build}
