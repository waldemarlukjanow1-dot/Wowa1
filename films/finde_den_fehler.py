"""'Finde den Fehler' - 6 levels of spot-the-odd-one-out, harder each level, > 60 s.

Render:  python3 -m films.finde_den_fehler
Preview: python3 -m films.finde_den_fehler --sheet
"""
import math
import random
import sys

from engine import sfx
from engine.gfx import back_out, ease, ease_out, lerp, prog
from engine.render import Film, Scene, render, stills
from films.illusions import BG, CX, GOLD, WHITE, ding, drone, follow_cta, text_block

RED = (230, 50, 60)
GRID = (90, 520, 900, 1400)          # left, top, right, bottom: clear of TikTok buttons
REVEAL = 2.6                         # seconds of solution per level


def level_text(lv, n, txt, cols, rows, odd, seed, size, weight="Bold", t_find=7.0, colour=WHITE):
    return dict(kind="text", lv=lv, n=n, txt=txt, cols=cols, rows=rows, odd=odd, seed=seed, size=size,
                weight=weight, t_find=t_find, colour=colour)


def level_colour(lv, n, cols, rows, base, diff, seed, t_find=7.0):
    return dict(kind="colour", lv=lv, n=n, cols=cols, rows=rows, base=base, diff=diff, seed=seed, t_find=t_find,
                txt="Finde das ANDERE Feld!")


LEVELS = [
    level_text(1, "Finde die 6!", "9", 7, 10, "6", 11, 82, t_find=6.0),
    level_text(2, "Finde das Q!", "O", 8, 11, "Q", 12, 74, t_find=7.0),
    level_colour(3, "", 6, 8, (60, 150, 230), 26, 13, t_find=7.0),
    level_text(4, "Finde die 8!", "B", 9, 12, "8", 14, 62, t_find=8.0),
    level_colour(5, "", 8, 10, (230, 110, 60), 13, 15, t_find=8.0),
    level_text(6, "Finde das kleine L!", "I", 10, 13, "l", 16, 56, weight="Medium", t_find=9.0),
]


def odd_cell(L):
    rnd = random.Random(L["seed"])
    # keep the odd cell away from the outermost ring so it is never cut off visually
    return rnd.randrange(1, L["cols"] - 1), rnd.randrange(1, L["rows"] - 1)


def cell_xy(L, i, j):
    x0, y0, x1, y1 = GRID
    cw, ch = (x1 - x0) / L["cols"], (y1 - y0) / L["rows"]
    return x0 + cw * (i + 0.5), y0 + ch * (j + 0.5), cw, ch


def draw_level(c, t, L):
    c.fill(BG)
    T = L["t_find"]
    solved = ease(prog(t, T, T + 0.35))
    oi, oj = odd_cell(L)
    if L["kind"] == "text":
        for i in range(L["cols"]):
            for j in range(L["rows"]):
                x, y, _, _ = cell_xy(L, i, j)
                odd = (i, j) == (oi, oj)
                a = 255 if odd else int(255 * (1 - 0.75 * solved))
                col = GOLD if odd and solved > 0 else L["colour"]
                c.text(x, y, L["odd"] if odd else L["txt"], L["size"], (*col[:3], a), weight=L["weight"])
    else:
        base, d = L["base"], L["diff"]
        odd_col = tuple(min(255, v + d) for v in base)
        for i in range(L["cols"]):
            for j in range(L["rows"]):
                x, y, cw, ch = cell_xy(L, i, j)
                odd = (i, j) == (oi, oj)
                col = odd_col if odd else base
                a = 255 if odd else int(255 * (1 - 0.7 * solved))
                c.rect(x - cw / 2 + 5, y - ch / 2 + 5, x + cw / 2 - 5, y + ch / 2 - 5, fill=(*col, a), r=10)
    if solved > 0:
        x, y, cw, ch = cell_xy(L, oi, oj)
        r = max(cw, ch) * 0.62 * (2.2 - 1.2 * back_out(prog(t, T, T + 0.4)))
        c.circle(x, y, r, outline=(*RED, int(255 * solved)), w=9)


def draw_ui(c, t, L, first):
    T = L["t_find"]
    a_in = ease_out(prog(t, 0, 0.3))
    if first:
        c.text(CX, 238, "NUR 1 % SCHAFFEN LEVEL 6", 32, (*GOLD, int(255 * a_in)))
    else:
        c.text(CX, 238, f"LEVEL {L['lv']} / 6", 34, (*GOLD, int(255 * a_in)))
    q = L["n"] or L["txt"]
    if t < T:
        sub = f"Level {L['lv']} / 6 · " if first else ""
        text_block(c, [(q, WHITE)], 322, 62, a_in)
        if first:
            c.text(CX, 392, f"{sub}{int(T)} Sekunden", 34, (*WHITE, int(170 * a_in)))
        k = 1 - prog(t, 0.3, T)
        late = T - t < 3
        y = 440
        c.rect(CX - 300, y, CX + 300, y + 12, fill=(255, 255, 255, 40), r=6)
        c.rect(CX - 300, y, CX - 300 + 600 * k, y + 12, fill=(*(RED if late else GOLD), 235), r=6)
    else:
        a = ease_out(prog(t, T, T + 0.3))
        text_block(c, [("Hast du es gefunden?", WHITE)], 322, 62, a)
        c.text(CX, 405, "Schreib deine Zeit in die Kommentare", 34, (*GOLD, int(255 * a)))


def level_sounds(L):
    T = L["t_find"]
    s = [(0.0, sfx.whoosh(0.35), 0.5), (0.0, drone(T + REVEAL), 0.3)]
    s += [(k, sfx.click(), 0.4) for k in range(1, int(T))]
    s += [(T - n, sfx.beep(880, 0.12), 0.5) for n in (3, 2, 1)]
    s += [(T, ding(), 0.8), (T, sfx.bass_hit(), 0.5)]
    return s


def draw_outro(c, t):
    c.fill(BG)
    a = ease_out(prog(t, 0, 0.3))
    text_block(c, [("Bei welchem Level", WHITE), ("warst du raus?", WHITE)], 820, 70, a)
    b = ease_out(prog(t, 0.5, 0.8))
    text_block(c, [("1  2  3  4  5  6", GOLD)], 1040, 76, b)
    c.text(CX, 1160, "Schick das deinem schlauesten Freund!", 38, (*WHITE, int(220 * b)))
    f = ease_out(prog(t, 1.6, 2.0))
    if f > 0:
        follow_cta(c, f, "FOLGEN für Teil 2")


def make():
    scenes = []
    for k, L in enumerate(LEVELS):
        def draw(c, t, L=L, first=(k == 0)):
            draw_level(c, t, L)
            draw_ui(c, t, L, first)

        scenes.append(Scene(L["t_find"] + REVEAL, draw, None, level_sounds(L), header=False, zoom=1.0, ty=1330.0))
    scenes.append(Scene(4.5, draw_outro, None, [(0.0, sfx.whoosh(0.4), 0.5), (0.5, sfx.click(), 0.6)],
                        header=False, zoom=1.0, ty=1330.0))
    return Film("Finde den Fehler", "6 Level", scenes)


FILM = make()

if __name__ == "__main__":
    print(f"duration {FILM.dur:.1f}s")
    if "--sheet" in sys.argv:
        ts = [st + k for st, sc in zip(FILM.starts, FILM.scenes) for k in (0.5, sc.dur - 1.0)]
        print(stills(FILM, ts, "output/preview_fehler", cols=7, scale=0.22))
    else:
        render(FILM, "output/finde_den_fehler_6_level.mp4")
