"""Gehirn-Test: Konzentration - 5 video-native brain tests with distractions (fly, cat cameo).

Render:  python3 -m films.gehirntest_konzentration
Preview: python3 -m films.gehirntest_konzentration --sheet
"""
import math
import random
import sys

import numpy as np

from engine import sfx
from engine.gfx import INK, back_out, ease, ease_in, ease_out, lerp, prog
from engine.render import Film, Scene, render, stills
from films.illusions import BG, CX, GOLD, WHITE, ding, drone, follow_cta, text_block
from films.finde_den_fehler_katze import cat, meow, purr, speech_right

RED = (230, 50, 60)
GREEN = (60, 200, 110)
TOTAL = 5


# ------------------------------------------------------------------ sounds
def buzz(d=2.0):
    t = sfx.tt(d)
    f = 190 + 25 * np.sin(2 * np.pi * 3.1 * t) + 12 * np.sin(2 * np.pi * 7.7 * t)
    ph = 2 * np.pi * np.cumsum(f) / sfx.SR
    saw = sum(np.sin(ph * h) / h for h in range(1, 12))
    am = 0.75 + 0.25 * np.sin(2 * np.pi * 31 * t)
    return sfx.fade(sfx.norm(sfx.band(saw * am, 120, 3500)) * 0.7, 0.15, 0.25)


def pop():
    d = 0.25
    return sfx.norm(sfx.chirp(420, 160, d, 0.5) * sfx.env(d, 0.002, 0.05)) * 0.8


def swish():
    return sfx.whoosh(0.3) * 0.7


# ------------------------------------------------------------------ the fly
def fly(c, x, y, t, ang=0.0, flying=True, s=1.0):
    a = math.radians(ang)
    dx, dy = math.cos(a), math.sin(a)

    def P(u, v):
        return (x + dx * u * s - dy * v * s, y + dy * u * s + dx * v * s)

    for side in (-1, 1):          # legs
        for k in (-1, 0, 1):
            c.line([P(k * 6, side * 6), P(k * 9 - 3, side * 15)], (20, 20, 22), 2.2, cap=False)
    if flying:
        flap = abs(math.sin(t * 90))
        for side in (-1, 1):
            c.ellipse(*P(-4, side * (12 + 6 * flap)), 13 * s, 7 * s, fill=(210, 225, 240, 150))
    else:
        for side in (-1, 1):
            c.ellipse(*P(-10, side * 6), 14 * s, 6 * s, fill=(210, 225, 240, 170))
    # light rim so the dark fly stays visible on the dark background
    c.ellipse(*P(0, 0), 17 * s, 12 * s, fill=(150, 156, 168))
    c.circle(*P(13, 0), 9.5 * s, fill=(150, 156, 168))
    c.ellipse(*P(0, 0), 14 * s, 9 * s, fill=(40, 42, 48))
    c.circle(*P(13, 0), 7 * s, fill=(40, 42, 48))
    for side in (-1, 1):
        c.circle(*P(16, side * 4.5), 3.6 * s, fill=(170, 40, 40))


def fly_path(t, t0, t1, p0, p1, wiggle=90, seed=1):
    """Wiggly flight from p0 to p1; returns (x, y, angle) or None outside [t0, t1]."""
    if not (t0 <= t <= t1):
        return None
    k = (t - t0) / (t1 - t0)
    r = random.Random(seed)
    f1, f2 = r.uniform(1.5, 2.5), r.uniform(3, 4.5)
    x = lerp(p0[0], p1[0], k) + math.sin(k * 6.28 * f1) * wiggle
    y = lerp(p0[1], p1[1], k) + math.sin(k * 6.28 * f2 + 1) * wiggle * 0.6
    k2 = min(1, k + 0.01)
    x2 = lerp(p0[0], p1[0], k2) + math.sin(k2 * 6.28 * f1) * wiggle
    y2 = lerp(p0[1], p1[1], k2) + math.sin(k2 * 6.28 * f2 + 1) * wiggle * 0.6
    return x, y, math.degrees(math.atan2(y2 - y, x2 - x))


