"""Gehirn-Test Teil 3 with the distracting cat: mixed puzzle types (search, count, read, Stroop).

Render:  python3 -m films.gehirntest_katze_teil3
Preview: python3 -m films.gehirntest_katze_teil3 --sheet
"""
import math
import random
import sys

from engine import sfx
from engine.gfx import INK, back_out, ease, ease_out, lerp, prog
from engine.render import Film, Scene, render, stills
from films.illusions import BG, CX, GOLD, WHITE, follow_cta, text_block
from films.finde_den_fehler_katze import (GRID, ORANGE, PINK, REVEAL, RED, cat, cell_xy, draw_level, fish,
                                         icon_level, level_sounds, meow, speech_right, text_level)


# ------------------------------------------------------------------ icons
def mouse(c, x, y, s, tail=True, a=255):
    body, ink = (172, 172, 184, a), (*INK, a)
    if tail:
        c.line([(x - 0.24 * s, y + 0.04 * s), (x - 0.42 * s, y - 0.04 * s), (x - 0.38 * s, y - 0.2 * s)],
               (230, 150, 170, a), max(2, 0.03 * s), cap=False)
    c.ellipse(x - 0.02 * s, y + 0.03 * s, 0.26 * s, 0.15 * s, fill=body)
    c.circle(x + 0.2 * s, y - 0.02 * s, 0.12 * s, fill=body)
    c.circle(x + 0.15 * s, y - 0.14 * s, 0.075 * s, fill=(*PINK, a))
    c.circle(x + 0.25 * s, y - 0.04 * s, 0.025 * s, fill=ink)
    c.circle(x + 0.33 * s, y + 0.0 * s, 0.03 * s, fill=(*PINK, a))


def lookface(c, x, y, s, look=-1, a=255):
    col, ink = (*ORANGE, a), (*INK, a)
    r = 0.3 * s
    for sx in (-1, 1):
        ex = x + sx * r * 0.6
        c.poly([(ex - r * 0.4, y - r * 0.55), (ex + sx * r * 0.12, y - r * 1.25), (ex + r * 0.4, y - r * 0.6)], fill=col)
    c.circle(x, y, r, fill=col)
    for sx in (-1, 1):
        ex, ey = x + sx * r * 0.42, y - r * 0.1
        c.circle(ex, ey, r * 0.2, fill=(255, 255, 255, a))
        c.circle(ex + look * r * 0.08, ey, r * 0.1, fill=ink)
    c.circle(x, y + r * 0.25, r * 0.08, fill=(*PINK, a))


# ------------------------------------------------------------------ level 2: count the fish
def fish_layout(n=14, seed=31):
    rnd = random.Random(seed)
    pts = []
    x0, y0, x1, y1 = GRID
    while len(pts) < n:
        s = rnd.uniform(110, 230)
        x, y = rnd.uniform(x0 + s * 0.4, x1 - s * 0.4), rnd.uniform(y0 + s * 0.3, y1 - s * 0.3)
        if all(math.hypot(x - px, y - py) > (s + ps) * 0.33 for px, py, ps, _, _ in pts):
            col = rnd.choice(((110, 190, 250), (250, 170, 70), (120, 220, 150), (240, 110, 150)))
            pts.append((x, y, s, rnd.choice((-1, 1)), col))
    return pts


FISH = fish_layout()


def draw_count(c, t, L):
    T = L["t_find"]
    for k, (x, y, s, face, col) in enumerate(FISH):
        a = 255
        c.ellipse(x + face * 0.04 * s, y, 0.3 * s, 0.17 * s, fill=(*col, a))
        tx = x - face * 0.24 * s
        c.poly([(tx + face * 0.04 * s, y), (tx - face * 0.16 * s, y - 0.14 * s), (tx - face * 0.16 * s, y + 0.14 * s)],
               fill=(*col, a))
        c.circle(x + face * 0.18 * s, y - 0.04 * s, 0.035 * s, fill=(20, 20, 30))
        ts = T + 0.25 + k * 0.13
        if t >= ts:
            p = back_out(prog(t, ts, ts + 0.15))
            c.circle(x, y, 30 * p, fill=GOLD)
            c.text(x, y + 1, str(k + 1), int(34 * min(1, p)) + 1, BG)


# ------------------------------------------------------------------ level 3: read it aloud (double word)
SIGN = [("EINE", 0), ("KATZE IM", 1), ("IM KARTON", 2)]


def draw_read(c, t, L):
    T = L["t_find"]
    cx, cy = CX - 40, 1080
    top, bot, half = (cx, 700), (cx, 1420), 430
    pts = [(cx, 720), (cx + half, 1400), (cx - half, 1400)]
    c.poly(pts, fill=(250, 250, 250))
    c.line(pts + [pts[0]], RED, 34, cap=False)
    solved = ease(prog(t, T, T + 0.3))
    ys = (1030, 1140, 1250)
    for (txt, row), y in zip(SIGN, ys):
        c.text(cx, y, txt, 70, INK)
    if solved > 0:
        # highlight both "IM"
        w1 = c.text_w("KATZE IM", 70)
        x_im1 = cx + w1 / 2 - c.text_w("IM", 70) / 2
        w2 = c.text_w("IM KARTON", 70)
        x_im2 = cx - w2 / 2 + c.text_w("IM", 70) / 2
        for k, (x, y) in enumerate(((x_im1, ys[1]), (x_im2, ys[2]))):
            p = back_out(prog(t, T + 0.1 + k * 0.35, T + 0.4 + k * 0.35))
            if p > 0:
                c.circle(x, y, 62 * p, outline=(*RED, 255), w=8)


