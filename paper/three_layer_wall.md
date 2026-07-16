---
title: "The Three-Layer Wall: Authorship-Bias Controls for Generative Agent-Based Simulations"
author: "Pranab Sarkar — Independent Researcher — ORCID: 0009-0009-8683-1481"
date: "July 2026"
---

## Abstract

Agent-based simulations built to explore soft-domain questions — cultural
transmission, moral behavior, institutional dynamics — face a structural
credibility problem: the author writes both the mechanism and the metric, so
the simulation can "discover" precisely what its author assumed. This paper
presents a practical discipline for building simulations whose results are
findings rather than echoes. The core device is the *three-layer wall*: a hard
partition of every quantity in the system into fixed ontology, tunable
hypotheses, and measured outcomes, with information permitted to flow in only
one direction. Around the wall, four operational controls are developed:
placebo arms, observability separation with metamorphic audit tests,
random-stream isolation for causal attribution, and narration–physics
separation. The discipline is demonstrated in a case study: a cosmological
agent-based simulation implementing a layered metaphysics as executable
mechanism, including a dual-process decision architecture and an endogenous
cultural-transmission loop in which agents generate, distort, and are in turn
influenced by their own mythology. The controls caught three real
authorship-bias defects during development, each of which would otherwise have
been reported as a result. Two findings that survived the full battery are
reported: living cultural memory exhibits a measurable fidelity half-life
(stories under 60 years old matched their source records at 94%; past 150
years, 46%), and narrative influence on behavior is nonlinear — below a
threshold exposure strength, stories with 76% population reach produced no
measurable behavioral effect, while at full strength the same channel shifted
cooperation by +1.9 points and increased the simulation's terminal attainment
rate by 9%, despite negatively-valenced stories dominating the myth pool. The
methods are domain-agnostic and inexpensive, and are offered as a checklist
for any generative simulation whose author also writes its grading function.

**Keywords:** agent-based modeling, validation, authorship bias, metamorphic
testing, cultural evolution, simulation methodology, placebo controls, model
credibility, computational philosophy

## 1. Introduction

Every generative simulation is an argument written twice: once as mechanism
and once as measurement. When the same author writes both, a circularity
threatens that is more insidious than ordinary bugs, because its symptom is
success. The simulation produces exactly the phenomenon the author hoped to
see; the plots are beautiful; nothing crashes. The result is then reported as
if the world inside the machine had testified independently, when in fact the
author asked a question of their own assumptions and received their own
assumptions in reply.

The problem is old — Epstein's defense of modeling [1] and the
pattern-oriented modeling program of Grimm et al. [2] both circle it — but it
is acute for a particular class of simulation that has become easy to build
and tempting to trust: *generative soft-domain simulations*, in which agents
carry psychological or cultural state, mechanisms encode contestable theory
("hardship refines character," "stories shape conduct"), and the outputs are
narratively compelling. Compelling narrative output is precisely the condition
under which an author is least likely to audit their own graders, a
Goodhart-type failure [3] in which the simulation optimizes the author's
satisfaction rather than the question's answer.

This paper reports a discipline developed while building such a simulation
deliberately — a cosmological agent-based model that takes the layered
metaphysics formalized in earlier structural work on simulation-class
ontologies [4] and implements it as executable mechanism: persistent agents
("souls") that carry state across embodied episodes, a dual-process decision
architecture, a coupled vice dynamic, and an endogenous mythology loop in
which the population generates, distorts, institutionalizes, and is in turn
behaviorally influenced by stories about its own history. A system like this
is an authorship-bias worst case: every mechanism encodes a philosophical
commitment, every metric tempts the author to grade their own thesis, and the
output is *maximally* charming. It is therefore a good stress test for
credibility controls: anything that keeps this system honest will keep a
traffic model honest.

The contributions are: (i) the three-layer wall, a partition-and-flow rule
that makes authorship bias a checkable property rather than a virtue of
character; (ii) four operational controls that enforce the wall at the code
level — placebo arms, observability separation with metamorphic audit tests,
random-stream isolation, and narration–physics separation; (iii) a case study
in which these controls caught three real defects that would otherwise have
been published as findings; and (iv) two positive findings that survived the
full battery, reported with the controls that license them.

## 2. The Three-Layer Wall

Every quantity in the simulation is assigned to exactly one layer:

