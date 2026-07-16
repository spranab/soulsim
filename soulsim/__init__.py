"""soulsim — an agent-based cosmological simulation.

A "computational philosophy laboratory": metaphysical concepts (persistent
souls, karma, yugas, moksha) are treated as *literal mechanisms* so we can
watch what kind of world they generate.

The whole design rests on one discipline — the three-layer wall (see config.py):

    FIXED     : the ontology we assume (souls persist, karma updates, etc.)
    HYPOTHESIS: knobs we are allowed to vary and test
    MEASURED  : outcomes we observe — these must NEVER feed back into rules.

If a quantity that we measure (e.g. "compassion produced moksha") is also
hard-coded into the rules, it is not a finding. Keep the wall intact.
"""

__all__ = ["__version__"]
__version__ = "0.1.0"
