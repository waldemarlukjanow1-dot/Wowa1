"""Short (~16 s), loopable, high-comment 'find it' puzzles with a coordinate grid (comment "C7").

Built for reach on a small account: bright colours, challenge visible in frame 0, comment bait with grid
coordinates, very short so completion rate and rewatches are high, and the last frame loops into the first.

Render all:  python3 -m films.viral_shorts
Preview:     python3 -m films.viral_shorts --sheet
"""
import math
import random
import sys

from engine import sfx
from engine.gfx import INK, back_out, ease, ease_out, lerp, prog
from engine.render import Film, Scene, render, stills
from films.illusions import CX, ding
from films.gehirntest_konzentration import buzz, fly, fly_path

T_SEARCH = 10.0            # countdown
T_REVEAL = 10.6            # answer appears
T_LOOP = 14.4              # start fading back to the first frame
DUR = 15.4
RED = (226, 36, 48)

GX0, GX1, GY0, GY1 = 140, 900, 640, 1440       # grid area (labels sit left of / above it)


def heartbeat_track(d):
    """Heartbeat that speeds up towards the end of the countdown."""
    out = []
    t = 0.6
    while t < T_SEARCH - 0.2:
        out.append((t, sfx.heartbeat(), lerp(0.35, 0.8, t / T_SEARCH)))
        t += lerp(0.95, 0.42, t / T_SEARCH)
    return out


def make_short(spec):
    cols, rows = spec["cols"], spec["rows"]
    rnd = random.Random(spec["seed"])
    oi, oj = rnd.randrange(1, cols - 1), rnd.randrange(2, rows - 1)
    answer = f"{'ABCDEFGHIJ'[oi]}{oj + 1}"
    bg, ink = spec["bg"], spec.get("ink", INK)
    cw, ch = (GX1 - GX0) / cols, (GY1 - GY0) / rows

    def cell(i, j):
        return GX0 + cw * (i + 0.5), GY0 + ch * (j + 0.5)

    def draw(c, t):
        c.fill(bg)
        reveal = ease(prog(t, T_REVEAL, T_REVEAL + 0.35)) * (1 - ease(prog(t, T_LOOP, T_LOOP + 0.6)))
        # hook text: present from the very first frame
        c.text(CX, 268, spec["hook1"], 66, ink)
        c.text(CX, 350, spec["hook2"], 66, RED)
        # countdown
        if t < T_SEARCH or t >= T_LOOP:
            k = 1 - prog(t, 0.0, T_SEARCH) if t < T_SEARCH else 1.0
            c.rect(CX - 380, 418, CX + 380, 440, fill=(*ink, 40), r=11)
            c.rect(CX - 380, 418, CX - 380 + 760 * k, 440, fill=RED if k < 0.3 else ink, r=11)
            n = max(1, int(math.ceil(T_SEARCH - t))) if t < T_SEARCH else 10
            pulse = 1 + 0.12 * max(0.0, 1 - ((T_SEARCH - t) % 1.0) / 0.25) if t < T_SEARCH else 1
            c.circle(CX, 520, 50 * pulse, fill=RED if (t < T_SEARCH and n <= 3) else ink)
            c.text(CX, 522, str(n), int(56 * pulse), bg)
        elif t < T_REVEAL:
            p = back_out(prog(t, T_SEARCH, T_SEARCH + 0.2))
            c.text(CX, 520, "ZEIT UM!", int(76 * p) + 1, RED)
        # coordinate labels (the comment bait)
        for i in range(cols):
            x, _ = cell(i, 0)
            c.text(x, GY0 - 34, "ABCDEFGHIJ"[i], 40, RED)
        for j in range(rows):
            _, y = cell(0, j)
            c.text(GX0 - 48, y, str(j + 1), 36, RED)
        # the wall of characters
        for i in range(cols):
            for j in range(rows):
                x, y = cell(i, j)
                odd = (i, j) == (oi, oj)
                a = 255 if odd else int(255 * (1 - 0.8 * reveal))
                c.text(x, y, spec["odd"] if odd else spec["base"], spec["size"], (*ink, a), weight=spec["weight"])
        if reveal > 0:
            x, y = cell(oi, oj)
            r = max(cw, ch) * 0.8 * (2.6 - 1.6 * back_out(prog(t, T_REVEAL, T_REVEAL + 0.4)))
            c.circle(x, y, r, outline=(*RED, int(255 * reveal)), w=10)
            c.rect(CX - 330, 470, CX + 330, 572, fill=(*RED, int(255 * reveal)), r=50)
            c.text(CX, 522, f"Lösung: {answer}", 58, (255, 255, 255, int(255 * reveal)))
        # one distraction: a fly crossing the grid
        if spec.get("fly"):
            p = fly_path(t, *spec["fly"], (1200, 1350), (-150, 760), 140, spec["seed"])
            if p:
                fly(c, *p, t, s=2.2)

    snd = [(k + 0.0, sfx.click(), 0.45) for k in range(1, int(T_SEARCH))]
    snd += [(T_SEARCH - n, sfx.beep(900, 0.12), 0.5) for n in (3, 2, 1)]
    snd += heartbeat_track(T_SEARCH)
    snd += [(T_SEARCH, sfx.bass_hit(), 0.7), (T_REVEAL, ding(), 0.9), (T_REVEAL, sfx.whoosh(0.4), 0.4),
            (T_LOOP, sfx.whoosh(0.6, False), 0.35)]
    if spec.get("fly"):
        snd.append((spec["fly"][0], buzz(spec["fly"][1] - spec["fly"][0]), 0.55))
    film = Film(spec["slug"], answer, [Scene(DUR, draw, None, snd, header=False, zoom=1.0, ty=1330.0)])
    film.answer = answer
    return film


SHORTS = [
    dict(slug="oe", hook1="Nur 1 von 10 findet", hook2="das Ö in 10 Sekunden", base="O", odd="Ö",
         cols=8, rows=12, size=60, weight="Bold", seed=201, bg=(255, 214, 64), fly=(4.0, 6.2)),
    dict(slug="q", hook1="Siehst du das O", hook2="zwischen den Qs?", base="Q", odd="O",
         cols=8, rows=12, size=60, weight="Bold", seed=202, bg=(120, 220, 255), fly=(5.0, 7.0)),
    dict(slug="acht", hook1="Adleraugen-Test:", hook2="Finde die 8!", base="B", odd="8",
         cols=8, rows=12, size=60, weight="Bold", seed=203, bg=(255, 150, 190), fly=(4.5, 6.6)),
]

if __name__ == "__main__":
    for spec in SHORTS:
        film = make_short(spec)
        print(spec["slug"], "answer", film.answer, f"{film.dur:.1f}s")
        if "--sheet" in sys.argv:
            print(stills(film, [0.0, 5.0, 9.5, 10.2, 11.5, 15.3], f"output/preview_short_{spec['slug']}", cols=6,
                         scale=0.25))
        else:
            render(film, f"output/short_{spec['slug']}.mp4")