**Layer F — Fixed ontology.** The commitments that define *which universe this
is*. In the case study: agents persist across episodes; decisions pass through
an impulse–awareness–veto pipeline; an exit criterion exists. Changing Layer F
is not tuning; it is changing the subject of study.

**Layer H — Hypotheses.** Named, numeric, sweepable knobs, each phrased as a
question rather than an answer: *does hardship refine or damage?* (a scalar
multiplying stress-conditioned growth); *do stories shape conduct?* (a scalar
on the narrative-exposure channel, sweepable to zero). A hypothesis knob's
default value is a confession, not a conclusion.

**Layer M — Measured outcomes.** Everything reported: rates, distributions,
survival curves, accuracy scores. Layer M is write-only from the simulation's
perspective.

The wall is the flow rule: **F and H may influence the run; M may never.** No
rule, no mechanism, no scheduling decision may read a measured value. The rule
sounds trivial and is violated constantly in practice, usually through one of
three channels: (a) a *grading channel* — the metric quietly encodes the same
assumptions as a mechanism, so agreement is tautological; (b) an *oracle
channel* — a mechanism reads state that no in-world entity could observe,
smuggling the analyst's omniscience into the world; (c) a *narration channel*
— labels generated for human legibility ("this agent is a sage") leak back
into behavior. The controls below target each channel.

An important clarification: the wall does not forbid *interventions*. An
experimenter (or an interactive user) may reach into the world and perturb
Layer F/H state at runtime. What it forbids is the *world's own physics*
conditioning on Layer M. Interventions are honest precisely because they are
declared as external hands rather than disguised as endogenous law.

## 3. Four Operational Controls

### 3.1 Placebo arms

Any claimed effect of an informational mechanism must be compared against a
*shape-matched placebo*, not only against absence. In a companion experiment
on memory-augmented language-model generation, a treatment arm injecting
twelve retrieved craft rules outperformed a no-injection baseline by 26
percentage points on a compliance rubric — but a placebo arm injecting twelve
length-matched, framing-matched platitudes captured 9 of those points. A third
of the naive effect was prompt mass, not knowledge. The general rule: when the
treatment is *content*, the control must be *content-shaped noise*. Reporting
treatment-versus-nothing for informational interventions should be regarded
as under-controlled by default.

### 3.2 Observability separation and metamorphic audit tests

The oracle channel is subtlest where a simulation contains both an inner
truth and an outer appearance. In the case study, the decision pipeline
distinguishes inwardly *effortless* right action from right action won by
costly self-override — but no in-world observer can see that difference; a
witness sees only the outward act. When the cultural loop was first designed,
story-formation was keyed to the analyst's event registry, which recorded
inner difficulty and cross-episode identity. This was an oracle: the culture
would have "remembered" precisely those deeds the metaphysics deemed
significant, and the finding "cultural fame tracks inner merit" would have
been prewritten.

The repair is a schema separation. A causal **public trace** carries only what
witnesses could observe (actor's public name, situation type, outward act,
apparent scale, witness count), with publicness sampled from situational
observability, never from inner significance. A noncausal **audit record**
carries the inner truth (agent identity across episodes, inner decision type)
for analytics only. The invariant is then *metamorphically testable* [5]:
perturbing or destroying audit-only fields mid-run must leave the world's
trajectory bit-identical. In the case study this test is run by vandalizing
the audit log every simulated year in a paired run and asserting identical
population, attainment, and myth histories. The test failed on first
execution — not through an oracle, but by exposing a latent nondeterminism
(unseeded unique identifiers perturbing set-iteration order), itself a
credibility defect, since claimed "paired runs" had not been pairs at all.
Both defects were fixed; the test now passes and runs as part of the
experiment harness.

### 3.3 Random-stream isolation

Dose-response comparisons attribute outcome differences to a mechanism's
strength. But if all mechanisms draw from one random stream, arms differ not
only in the mechanism under test but in *dice consumption*: a channel that
merely rolls random numbers shifts every subsequent draw, and chaotic
divergence masquerades as effect. The case study therefore assigns the
cultural subsystem its own generator, seeded independently of the core
life-cycle stream. With streams isolated, a swept channel can be attenuated
to zero without perturbing any draw outside itself; behavioral differences
between arms then flow only through the mechanism's declared causal path.
Stream isolation is cheap, and without it, single-seed intervention studies
in coupled agent systems are largely theater.