# ------------------------------------------------------------------ shared UI
def ui(c, t, lv, label, question, t0, t1, solved_t, solved, sub):
    a_in = ease_out(prog(t, 0, 0.3))
    lab = label if label else f"TEST {lv} / {TOTAL}"
    if t < solved_t:
        c.text(CX, 238, lab, 32, (*GOLD, int(255 * a_in)))
        lines = question.split("\n")
        text_block(c, [(l, WHITE) for l in lines], 318, 58, a_in)
        if t0 is not None and t0 <= t < t1:
            k = 1 - prog(t, t0, t1)
            late = t1 - t < 3
            y = 318 + 68 * len(lines) + 6
            c.rect(CX - 300, y, CX + 300, y + 12, fill=(255, 255, 255, 40), r=6)
            c.rect(CX - 300, y, CX - 300 + 600 * k, y + 12, fill=(*(RED if late else GOLD), 235), r=6)
    else:
        a = ease_out(prog(t, solved_t, solved_t + 0.3))
        c.rect(CX - 170, 205, CX + 170, 268, fill=(*GOLD, int(255 * a)), r=31)
        c.text(CX, 237, "LÖSUNG", 36, (*BG, int(255 * a)))
        text_block(c, [(solved, WHITE)], 330, 60, a)
        if sub:
            c.text(CX, 410, sub, 34, (*GOLD, int(255 * a)))


def count_snd(t0, t1):
    s = [(k, sfx.click(), 0.35) for k in np.arange(t0 + 1, t1 - 3 + 0.01, 1.0)]
    s += [(t1 - n, sfx.beep(880, 0.12), 0.45) for n in (3, 2, 1)]
    return s


def cat_say(c, t, t0, t1, txt):
    """Cat cameo: slides in, says something, slides out."""
    if not (t0 <= t < t1):
        return
    slide = ease_out(prog(t, t0, t0 + 0.35)) * (1 - ease(prog(t, t1 - 0.35, t1)))
    age = t - t0 - 0.3
    talk = max(0.0, math.sin(age * 14)) * (1 - prog(age, 0.5, 0.7)) if age > 0 else 0
    cat(c, t, talk, "sly", slide=slide)
    if age > 0:
        speech_right(c, txt, ease_out(prog(age, 0, 0.2)) * slide, y=520)


# ------------------------------------------------------------------ 1. arithmetic trap
SEQ = ["1000", "+ 40", "+ 1000", "+ 30", "+ 1000", "+ 20", "+ 1000", "+ 10"]
A1 = dict(t_step=0.95, t_first=0.9)


def s_math(c, t):
    c.fill(BG)
    ts, tf = A1["t_step"], A1["t_first"]
    t_ask = tf + len(SEQ) * ts          # 8.5
    t_sol = t_ask + 2.5                 # 11.0
    for k, n in enumerate(SEQ):
        t0 = tf + k * ts
        if t0 <= t < t0 + ts:
            p = back_out(prog(t, t0, t0 + 0.18))
            c.text(CX, 960, n, int(210 * p) + 1, WHITE)
            for j in range(len(SEQ)):                     # progress dots
                c.circle(CX - 140 + j * 40, 1170, 9, fill=GOLD if j <= k else (70, 70, 80))
    if t_ask <= t < t_sol:
        p = back_out(prog(t, t_ask, t_ask + 0.2))
        c.text(CX, 960, "= ?", int(220 * p) + 1, GOLD)
        c.text(CX, 1150, "Ergebnis laut sagen!", 44, (255, 255, 255, 200))
    if t >= t_sol:
        p = back_out(prog(t, t_sol, t_sol + 0.25))
        c.text(CX, 960, "4100", int(230 * p) + 1, GOLD)
        if t > t_sol + 0.6:
            a = int(255 * ease_out(prog(t, t_sol + 0.6, t_sol + 0.9)))
            c.text(CX, 1150, "5000", 90, (*RED, a))
            c.line([(CX - 130, 1150), (CX + 130, 1150)], (*RED, a), 10)
    ui(c, t, 1, "99 % RECHNEN FALSCH", "Rechne im Kopf mit!", t_ask, t_sol, t_sol, "Es sind 4100!", "Nicht 5000 :)")
    cat_say(c, t, t_sol + 0.9, t_sol + 3.6, "Du hast 5000 gesagt, oder?")


def math_snd():
    ts, tf = A1["t_step"], A1["t_first"]
    t_ask = tf + len(SEQ) * ts
    t_sol = t_ask + 2.5
    s = [(0.0, drone(14.0), 0.25), (0.0, sfx.whoosh(0.35), 0.4)]
    s += [(tf + k * ts, pop(), 0.8) for k in range(len(SEQ))]
    s += [(t_ask, sfx.whoosh(0.3), 0.4)] + [(t_sol - n, sfx.beep(880, 0.12), 0.45) for n in (2, 1)]
    s += [(t_sol, ding(), 0.8), (t_sol, sfx.bass_hit(), 0.6), (t_sol + 0.6, sfx.zap(0.2), 0.3),
          (t_sol + 1.2, meow(0.5, 1.1), 0.5)]
    return s


