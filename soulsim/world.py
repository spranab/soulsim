"""The Universe — container and the yearly system loop.

Order of systems each simulated year:
    1. resolve the current yuga (global difficulty)
    2. aging & mortality        -> deaths, and moksha assessment at death
    3. life events              -> decision (free will) -> karma (soul update)
    4. pairing & reproduction   -> soul injection into newborns
    5. measurement              -> one YearRecord (observation only)

Nothing in steps 1-4 ever reads a measured value from step 5. Souls persist;
bodies are temporary; liberated souls leave the pool for good.
"""
from __future__ import annotations

import random
from dataclasses import replace
from typing import Dict, List, Optional, Set
from uuid import UUID

from .body import Body, Genome, random_genome, child_genome
from .config import SimConfig
from .decision import choose_action
from .events import EVENT_TEMPLATES
from .karma import apply_outcome
from .metrics import MetricsLog, YearRecord
from .person import Person
from .arts import ArtSystem
from .culture import CultureSystem
from .religion import ReligionSystem
from .soul import (SoulState, assess_moksha, clamp, CORE_VIRTUES, INSTABILITIES,
                   ROBUSTNESS, YONI_STAGES)
from .yoni import mature
from .yuga import YugaClock


def _random_soul(rng: random.Random) -> SoulState:
    """A fresh, unrefined soul: middling virtues, live instabilities, low robustness,
    an untrained charioteer, and a guna mix leaning rajasic (appetite before clarity)."""
    s = SoulState()
    for v in CORE_VIRTUES:
        setattr(s, v, clamp(rng.gauss(0.42, 0.12)))
    s.unity_awareness = clamp(rng.gauss(0.10, 0.06))
    for i in INSTABILITIES:
        setattr(s, i, clamp(rng.gauss(0.52, 0.12)))
    for r in ROBUSTNESS:
        setattr(s, r, clamp(rng.gauss(0.18, 0.05)))
    s.buddhi = clamp(rng.gauss(0.15, 0.05), 0.02, 0.5)
    s.sattva = clamp(rng.gauss(0.30, 0.06))
    s.rajas = clamp(rng.gauss(0.45, 0.06))
    s.tamas = clamp(rng.gauss(0.25, 0.06))
    s.normalize_gunas()
    s.recompute_karmic_load()
    return s