### 3.4 Narration–physics separation

Generative simulations produce human-facing narration: role labels, event
prose, biography summaries. The temptation is to reuse these labels as state.
The rule: narration is computed *from* physics and never read *by* physics,
enforced by a renaming invariance — any narration string may be arbitrarily
relabeled without changing the trajectory. In the case study, derived life
roles ("mystic," "reformer") appear in agent biographies and nowhere in any
mechanism.

### 3.5 Adversarial design review

As a process control, the design of each new mechanism was subjected to
red-team review by an independent large language model prompted specifically
to locate wall violations and oracle channels before implementation. This
practice located the observability defect of §3.2 at the design stage. The
practice is noted because it is cheap, repeatable, and materially changed the
shipped architecture; model-assisted red-teaming of *designs* (as distinct
from code) appears underused in the simulation literature.

## 4. Case Study

The host system implements, as executable mechanism, the layered ontology
analyzed structurally in [4]: persistent agents cycle through embodied
episodes; an exit criterion ("liberation") requires not only optimal state
but demonstrated robustness across all stress conditions and *effortlessness*
— the agent's unmediated first impulses must themselves be aligned, so that
suppression is distinguishable from transformation. Decisions pass through a
dual-process pipeline: conditioned impulse assembly (weighted by habit traces
that deepen with use and decay between episodes), a stochastic awareness gate,
and a costly self-override contest whose faculty strengthens only through
exercise and erodes under witnessed self-betrayal. A coupled vice dynamic
makes moral failure a feedback attractor rather than a low score. None of
these commitments is defended here; they are Layer F, and the point is
methodological: a maximally tempting system kept honest.

The cultural loop closes the largest cycle: outward acts probabilistically
leave public traces; traces are narrated by witnesses (and fabricated by
motivated liars — fabrication is an agent act driven by agent state, not a
scheduler event); narrations become myths represented as *claim bundles*
(actor claim, event claim on a categorical scale ladder, doctrinal
propositions) whose components mutate independently through retelling —
misattribution, scale drift, moral inversion, collective-to-hero compression,
and annexation of doctrine by unrelated stories; myths compete for finite
attention, and heard stories lay weak, episode-local habit traces in the same
representational slot as personally acquired habit — increasing an act's
availability, never its alignment. Because the simulation's physics is the
ground truth its own mythology describes, every myth is gradeable: doctrinal
accuracy, doctrinal coverage, and historical fidelity are computed against
the noncausal audit archive.

Three defects caught by the controls during development, each of which would
otherwise have shipped inside a result:

1. **A grading-channel defect** (companion experiment): a compliance rubric
   written by the same hand that wrote the injected guidance, discovered when
   an obviously degenerate output scored 11.8% by vacuously passing the
   rubric's negative checks. Repair: validity gates before scoring; and for
   the main claim, replacement of the authored rubric with a spec the
   generator could not have seen.
2. **An oracle-channel defect** (§3.2): story formation keyed to inner
   significance. Caught at design review; repaired by observability
   separation.
3. **A pairing defect**: unseeded identifiers made "identical seeds"
   non-identical, invalidating paired-run claims silently. Caught by the
   metamorphic audit test; repaired with deterministic serials and ordered
   iteration at every random-consuming boundary.

## 5. Findings That Survived

Two results are reported *because* the battery licenses them; the controls
they passed are listed with each.

**5.1 Living cultural memory has a fidelity half-life.** Grading each living
story-myth against its archived source trace: myths younger than 60 simulated
years matched their sources at 0.94 (actor, act-valence, scale, plurality);
myths older than 150 years matched at 0.46, with fabricated stories
(no source event) additionally occupying a large share of the high-popularity
tail. Doctrinal coverage remained at 1.0 throughout — every ground-truth
proposition remained taught by some living tradition even as the biographies
carrying doctrine rotted. Distortion operators were not fitted to produce
this; decay-with-age is emergent from uniform per-retelling mutation exposure.
*Controls passed:* audit noncausality (metamorphic test), narration
separation; the fidelity metric reads the analytics archive only.