# ------------------------------------------------------------------ 2. how many squares (with landing fly)
SQ_N, SQ_S = 4, 150
SQ_X0, SQ_Y0 = CX - SQ_N * SQ_S / 2, 1010 - SQ_N * SQ_S / 2
T2 = 8.0


def s_squares(c, t):
    c.fill(BG)
    x0, y0, S = SQ_X0, SQ_Y0, SQ_S
    for i in range(SQ_N + 1):
        c.line([(x0 + i * S, y0), (x0 + i * S, y0 + SQ_N * S)], WHITE, 8)
        c.line([(x0, y0 + i * S), (x0 + SQ_N * S, y0 + i * S)], WHITE, 8)
    if t >= T2:
        groups = [(1, T2 + 0.2, 0.7), (2, T2 + 1.0, 0.9), (3, T2 + 2.0, 0.6), (4, T2 + 2.7, 0.3)]
        total = 0
        parts = []
        for size, g0, gd in groups:
            pos = [(i, j) for j in range(SQ_N - size + 1) for i in range(SQ_N - size + 1)]
            if t < g0:
                break
            k = min(len(pos), int((t - g0) / gd * len(pos)) + 1)
            if t < g0 + gd + 0.15:
                i, j = pos[k - 1]
                c.rect(x0 + i * S + 6, y0 + j * S + 6, x0 + (i + size) * S - 6, y0 + (j + size) * S - 6,
                       fill=(*GOLD, 70), outline=(*GOLD, 255), w=8)
                cur = k
            else:
                cur = len(pos)
            total += cur
            parts.append(str(cur))
        c.text(CX, 1400, " + ".join(parts) + (f" = {total}" if t > T2 + 3.1 else ""), 52, GOLD)
    # the fly lands on the grid, walks around, then leaves
    p = fly_path(t, 1.8, 3.2, (1150, 700), (560, 940), 70, 3)
    if p:
        fly(c, *p, t, s=1.6)
    elif 3.2 < t < 5.6:
        k = prog(t, 3.2, 5.6)
        x, y = lerp(560, 430, ease(k)), lerp(940, 1060, ease(k))
        walking = int(t * 8) % 2
        fly(c, x + walking, y, t, ang=120 + math.sin(t * 5) * 25, flying=False, s=1.6)
    else:
        p = fly_path(t, 5.6, 7.0, (430, 1060), (-150, 600), 80, 4)
        if p:
            fly(c, *p, t, s=1.6)
    ui(c, t, 2, None, "Wie viele Quadrate\nsiehst du?", 0.4, T2, T2, "Es sind 30 Quadrate!", "Wie viele hattest du?")


def squares_snd():
    s = [(0.0, drone(12.0), 0.25), (0.0, sfx.whoosh(0.35), 0.4)] + count_snd(0.4, T2)
    s += [(1.8, buzz(1.5), 0.55), (5.6, buzz(1.5), 0.55)]
    s += [(T2, sfx.bass_hit(), 0.5)]
    s += [(T2 + 0.2 + k * 0.7 / 16, sfx.click(), 0.4) for k in range(16)]
    s += [(T2 + 1.0 + k * 0.1, sfx.click(), 0.4) for k in range(9)]
    s += [(T2 + 2.0 + k * 0.15, sfx.click(), 0.4) for k in range(4)]
    s += [(T2 + 2.7, sfx.click(), 0.4), (T2 + 3.1, ding(), 0.8)]
    return s


# ------------------------------------------------------------------ 3. which path leads to the trophy
COLX = [CX - 300, CX, CX + 300]
PATH_Y = [700, 820, 940, 1060, 1180, 1300]
T3 = 7.0


def _paths(seed=7):
    rnd = random.Random(seed)
    order = [0, 1, 2]
    rows = [list(order)]
    for _ in range(len(PATH_Y) - 1):
        nxt = rows[-1][:]
        while nxt == rows[-1]:
            rnd.shuffle(nxt)
        rows.append(nxt)
    # rows[r][line] = column of that line at level r
    return [[(COLX[rows[r][ln]] + rnd.uniform(-40, 40) * (0 < r < len(PATH_Y) - 1), PATH_Y[r])
             for r in range(len(PATH_Y))] for ln in range(3)]


