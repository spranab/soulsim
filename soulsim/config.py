"""The three-layer wall.

Everything the simulation needs to know is split into three dataclasses so
that we never accidentally bake a conclusion into a rule.

  FixedRules   — the ontology. Changing these changes *what universe this is*.
  Hypotheses   — the tunable knobs. These are what an experiment varies.
  MeasuredKeys — a registry of the things we are allowed to observe. It exists
                 only as documentation/assertion: measured quantities must not
                 be read by any rule or hypothesis during a run.

A rule of thumb while editing: if you find yourself importing a Measured value
inside decision.py / karma.py / soul.py, stop — you are drilling a hole in the
wall.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


# --------------------------------------------------------------------------
# LAYER 1 — FIXED RULES (the ontology of this universe)
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class FixedRules:
    # Soul ontology
    soul_count: int = 1000          # jivas present at the first dawn of creation
    # Saṃsāra is beginningless and effectively inexhaustible: prakṛti keeps
    # manifesting NEW jivas at the base of the yoni ladder, so the wheel never
    # empties even as a few souls liberate. Turn this off to study a closed,
    # finite soul-economy (which *does* eventually drain — non-canonical).
    create_new_souls: bool = True

    # Pralaya: at the end of each mahayuga (Kali -> next Satya) the manifest world
    # dissolves and a new Satya dawns. Unliberated souls are NOT destroyed and do
    # NOT attain moksha at pralaya — their karma is preserved and they re-manifest
    # (BG 8.18-19). This is what makes the cosmos eternally recurring.
    pralaya_at_mahayuga: bool = True

    # Where the liberated go. The merge into the substrate ALWAYS happens (their
    # refinement enriches the ground future souls are born from). This switch is
    # the school disagreement: True = Vishishtadvaita — a liberated soul also keeps
    # its individuality and may FREELY descend as an avatar when dharma collapses;
    # False = Advaita — individuality dissolves into the ground and does not return.
    avatar_return: bool = True

    # Moksha (the pass / exit criterion) -----------------------------------
    # A soul exits the simulation when it reaches optimum across its dimensions
    # AND has been tested across every hardship condition. Breadth is required
    # so that an "easy life" cannot buy liberation.
    virtue_threshold: float = 0.90        # every core virtue must clear this
    instability_threshold: float = 0.12   # every instability must be below this
    robustness_threshold: float = 0.85    # every robustness dimension must clear
    min_tests_per_condition: int = 6      # must have faced each condition >= N times
    # v2 — EFFORTLESSNESS: liberation is transformation, not suppression. A soul
    # still white-knuckling vetoes against unaligned impulses is winning, not
    # free. Its recent FIRST impulses must themselves be mostly aligned.
    compulsion_threshold: float = 0.15    # EWMA of "dominant impulse was unaligned"

    # Time
    step_years: int = 1

    # Reproduction / lifespan floor / ceiling (biological givens)
    adult_age: int = 16
    max_age: int = 110
    base_longevity_years: float = 70.0


# --------------------------------------------------------------------------
# LAYER 2 — HYPOTHESES (the knobs an experiment is allowed to turn)
# --------------------------------------------------------------------------
@dataclass
class Hypotheses:
    # How fast souls learn from an integrated experience.
    learning_rate: float = 0.06

    # Free will / reflection -----------------------------------------------
    # Reflection is what lets a soul override its strongest impulse. Higher =>
    # values win more often over conditioning.
    reflection_strength: float = 1.4
    decision_noise: float = 0.35          # irreducible indeterminacy (epsilon)
    temptation_pull: float = 1.0          # how hard the environment pulls to unaligned
    misinfo_awareness_penalty: float = 0.7  # how much yuga misinformation blinds reflection

    # Environment coupling --------------------------------------------------
    yuga_temperature_scale: float = 0.9   # how much a hostile age adds impulsiveness

    # Reproduction ----------------------------------------------------------
    base_conception_prob: float = 0.22
    pairing_prob: float = 0.30            # chance an eligible single pairs up in a year

    # Soul injection: how sharply births prefer souls with more left to learn.
    karmic_pull: float = 1.0
    injection_topk: int = 12

    # Yoni ladder: capacity gained per year of pre-human bhoga. Higher => souls
    # reach human birth faster, so the human pool refills more quickly.
    yoni_maturation_rate: float = 0.02

    # New jivas prakriti manifests per year at the base of the ladder (mineral),
    # keeping saṃsāra supplied. Only active when rules.create_new_souls is True.
    new_jiva_rate: float = 4.0

    # Substrate: how far a NEW jiva's starting character (virtues/vices, never its
    # earned robustness) is pulled toward the mean profile of all liberated souls.
    # 0 = each generation starts raw; higher = later souls stand on the shoulders
    # of everyone who graduated. The "rising ground."
    substrate_influence: float = 0.20

    # Avatars — a liberated soul descends when, in a dark age (Dvapara/Kali), the
    # rate of aligned choice (behavioural dharma) falls below this. It softens the
    # local age by `avatar_field_relief` (temptation & misinformation) and amplifies
    # the karmic integration of others' aligned choices by `avatar_teaching_boost`
    # (learning by darshan).
    avatar_dharma_threshold: float = 0.75
    avatar_field_relief: float = 0.55
    avatar_teaching_boost: float = 0.6

    # THE HYPOTHESIS UNDER TEST (leave neutral by default!) -----------------
    # These let you *ask* things like "does adversity refine or just damage?"
    # without hand-coding the answer. adversity_refines scales how much holding
    # alignment under difficulty builds robustness vs. how much it just erodes.
    adversity_refines: float = 1.0

    # -- soul v2: the chariot, habits, gunas, and the 2.62 cascade ----------
    # The EXISTENCE of these mechanisms is fixed ontology; their STRENGTHS are
    # hypotheses. Each is a real question the lab can now ask.
    samskara_weight: float = 0.8       # how hard habit traces pull the impulse
    samskara_rate: float = 0.10        # how fast a repeated act deepens its groove
    vasana_carry: float = 0.4          # fraction of habit that survives death (as vasana)
    veto_cost: float = 0.15            # fatigue per veto attempt (freedom is expensive)
    veto_scale: float = 3.0            # sharpness of the buddhi-vs-habit contest
    buddhi_training_rate: float = 0.03 # each SUCCESSFUL veto strengthens the charioteer
    akrasia_erosion: float = 0.01      # seeing the better and doing the worse erodes buddhi
    cascade_strength: float = 1.0      # BG 2.62-63 coupling: kama->krodha->moha->buddhi-nasha
    guna_drift: float = 0.04           # how fast the age's ambient guna pulls a soul
    fatigue_recovery: float = 0.5      # fraction of fatigue recovered each year
    # Pralaya is the night of Brahma — a REST. Karmic seeds (virtues, vices,
    # robustness, buddhi) persist; manifest activity-patterns dissolve with the
    # world. This is the fraction of habit-groove that survives cosmic night.
    # Without it, each new Satya inherits Kali's addictions and the dawn never
    # comes (verified: the second cycle collapses into the cascade attractor).
    pralaya_rest: float = 0.1

    # -- v3: attraction as GUIDANCE (the design thesis) ----------------------
    # The claim under test: attraction, mating and soulmates are not chemistry
    # but steering — the design uses desire to route each soul toward its
    # curriculum. attraction_guidance is the master switch (0 = chemistry only,
    # 1 = full teleology); it scales all three mechanisms:
    #   teaching pull — drawn to the one whose virtue schools your ruling enemy
    #   thread pull   — recognition: open karmic threads reunite across lives
    #   guided birth  — souls incarnate near their thread-partners, into
    #                   families fit to teach their unresolved lesson
    # THE EXPERIMENT: does a guided cosmos liberate souls faster than a
    # chemistry-only one? sweep attraction_guidance 0 vs 1 and measure.
    attraction_guidance: float = 1.0
    thread_pull: float = 1.0
    guided_birth: float = 1.0

    # -- arts: rasa as the emotional weather system ---------------------------
    art_rate: float = 0.008     # per-adult-per-year chance to compose, scaled by
                                # emotional sensitivity and the pressure of the life
    art_pull: float = 0.6       # how strongly heard rasa tunes the hearer's gunas
    # THE CATHARSIS DIAL: does tragedy purge (Aristotle, +1: karuna -> sattva)
    # or contaminate (Plato, -1: karuna -> tamas)? Two millennia of aesthetics
    # as a sweepable hypothesis.
    catharsis: float = 1.0

    # -- the meta-loop: emergent religion ------------------------------------
    revelation_rate: float = 0.004     # per-adult-per-year chance, scaled by clarity
    myth_mutation: float = 0.25        # per-myth-per-year retelling corruption
    myth_spread: float = 0.10          # logistic growth of believers
    institution_threshold: float = 0.12  # fraction of population that ossifies a myth

    # -- deeds become myth (culture; design redteamed with gpt-5.6-sol) ------
    utterance_rate: float = 1.0        # how readily witnesses tell what they saw
    fabrication_rate: float = 0.02     # vice-driven lying (mada: glory, matsarya: villainy)
    story_spread_bonus: float = 1.5    # hypothesis: stories about persons travel better
    exemplar_pull: float = 0.5         # strength of the shravana-samskara (cultural groove)
                                        # channel; 0 = stories never shape conduct


# --------------------------------------------------------------------------
# LAYER 3 — MEASURED (a registry, NOT inputs to any rule)
# --------------------------------------------------------------------------
# These names are what metrics.py is allowed to compute and report. They are
# listed here purely so the wall is visible in one place. Nothing in the rule
# path (soul/decision/karma/yuga/reproduction) may import or branch on them.
MEASURED_KEYS: List[str] = [
    "population",
    "births",
    "deaths",
    "liberated_total",       # cumulative moksha
    "liberated_this_year",
    "avg_virtue",
    "avg_instability",
    "avg_robustness",
    "avg_lives_to_moksha",   # how many incarnations liberation took
    "cooperation_rate",      # fraction of aligned choices this year
    "violence_rate",         # fraction of strongly-unaligned choices this year
    "yuga",
    "cosmic_cycle",
]


@dataclass
class SimConfig:
    seed: int = 7
    years: int = 2000
    initial_adults: int = 200
    rules: FixedRules = field(default_factory=FixedRules)
    hyp: Hypotheses = field(default_factory=Hypotheses)
