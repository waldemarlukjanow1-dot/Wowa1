"""'Finde den Buchstaben' - walls of letters with one odd character (OOOOÖOOO), 8 levels, harder each time.

Render:  python3 -m films.finde_den_buchstaben
Preview: python3 -m films.finde_den_buchstaben --sheet
"""
import math
import random
import sys

from engine import sfx
from engine.gfx import back_out, ease, ease_out, prog
from engine.render import Film, Scene, render, stills
from films.illusions import BG, CX, GOLD, WHITE, ding, drone, follow_cta, text_block
from films.finde_den_fehler_katze import cat, meow, purr, speech_right
from films.gehirntest_konzentration import RED, buzz, cat_say, count_snd, fly, fly_path, ui

BOX = (80, 610, 900, 1440)
REVEAL = 2.3


def lv(q, base, odd, cols, rows, size, t_find, seed, weight="Bold", fly_at=None, cat_line=None):
    return dict(q=q, base=base, odd=odd, cols=cols, rows=rows, size=size, t_find=t_find, seed=seed,
                weight=weight, fly_at=fly_at, cat_line=cat_line)


LEVELS = [
    lv("Finde das Ö!", "O", "Ö", 11, 16, 58, 5.0, 71),
    lv("Finde das N!", "M", "N", 11, 17, 54, 6.0, 72),
    lv("Finde die 3!", "8", "3", 12, 17, 52, 6.0, 73, fly_at=(1.6, 3.6)),
    lv("Finde das R!", "P", "R", 12, 18, 50, 6.0, 74),
    lv("Finde das O!", "Q", "O", 12, 18, 50, 7.0, 75, cat_line=(2.0, 4.6, "Ich seh's schon! Du nicht?")),
    lv("Finde das A!", "Ä", "A", 13, 19, 46, 7.0, 76, fly_at=(2.2, 4.4)),
    lv("Finde das m!", "rn", "m", 10, 20, 44, 8.0, 77, weight="Medium"),
    lv("Finde die 1!", "l", "1", 14, 20, 44, 8.0, 78, weight="Medium", fly_at=(3.0, 5.4)),
]


def odd_cell(L):
    r = random.Random(L["seed"])
    return r.randrange(1, L["cols"] - 1), r.randrange(1, L["rows"] - 1)


def cell(L, i, j):
    x0, y0, x1, y1 = BOX
    cw, ch = (x1 - x0) / L["cols"], (y1 - y0) / L["rows"]
    return x0 + cw * (i + 0.5), y0 + ch * (j + 0.5), max(cw, ch)


def draw_level(c, t, L, k, N=8, hook="NUR 2 % FINDEN ALLE 8"):
    c.fill(BG)
    T = L["t_find"]
    solved = ease(prog(t, T, T + 0.3))
    oi, oj = odd_cell(L)
    for i in range(L["cols"]):
        for j in range(L["rows"]):
            x, y, _ = cell(L, i, j)
            odd = (i, j) == (oi, oj)
            a = 255 if odd else int(255 * (1 - 0.78 * solved))
            col = GOLD if odd and solved > 0 else WHITE
            c.text(x, y, L["odd"] if odd else L["base"], L["size"], (*col, a), weight=L["weight"])
    if solved > 0:
        x, y, s = cell(L, oi, oj)
        r = s * 0.75 * (2.4 - 1.4 * back_out(prog(t, T, T + 0.4)))
        c.circle(x, y, r, outline=(*RED, int(255 * solved)), w=8)
    if L["fly_at"]:
        a, b = L["fly_at"]
        p = fly_path(t, a, b, (1200, 1350) if k % 2 else (-150, 700), (-150, 800) if k % 2 else (1200, 1300),
                     130, 80 + k)
        if p:
            fly(c, *p, t, s=2.0)
    label = hook if k == 0 else f"LEVEL {k + 1} / {N}"
    ui(c, t, k + 1, label, L["q"], 0.3, T, T, "Gefunden?", "Schreib deine Zeit in die Kommentare")
    if L["cat_line"]:
        cat_say(c, t, *L["cat_line"])


def level_snd(L):
    T = L["t_find"]
    s = [(0.0, drone(T + REVEAL), 0.25), (0.0, sfx.whoosh(0.35), 0.4)] + count_snd(0.3, T)
    s += [(T, ding(), 0.8), (T, sfx.bass_hit(), 0.45)]
    if L["fly_at"]:
        s.append((L["fly_at"][0], buzz(L["fly_at"][1] - L["fly_at"][0]), 0.55))
    if L["cat_line"]:
        s.append((L["cat_line"][0] + 0.3, meow(0.5, 1.05), 0.5))
    return s


def s_outro(c, t, cat_txt="Level 7 war gemein, oder?", cta="FOLGEN für Teil 2"):
    c.fill(BG)
    a = ease_out(prog(t, 0, 0.3))
    text_block(c, [("Bei welchem Level", WHITE), ("warst du raus?", WHITE)], 860, 70, a)
    b = ease_out(prog(t, 0.5, 0.8))
    text_block(c, [("1 2 3 4 5 6 7 8", GOLD)], 1060, 70, b)
    c.text(CX, 1160, "Schick das deinem Freund mit Adleraugen", 36, (*WHITE, int(220 * b)))
    cat(c, t + 3, talk=0.0, mood="happy")
    speech_right(c, cat_txt, ease_out(prog(t, 0.3, 0.5)), y=520)
    f = ease_out(prog(t, 1.6, 2.0))
    if f > 0:
        follow_cta(c, f, cta)


def make(levels=LEVELS, hook="NUR 2 % FINDEN ALLE 8", cat_txt="Level 7 war gemein, oder?",
         cta="FOLGEN für Teil 2"):
    n = len(levels)
    scenes = [Scene(L["t_find"] + REVEAL, lambda c, t, L=L, k=k: draw_level(c, t, L, k, n, hook), None, level_snd(L),
                    header=False, zoom=1.0, ty=1330.0) for k, L in enumerate(levels)]
    scenes.append(Scene(4.3, lambda c, t: s_outro(c, t, cat_txt, cta), None, [(0.0, sfx.whoosh(0.4), 0.5), (0.3, meow(0.6, 1.1), 0.6),
                                             (0.6, purr(1.5), 0.5)], header=False, zoom=1.0, ty=1330.0))
    return Film("Finde den Buchstaben", "8 Level", scenes)


FILM = make()

if __name__ == "__main__":
    print(f"duration {FILM.dur:.1f}s")
    if "--sheet" in sys.argv:
        ts = [st + k for st, sc in zip(FILM.starts, FILM.scenes) for k in (1.0, sc.dur - 0.6)]
        print(stills(FILM, ts, "output/preview_buchst", cols=6, scale=0.25))
    else:
        render(FILM, "output/finde_den_buchstaben.mp4")