def _catmull(pts, n=14):
    out = []
    P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            u = k / n
            out.append(tuple(0.5 * ((2 * p1[d]) + (-p0[d] + p2[d]) * u + (2 * p0[d] - 5 * p1[d] + 4 * p2[d] - p3[d]) * u * u
                                    + (-p0[d] + 3 * p1[d] - 3 * p2[d] + p3[d]) * u ** 3) for d in (0, 1)))
    out.append(pts[-1])
    return out


PATHS = [_catmull(p) for p in _paths()]
ANSWER3 = 2                                     # line C reaches the trophy
TROPHY_X = PATHS[ANSWER3][-1][0]


def trophy(c, x, y):
    c.poly([(x - 46, y - 40), (x + 46, y - 40), (x + 30, y + 10), (x - 30, y + 10)], fill=GOLD)
    c.arc(x - 46, y - 22, 20, 90, 270, GOLD, 8)
    c.arc(x + 46, y - 22, 20, 270, 450, GOLD, 8)
    c.rect(x - 8, y + 10, x + 8, y + 34, fill=GOLD)
    c.rect(x - 34, y + 34, x + 34, y + 48, fill=GOLD, r=4)


def s_paths(c, t):
    c.fill(BG)
    for ln, pts in enumerate(PATHS):
        c.line(pts, (225, 225, 232), 10)
    for ln, x in enumerate(COLX):
        c.circle(x, PATH_Y[0] - 36, 38, fill=(70, 120, 230))
        c.text(x, PATH_Y[0] - 34, "ABC"[ln], 44, WHITE)
    for pts in PATHS:
        x, y = pts[-1]
        if abs(x - TROPHY_X) < 1:
            trophy(c, x, y + 50)
        else:
            c.text(x, y + 52, "X", 64, RED)
    if t >= T3:
        k = ease(prog(t, T3 + 0.2, T3 + 1.6))
        pts = PATHS[ANSWER3]
        n = max(2, int(k * len(pts)))
        c.line(pts[:n], GOLD, 14)
        c.circle(*pts[n - 1], 16, fill=GOLD)
    cat_say(c, t, 2.6, 5.0, "Ich nehme A. Ganz sicher.")
    ui(c, t, 3, None, "Welcher Weg führt\nzum Pokal?", 0.4, T3, T3, "Es ist Weg C!", "Schreib A, B oder C")


def paths_snd():
    s = [(0.0, drone(12.0), 0.25), (0.0, sfx.whoosh(0.35), 0.4)] + count_snd(0.4, T3)
    s += [(2.9, meow(0.5, 1.0), 0.5), (T3, sfx.bass_hit(), 0.5), (T3 + 0.2, sfx.whoosh(1.4), 0.4),
          (T3 + 1.6, ding(), 0.8)]
    return s


# ------------------------------------------------------------------ 4. memory with distraction
CODE = "739148"
OPTIONS = ["739184", "739148", "793148"]
ANSWER4 = 1
T4_SHOW, T4_ASK, T4 = (0.5, 2.6), 6.4, 9.6


def s_memory(c, t):
    c.fill(BG)
    if T4_SHOW[0] <= t < T4_SHOW[1]:
        p = back_out(prog(t, T4_SHOW[0], T4_SHOW[0] + 0.2))
        c.rect(CX - 400, 870, CX + 400, 1070, fill=(30, 34, 46), r=30)
        c.text(CX, 972, " ".join(CODE), int(120 * p) + 1, WHITE)
        k = 1 - prog(t, T4_SHOW[0], T4_SHOW[1])
        c.rect(CX - 300, 1110, CX - 300 + 600 * k, 1122, fill=GOLD, r=6)
    elif T4_SHOW[1] <= t < T4_ASK:
        # distraction phase: a quick fake task + fly + cat
        c.text(CX, 900, "Kurze Pause...", 56, (255, 255, 255, 120))
        c.text(CX, 990, "Zähl bis 3 :)", 56, (255, 255, 255, 120))
        p = fly_path(t, T4_SHOW[1], T4_ASK, (-120, 1200), (1200, 800), 140, 9)
        if p:
            fly(c, *p, t, s=2.2)
    if t >= T4_ASK:
        for k, opt in enumerate(OPTIONS):
            y = 800 + k * 200
            a_in = ease_out(prog(t, T4_ASK + k * 0.12, T4_ASK + k * 0.12 + 0.25))
            good = t >= T4 and k == ANSWER4
            bad = t >= T4 and k != ANSWER4
            fill = (*GREEN, int(255 * a_in)) if good else (30, 34, 46, int(255 * a_in * (0.4 if bad else 1)))
            c.rect(CX - 380, y - 70, CX + 380, y + 70, fill=fill, r=26)
            c.text(CX - 300, y + 2, "ABC"[k], 64, (*GOLD, int(255 * a_in * (0.4 if bad else 1))))
            c.text(CX + 40, y + 2, " ".join(opt), 76, (*WHITE, int(255 * a_in * (0.4 if bad else 1))))
    cat_say(c, t, 3.2, 5.9, "Wie war die Zahl nochmal?")
    q = "Merk dir diese Zahl!" if t < T4_ASK else "Welche Zahl war es?"
    ui(c, t, 4, None, q, T4_ASK if t >= T4_ASK else T4_SHOW[0], T4 if t >= T4_ASK else T4_SHOW[1], T4,
       "Richtig ist B!", "Hattest du es? A, B oder C?")


