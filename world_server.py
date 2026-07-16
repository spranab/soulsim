#!/usr/bin/env python3
"""The real soulsim engine, live and visible.

Runs the actual Python engine (yoni ladder, genetics, chariot, cascade,
substrate, avatars, religion — everything) in a background thread and streams
the world to a browser over Server-Sent Events. Pure stdlib; no installs.

    python3 world_server.py                      # Bharatavarsha, opens browser
    python3 world_server.py --theme academy --souls 1000 --port 8777

Endpoints:  /  the world view · /events SSE stream · /soul?pid= real soul data
            /cmd POST {op: pause|play|speed|avatar|pralaya|miracle|calamity|
                        bless|tempt}  · /meta theme + places
"""
from __future__ import annotations

import argparse
import json
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from soulsim.config import SimConfig, FixedRules
from soulsim.soul import CORE_VIRTUES, INSTABILITIES, CONDITIONS
from soulsim.world import Universe

THEMES = {
    "bharat": dict(
        world="Bharatavarsha",
        ages=["Satya", "Treta", "Dvapara", "Kali"],
        places=[{"n": "the river ghat", "x": 200, "y": 430, "k": "steps"},
                {"n": "the banyan court", "x": 430, "y": 300, "k": "tree"},
                {"n": "the mountain ashram", "x": 840, "y": 170, "k": "hut"},
                {"n": "the spice bazaar", "x": 600, "y": 430, "k": "stalls"},
                {"n": "the temple tank", "x": 320, "y": 200, "k": "pool"},
                {"n": "the burning ground", "x": 790, "y": 460, "k": "pyre"}],
        names=["Aruni", "Kavya", "Bodhi", "Tara", "Ishan", "Mira", "Dev", "Lila",
               "Ravi", "Anaya", "Karan", "Ved", "Asha", "Nila", "Jai", "Uma"],
        libLabel="liberated", sky=["#1a1030", "#4a2440"], ground="#141024"),
    "academy": dict(
        world="Thornspire Academy",
        ages=["Age of Wonder", "Age of Study", "Age of Rivalry", "Age of Shadows"],
        places=[{"n": "Whispering Library", "x": 175, "y": 330, "k": "dome"},
                {"n": "the Undercroft", "x": 470, "y": 470, "k": "arch"},
                {"n": "Astronomy Spire", "x": 830, "y": 210, "k": "tower"},
                {"n": "Great Refectory", "x": 490, "y": 290, "k": "hall"},
                {"n": "Mirror Gallery", "x": 300, "y": 170, "k": "gallery"},
                {"n": "Forbidden Greenhouse", "x": 720, "y": 420, "k": "glass"}],
        names=["Elara", "Corvin", "Maeve", "Ondine", "Basil", "Wren", "Isolde",
               "Fen", "Aurelia", "Dorian", "Sable", "Petra", "Lucan", "Briar"],
        libLabel="beyond the veil", sky=["#0a0d1f", "#182448"], ground="#0e1526"),
    "station": dict(
        world="Ashvale Station",
        ages=["Founding Era", "Expansion Era", "Scarcity Era", "Blackout Era"],
        places=[{"n": "hydroponics bay", "x": 180, "y": 250, "k": "glass"},
                {"n": "the reactor deck", "x": 430, "y": 430, "k": "module"},
                {"n": "observation dome", "x": 850, "y": 200, "k": "dome"},
                {"n": "the cargo spine", "x": 620, "y": 320, "k": "module"},
                {"n": "the cryo vaults", "x": 300, "y": 440, "k": "arch"},
                {"n": "the long corridor", "x": 520, "y": 180, "k": "gallery"}],
        names=["Juno", "Cassian", "Vex", "Orla", "Dane", "Echo", "Marlow", "Zia",
               "Callis", "Nova", "Reyes", "Sol", "Indra", "Kite"],
        libLabel="ascended", sky=["#05070d", "#0c1526"], ground="#0a0f1a"),
}