# ------------------------------------------------------------------ level 5: Stroop
COLS = {"ROT": (235, 50, 60), "BLAU": (60, 120, 255), "GRÜN": (40, 200, 90), "GELB": (250, 210, 40),
        "LILA": (175, 95, 235)}


def stroop_layout(seed=35, n=18):
    rnd = random.Random(seed)
    names = list(COLS)
    out = []
    for _ in range(n):
        w = rnd.choice(names)
        col = rnd.choice([x for x in names if x != w])
        out.append((w, col))
    return out


STROOP = stroop_layout()


def draw_stroop(c, t, L):
    for k, (word, col) in enumerate(STROOP):
        i, j = k % 3, k // 3
        x, y, _, _ = cell_xy(dict(cols=3, rows=6), i, j)
        c.text(x, y, word, 64, COLS[col])


# ------------------------------------------------------------------ levels
LEVELS = [
    icon_level(1, "Finde die Maus ohne Schwanz!", 6, 9, lambda c, x, y, s, a: mouse(c, x, y, s, True, a),
               lambda c, x, y, s, a: mouse(c, x, y, s, False, a), 6.0, 41,
               [(1.0, "Mäuse! Lecker!")], "Die gehört mir!"),
    dict(icon_level(2, "Wie viele Fische\nsiehst du?", 1, 1, None, None, 8.0, 42,
                    [(1.0, "Zähl laut mit!"), (4.4, "Ich hab einen gegessen...")], "Hattest du 14?"),
         draw=draw_count, solved="Es sind 14 Fische!", sub="Wie viele hattest du?",
         extra_snd=[(8.25 + k * 0.13, sfx.click(), 0.5) for k in range(14)]),
    dict(icon_level(3, "Lies das Schild\nLAUT vor!", 1, 1, None, None, 6.0, 43,
                    [(1.0, "Schnell! Schnell!")], "Reingefallen? Hihi."),
         draw=draw_read, solved="Da steht 2x IM!", sub="Die meisten lesen es nur 1x"),
    text_level(4, "Finde die TATZE!", 4, 14, "KATZE", "TATZE", 44, 8.0, 44,
               [(0.9, "Hier ist meine Tatze!"), (4.6, "War nur Spaß.")], "TATZE! Wie meine!", paw=(2.6, 4.0)),
    dict(icon_level(5, "Sag die FARBE –\nnicht das Wort!", 1, 1, None, None, 8.0, 45,
                    [(1.0, "Laut sagen! Los!"), (4.6, "Du hast BLAU gesagt, oder?")], "Ich kann nicht lesen."),
         draw=draw_stroop, solved="Ohne Fehler geschafft?", sub="Schreib JA oder NEIN in die Kommentare"),
    icon_level(6, "Welche Katze schaut\nin die andere Richtung?", 6, 8,
               lambda c, x, y, s, a: lookface(c, x, y, s, -1, a), lambda c, x, y, s, a: lookface(c, x, y, s, 1, a),
               9.0, 46, [(1.2, "Ich beobachte dich."), (5.0, "Nicht blinzeln!")], "Die hat MICH angeschaut!"),
]


def draw_outro(c, t):
    c.fill(BG)
    a = ease_out(prog(t, 0, 0.3))
    text_block(c, [("Wie viele hast du", WHITE), ("geschafft?", WHITE)], 860, 66, a)
    b = ease_out(prog(t, 0.5, 0.8))
    text_block(c, [("0 bis 6 – ehrlich sein!", GOLD)], 1060, 56, b)
    c.text(CX, 1160, "Schick das jemandem, der sich für schlau hält", 34, (*WHITE, int(220 * b)))
    cat(c, t + 3, talk=0.0, mood="happy")
    speech_right(c, "Ich hatte alle 6.", ease_out(prog(t, 0.3, 0.5)), y=520)
    f = ease_out(prog(t, 1.6, 2.0))
    if f > 0:
        follow_cta(c, f, "FOLGEN für Teil 4")


def make():
    scenes = [Scene(L["t_find"] + REVEAL, lambda c, t, L=L: draw_level(c, t, L), None, level_sounds(L),
                    header=False, zoom=1.0, ty=1330.0) for L in LEVELS]
    scenes.append(Scene(4.5, draw_outro, None, [(0.0, sfx.whoosh(0.4), 0.5), (0.3, meow(0.6, 1.1), 0.6)],
                        header=False, zoom=1.0, ty=1330.0))
    return Film("Gehirn-Test 3", "Katze", scenes)


FILM = make()

if __name__ == "__main__":
    print(f"duration {FILM.dur:.1f}s")
    if "--sheet" in sys.argv:
        ts = [st + k for st, sc in zip(FILM.starts, FILM.scenes) for k in (1.6, sc.dur - 0.8)]
        print(stills(FILM, ts, "output/preview_teil3", cols=7, scale=0.24))
    else:
        render(FILM, "output/gehirntest_katze_teil3.mp4")