**5.2 Narrative influence on conduct is a threshold, not a dial.** Sweeping
the exposure-strength knob across {0, 0.5, 1.0} (three seeds, 350 years, 800
agents, isolated cultural stream): at 0.5, with 76% of the adult population
carrying story-laid habit traces, no behavioral metric moved (cooperation
Δ−0.001). At 1.0, cooperation rose +1.9 points, violence fell −1.9,
effortless action rose +2.0, and terminal attainment rose 9% — despite
negatively-valenced stories holding a majority of believers. The sign
asymmetry has a mechanistic reading visible in the decision pipeline:
negative stories groove acts that unrefined agents' impulses already
dominate (redundant at the argmax), while positive stories can flip
marginal agents (pivotal). Stated as a portable hypothesis: *exemplar
narratives act on the margin, not the mode; and below a salience threshold,
saturating reach produces no behavioral effect.* *Controls passed:* stream
isolation (arms differ only in the declared channel), placebo logic (the
0-arm is a true mechanism ablation, not merely content absence), narration
separation.

Neither finding is offered as a claim about human societies. Both are offered
as cheaply generated, control-hardened hypotheses of the kind such
simulations are for [1]: precise enough to look for in empirical data on
oral-tradition fidelity and narrative persuasion, and honest about their
provenance.

## 6. Related Work

Pattern-oriented modeling [2] disciplines model *structure* against observed
patterns; the present work is complementary, disciplining the *authorship
relation* between mechanism and metric. Classic cultural-transmission models
[6, 7] established mutation-and-selection dynamics for traits and opinions;
the case study differs in grading transmitted content against an internal
ground truth, which is only possible when the modeled world's physics is
owned — a methodological advantage of simulation unavailable to field
studies, and one that authorship controls are required to spend honestly.
Metamorphic testing [5] supplies the template for the audit invariants.
The memory substrate underlying the persistent-agent implementation is
described in [8].

## 7. Limitations

The case-study effects are small-n (three seeds per arm) and
single-parameterization; the wall governs *validity*, not statistical power.
The placebo principle is demonstrated in a companion language-model
experiment rather than in-simulation. Surgical single-myth deletion — proving
that one specific false story altered history — remains confounded by chaotic
divergence even under stream isolation and is left as future work requiring
larger seed batteries. Finally, the wall constrains what a simulation may
claim, not what an author may believe; it is a hygiene practice, not an
epistemology.

## 8. Conclusion

A generative simulation is trustworthy in proportion to the difficulty of
lying to oneself with it. The three-layer wall and its four controls make
several common self-deceptions mechanically checkable: tautological grading
(placebo arms), smuggled omniscience (observability separation with
metamorphic tests), chaos dressed as effect (stream isolation), and narration
leaking into law (renaming invariance). In the case study these controls
converted three would-be findings into three found bugs — which is the
method working, since a discipline that never catches its author is
decoration. What remains after the battery is smaller than what was hoped
and more likely to be true, which is the correct direction of trade.

## References

[1] J. M. Epstein, "Why Model?", *Journal of Artificial Societies and Social
Simulation*, 11(4):12, 2008.

[2] V. Grimm et al., "Pattern-Oriented Modeling of Agent-Based Complex
Systems: Lessons from Ecology," *Science*, 310(5750):987–991, 2005.

[3] M. Strathern, "'Improving ratings': audit in the British University
system," *European Review*, 5(3):305–321, 1997.

[4] P. Sarkar, "Simulation-Class Ontologies and Vedantic Metaphysics: A
Structural-Comparative Analysis of the Bhagavad Gita," Zenodo, 2026.
doi:10.5281/zenodo.19339801.

[5] T. Y. Chen, S. C. Cheung, and S. M. Yiu, "Metamorphic Testing: A New
Approach for Generating Next Test Cases," Technical Report
HKUST-CS98-01, 1998.

[6] R. Axelrod, "The Dissemination of Culture: A Model with Local Convergence
and Global Polarization," *Journal of Conflict Resolution*, 41(2):203–226,
1997.

[7] R. Boyd and P. J. Richerson, *Culture and the Evolutionary Process*,
University of Chicago Press, 1985.

[8] P. Sarkar, "YantrikDB: A Cognitive Memory Engine for Persistent AI
Systems," Zenodo, 2026. doi:10.5281/zenodo.18793952.

---

## Code Availability

The complete engine, experiment harnesses, wall tests, and interactive
visualizations are open-source at
<https://github.com/spranab/soulsim> (v1.0, the version described here).
