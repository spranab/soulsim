# soulsim

An agent-based **cosmological** simulation — a *computational philosophy
laboratory*. Metaphysical ideas from Hindu cosmology (persistent souls, karma,
the yuga cycle, the yoni ladder, mokṣa) are treated as **literal mechanisms** so
we can run them and watch what kind of universe they generate.

It does **not** claim any of this is how reality works. It asks: *suppose these
were the rules — what happens?*

```
python3 run.py                       # one universe, 2000 years, 1000 souls
python3 run.py --years 800 --seed 3 --csv out.csv
python3 experiment.py                 # sweep a hypothesis knob and watch the outcome move
python3 experiment.py --knob learning_rate --values 0.02,0.05,0.1
```

Pure standard-library Python 3.9+. No dependencies.

---

## The one rule that makes it a laboratory: the three-layer wall

Everything is sorted into three layers (`config.py`), and information only ever
flows *down* them, never up:

| Layer | What it is | Example |
|---|---|---|
| **FIXED** | the ontology we assume | souls persist; karma updates a soul; mokṣa is the exit |
| **HYPOTHESIS** | knobs an experiment may turn | `adversity_refines`, `learning_rate`, `reflection_strength` |
| **MEASURED** | outcomes we observe (read-only) | liberation fraction, lives-to-mokṣa, cooperation by age |

If a thing we *measure* ("compassion produces mokṣa") were also hard-coded into
a *rule*, it wouldn't be a finding — it would be an echo of the code. So no rule,
hypothesis, or decision ever reads a measured value. That wall is the whole
point; keep it intact.

---

## What a soul is

A `SoulState` (`soul.py`) is a bundle of **tendencies**, never a script. Its
numbers bias probabilities; behaviour is decided separately (`decision.py`).

- **7 core virtues** — compassion, discernment, truth_alignment, courage,
  humility, non_attachment, unity_awareness (higher = more refined)
- **6 instabilities — the ariṣaḍvarga** (the inner enemies that bind a soul to
  saṃsāra): kāma (lust), krodha (anger), lobha (greed), moha (attachment), mada
  (ego), mātsarya (envy) — lower = more refined. Mokṣa requires *every one*
  quieted below the gate.
- **5 robustness dimensions** — one per hardship condition: does alignment
  *survive* power / scarcity / loss / success / uncertainty?

A person is `soul + body + emergent personality` for one life. The *current
personality* is not the deep soul: a calm soul in a reactive body behaves
impulsively. That gap is where realistic contradiction lives.

## Free will (`decision.py`) — the chariot (v2)

Free will here is **not** randomness and **not** a multiplier. It is the chariot
of the Katha Upaniṣad, implemented as a control stack:

1. **Horses/reins** — every action gets an impulse score: soul tendencies, habit
   grooves (saṃskāras, weighted by tamas), the age's temptation (amplified by
   rajas). The strongest impulse is what the being *will* do if nothing
   intervenes. Conditioning, made explicit.
2. **The gap** — with probability gated by sattva, self-awareness, and the age's
   noise (Kali blinds), the soul *notices* its impulse before acting. No
   noticing, no freedom: an unseen impulse simply executes.
3. **The charioteer** — if the impulse is unaligned and seen, the **buddhi** may
   contest it: a strength test against the groove and rajas' heat, costing
   fatigue win or lose. Freedom is expensive; the expense is why beings stay
   bound.

Buddhi is **trained** (grows only by winning vetoes), **finite** (fatigue),
**internal** (nothing outside the soul can veto for it), and **destructible**
(see the cascade). The liberated being needs no veto — its first impulse is
already dharma — and mokṣa now *requires* that effortlessness
(`compulsion_ewma` below threshold): a soul still winning by veto is
suppressed, not transformed.

## Karma (`karma.py`) — how you chose matters (v2)