class Live:
    """Owns the universe, the visual layer (positions, names), and SSE clients."""

    def __init__(self, args):
        self.theme = THEMES[args.theme]
        self.theme_key = args.theme
        cfg = SimConfig(seed=args.seed, years=10**9, initial_adults=200,
                        rules=FixedRules(soul_count=args.souls))
        self.u = Universe(cfg)
        self.lock = threading.RLock()
        self.playing = True
        self.yps = 4.0
        self.clients = []          # (wfile, lock)
        # visual layer
        self.vis = {}              # body_id -> dict(pid, x, y, place)
        self.names = {}            # body_id -> name
        self.pid2body = {}
        self.next_pid = 1
        self.chron_sent = 0
        import random
        self.vrng = random.Random(args.seed ^ 0xBEEF)

    # ---- visual layer ----
    def _ensure_vis(self):
        places = self.theme["places"]
        alive_ids = set()
        for bid, person in self.u.persons.items():
            alive_ids.add(bid)
            if bid not in self.vis:
                pi = self.vrng.randrange(len(places))
                p = places[pi]
                pid = self.next_pid; self.next_pid += 1
                self.vis[bid] = dict(pid=pid, place=pi,
                                     x=p["x"] + self.vrng.gauss(0, 26),
                                     y=p["y"] + 14 + self.vrng.gauss(0, 13))
                self.names[bid] = self.vrng.choice(self.theme["names"])
                self.pid2body[pid] = bid
            elif self.vrng.random() < 0.25:   # wander to a new place this year
                pi = self.vrng.randrange(len(places))
                p = places[pi]
                v = self.vis[bid]
                v["place"] = pi
                v["x"] = p["x"] + self.vrng.gauss(0, 26)
                v["y"] = p["y"] + 14 + self.vrng.gauss(0, 13)
        for bid in list(self.vis):
            if bid not in alive_ids:
                self.pid2body.pop(self.vis[bid]["pid"], None)
                del self.vis[bid]
                self.names.pop(bid, None)

    def snapshot(self):
        u = self.u
        self._ensure_vis()
        r = u.metrics.records[-1] if u.metrics.records else None
        souls = []
        for bid, person in u.persons.items():
            v = self.vis[bid]
            s = person.soul
            if person.is_avatar:
                k = 4
            elif person.body.age < u.cfg.rules.adult_age:
                k = 0
            else:
                g = [s.sattva, s.rajas, s.tamas]
                k = 1 + g.index(max(g))
            souls.append([v["pid"], round(v["x"]), round(v["y"]), k])
        ladder = {"mineral": 0, "plant": 0, "animal": 0}
        for sid in u.maturing:
            ladder[u.souls[sid].yoni_stage] += 1
        new_chron = [{"y": y, "k": k, "t": t}
                     for (y, k, t) in u.chronicle[self.chron_sent:]]
        self.chron_sent = len(u.chronicle)
        return {
            "y": u.year, "cc": u.year // 500,
            "ageIdx": ["Satya", "Treta", "Dvapara", "Kali"].index(
                u.clock.at(u.year)[0].name),
            "pop": len(u.persons), "lib": len(u.liberated),
            "virt": round(r.avg_virtue, 3) if r else 0,
            "eff": round(r.effortless_rate, 3) if r else 0,
            "doct": round(r.doctrine_accuracy, 3) if r else 0,
            "myths": len(u.religion.myths),
            "avat": sum(1 for p in u.persons.values() if p.is_avatar),
            "ladder": ladder, "waiting": len(u.available),
            "souls": souls, "chron": new_chron,
            "playing": self.playing, "yps": self.yps,
        }

    # ---- sim thread ----
    def run(self):
        while True:
            if not self.playing:
                time.sleep(0.1)
                self.push()          # keep clients fresh while paused
                continue
            t0 = time.time()
            with self.lock:
                self.u.step()
            self.push()
            dt = time.time() - t0
            time.sleep(max(0.0, 1.0 / self.yps - dt))

    def push(self):
        with self.lock:
            data = "data: " + json.dumps(self.snapshot(),
                                         separators=(",", ":")) + "\n\n"
        dead = []
        for wf in self.clients:
            try:
                wf.write(data.encode()); wf.flush()
            except Exception:
                dead.append(wf)
        for wf in dead:
            self.clients.remove(wf)

    # ---- commands ----
    def cmd(self, body):
        op = body.get("op")
        with self.lock:
            u = self.u
            if op == "pause": self.playing = False
            elif op == "play": self.playing = True
            elif op == "speed": self.yps = max(0.5, min(30, float(body.get("yps", 4))))
            elif op == "tempt": u.tempt_bias = float(body.get("v", 0))
            elif op == "avatar": return {"ok": u.god_avatar()}
            elif op == "pralaya": u.god_pralaya()
            elif op == "miracle":
                targets = self._radius_souls(body)
                n = u.god_miracle([p.soul for p in targets] if targets is not None else None)
                return {"ok": True, "n": n}
            elif op == "calamity":
                targets = self._radius_souls(body)
                n = u.god_calamity(targets)
                return {"ok": True, "n": n}
            elif op == "bless":
                bid = self.pid2body.get(int(body.get("pid", -1)))
                if bid and bid in u.persons:
                    u.god_miracle([u.persons[bid].soul], d_sattva=0.15)
                    u.note("reform", f"A quiet grace touches {self.names.get(bid,'a soul')}")
                    return {"ok": True}
                return {"ok": False}
        if not self.playing:
            self.push()
        return {"ok": True}

    def _radius_souls(self, body):
        if "x" not in body:
            return None
        x, y, rad = float(body["x"]), float(body["y"]), float(body.get("r", 130))
        out = []
        for bid, person in self.u.persons.items():
            v = self.vis.get(bid)
            if v and (v["x"] - x) ** 2 + (v["y"] - y) ** 2 <= rad * rad:
                out.append(person)
        return out

    def biography(self, p) -> str:
        """The inspector's answer to: why did this soul become this person?"""
        s = p.soul
        parts = [f"Born because {s.born_reason or 'its turn on the wheel came round'}."]
        for h in s.history[-3:]:
            arrow = ("virtue rose" if h["dv"] > 0.02 else
                     "virtue fell" if h["dv"] < -0.02 else "virtue held")
            line = (f"Life {h['n']}: a {h['role']} for {h['years']} years; "
                    f"{arrow} ({h['dv']:+.2f}), ruled by {h['enemy']}")
            if h.get("note"):
                line += f" — {h['note']}"
            parts.append(line + ".")
        parts.append(f"This life: {p.life_veto} impulses mastered, "
                     f"{p.life_akrasia} seen but lost, {p.life_unseen} unseen, "
                     f"{p.life_effortless} effortless.")
        if p.notable:
            parts.append("Remembered: " + "; ".join(p.notable[:3]) + ".")
        return " ".join(parts)

    def soul_detail(self, pid):
        with self.lock:
            bid = self.pid2body.get(pid)
            if not bid or bid not in self.u.persons:
                return {"ok": False}
            p = self.u.persons[bid]
            s = p.soul
            return {"ok": True, "name": self.names.get(bid, "a soul"),
                    "born": s.born_reason,
                    "bio": self.biography(p),
                    "history": s.history[-6:],
                    "avatar": p.is_avatar, "age": p.body.age,
                    "lives": s.lifetime_count + 1,
                    "virtues": {k: round(getattr(s, k), 3) for k in CORE_VIRTUES},
                    "vices": {k: round(getattr(s, k), 3) for k in INSTABILITIES},
                    "buddhi": round(s.buddhi, 3),
                    "compulsion": round(s.compulsion_ewma, 3),
                    "gunas": [round(s.sattva, 3), round(s.rajas, 3), round(s.tamas, 3)],
                    "robustness": {c: round(getattr(s, "robustness_" + c), 3)
                                   for c in CONDITIONS},
                    "tested": s.tested,
                    "samskaras": dict(sorted(s.samskaras.items(),
                                             key=lambda kv: -kv[1])[:5])}