def memory_snd():
    s = [(0.0, drone(12.0), 0.25), (0.0, sfx.whoosh(0.35), 0.4), (T4_SHOW[0], pop(), 0.8),
         (T4_SHOW[1], sfx.whoosh(0.3, False), 0.4), (T4_SHOW[1], buzz(T4_ASK - T4_SHOW[1]), 0.6),
         (3.5, meow(0.6, 0.95), 0.6), (T4_ASK, sfx.whoosh(0.35), 0.5)]
    s += count_snd(T4_ASK, T4)
    s += [(T4, ding(), 0.8), (T4, sfx.bass_hit(), 0.5)]
    return s


# ------------------------------------------------------------------ 5. shell game finale
CUP_X = [CX - 270, CX, CX + 270]
TABLE_Y = 1180
SHUF0 = 2.4
SWAPS = [(0, 1, 0.62), (1, 2, 0.58), (0, 2, 0.55), (0, 1, 0.5), (1, 2, 0.46), (0, 2, 0.44), (0, 1, 0.42),
         (1, 2, 0.4), (0, 1, 0.38), (0, 2, 0.38), (1, 2, 0.36), (0, 1, 0.36), (0, 2, 0.36), (1, 2, 0.35)]
BALL_CUP = 1
T5_ASK = SHUF0 + sum(d for _, _, d in SWAPS) + 0.2
T5 = T5_ASK + 2.6


def cup_state(t):
    """slot of each cup + (x, y) offsets at time t."""
    slot = [0, 1, 2]
    tt = SHUF0
    xy = {k: (CUP_X[slot[k]], 0.0) for k in range(3)}
    for a, b, d in SWAPS:
        ca, cb = slot.index(a), slot.index(b)
        if t < tt:
            break
        if t < tt + d:
            p = ease(prog(t, tt, tt + d))
            xy = {k: (CUP_X[slot[k]], 0.0) for k in range(3)}
            xy[ca] = (lerp(CUP_X[a], CUP_X[b], p), -math.sin(math.pi * p) * 70)
            xy[cb] = (lerp(CUP_X[b], CUP_X[a], p), math.sin(math.pi * p) * 40)
            return xy, slot
        slot[ca], slot[cb] = b, a
        tt += d
    xy = {k: (CUP_X[slot[k]], 0.0) for k in range(3)}
    return xy, slot


def cup(c, x, y, lift=0.0):
    y = y - lift * 190
    c.ellipse(x, TABLE_Y + 6, 100, 18, fill=(0, 0, 0, 90))
    c.poly([(x - 92, y), (x + 92, y), (x + 58, y - 210), (x - 58, y - 210)], fill=(208, 40, 52))
    c.rect(x - 92, y - 26, x + 92, y, fill=(170, 26, 38))
    c.rect(x - 70, y - 150, x + 70, y - 130, fill=(240, 240, 240))
    c.ellipse(x, y - 210, 58, 12, fill=(230, 70, 80))