class Universe:
    def __init__(self, config: SimConfig) -> None:
        self.cfg = config
        self.rng = random.Random(config.seed)
        # separate stream for the story-world: interventions on myths must not
        # shift the core stream's dice (attribution needs stream isolation)
        self.crng = random.Random(config.seed ^ 0xC0FFEE)
        self.clock = YugaClock()
        self.metrics = MetricsLog()
        self.year = 0

        self.souls: Dict[UUID, SoulState] = {}
        self.available: Set[UUID] = set()      # HUMAN-stage, disembodied, not liberated
        self.maturing: Set[UUID] = set()       # pre-human souls climbing the yoni ladder
        self.liberated: Set[UUID] = set()
        self.persons: Dict[UUID, Person] = {}  # body_id -> living Person

        self.pralaya_count = 0
        self.souls_created = 0                 # total jivas ever manifested
        self._last_cycle = 0
        self.reunions = 0                      # soulmate recognitions across lives
        self.resolutions = 0                   # old threads released

        # Where the liberated go
        self.returnable: Set[UUID] = set()     # liberated individuals who may descend as avatars
        self.avatar_descents = 0
        self._sub_n = 0                         # count of souls merged into the substrate
        self._sub_sums = {p: 0.0 for p in (CORE_VIRTUES + INSTABILITIES)}

        # The meta-loop: this world writes its own scriptures
        self.religion = ReligionSystem(self.crng)
        # Deeds become myth: traces, utterances, and the noncausal audit
        self.culture = CultureSystem(self.crng)
        # Souls give form to their inner life; the world builds a library
        self.arts = ArtSystem(self.crng)
        # Chronicle: notable events, for viewers and posterity
        self.chronicle: List[tuple] = []       # (year, kind, text)
        self._first_moksha_noted = False

        self._init_souls()
        self._init_population()

    def note(self, kind: str, text: str) -> None:
        self.chronicle.append((self.year, kind, text))

    # -- god-ops: external interventions (a viewer's hand, not the physics) --
    # These do not violate the wall: they are USER actions entering the fixed
    # ontology through the same mechanisms the world already has.
    tempt_bias: float = 0.0   # live bend on the age's temptation

    def god_avatar(self) -> bool:
        """Force a willing liberated soul to descend now."""
        if not self.returnable:
            return False
        sid = self.rng.choice(sorted(self.returnable, key=lambda x: self.souls[x].serial))
        self.returnable.discard(sid)
        soul = self.souls[sid]
        body = Body(soul_id=sid, age=self.rng.randint(22, 30),
                    sex=self.rng.choice(["female", "male"]),
                    genome=Genome(health_potential=0.9, intelligence_potential=0.95,
                                  emotional_sensitivity=0.5, aggression_tendency=0.1,
                                  sociability=0.85, fertility=0.3, longevity=0.85))
        soul.current_body_id = body.body_id
        p = Person(soul=soul, body=body)
        p.is_avatar = True
        self.persons[body.body_id] = p
        self.avatar_descents += 1
        self._avatar_this_year = 1
        self.note("avatar", "A hand reaches in: a liberated one descends")
        return True

    def god_pralaya(self) -> None:
        self._pralaya()
        self._pralaya_this_year = 1
        self.note("pralaya", "The hand closes: the world dissolves before its time")

    def god_miracle(self, souls=None, d_sattva: float = 0.12) -> int:
        """Grace: clear minds (sattva up, a touch of unity)."""
        targets = souls if souls is not None else [p.soul for p in self.persons.values()]
        for s in targets:
            s.shift_gunas(d_sattva=d_sattva)
            s.unity_awareness = clamp(s.unity_awareness + 0.02)
        self.note("reform", f"A quiet grace moves through the world; {len(targets)} souls are touched")
        return len(targets)

    def god_calamity(self, persons=None) -> int:
        """Trial: every targeted adult faces a loss event now, at full difficulty."""
        from .events import EVENT_TEMPLATES
        loss = next(t for t in EVENT_TEMPLATES if t.condition == "loss")
        yuga, _ = self.clock.at(self.year)
        targets = [p for p in (persons if persons is not None else self.persons.values())
                   if p.is_adult(self.cfg.rules.adult_age) and not p.is_avatar]
        for p in targets:
            d = choose_action(p, loss, yuga, self.cfg.hyp, self.rng)
            apply_outcome(p, loss, d, yuga, self.cfg.hyp)
        self.note("corruption", f"Calamity strikes; {len(targets)} souls are tested by loss")
        return len(targets)

    # -- the substrate (the enriched ground the liberated leave behind) ----
    def _substrate_absorb(self, soul: SoulState) -> None:
        for p in self._sub_sums:
            self._sub_sums[p] += getattr(soul, p)
        self._sub_n += 1

    def _substrate_profile(self):
        if self._sub_n == 0:
            return None
        return {p: self._sub_sums[p] / self._sub_n for p in self._sub_sums}

    def substrate_virtue(self) -> float:
        prof = self._substrate_profile()
        if not prof:
            return 0.0
        return sum(prof[v] for v in CORE_VIRTUES) / len(CORE_VIRTUES)

    # -- setup -------------------------------------------------------------
    def _init_souls(self) -> None:
        """Seed souls spread across the yoni ladder, so the human pool is fed by
        a reservoir already climbing from mineral/plant/animal."""
        # rough starting spread across the ladder (before embodiment carve-out)
        spread = [("human", 0.42), ("animal", 0.25), ("plant", 0.20), ("mineral", 0.13)]
        # capacity a soul carries when it *starts* at a given stage
        start_cap = {"mineral": 0.0, "plant": 0.28, "animal": 0.55, "human": 0.85}
        for _ in range(self.cfg.rules.soul_count):
            s = _random_soul(self.rng)
            r = self.rng.random()
            acc = 0.0
            stage = "human"
            for name, frac in spread:
                acc += frac
                if r <= acc:
                    stage = name
                    break
            s.yoni_stage = stage
            s.capacity = clamp(start_cap[stage] + self.rng.gauss(0.0, 0.03))
            s.serial = self.souls_created
            self.souls[s.soul_id] = s
            self.souls_created += 1
            if s.is_human:
                self.available.add(s.soul_id)
            else:
                self.maturing.add(s.soul_id)

    def _creation(self) -> int:
        """Prakṛti manifests new jivas at the base of the ladder (mineral), so
        saṃsāra is continuously resupplied and never drains to nothing."""
        if not self.cfg.rules.create_new_souls:
            return 0
        n = self.rng.random()
        rate = self.cfg.hyp.new_jiva_rate
        count = int(rate) + (1 if self.rng.random() < (rate - int(rate)) else 0)
        prof = self._substrate_profile()
        w = self.cfg.hyp.substrate_influence
        for _ in range(count):
            s = _random_soul(self.rng)
            s.serial = self.souls_created
            s.yoni_stage = "mineral"
            s.capacity = 0.0
            # Stand on the shoulders of the liberated: a new jiva's *character*
            # (virtues, vices) is pulled toward the substrate profile — but NOT its
            # robustness, which every soul must still earn by being tested itself.
            if prof is not None and w > 0.0:
                for p in (CORE_VIRTUES + INSTABILITIES):
                    setattr(s, p, clamp((1 - w) * getattr(s, p) + w * prof[p]))
                s.recompute_karmic_load()
            self.souls[s.soul_id] = s
            self.maturing.add(s.soul_id)
            self.souls_created += 1
        return count

    def _pralaya(self) -> None:
        """Dissolution at the mahayuga boundary. The manifest world withdraws
        into the unmanifest: living bodies dissolve, but their souls are NOT
        liberated and NOT destroyed — karma is preserved and they wait, then a
        new Satya re-manifests. This is the wheel turning (BG 8.18-19)."""
        for person in list(self.persons.values()):
            soul = person.soul
            person.body.alive = False
            soul.current_body_id = None
            if person.is_avatar:
                self.returnable.add(soul.soul_id)   # an avatar simply withdraws
                continue
            soul.lifetime_count += 1          # a dissolved life is still a life lived
            soul.recompute_karmic_load()
            self.available.add(soul.soul_id)  # returns to the unmanifest pool, not moksha
        self.persons.clear()

        # The night of Brahma: rest in the unmanifest. Karmic seeds persist;
        # activity-patterns dissolve with the manifest world. Every soul's habit
        # grooves fade deeply and its gunas settle toward the coming dawn's
        # sattvic climate — the new Satya genuinely dawns golden.
        rest = self.cfg.hyp.pralaya_rest
        for soul in self.souls.values():
            if soul.moksha:
                continue
            soul.consolidate_death(rest)
            soul.sattva, soul.rajas, soul.tamas = 0.55, 0.27, 0.18
            soul.normalize_gunas()
        self.note("pralaya", "Pralaya: the world dissolves into the unmanifest; a new Satya dawns")
        self.pralaya_count += 1
        self._init_population()               # a new Satya dawns; souls re-embody

    def _init_population(self) -> None:
        rules = self.cfg.rules
        ids = sorted(self.available, key=lambda sid: self.souls[sid].serial)
        self.rng.shuffle(ids)
        for sid in ids[: self.cfg.initial_adults]:
            soul = self.souls[sid]
            body = Body(
                soul_id=sid,
                age=self.rng.randint(rules.adult_age, 40),
                sex=self.rng.choice(["female", "male"]),
                genome=random_genome(self.rng),
            )
            soul.current_body_id = body.body_id
            self.available.discard(sid)
            p = Person(soul=soul, body=body)
            p.snapshot_start()
            soul.born_reason = soul.born_reason or "was among the first, at the founding"
            self.persons[body.body_id] = p

    # -- soul injection ----------------------------------------------------
    def _select_soul_for_birth(self, mother: Optional[Person] = None,
                               father: Optional[Person] = None) -> Optional[SoulState]:
        if not self.available:
            return None
        hyp = self.cfg.hyp
        candidates = sorted(self.available, key=lambda sid: self.souls[sid].serial)
        # v3 guided birth: souls with open threads to the EMBODIED are pulled
        # into incarnation now — the design arranges the meeting.
        embodied = None
        if hyp.attraction_guidance > 0 and hyp.guided_birth > 0:
            embodied = {str(p.soul.soul_id) for p in self.persons.values()}
        # Prefer souls with more left to resolve (karmic pull) + noise. Sample
        # from the top-k rather than always the max, so injection isn't deterministic.
        scored = []
        g = hyp.attraction_guidance * hyp.guided_birth
        for sid in candidates:
            soul = self.souls[sid]
            score = 1.0 + hyp.karmic_pull * soul.karmic_load + self.rng.gauss(0.0, 0.2)
            if embodied is not None:
                if soul.threads:
                    live = [v for k, v in soul.threads.items() if k in embodied]
                    if live:
                        score += g * 0.6 * max(live)
                if mother is not None and father is not None:
                    # born to the family fit to teach its unresolved lesson
                    dv = max(INSTABILITIES, key=lambda v: getattr(soul, v))
                    opp = self.OPPOSING[dv]
                    fit = getattr(soul, dv) * (getattr(mother.soul, opp)
                                               + getattr(father.soul, opp)) / 2
                    score += g * 0.4 * fit
            scored.append((score, sid))
        scored.sort(reverse=True, key=lambda t: t[0])
        top = scored[: min(hyp.injection_topk, len(scored))]
        sid = self.rng.choice(top)[1]
        # record WHY this soul got this body — the inspector's answer to
        # "why did this soul become this person"
        chosen = self.souls[sid]
        why = []
        if chosen.karmic_load > 0.55:
            why.append("much left unresolved")
        if embodied is not None and chosen.threads and any(k in embodied for k in chosen.threads):
            why.append("an old thread waits in the world")
        if embodied is not None and mother is not None and father is not None:
            dv = max(INSTABILITIES, key=lambda v: getattr(chosen, v))
            opp = self.OPPOSING[dv]
            fit = getattr(chosen, dv) * (getattr(mother.soul, opp)
                                         + getattr(father.soul, opp)) / 2
            if fit > 0.3:
                why.append(f"born to parents whose {opp.replace('_', '-')} can school its {dv}")
        chosen.born_reason = "; ".join(why) if why else "its turn on the wheel came round"
        self.available.discard(sid)
        return self.souls[sid]

    # -- systems -----------------------------------------------------------
    def _yoni_ladder(self) -> int:
        """Mature every pre-human soul by a year of bhoga; promote arrivals to the
        human pool. Returns how many reached human birth this year."""
        rate = self.cfg.hyp.yoni_maturation_rate
        arrivals = 0
        for sid in sorted(self.maturing, key=lambda x: self.souls[x].serial):
            if mature(self.souls[sid], rate, self.rng):
                self.maturing.discard(sid)
                self.available.add(sid)
                arrivals += 1
        return arrivals

    def _mortality_prob(self, person: Person) -> float:
        L = person.body.longevity_years(self.cfg.rules.base_longevity_years)
        age = person.age
        base = 0.005 + (0.02 if age < 1 else 0.0)
        old = (age / max(L, 1.0)) ** 7 * 0.20
        return clamp(base + old, 0.0, 0.97)

    def _aging_and_death(self) -> int:
        deaths = 0
        for person in list(self.persons.values()):
            person.body.age += self.cfg.rules.step_years
            if person.age > self.cfg.rules.max_age or self.rng.random() < self._mortality_prob(person):
                self._process_death(person)
                deaths += 1
        return deaths

    # v4: a life's derived ROLE — a narration of the soul's end-state, purely a
    # label on the visual/measured side (nothing in the physics reads it).
    def _derive_role(self, soul: SoulState) -> str:
        sigs = {
            "mystic": 1.5 * soul.unity_awareness + soul.sattva,
            "teacher": 1.2 * soul.buddhi + soul.discernment - 0.3,
            "reformer": 0.7 * (soul.truth_alignment + soul.courage) - 0.2,
            "caretaker": 1.25 * soul.compassion - 0.15,
            "ruler": 0.8 * soul.mada + 0.6 * soul.courage,
            "opportunist": 0.7 * (soul.kama + soul.lobha) - 0.3 * soul.humility,
            "brooder": soul.tamas + 0.5 * soul.moha - 0.2,
            "wanderer": 0.45,
        }
        return max(sigs, key=lambda k: sigs[k])

    def _process_death(self, person: Person) -> None:
        soul = person.soul
        person.body.alive = False
        soul.current_body_id = None
        del self.persons[person.body_id]

        # v4: consolidate this life into the soul's memory (avatars excepted —
        # their walk is not a life on the wheel)
        if not person.is_avatar:
            end_virtue = sum(getattr(soul, v) for v in CORE_VIRTUES) / len(CORE_VIRTUES)
            entry = {
                "n": soul.lifetime_count + 1,
                "role": self._derive_role(soul),
                "years": person.body.age,
                "dv": round(end_virtue - person.start_virtue, 3),
                "enemy": max(INSTABILITIES, key=lambda v: getattr(soul, v)),
                "born": soul.born_reason,
                "note": person.notable[0] if person.notable else "",
                "ledger": [person.life_veto, person.life_akrasia,
                           person.life_unseen, person.life_effortless],
            }
            soul.history.append(entry)
            if len(soul.history) > 12:
                soul.history.pop(0)

        # v3: the thread — how the partnership ends decides whether it recurs.
        # A long, well-lived bond resolves and releases; an unfinished one
        # leaves an open thread on both souls that will seek reunion.
        partner = self.persons.get(person.partner_id) if person.partner_id else None
        if partner is not None:
            other = partner.soul
            harmony = clamp(0.20 + 0.05 * min(person.bond_years, 10)
                            + 0.30 * (person.alignment_consistency()
                                      + partner.alignment_consistency()) / 2
                            + 0.15 * (1.0 - abs(soul.compulsion_ewma - other.compulsion_ewma)))
            openness = 1.0 - harmony
            ka, kb = str(other.soul_id), str(soul.soul_id)
            if openness > 0.35:
                soul.add_thread(ka, openness)
                other.add_thread(kb, openness)
            elif ka in soul.threads or kb in other.threads:
                soul.threads.pop(ka, None)
                other.threads.pop(kb, None)
                self.resolutions += 1
                self.note("bond", "An old thread between two souls is released at last")
            partner.partner_id = None
            partner.bond_years = 0

        # An avatar was never bound; when its body dies it simply withdraws,
        # still liberated, back into the returnable pool. No karma, no re-count.
        if person.is_avatar:
            self.returnable.add(soul.soul_id)
            return

        soul.lifetime_count += 1
        soul.consolidate_death(self.cfg.hyp.vasana_carry)  # habits fade into vasanas
        soul.recompute_karmic_load()

        if assess_moksha(soul, self.cfg.rules):
            soul.moksha = True
            self.liberated.add(soul.soul_id)
            self._substrate_absorb(soul)          # merge: wisdom enriches the ground (always)
            if self.cfg.rules.avatar_return:       # Vishishtadvaita: it also abides, and may return
                self.returnable.add(soul.soul_id)
            self.metrics.record_liberation(soul.lifetime_count)
            self._liberated_this_year += 1
            if not self._first_moksha_noted:
                self._first_moksha_noted = True
                self.note("moksha", f"The first soul attains moksha, after {soul.lifetime_count} lives")
        else:
            self.available.add(soul.soul_id)

    # -- avatars -----------------------------------------------------------
    def _avatars_alive(self) -> int:
        return sum(1 for p in self.persons.values() if p.is_avatar)

    def _maybe_descend_avatar(self, yuga) -> None:
        """In a dark age (Dvapara/Kali), if *behavioural* dharma has declined —
        the rate of aligned choice has fallen below threshold — and a liberated
        soul is willing, one descends. Freely, since no karma compels it. Dharma
        here is what people DO, not what their souls privately are: a hostile age
        makes even decent souls act badly, and that is the decline an avatar meets.
        At most one walks at a time."""
        if not self.cfg.rules.avatar_return or not self.returnable:
            return
        if yuga.hardness < 0.7 or self._avatars_alive() > 0:   # only the dark ages
            return
        if getattr(self, "_last_cooperation", 1.0) > self.cfg.hyp.avatar_dharma_threshold:
            return
        sid = self.rng.choice(sorted(self.returnable, key=lambda x: self.souls[x].serial))
        self.returnable.discard(sid)
        soul = self.souls[sid]                      # already perfected; retains its state
        body = Body(soul_id=sid, age=self.rng.randint(22, 30),
                    sex=self.rng.choice(["female", "male"]),
                    genome=Genome(health_potential=0.9, intelligence_potential=0.95,
                                  emotional_sensitivity=0.5, aggression_tendency=0.1,
                                  sociability=0.85, fertility=0.3, longevity=0.85))
        soul.current_body_id = body.body_id
        p = Person(soul=soul, body=body)
        p.is_avatar = True
        self.persons[body.body_id] = p
        self.avatar_descents += 1
        self._avatar_this_year = 1
        self.note("avatar", "Dharma has fallen; a liberated one descends")

    def _mind_cycle(self, yuga) -> None:
        """Yearly inner weather: fatigue recovers with rest; each soul's gunas
        drift toward the age's ambient climate. In Kali the weather itself is
        agitation and inertia — the charioteer works uphill."""
        hyp = self.cfg.hyp
        for person in self.persons.values():
            person.fatigue = max(0.0, person.fatigue * (1.0 - hyp.fatigue_recovery))
            s = person.soul
            s.sattva += hyp.guna_drift * (yuga.ambient_sattva - s.sattva)
            s.rajas += hyp.guna_drift * (yuga.ambient_rajas - s.rajas)
            s.tamas += hyp.guna_drift * (yuga.ambient_tamas - s.tamas)
            s.normalize_gunas()

    def _life_events(self, yuga) -> None:
        hyp = self.cfg.hyp
        avatar_present = self._avatars_alive() > 0
        # Field relief: while an avatar walks, the age itself lightens — truth is
        # easier to see and temptation loosens — reopening real choice.
        eff_yuga = yuga
        teaching = 0.0
        if avatar_present:
            eff_yuga = replace(
                yuga,
                temptation=yuga.temptation * (1.0 - hyp.avatar_field_relief),
                misinformation=yuga.misinformation * (1.0 - hyp.avatar_field_relief),
            )
            teaching = hyp.avatar_teaching_boost
        if self.tempt_bias:
            eff_yuga = replace(eff_yuga,
                               temptation=clamp(eff_yuga.temptation + self.tempt_bias))
        for person in list(self.persons.values()):
            if not person.is_adult(self.cfg.rules.adult_age):
                continue
            n_events = 1 + (1 if self.rng.random() < 0.25 else 0)
            for _ in range(n_events):
                event = self.rng.choice(EVENT_TEMPLATES)
                decision = choose_action(person, event, eff_yuga, hyp, self.rng)
                # The avatar acts (always aligned, lifting the world) but is beyond
                # refinement — no karma updates its already-perfected soul.
                if not person.is_avatar:
                    apply_outcome(person, event, decision, eff_yuga, hyp,
                                  integration_bonus=teaching)
                    # a public act may leave a trace — witnesses see the OUTWARD
                    # act only; the inner kind goes to the noncausal audit
                    self.culture.maybe_trace(person, event.condition,
                                             decision.action.alignment,
                                             decision, self.year)
                # measurement only
                self._choice_total += 1
                if decision.action.alignment > 0:
                    self._choice_aligned += 1
                if decision.action.alignment <= -1.0 + 1e-9:
                    self._choice_violent += 1
                if decision.noticed:
                    self._noticed += 1
                if not decision.veto_needed:
                    self._effortless += 1
                if decision.veto_attempted:
                    self._veto_attempts += 1
                    if decision.veto_won:
                        self._veto_wins += 1

    # -- guidance (v3): what schools each inner enemy ------------------------
    # kama is schooled by a partner's non-attachment, krodha by compassion,
    # mada by humility, moha by discernment, matsarya by unity. The design
    # routes you toward your teacher and calls the routing desire.
    OPPOSING = {"kama": "non_attachment", "krodha": "compassion",
                "lobha": "non_attachment", "moha": "discernment",
                "mada": "humility", "matsarya": "unity_awareness"}

    def _teaching_fit(self, a: Person, b: Person) -> float:
        """How much b's presence would school a's ruling enemy."""
        sa = a.soul
        dv = max(INSTABILITIES, key=lambda v: getattr(sa, v))
        return getattr(sa, dv) * getattr(b.soul, self.OPPOSING[dv])

    # -- attraction (v3) ----------------------------------------------------
    # Not a coin flip: two people are drawn together by resonance across every
    # layer a person IS in this model —
    #   gunas      : similar inner weather feels like home (dot of the simplex)
    #   temperament: genome sociability/emotional-sensitivity compatibility
    #   character  : virtue homophily — like seeks like (the soul layer)
    #   age        : proximity
    # plus irreducible spark. Souls pair for reasons; children inherit through
    # three channels (genome, soul, era) from parents who CHOSE each other,
    # which lets assortative patterns emerge across generations.
    def _attraction(self, a: Person, b: Person) -> float:
        sa, sb = a.soul, b.soul
        guna = sa.sattva * sb.sattva + sa.rajas * sb.rajas + sa.tamas * sb.tamas
        ga, gb = a.body.genome, b.body.genome
        temperament = 1.0 - 0.5 * (abs(ga.sociability - gb.sociability)
                                   + abs(ga.emotional_sensitivity - gb.emotional_sensitivity))
        va = sum(getattr(sa, v) for v in CORE_VIRTUES) / len(CORE_VIRTUES)
        vb = sum(getattr(sb, v) for v in CORE_VIRTUES) / len(CORE_VIRTUES)
        homophily = 1.0 - abs(va - vb)
        age = 1.0 / (1.0 + abs(a.body.age - b.body.age) / 12.0)
        spark = self.rng.random() * 0.35
        chemistry = 0.30 * guna * 2.0 + 0.20 * temperament + 0.25 * homophily + 0.15 * age + spark
        # guidance: desire as the design's routing layer
        h = self.cfg.hyp
        guidance = 0.0
        if h.attraction_guidance > 0:
            teach = 0.5 * (self._teaching_fit(a, b) + self._teaching_fit(b, a))
            guidance += h.attraction_guidance * 0.5 * teach
            thread = sa.threads.get(str(sb.soul_id), 0.0)
            if thread:  # recognition — you have met before
                guidance += h.attraction_guidance * h.thread_pull * 0.9 * thread
        return chemistry + guidance

    def _reproduction(self, yuga) -> int:
        rules, hyp = self.cfg.rules, self.cfg.hyp
        adults = [p for p in self.persons.values() if p.is_adult(rules.adult_age)]

        # courtship: each unpartnered woman meets a handful of unpartnered men
        # and pairs with the most attractive IF the pull is strong enough
        singles_f = [p for p in adults if p.partner_id is None and p.body.sex == "female"]
        singles_m = [p for p in adults if p.partner_id is None and p.body.sex == "male"]
        self.rng.shuffle(singles_f)
        for f in singles_f:
            if not singles_m:
                break
            met = self.rng.sample(singles_m, min(6, len(singles_m)))
            best = max(met, key=lambda m: self._attraction(f, m))
            pull = self._attraction(f, best)
            if self.rng.random() < hyp.pairing_prob * clamp(pull, 0.1, 1.6):
                f.partner_id = best.body_id
                best.partner_id = f.body_id
                f.bond_years = best.bond_years = 0
                singles_m.remove(best)
                if str(best.soul.soul_id) in f.soul.threads:
                    self.reunions += 1
                    self.note("bond", "Two souls, long entangled, find each other again")
                    for pp in (f, best):
                        if len(pp.notable) < 6:
                            pp.notable.append(f"at {pp.body.age}, met a soul known from another life")

        births = 0
        for f in adults:
            if f.body.sex != "female" or f.partner_id is None:
                continue
            m = self.persons.get(f.partner_id)
            if m is None or not m.alive:
                f.partner_id = None
                f.bond_years = 0
                continue
            # the bond deepens with years — or, drifted far apart, dissolves
            f.bond_years += 1
            m.bond_years = f.bond_years
            if f.bond_years > 3 and self._attraction(f, m) < 0.55 and self.rng.random() < 0.06:
                f.partner_id = m.partner_id = None
                f.bond_years = m.bond_years = 0
                continue
            if not f.body.fertile(rules.adult_age):
                continue
            fert = (f.body.genome.fertility + m.body.genome.fertility) / 2.0
            # F_fertility x F_relationship x F_era: conception favors settled
            # bonds and is depressed by a harsh age (resource pressure proxy)
            bond_f = 0.55 + 0.12 * min(f.bond_years, 5)
            p_conceive = (hyp.base_conception_prob * (0.5 + fert) * bond_f
                          * (1.0 - 0.25 * yuga.hardness))
            if self.rng.random() < p_conceive:
                soul = self._select_soul_for_birth(mother=f, father=m)
                if soul is None:
                    continue  # no soul available to incarnate
                baby = Body(
                    soul_id=soul.soul_id,
                    age=0,
                    sex=self.rng.choice(["female", "male"]),
                    genome=child_genome(f.body.genome, m.body.genome, self.rng),
                    mother_id=f.body_id,
                    father_id=m.body_id,
                )
                soul.current_body_id = baby.body_id
                baby_p = Person(soul=soul, body=baby)
                baby_p.snapshot_start()
                self.persons[baby.body_id] = baby_p
                births += 1
        return births

    def _exposure(self, adults) -> None:
        """Stochastic exposure: hearing a story lays a weak cultural groove —
        a this-life samskara by shravana. Availability, never alignment; the
        chariot still decides. Unexposed agents receive nothing."""
        hyp = self.cfg.hyp
        if hyp.exemplar_pull <= 0:
            return
        story_myths = [m for m in self.religion.myths if m.story is not None]
        if not story_myths or not adults:
            return
        total = sum(m.strength for m in story_myths)
        p_hear = min(0.5, total / (0.8 * len(adults) + 1))
        weights = [m.strength for m in story_myths]
        wsum = sum(weights)
        for person in adults:
            if self.crng.random() > p_hear:
                continue
            r = self.crng.uniform(0, wsum)
            acc = 0.0
            m = story_myths[-1]
            for i, w in enumerate(weights):
                acc += w
                if r <= acc:
                    m = story_myths[i]
                    break
            sc = m.story
            a = sc.align
            act = ("aligned" if a >= 0.7 else "compromise" if a >= 0 else
                   "avoid" if a >= -0.6 else "unaligned")
            key = f"{sc.condition}:{act}"
            person.cultural[key] = min(0.6, person.cultural.get(key, 0.0)
                                       + hyp.exemplar_pull * 0.05)

    # -- driver ------------------------------------------------------------
    def _measure(self, yuga, cosmic_cycle: int, births: int, deaths: int) -> None:
        souls = [p.soul for p in self.persons.values()]
        n = max(len(souls), 1)
        avg_v = sum(s.mean_virtue() for s in souls) / n
        avg_i = sum(s.mean_instability() for s in souls) / n
        avg_r = sum(s.mean_robustness() for s in souls) / n
        tot = max(self._choice_total, 1)
        ladder = {"mineral": 0, "plant": 0, "animal": 0}
        for sid in self.maturing:
            ladder[self.souls[sid].yoni_stage] += 1
        vice = {v: (sum(getattr(s, v) for s in souls) / n if souls else 0.0)
                for v in INSTABILITIES}
        rec = YearRecord(
            year=self.year,
            cosmic_cycle=cosmic_cycle,
            yuga=yuga.name,
            population=len(self.persons),
            births=births,
            deaths=deaths,
            liberated_this_year=self._liberated_this_year,
            liberated_total=len(self.liberated),
            avg_virtue=avg_v,
            avg_instability=avg_i,
            avg_robustness=avg_r,
            cooperation_rate=self._choice_aligned / tot,
            violence_rate=self._choice_violent / tot,
            pool_mineral=ladder["mineral"],
            pool_plant=ladder["plant"],
            pool_animal=ladder["animal"],
            pool_human_waiting=len(self.available),
            yoni_arrivals=getattr(self, "_yoni_arrivals", 0),
            pralaya=self._pralaya_this_year,
            souls_total=self.souls_created,
            vice_kama=vice["kama"], vice_krodha=vice["krodha"], vice_lobha=vice["lobha"],
            vice_moha=vice["moha"], vice_mada=vice["mada"], vice_matsarya=vice["matsarya"],
            avatar=self._avatar_this_year,
            avatars_alive=self._avatars_alive(),
            avatar_total=self.avatar_descents,
            substrate_virtue=self.substrate_virtue(),
            returnable=len(self.returnable),
            avg_buddhi=(sum(s.buddhi for s in souls) / n if souls else 0.0),
            avg_sattva=(sum(s.sattva for s in souls) / n if souls else 0.0),
            avg_rajas=(sum(s.rajas for s in souls) / n if souls else 0.0),
            avg_tamas=(sum(s.tamas for s in souls) / n if souls else 0.0),
            avg_compulsion=(sum(s.compulsion_ewma for s in souls) / n if souls else 0.0),
            noticing_rate=self._noticed / tot,
            effortless_rate=self._effortless / tot,
            veto_rate=self._veto_attempts / tot,
            veto_win_rate=(self._veto_wins / self._veto_attempts
                           if self._veto_attempts else 0.0),
            myths_alive=self.religion.counts()[0],
            institutions=self.religion.counts()[1],
            doctrine_accuracy=self.religion.doctrine_accuracy(),
            doctrine_coverage=self.religion.doctrine_coverage(),
            artworks_alive=len(self.arts.works),
            classics=len(self.arts.library),
            historical_fidelity=self.culture.fidelity(
                [m for m in self.religion.myths if m.story is not None]),
            story_myths=sum(1 for m in self.religion.myths if m.story is not None),
        )
        # stash this year's behavioural-dharma signal for next year's avatar check
        self._last_cooperation = self._choice_aligned / tot
        self.metrics.add(rec)

    def step(self) -> None:
        yuga, cosmic_cycle = self.clock.at(self.year)
        self._liberated_this_year = 0
        self._pralaya_this_year = 0
        self._avatar_this_year = 0
        self._choice_total = 0
        self._choice_aligned = 0
        self._choice_violent = 0
        self._noticed = 0
        self._effortless = 0
        self._veto_attempts = 0
        self._veto_wins = 0

        # Pralaya at each mahayuga boundary (Kali -> new Satya): dissolve and
        # re-manifest. The wheel turns; the cosmos does not end.
        if self.cfg.rules.pralaya_at_mahayuga and cosmic_cycle != self._last_cycle:
            self._pralaya()
            self._pralaya_this_year = 1
            self._last_cycle = cosmic_cycle

        self._creation()
        self._yoni_arrivals = self._yoni_ladder()
        self._maybe_descend_avatar(yuga)   # a liberated one returns when dharma is low
        self._mind_cycle(yuga)             # fatigue recovers; gunas drift with the age
        deaths = self._aging_and_death()
        self._life_events(yuga)
        births = self._reproduction(yuga)

        # Deeds become accounts (and lies); stories land on hearers as grooves
        adults = [p for p in self.persons.values()
                  if p.is_adult(self.cfg.rules.adult_age) and not p.is_avatar]
        self.culture.utter(adults, self.year, self.cfg.hyp)
        self._exposure(adults)
        for kind, text in self.arts.step(self, yuga, adults):
            self.note(kind, text)

        # The meta-loop: the world's own inhabitants write and rewrite its scriptures
        for kind, text in self.religion.step(self, yuga):
            self.note(kind, text)

        # Safety net: if the manifest world collapses mid-cycle while souls remain
        # in the unmanifest, a new Satya still dawns rather than the run ending.
        if not self.persons and self.available:
            self._pralaya()
            self._pralaya_this_year = 1

        self._measure(yuga, cosmic_cycle, births, deaths)
        self.year += 1

    def run(self, verbose: bool = True) -> MetricsLog:
        for _ in range(self.cfg.years):
            self.step()
            # The cosmos only truly ends if EVERY jiva has been liberated with no
            # unmanifest souls left to re-manifest — sarva-mukti, astronomically
            # far off while prakriti keeps creating. Otherwise the wheel turns.
            if not self.persons and not self.available and not self.maturing:
                if verbose:
                    print(f"[year {self.year}] sarva-mukti: every soul liberated; the wheel stops.")
                break
        return self.metrics