Learning is weighted by the *inner* event, not just the act: a **won veto** is
the deepest learning there is (buddhi strengthens, a restraint-groove is laid);
**akrasia** — seeing the better and doing the worse — specifically erodes the
buddhi; **unseen** conditioning deepens the groove quietly; **effortless**
alignment reinforces mildly. Habit traces consolidate at death into vāsanās and
ride to the next life.

And the Gītā's 2.62–63 chain is implemented as a coupled cascade:
craving → anger → delusion → **destruction of discernment** (buddhi-nāśa). The
vices attack the faculty that could resist them, making bondage a positive-
feedback attractor — a *trap*, not a low score. Verified by sweep: doubling
`cascade_strength` halves the liberation fraction (0.39 → 0.20) while barely
changing lives-to-mokṣa — the trap doesn't slow the successful, it removes the
marginal. Escape channels: a kind age's guṇa climate, an avatar's field relief,
the substrate's rising ground, and pralaya's rest.

Pralaya (v2) is the **night of Brahmā — a rest**: karmic seeds (virtues, vices,
robustness, buddhi) persist, but habit-grooves largely dissolve with the
manifest world and guṇas settle sattvic for the dawn. Without this, each new
Satya inherits Kali's addictions and the second cycle collapses into the trap
(verified before the fix).

## The yuga cycle (`yuga.py`)

Four ages = four training distributions, in the classical 4:3:2:1 proportion,
looping into successive cosmic cycles. Satya is easy (truth visible, low
temptation); **Kali is the adversarial regime** (truth buried in noise, high
temptation, amplified impulsiveness). Same tests, different difficulty of holding
the line.

## The yoni ladder (`yoni.py`) — the pre-human ascent

Souls climb **mineral → plant → animal → human**. Lower rungs are *bhoga* — they
make no moral choices and accrue no virtue; they only **mature capacity**, the
reflective ceiling a human life needs for reflection to function. The ascent is
**one-way**. This ladder is the supply chain of the whole world: the only source
of human souls eligible for birth. As humans liberate and leave, the ladder keeps
feeding new (greener) souls up from below — until the reservoir drains.

## The meta-loop (`religion.py`) — this world writes its own scriptures

