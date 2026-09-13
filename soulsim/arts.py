"""Arts — souls giving form to their inner life.

Myth carries CLAIMS (who did what; what is true) and grooves action
availability. Art carries RASA — the Natyashastra's aesthetic essences — and
tunes the hearer's gunas. A poem of grief does not tell you what happened or
what to do; it changes the weather inside you. Two channels, two ancient
theories, both mechanized:

  story  -> exemplar groove   (what feels DOABLE)
  art    -> rasa resonance    (what the inner climate IS)

Creation is not reserved for the clear: suffering composes as much as
serenity. A soul creates when its life has pressed hard enough on it —
intensity comes from the life ledger (notable moments, akrasia, vetoes won),
and WHICH rasa emerges is read from what the soul actually is: fury from
krodha, grief from loss, wonder from clarity in a bright age, peace from
unity. Art outlives its maker; the strongest works become classics, and a
world slowly builds a library written by nobody living.

THE CATHARSIS DIAL (hypothesis, sweepable): does karuna-art purge the hearer
(Aristotle: witnessed sorrow -> sattva) or contaminate (Plato: feeding grief
-> tamas)? `catharsis` = +1 Aristotle, -1 Plato, 0 inert. Two millennia of
aesthetics, one knob, measurable outcome.

Wall discipline: creation triggers and rasa selection read only soul/person
state (Layer F/H); rendered verse text is narration — never read by physics;
art affects hearers only through shift_gunas, an existing fixed channel, at
hypothesis-knob strength, on the culture rng stream.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List

# rasa -> (d_sattva, d_rajas, d_tamas) per exposure, before art_pull scaling.
# karuna is special-cased by the catharsis dial.
RASAS: Dict[str, tuple] = {
    "shringara": (0.006, 0.004, 0.0),     # love / beauty
    "hasya":     (0.008, 0.0, -0.006),    # mirth
    "karuna":    (0.0, 0.0, 0.0),         # sorrow-compassion — see catharsis
    "raudra":    (0.0, 0.010, 0.0),       # fury
    "vira":      (0.005, 0.007, 0.0),     # heroism
    "bhayanaka": (0.0, 0.003, 0.008),     # terror
    "bibhatsa":  (0.0, 0.0, 0.009),       # disgust / world-weariness
    "adbhuta":   (0.010, 0.0, -0.003),    # wonder
    "shanta":    (0.012, -0.008, 0.0),    # peace
}
FORMS = ["poem", "song", "carving", "dance", "mural", "hymn", "lament", "tale-in-verse"]

# narration-only verse templates; {name}, {born}, {age} slots come from true state
VERSE = {
    "karuna": ["what the river took, the river keeps;\nI sing so {name} need not weep alone",
               "ash on the water, and still the lamp —\nwhat was taken from {name}, told slowly"],
    "raudra": ["let the granaries burn that lied to us —\n{name} carves each blow into the beam",
               "I was told to kneel in the {age};\nthis drum is my answer"],
    "shanta": ["the wheel turns; I no longer count the turns.\nsit with me; the evening is enough",
               "{name} set down the wanting like a water-jar,\nand the path grew quiet"],
    "vira":   ["stand where the ground breaks, {name} —\nthe age is dark so that you can be seen",
               "one held the line when the {age} pressed;\nthe song remembers the holding, not the loss"],
    "adbhuta":["who hung the liberated in the sky like lamps?\nI counted; there is one more tonight",
               "the {age} opened like an eye —\nand everything ordinary shone"],
    "shringara": ["I knew your walk before I knew your name;\nsome threads are older than the loom",
                  "meet me where the two paths cross —\nthe stars can chaperone"],
    "hasya":  ["the sage tripped on his own sandal;\neven the wheel laughs, turning",
               "{name} traded wisdom for a joke\nand the market called it a fair price"],
    "bhayanaka": ["do not go past the last lamp in the {age};\nwhat waits there wears familiar faces",
                  "the dark is patient; it learned from us"],
    "bibhatsa": ["they gilded the rot and called it a shrine;\n{name} will not bow to perfume",
                 "count what the {age} sold: everything, twice"],
}


# The refrain couplet above is chosen on the culture stream, exactly as before.
# Around it, on the narration stream, a verse grows an opening and a closing —
# so no two hymns of the same rasa are the same poem. Slots come from true state.
OPENERS = {
    "karuna": ["{name} of {house} sat by the cold hearth and would not be moved;",
               "there is a hollow in the house where a voice used to be;",
               "the year the {age} took its share of us, {name} learned the weight of a name;",
               "do not tell me the river is kind —"],
    "raudra": ["hear it, {house} — {name} has counted the wrongs and will not stop counting;",
               "there is a fire that was banked too long in the {age};",
               "they thought the quiet one had no teeth;",
               "let the elders say what they will:"],
    "shanta": ["at evening in {house} the wheel is only a sound;",
               "{name} has walked the road until the road forgot to argue;",
               "in the {age} the light is honest, and there is nothing to defend;",
               "what is left when the wanting is set down? this:"],
    "vira":   ["when the {age} broke the ground under {house},",
               "there is a place where the line must be held or nothing is held;",
               "{name} did not ask to be the one standing;",
               "the drum says one name tonight and the name is {name}:"],
    "adbhuta": ["something in the {age} is not made of anything we know;",
                "{name} of {house} looked up and could not look down again;",
                "count the lamps in the dark — there are more than there were;",
                "who set the wheel spinning and left it so beautiful?"],
    "shringara": ["{name} walks the long way home through {house} to pass one door;",
                  "the {age} is only weather; you are the season;",
                  "I have a debt to you older than my name;",
                  "say nothing yet; the lamp has not been lit —"],
    "hasya":  ["listen, {house}, to the great matter of the sandal:",
               "{name} went to the market with a wise face and came back with a goose;",
               "the {age} is grim, the elders say, so we laughed until it wasn't;",
               "a joke is a small wheel; watch it go —"],
    "bhayanaka": ["in the {age} the road home is not the road you took;",
                  "{name} of {house} has seen what the well sees;",
                  "there is a sound the night makes when it has learned your name;",
                  "bar the door; it will not help, but bar the door —"],
    "bibhatsa": ["the {age} put its finger in every honey-pot of {house};",
                 "{name} has smelled the rot beneath the incense and says so;",
                 "they call it a feast; look at the bones;",
                 "spare me the temple and its accounts —"],
}
CLOSERS = {
    "karuna": ["so I go on singing, which is all a mouth can do for a wound.",
               "and the house of {house} keeps one lamp lit for the one who is not coming.",
               "grief is a debt the {age} collects slowly; {name} pays it a coin a day.",
               "sit with me; there is no hurry left to have."],
    "raudra": ["and when the fire is done there will be a clean place to stand.",
               "{name} will not kneel; the {age} can keep its perfume.",
               "write it on the beam; let the children read what we were.",
               "let it burn — some things are only true as ash."],
    "shanta": ["and the evening, being enough, asks nothing more of {name}.",
               "the wheel turns; {house} turns with it; nothing is lost that was true.",
               "this is what the {age} was for: to make the quiet audible.",
               "sit. the water-jar is full. it was always full."],
    "vira":   ["and the song remembers the standing, not the cost.",
               "{house} is a place again because {name} refused to move.",
               "the {age} was dark, which is why the one who stood could be seen.",
               "hold; hold; the dawn is nothing but people holding."],
    "adbhuta": ["and everything ordinary shone, and has not stopped shining.",
                "{name} came home and could not say it, and said it anyway.",
                "the {age} opened like an eye, and {house} was inside the looking.",
                "there is one more lamp tonight; I do not know whose."],
    "shringara": ["some threads are older than the loom; ours is one.",
                  "meet me where the two paths cross; the stars will not tell.",
                  "{name} of {house} knew your walk before your name, and knows it still.",
                  "the {age} may keep its ages; I have this hour."],
    "hasya":  ["and the wheel, hearing it, laughed, and turned a little easier.",
               "{name} says wisdom was a fair price for a goose; {house} agrees.",
               "even the {age} could not keep its face straight.",
               "the sage found his sandal. it was on his foot."],
    "bhayanaka": ["the dark is patient; it learned from {house}.",
                  "do not go past the last lamp; the {age} is waiting there in a familiar coat.",
                  "{name} bars the door each night and each night it is already open.",
                  "what waits there wears our faces, and is polite."],
    "bibhatsa": ["{name} will not bow to perfume; the rot is at least honest.",
                 "count what the {age} sold: everything, twice, and the receipt.",
                 "gild it again; {house} can see the beam under the gold.",
                 "spit, and go. there is nothing here to keep."],
}


def compose_verse(rasa: str, refrain: str, name: str, age: str, house: str,
                  nrng) -> str:
    """Narration only: grow the refrain into a short hymn on the narration dice."""
    slots = dict(name=name, age=age, house=house or "the house")
    parts = []
    r = nrng.random()
    if r < 0.8:
        parts.append(nrng.choice(OPENERS[rasa]).format(**slots))
    parts.append(refrain)
    if r > 0.2:
        parts.append(nrng.choice(CLOSERS[rasa]).format(**slots))
    return "\n".join(parts)


@dataclass
class Artwork:
    aid: int
    year: int
    age_name: str
    creator: str           # in-world name token
    form: str
    rasa: str
    intensity: float
    born_of: str           # true biographical spark, phrased for narration
    strength: float
    classic: bool = False
    verse: str = ""        # narration only — physics never reads this


class ArtSystem:
    MAX_WORKS = 100

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.works: List[Artwork] = []
        self.library: List[Artwork] = []   # classics, kept forever (the corpus)
        self._aid = 0

    # -- which rasa does THIS soul's state produce? ---------------------------
    def _rasa_for(self, person, yuga) -> tuple:
        s = person.soul
        recent_loss = any("loss" in n for n in person.notable)
        recent_power = any("power" in n for n in person.notable)
        scores = {
            "raudra": s.krodha * 1.2,
            "karuna": (0.9 if recent_loss else 0.0) + s.compassion * 0.4,
            "shringara": s.kama * 0.9,
            "shanta": s.unity_awareness * 1.3 + s.sattva * 0.5,
            "vira": (0.6 if recent_power else 0.0) + s.courage * 0.6,
            "bhayanaka": (s.moha * 0.8 if yuga.hardness >= 0.7 else 0.0),
            "bibhatsa": s.matsarya * 0.7 + (0.3 if yuga.hardness >= 0.7 else 0.0),
            "adbhuta": (s.sattva * 0.9 if yuga.hardness <= 0.4 else 0.0),
            "hasya": (person.body.genome.sociability if person.body.genome else 0.4) * 0.6,
        }
        for k in scores:
            scores[k] += self.rng.random() * 0.25
        rasa = max(scores, key=lambda k: scores[k])
        born = (person.notable[-1] if person.notable else
                f"a life of {max(RASAS, key=lambda r: scores.get(r, 0))}")
        return rasa, born

    def step(self, universe, yuga, adults) -> List[tuple]:
        hyp = universe.cfg.hyp
        rng = self.rng
        events: List[tuple] = []

        # 1. creation — pressed lives compose
        for person in adults:
            g = person.body.genome
            sens = g.emotional_sensitivity if g else 0.5
            intensity = min(1.0, 0.25 * len(person.notable)
                            + 0.04 * person.life_akrasia + 0.04 * person.life_veto)
            if rng.random() < hyp.art_rate * sens * (0.3 + intensity):
                if getattr(person, "name_token", None) is None:
                    # dice discipline: the mint rolls as before; the name is the
                    # annals name (one person, one name)
                    minted = universe.culture.mint_name()
                    person.name_token = getattr(person, "name", "") or minted
                rasa, born = self._rasa_for(person, yuga)
                self._aid += 1
                refrain = rng.choice(VERSE[rasa]).format(
                    name=person.name_token, born=born, age=yuga.name)
                annals = getattr(universe, "annals", None)
                verse = (compose_verse(rasa, refrain, person.name_token, yuga.name,
                                       getattr(person, "house", ""), annals.nrng)
                         if annals is not None else refrain)
                w = Artwork(aid=self._aid, year=universe.year, age_name=yuga.name,
                            creator=person.name_token, form=rng.choice(FORMS),
                            rasa=rasa, intensity=intensity, born_of=born,
                            strength=2.0 + 4.0 * intensity, verse=verse)
                if annals is not None:
                    annals.work(person, w)
                self.works.append(w)
                if rng.random() < 0.10:
                    events.append(("art", f"{w.creator} makes a {w.form} of {w.rasa}, born of {w.born_of}"))

        # 2. spread & decay — attention is preferential: the talked-about get
        # talked about more (strength^1.5 shares of a fixed budget), so winners
        # compound and a canon becomes possible; the rest die with their moment.
        pop = max(len(adults), 1)
        if self.works:
            budget = 0.15 * pop
            shares = [w.strength ** 1.15 * (1.0 + 0.6 * w.intensity) for w in self.works]
            ssum = sum(shares)
            for w, sh in zip(self.works, shares):
                w.strength += budget * sh / ssum
        retired = []
        universe_year = universe.year
        for w in self.works:
            w.strength *= 0.96
            if w.strength > 0.08 * pop and (universe_year - w.year) >= 15:
                # canonized: the work leaves the daily contest and enters the
                # library — remembered permanently, no longer hoarding attention
                w.classic = True
                self.library.append(w)
                retired.append(w)
                events.append(("art", f"'{w.form} of {w.creator}' enters the canon; "
                                      f"the world knows its {w.rasa} by heart"))
                annals = getattr(universe, "annals", None)
                if annals is not None:
                    annals.event(universe_year, "canon",
                                 f"the {w.form} of {w.creator} enters the canon",
                                 who=[w.creator], aid=w.aid, rasa=w.rasa, form=w.form)
        self.works = [w for w in self.works if w.strength >= 0.8 and w not in retired]
        self.works.sort(key=lambda w: w.strength, reverse=True)
        self.works = self.works[: self.MAX_WORKS]

        # 3. exposure — rasa tunes the hearer's gunas (the only causal channel)
        if hyp.art_pull > 0 and self.works:
            total = sum(w.strength for w in self.works)
            weights = [w.strength for w in self.works]
            wsum = sum(weights)
            p_hear = min(0.4, total / (0.8 * pop + 1))
            for person in adults:
                if rng.random() > p_hear:
                    continue
                r = rng.uniform(0, wsum)
                acc = 0.0
                w = self.works[-1]
                for i, wt in enumerate(weights):
                    acc += wt
                    if r <= acc:
                        w = self.works[i]
                        break
                if w.rasa == "karuna":
                    c = hyp.catharsis  # +1 Aristotle purges; -1 Plato contaminates
                    ds, dr, dt = 0.010 * max(c, 0), -0.006 * max(c, 0), 0.010 * max(-c, 0)
                else:
                    ds, dr, dt = RASAS[w.rasa]
                k = hyp.art_pull * (0.5 + w.intensity)
                person.soul.shift_gunas(d_sattva=ds * k, d_rajas=dr * k, d_tamas=dt * k)
        return events

    # -- measurement (read-only) ----------------------------------------------
    def dominant_rasa(self) -> str:
        if not self.works:
            return "-"
        agg: Dict[str, float] = {}
        for w in self.works:
            agg[w.rasa] = agg.get(w.rasa, 0.0) + w.strength
        return max(agg, key=lambda k: agg[k])