LIVE: Live = None
PAGE: bytes = b""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(PAGE)))
            self.end_headers()
            self.wfile.write(PAGE)
        elif u.path == "/meta":
            self._json({"theme": LIVE.theme, "themeKey": LIVE.theme_key,
                        "souls": LIVE.u.cfg.rules.soul_count})
        elif u.path == "/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            LIVE.clients.append(self.wfile)
            try:
                self.wfile.write(("data: " + json.dumps(LIVE.snapshot(),
                                  separators=(",", ":")) + "\n\n").encode())
                self.wfile.flush()
                while True:
                    time.sleep(3600)
            except Exception:
                pass
        elif u.path == "/soul":
            pid = int(parse_qs(u.query).get("pid", ["-1"])[0])
            self._json(LIVE.soul_detail(pid))
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        if urlparse(self.path).path == "/cmd":
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
            self._json(LIVE.cmd(body))
        else:
            self.send_response(404); self.end_headers()


def main():
    global LIVE, PAGE
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", choices=list(THEMES), default="bharat")
    ap.add_argument("--souls", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--port", type=int, default=8777)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    import os
    here = os.path.dirname(os.path.abspath(__file__))
    PAGE = open(os.path.join(here, "world_live.html"), "rb").read()

    LIVE = Live(args)
    threading.Thread(target=LIVE.run, daemon=True).start()

    srv = ThreadingHTTPServer(("127.0.0.1", args.port), H)
    url = f"http://127.0.0.1:{args.port}"
    print(f"⚘ {LIVE.theme['world']} is alive at {url}  "
          f"(theme={args.theme}, souls={args.souls}, seed={args.seed})")
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    srv.serve_forever()


if __name__ == "__main__":
    main()