Clear souls (high unity-awareness × sattva) occasionally *perceive the world's
actual mechanics* — drawn from `GROUND_TRUTHS`, the simulation's real fixed
rules — with accuracy proportional to their clarity. The revelations become
myths; myths spread under logistic competition for attention and **mutate in
the retelling** (worse in noisy ages — Kali corrupts scripture measurably);
popular myths **institutionalize** (canon freezes, but dark-age power sometimes
rewrites a true clause, and clear-age reform restores it). Because we are the
world's physics, we can *grade* its religions: `doctrine_accuracy` is the
believer-weighted truth of living doctrine. Observed: true gospels ("the wheel
does not stop", "helpers descend") and false ones ("power frees") competing for
believers; institutions canonized at 0% and 100% truth in the same year;
scriptures born in kinder ages measurably truer than Kali-born ones.

## The viewer (`viewer.html`, built by `export_viewer.py`)

A playback instrument: two deterministic passes (the first picks a cast worth
following — the first soul to liberate, the longest road, the most bound, the
sage, the returning avatar; the second replays the identical cosmos and shadows
them yearly). Play/pause/scrub through 1500 years — ages banding the charts,
pralaya flashes, KPIs and legends as live readouts, soul cards, and the
chronicle of everything the world will remember.

## The library (`bard.py`, `bardic/`, `soulsim/annals.py`) — the world writes books

A cosmos is only as readable as what it writes down. The **Annals**
(`soulsim/annals.py`) are the witness's record of everything narratable,
written *as it happens*: every body gets a name and a house at birth; every
life keeps its parents, partners (and whether a partner was a soul known from
another life), children, every test it faced and how it went (mastered /
betrayed / swept along / effortless), the deeds that were seen and by how
many, the works it composed, the teachings it spoke, its death and what the
world called it. Seers now have names; teachings have lineages (founded,
corrupted, reformed, forgotten); avatars are known by the body they took and
the body they once wore.

The Annals roll their own dice. The physics stream and the culture stream
consume exactly what they consumed before the record existed, so a seed's
measured outcome is **byte-identical** with or without it — verified by
diffing `run.py` output before and after.

The **Bard** (`bard.py`) turns the Annals into a library, one genre per book:

```
python3 bard.py                                # seed 11, 500 years, every genre
python3 bard.py --seed 108 --years 800 --genres epic,novel
python3 bard.py --model none                   # no LLM: the chronicler's plain prose
```

| genre | what it is | how it is mined |
|---|---|---|
| **epic** | one soul across many lives, a canto per life, the ages turning between them | the liberated soul with the hardest recorded road (falls, betrayals, reunions) |
| **novel** | one life in depth: the house, youth, the bond, the tests, the turning, the last year, what the world kept | the life with the most novel in it (a long span, a bond, children, tests won *and* failed, something done in public, something made) |
| **history** | the chronicle of the ages, a book per cycle, a chapter per yuga, numbers in tables | metrics + the Annals: great deeds, seers, institutions, canonized works, the houses, the notable dead, the freed |
| **scripture** | a Veda: a hymn of origins, the seers' sūtras with commentary, hymns by rasa grown from their own lines, ballads of deeds | the living traditions, the canon, the story-myths — with the witness's gloss (which clauses are true, which name is wrong) kept out of the text and in the colophon |
| **tales** | the three short forms | the long road, the fall, the forgotten doer |
| **saga** | one house across the ages: its rulers, seers, deeds, works, the freed | the house with the most weight in the record |
| **upanishad** | dialogues between a seer and a real listener from the seer's own household, one per clause the teaching holds | the top living teachings with a named seer |
| **letters** | two thread-bound souls write to each other across two lives, then the witness's afterword | the strongest reunion whose earlier bodies were bonded too |

The division of labour is the one this project already trusts: **the world
supplies the plot, the model supplies the prose, a verifier keeps it
honest.** Each chapter's fact-sheet (a list of true sentences) goes to a local
model (`ollama`; `--model auto` picks the best installed, preferring
`qwen3.6:35b`, then `qwen3.5:9b`) as *translator* under absolute rules —
invent no event, name, place, god or number. A groundedness lint rejects any
numeral or mid-sentence proper noun not in the fact-sheet and retries; a
near-miss is scrubbed rather than published. Then a **second reader**
(`bardic/verify.py`) grades every sentence — SUPPORTED, TEXTURE (light,
weather, feeling: allowed), UNSUPPORTED (a record-type fact the record does not
hold: a marriage, a death, a deed) or CONTRADICTED — with one test: *would the
Annals have a field for this if it were true?* Offending sentences are
rewritten or deleted. Every book ends with **The Record** (every chapter's
fact-sheet) and a **Groundedness** table (who wrote the chapter, whether the
lint passed, what fraction of the must-say facts survived, what the second
reader checked and rewrote), so any sentence can be checked. Without a model
the books are still written, in the chronicler's plain prose. Sample library:
`library/seed_11_500y/`; output goes to `library/seed_<seed>_<years>y/`.

Where this goes next is in `docs/brainstorm-2026-09-12-revelation.md`: not more
genres but *revelation* — The Wrong Name (the ballad, then the deed and the
person it erased), the witness beside the text, the count of recorded moments
each chapter leaves untold, and a benchmark of truth against socially
successful falsehood.

## Mokṣa — the pass / exit criterion (`soul.assess_moksha`)

A soul leaves the simulation (into a `liberated` set, never to return) when it
reaches optimum across **every** dimension **and** has been **tested across every
hardship condition** at least N times. Breadth is required so an easy run of
lives cannot buy liberation — mokṣa is *robustness across contexts*, not a high
score in one kind life. This is the computational meaning of spiritual maturity.

---

## Findings so far (this parameterization)

- **The wheel turns without end.** At each mahayuga boundary a *pralaya* dissolves
  the manifest world and a new Satya re-manifests; unliberated souls are preserved
  (not liberated, not destroyed) and prakṛti keeps creating fresh jivas at the base
  of the ladder. So the population is a **sawtooth that never reaches zero** — over
  a 6000-year run, 12 cosmic cycles, 11 pralayas, population still ~1600 at the end.
  (An earlier version wrongly let the cosmos empty and stop; that was a modelling
  bug — no re-manifestation, a finite pool — not the doctrine. Fixed.)
- **Mokṣa is a trickle, not a flood.** A rare few slip free each age; saṃsāra keeps
  churning. Lower `adversity_refines` and the trickle thins toward the scriptural
  "out of thousands, scarcely one."
- **The outcome tracks the hypothesis, not the code.** Sweeping `adversity_refines`
  (does hardship refine a soul, or damage it?) moves the liberation rate across the
  whole range — see `experiment.py`. When adversity mostly damages, few ever clear
  the robustness gate; when it strongly refines, many do.
- **A hostile age suppresses aligned choice.** Cooperation is lowest in Kali.
- **Where the liberated go — two destinations, both faithful.** Their refinement
  *merges into the substrate* (the enriched ground new jivas are born from — it
  climbs to ~0.999 mean virtue), and — under the Vishishtadvaita switch
  (`avatar_return`) — a liberated soul may *return by choice as an avatar*. Avatars
  descend in the dark ages (Dvapara/Kali) exactly when behavioural dharma collapses,
  soften the age, and deepen what others' sincere choices integrate — cooperation
  dips, then recovers at each descent. Gītā 4.7, emergent and measured.

## Honest limitations

- Numbers are illustrative, not calibrated against anything real.
- Liberation is still commoner than the scriptural "scarcely one" at the default
  knobs — tune `adversity_refines` / `learning_rate` down for a rarer trickle.
- No economy or geography in the physics. The "houses" of the Annals are
  lineage labels for narration (a child inherits its father's house), not
  places that do anything. Institutions and emergent religion exist
  (`religion.py`); civilizations still do not learn as entities.

## Next steps (candidates)

- Institutions/civilizations as entities that also learn (or get karmically
  trapped) independent of individual souls.
- The MVP experiment from the design: *does intelligence without compassion
  reliably cause collapse?* (2×2 over intelligence/compassion growth).
- A dashboard over the CSV output.
- Longer-form works from the Annals: a chronicle play, a lineage saga (one
  house across the ages), letters between thread-bound souls.

## Layout

```
run.py              single-universe runner + report
experiment.py       hypothesis-knob sweep
soulsim/
  config.py         the three-layer wall (FIXED / HYPOTHESIS / MEASURED)
  soul.py           SoulState, dimensions, yoni stage, assess_moksha (exit)
  body.py           Genome, Body, genetics
  person.py         soul+body -> emergent personality (self_awareness, impulsiveness)
  events.py         life events as moral tests (authored from tensions)
  decision.py       choice under pressure — free will via reflection
  karma.py          soul update — integration, robustness build/erode
  yuga.py           the four ages / cosmic cycles
  yoni.py           the pre-human ascent (bhoga, one-way)
  world.py          the Universe and the yearly system loop
  metrics.py        the measured layer (observation only)
  annals.py         the witness's narratable record (names, houses, lives, deeds)
bard.py             the library: epic / novel / history / scripture / tales
bardic/
  render.py         local model as translator + groundedness lint + plain fallback
  book.py           chapters -> markdown, with The Record and Groundedness appended
  common.py         true sentences about lives, myths, works
  verify.py         the second reader: sentence-level grading and repair
  epic.py novel.py history.py scripture.py tales.py   the genre miners
  saga.py upanishad.py letters.py                     the newer forms
tests/              unittest: the second reader (fake model) and the genre briefs
compile_veda.py     the collected canon, unrendered (what Vyasa did: collect, arrange)
```