def s_shell(c, t):
    c.fill(BG)
    c.rect(-50, TABLE_Y, 1130, TABLE_Y + 24, fill=(110, 80, 56), r=8)
    xy, slot = cup_state(t)
    lift_show = ease(prog(t, 0.4, 0.8)) * (1 - ease(prog(t, 1.6, 2.0)))
    lift_end = ease(prog(t, T5 + 0.1, T5 + 0.5))
    # ball under its cup
    bx = xy[BALL_CUP][0]
    if lift_show > 0.05 or lift_end > 0.05:
        c.circle(bx, TABLE_Y - 36, 36, fill=GOLD)
        if lift_end > 0.3:
            c.glow(bx, TABLE_Y - 36, 120, (255, 220, 120), lift_end)
    for k in range(3):
        x, dy = xy[k]
        lift = lift_show if k == BALL_CUP else 0.0
        if k == BALL_CUP:
            lift = max(lift, lift_end)
        cup(c, x, TABLE_Y + dy, lift)
    if t >= T5_ASK - 0.1:
        a = ease_out(prog(t, T5_ASK - 0.1, T5_ASK + 0.2))
        for s_ in range(3):
            c.circle(CUP_X[s_], TABLE_Y + 120, 44, fill=(255, 255, 255, int(235 * a)))
            c.text(CUP_X[s_], TABLE_Y + 122, str(s_ + 1), 54, (*BG, int(255 * a)))
    # distractions: fly buzzes over the cups, cat swipes at it
    p = fly_path(t, 4.2, 6.6, (1200, 760), (-100, 900), 110, 12)
    if p:
        fly(c, *p, t, s=2.0)
    cat_say(c, t, 5.6, 7.8, "FLIEGE!! Wo ist sie hin?")
    sol = f"Becher {cup_state(99.0)[1][BALL_CUP] + 1}!"
    ui(c, t, 5, "FINALE", "Wo ist die Kugel?", T5_ASK, T5, T5, sol, "Schreib 1, 2 oder 3 in die Kommentare")


def shell_snd():
    s = [(0.0, drone(T5 + 3.2), 0.25), (0.0, sfx.whoosh(0.35), 0.4), (0.4, swish(), 0.6), (1.6, sfx.thud(), 0.4)]
    tt = SHUF0
    for a, b, d in SWAPS:
        s.append((tt, sfx.whoosh(min(0.4, d)), 0.45))
        s.append((tt + d * 0.9, sfx.thud(), 0.25))
        tt += d
    s += [(4.2, buzz(2.4), 0.6), (6.0, meow(0.7, 0.9), 0.6)]
    s += [(T5 - n, sfx.beep(880, 0.12), 0.45) for n in (2, 1)]
    s += [(T5, ding(), 0.8), (T5, sfx.bass_hit(), 0.6), (T5 + 0.1, swish(), 0.5)]
    return s


# ------------------------------------------------------------------ outro
def s_outro(c, t):
    c.fill(BG)
    a = ease_out(prog(t, 0, 0.3))
    text_block(c, [("Wie viele hattest", WHITE), ("du richtig?", WHITE)], 860, 70, a)
    b = ease_out(prog(t, 0.5, 0.8))
    text_block(c, [("0 / 1 / 2 / 3 / 4 / 5", GOLD)], 1060, 64, b)
    c.text(CX, 1160, "Schick das jemandem, der sich nie konzentriert", 32, (*WHITE, int(220 * b)))
    cat(c, t + 3, talk=0.0, mood="happy")
    speech_right(c, "Ich hatte alle 5. Klar.", ease_out(prog(t, 0.3, 0.5)), y=520)
    f = ease_out(prog(t, 1.6, 2.0))
    if f > 0:
        follow_cta(c, f, "FOLGEN für Teil 2")


def make():
    sc = lambda d, fn, snd: Scene(d, fn, None, snd, header=False, zoom=1.0, ty=1330.0)
    t_math = A1["t_first"] + len(SEQ) * A1["t_step"] + 2.5 + 3.4
    scenes = [
        sc(t_math, s_math, math_snd()),
        sc(T2 + 4.6, s_squares, squares_snd()),
        sc(T3 + 3.6, s_paths, paths_snd()),
        sc(T4 + 3.0, s_memory, memory_snd()),
        sc(T5 + 3.4, s_shell, shell_snd()),
        sc(4.5, s_outro, [(0.0, sfx.whoosh(0.4), 0.5), (0.3, meow(0.6, 1.1), 0.6), (0.6, purr(1.5), 0.5)]),
    ]
    return Film("Gehirn-Test Konzentration", "5 Tests", scenes)


FILM = make()

if __name__ == "__main__":
    print(f"duration {FILM.dur:.1f}s")
    if "--sheet" in sys.argv:
        ts = [st + sc.dur * k for st, sc in zip(FILM.starts, FILM.scenes) for k in (0.15, 0.4, 0.62, 0.85)]
        print(stills(FILM, ts, "output/preview_konz", cols=8, scale=0.22))
    else:
        render(FILM, "output/gehirntest_konzentration.mp4")
