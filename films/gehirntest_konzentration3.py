"""Gehirn-Test: Konzentration Teil 3 - sheep trap, dice, order of operations, fly swarm, shadow match,
shell game in the dark.

Render:  python3 -m films.gehirntest_konzentration3
Preview: python3 -m films.gehirntest_konzentration3 --sheet
"""
import math
import random
import sys

from engine import sfx
from engine.gfx import INK, back_out, ease, ease_out, lerp, prog
from engine.render import Film, Scene, render, stills
from films.illusions import BG, CX, GOLD, WHITE, ding, drone, follow_cta, text_block
from films.finde_den_fehler_katze import cat, meow, purr, speech_right
from films.gehirntest_konzentration import (CUP_X, GREEN, RED, TABLE_Y, buzz, cat_say, count_snd, cup, fly, fly_path,
                                            pop, swish, ui)

N_TESTS = 6
LBL = lambda k: f"TEST {k} / {N_TESTS}"
SC = lambda d, fn, snd: Scene(d, fn, None, snd, header=False, zoom=1.0, ty=1330.0)


def base_snd(d):
    return [(0.0, drone(d), 0.25), (0.0, sfx.whoosh(0.35), 0.4)]


def solve_snd(t):
    return [(t, ding(), 0.8), (t, sfx.bass_hit(), 0.5)]


def big_wrong(c, t, t0, txt, y):
    a = int(255 * ease_out(prog(t, t0, t0 + 0.3)))
    if a <= 0:
        return
    w = c.text_w(txt, 80)
    c.text(CX, y, txt, 80, (*RED, a))
    c.line([(CX - w / 2 - 10, y), (CX + w / 2 + 10, y)], (*RED, a), 9)


# ------------------------------------------------------------------ 1. sheep trap
T1 = 5.5


def sheep(c, x, y, s=1.0, dead=False):
    col = (150, 150, 160) if dead else (245, 245, 245)
    for dx, dy in ((-30, -10), (0, -24), (30, -10), (-18, 12), (18, 12)):
        c.circle(x + dx * s, y + dy * s, 26 * s, fill=col)
    c.ellipse(x + 46 * s, y - 6 * s, 18 * s, 22 * s, fill=(40, 40, 46))
    for dx in (-24, 22):
        c.line([(x + dx * s, y + 28 * s), (x + dx * s, y + 52 * s)], (40, 40, 46), 7 * s)


def s_sheep(c, t):
    c.fill(BG)
    alive = 9
    rnd = random.Random(3)
    for k in range(17):
        x = 170 + (k % 6) * 128 + rnd.uniform(-12, 12)
        y = 760 + (k // 6) * 150 + rnd.uniform(-10, 10)
        dead = k >= alive and t >= T1
        a = 1 - 0.65 * ease(prog(t, T1, T1 + 0.4)) if dead else 1
        sheep(c, x, y, 0.95, dead)
        if dead:
            c.circle(x, y, 60, fill=(16, 17, 22, int(150 * (1 - a) / 0.65)))
        if t >= T1 and not dead:
            c.circle(x, y - 6, 66, outline=(*GREEN, 255), w=6)
    if t < T1:
        text_block(c, [("Ein Bauer hat 17 Schafe.", WHITE), ("Alle bis auf 9 sterben.", GOLD)], 1250, 52,
                   ease_out(prog(t, 0.3, 0.6)))
    else:
        p = back_out(prog(t, T1, T1 + 0.25))
        c.text(CX, 1270, "9", int(170 * p) + 1, GOLD)
        big_wrong(c, t, T1 + 0.5, "8", 1400)
    ui(c, t, 1, "90 % SAGEN DAS FALSCHE", "Wie viele Schafe\nbleiben übrig?", 0.6, T1, T1, "Es bleiben 9!",
       "\"Alle bis auf 9\" = 9 überleben")
    cat_say(c, t, T1 + 0.8, T1 + 3.4, "Ich hab 8 gesagt. Mist.")


def sheep_snd():
    return base_snd(T1 + 4) + count_snd(0.6, T1) + solve_snd(T1) + [(T1 + 1.1, meow(0.5, 1.0), 0.5)]


# ------------------------------------------------------------------ 2. count the dice pips
DICE = [(240, 860, 6), (520, 800, 4), (770, 900, 5), (360, 1110, 3), (650, 1160, 6)]
SHOW2 = (0.6, 3.1)
T2 = 7.0
PIPS = {1: [(0, 0)], 2: [(-1, -1), (1, 1)], 3: [(-1, -1), (0, 0), (1, 1)], 4: [(-1, -1), (1, -1), (-1, 1), (1, 1)],
        5: [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)], 6: [(-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1)]}


def die(c, x, y, v, s=110):
    c.rect(x - s / 2, y - s / 2, x + s / 2, y + s / 2, fill=(245, 245, 245), outline=(180, 180, 190), w=4, r=20)
    for px, py in PIPS[v]:
        c.circle(x + px * s * 0.27, y + py * s * 0.27, s * 0.09, fill=INK)


def s_dice(c, t):
    c.fill(BG)
    total = sum(v for *_, v in DICE)
    if SHOW2[0] <= t < SHOW2[1] or t >= T2:
        for k, (x, y, v) in enumerate(DICE):
            p = back_out(prog(t, SHOW2[0] + k * 0.06, SHOW2[0] + k * 0.06 + 0.2)) if t < T2 else 1
            die(c, x, y, v, 150 * p + 1)
            if t >= T2:
                b = ease_out(prog(t, T2 + 0.15 + k * 0.25, T2 + 0.35 + k * 0.25))
                c.circle(x + 70, y - 70, 32 * b + 1, fill=GOLD)
                c.text(x + 70, y - 68, str(v), int(38 * b) + 1, BG)
        if SHOW2[0] <= t < SHOW2[1]:
            k = 1 - prog(t, SHOW2[0], SHOW2[1])
            c.rect(CX - 300, 1330, CX - 300 + 600 * k, 1342, fill=GOLD, r=6)
    elif SHOW2[1] <= t < T2:
        c.text(CX, 980, "?", 260, (255, 255, 255, 60))
        p = fly_path(t, 3.4, 5.2, (1200, 1300), (-150, 700), 120, 7)
        if p:
            fly(c, *p, t, s=2.2)
    if t >= T2 + 1.5:
        c.text(CX, 1380, " + ".join(str(v) for *_, v in DICE) + f" = {total}", 54, GOLD)
    q = "Zähl ALLE Augen!" if t < SHOW2[1] else "Wie viele Augen\nwaren es insgesamt?"
    ui(c, t, 2, LBL(2), q, SHOW2[0] if t < SHOW2[1] else SHOW2[1], SHOW2[1] if t < SHOW2[1] else T2, T2,
       f"Es waren {total} Augen!", "Wie viele hattest du?")


def dice_snd():
    s = base_snd(T2 + 4) + [(SHOW2[0] + k * 0.06, sfx.click(), 0.5) for k in range(5)]
    s += [(SHOW2[1], sfx.whoosh(0.3, False), 0.4), (3.4, buzz(1.8), 0.55)] + count_snd(SHOW2[1], T2) + solve_snd(T2)
    s += [(T2 + 0.15 + k * 0.25, pop(), 0.5) for k in range(5)]
    return s


# ------------------------------------------------------------------ 3. order of operations
T3 = 6.0


def s_order(c, t):
    c.fill(BG)
    p = back_out(prog(t, 0.3, 0.6))
    c.text(CX, 940, "3 + 3 × 3 − 3", int(118 * p) + 1, WHITE)
    if t < T3:
        c.text(CX, 1090, "= ?", 110, (*GOLD, int(255 * ease_out(prog(t, 0.6, 0.9)))))
    else:
        steps = [("3 + 9 − 3", T3 + 0.2), ("= 9", T3 + 0.8)]
        for k, (txt, ts) in enumerate(steps):
            a = ease_out(prog(t, ts, ts + 0.3))
            c.text(CX, 1090 + k * 130, txt, 100 if k else 84, (*(GOLD if k else WHITE), int(255 * a)))
        big_wrong(c, t, T3 + 1.4, "15", 1360)
    ui(c, t, 3, LBL(3), "Rechne im Kopf!", 0.6, T3, T3, "Die Lösung ist 9!", "Punkt vor Strich ;)")
    cat_say(c, t, 2.0, 4.6, "15! Ganz sicher 15!")


def order_snd():
    return base_snd(T3 + 4) + [(0.3, pop(), 0.8)] + count_snd(0.6, T3) + [(2.3, meow(0.5, 1.15), 0.5)] + \
        solve_snd(T3) + [(T3 + 0.2, sfx.click(), 0.5), (T3 + 0.8, sfx.click(), 0.5), (T3 + 1.4, sfx.zap(0.2), 0.3)]


# ------------------------------------------------------------------ 4. count the swarm of flies
N_FLIES = 11
BOX4 = (120, 640, 860, 1420)
T4_FREEZE, T4 = 7.2, 9.2


def swarm_pos(k, t):
    """Each fly circles around its own home spot, so at the freeze they are spread out and countable."""
    cols, rows = 3, 4
    homes = [(i, j) for j in range(rows) for i in range(cols)][:N_FLIES]
    r = random.Random(100 + k)
    i, j = homes[(k * 5) % N_FLIES]
    cw, ch = (BOX4[2] - BOX4[0]) / cols, (BOX4[3] - BOX4[1]) / rows
    hx, hy = BOX4[0] + cw * (i + 0.5), BOX4[1] + ch * (j + 0.5)
    fx, fy, px, py = r.uniform(0.35, 0.7), r.uniform(0.35, 0.7), r.uniform(0, 6.28), r.uniform(0, 6.28)

    def at(tt):
        # big loops early (chaos), settling closer to home towards the freeze
        amp = lerp(1.5, 0.45, prog(tt, 0, T4_FREEZE))
        return (hx + math.sin(tt * fx * 6.28 + px) * cw * 0.5 * amp,
                hy + math.sin(tt * fy * 6.28 + py) * ch * 0.5 * amp)

    x, y = at(t)
    x2, y2 = at(t + 0.03)
    return x, y, math.degrees(math.atan2(y2 - y, x2 - x))


def s_swarm(c, t):
    c.fill(BG)
    tt = min(t, T4_FREEZE)
    for k in range(N_FLIES):
        x, y, ang = swarm_pos(k, tt)
        fly(c, x, y, t if t < T4_FREEZE else 0, ang, flying=t < T4_FREEZE, s=1.9)
        if t >= T4:
            p = back_out(prog(t, T4 + 0.15 + k * 0.12, T4 + 0.3 + k * 0.12))
            if p > 0:
                c.circle(x, y - 40, 24 * p, fill=GOLD)
                c.text(x, y - 39, str(k + 1), int(28 * min(1, p)) + 1, BG)
    if T4_FREEZE <= t < T4:
        c.text(CX, 1450, "STOPP!", 60, RED)
    cat_say(c, t, 3.0, 5.6, "Ich fange sie alle!")
    ui(c, t, 4, LBL(4), "Wie viele Fliegen\nsind es?", 0.6, T4, T4, f"Es sind {N_FLIES} Fliegen!",
       "Hattest du es? Schreib deine Zahl!")


def swarm_snd():
    s = base_snd(T4 + 4) + [(0.0, buzz(T4_FREEZE), 0.5), (0.4, buzz(T4_FREEZE - 0.4), 0.35)]
    s += count_snd(0.6, T4) + [(T4_FREEZE, sfx.bass_hit(), 0.5), (3.3, meow(0.6, 0.95), 0.5)] + solve_snd(T4)
    s += [(T4 + 0.15 + k * 0.12, sfx.click(), 0.45) for k in range(N_FLIES)]
    return s


# ------------------------------------------------------------------ 5. which shadow fits
T5 = 7.5


def key_shape(c, x, y, s, col, variant="ok"):
    flip = -1 if variant == "flip" else 1
    c.circle(x - 130 * s, y, 70 * s, fill=col)
    c.circle(x - 130 * s, y, 26 * s, fill=BG)
    c.rect(x - 70 * s, y - 16 * s, x + 150 * s, y + 16 * s, fill=col)
    teeth = [(90, 56), (125, 40)]
    if variant == "swap":
        teeth = [(90, 40), (125, 56)]
    if variant == "extra":
        teeth = teeth + [(55, 34)]
    for tx, tl in teeth:
        y0, y1 = sorted((y + 16 * s * flip, y + tl * s * flip))
        c.rect(x + (tx - 12) * s, y0, x + (tx + 12) * s, y1, fill=col)


OPTS5 = ["swap", "ok", "flip", "extra"]
ANS5 = 1


def s_shadow(c, t):
    c.fill(BG)
    key_shape(c, CX + 10, 760, 1.15, GOLD)
    for k, var in enumerate(OPTS5):
        i, j = k % 2, k // 2
        x, y = CX - 205 + i * 410, 1090 + j * 250
        good, bad = t >= T5 and k == ANS5, t >= T5 and k != ANS5
        frame = GREEN if good else (40, 44, 56)
        c.rect(x - 200, y - 115, x + 200, y + 115, fill=(*frame, 90 if bad else 255), r=24)
        key_shape(c, x + 20, y + 5, 0.8, (150, 150, 165) if not good else (20, 30, 24), var)
        c.text(x - 165, y - 80, "ABCD"[k], 40, (*GOLD, 120 if bad else 255))
    p = fly_path(t, 2.2, 4.0, (-150, 1300), (1200, 950), 100, 17)
    if p:
        fly(c, *p, t, s=2.0)
    ui(c, t, 5, LBL(5), "Welcher Schatten\ngehört zum Schlüssel?", 0.6, T5, T5, "Es ist B!", "A, C und D sind minimal anders")


def shadow_snd():
    return base_snd(T5 + 4) + count_snd(0.6, T5) + [(2.2, buzz(1.8), 0.55)] + solve_snd(T5)


# ------------------------------------------------------------------ 6. shell game in the dark (finale)
SH0 = 2.4
SW6 = [(0, 1, 0.6), (1, 2, 0.56), (0, 2, 0.52), (0, 1, 0.48), (1, 2, 0.45), (0, 2, 0.42), (0, 1, 0.4),
       (1, 2, 0.38), (0, 2, 0.37), (0, 1, 0.36), (1, 2, 0.35), (0, 2, 0.35), (0, 1, 0.34), (1, 2, 0.34)]
BALL = 0
T6_ASK = SH0 + sum(d for *_, d in SW6) + 0.2
T6 = T6_ASK + 2.6
DARK = [(4.0, 0.28), (5.9, 0.3), (7.3, 0.26), (8.4, 0.3)]


def cups3(t):
    slot = [0, 1, 2]
    tt = SH0
    for a, b, d in SW6:
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
    return {k: (CUP_X[slot[k]], 0.0) for k in range(3)}, slot


def s_dark(c, t):
    c.fill(BG)
    c.rect(-50, TABLE_Y, 1130, TABLE_Y + 24, fill=(110, 80, 56), r=8)
    xy, slot = cups3(t)
    show = ease(prog(t, 0.4, 0.8)) * (1 - ease(prog(t, 1.6, 2.0)))
    end = ease(prog(t, T6 + 0.1, T6 + 0.5))
    bx = xy[BALL][0]
    if show > 0.05 or end > 0.05:
        c.circle(bx, TABLE_Y - 36, 36, fill=GOLD)
        if end > 0.3:
            c.glow(bx, TABLE_Y - 36, 120, (255, 220, 120), end)
    for k in range(3):
        x, dy = xy[k]
        cup(c, x, TABLE_Y + dy, max(show, end) if k == BALL else 0.0)
    if t >= T6_ASK - 0.1:
        a = ease_out(prog(t, T6_ASK - 0.1, T6_ASK + 0.2))
        for s_ in range(3):
            c.circle(CUP_X[s_], TABLE_Y + 120, 44, fill=(255, 255, 255, int(235 * a)))
            c.text(CUP_X[s_], TABLE_Y + 122, str(s_ + 1), 54, (*BG, int(255 * a)))
    ui(c, t, 6, "FINALE · IM DUNKELN", "Wo ist die Kugel?", T6_ASK, T6, T6,
       f"Becher {cups3(99.0)[1][BALL] + 1}!", "Schreib 1, 2 oder 3")
    for ts, d in DARK:        # light goes out - mean but fair: never longer than a third of a swap
        if ts <= t < ts + d:
            c.overlay((0, 0, 0), 0.93)
    cat_say(c, t, 9.0, 11.2, "Wer hat das Licht aus?!")


def dark_snd():
    s = base_snd(T6 + 3.2) + [(0.4, swish(), 0.6), (1.6, sfx.thud(), 0.4)]
    tt = SH0
    for a, b, d in SW6:
        s += [(tt, sfx.whoosh(min(0.4, d)), 0.45), (tt + d * 0.9, sfx.thud(), 0.25)]
        tt += d
    for ts, d in DARK:
        s += [(ts, sfx.click(), 1.0), (ts + d, sfx.click(), 0.8)]
    s += [(9.2, meow(0.6, 0.9), 0.6)]
    s += [(T6 - n, sfx.beep(880, 0.12), 0.45) for n in (2, 1)] + solve_snd(T6) + [(T6 + 0.1, swish(), 0.5)]
    return s


# ------------------------------------------------------------------ outro
def s_outro(c, t):
    c.fill(BG)
    a = ease_out(prog(t, 0, 0.3))
    text_block(c, [("Wie viele hattest", WHITE), ("du richtig?", WHITE)], 860, 70, a)
    b = ease_out(prog(t, 0.5, 0.8))
    text_block(c, [("0 / 1 / 2 / 3 / 4 / 5 / 6", GOLD)], 1060, 58, b)
    c.text(CX, 1160, "Schick es der Person, die immer recht hat", 34, (*WHITE, int(220 * b)))
    cat(c, t + 3, talk=0.0, mood="happy")
    speech_right(c, "Teil 4 wird noch gemeiner.", ease_out(prog(t, 0.3, 0.5)), y=520)
    f = ease_out(prog(t, 1.6, 2.0))
    if f > 0:
        follow_cta(c, f, "FOLGEN für Teil 4")


def make():
    scenes = [
        SC(T1 + 3.6, s_sheep, sheep_snd()),
        SC(T2 + 3.6, s_dice, dice_snd()),
        SC(T3 + 3.4, s_order, order_snd()),
        SC(T4 + 3.0, s_swarm, swarm_snd()),
        SC(T5 + 2.8, s_shadow, shadow_snd()),
        SC(T6 + 3.4, s_dark, dark_snd()),
        SC(4.5, s_outro, [(0.0, sfx.whoosh(0.4), 0.5), (0.3, meow(0.6, 1.1), 0.6), (0.6, purr(1.5), 0.5)]),
    ]
    return Film("Gehirn-Test Konzentration 3", "6 Tests", scenes)


FILM = make()

if __name__ == "__main__":
    print(f"duration {FILM.dur:.1f}s")
    if "--sheet" in sys.argv:
        ts = [st + sc.dur * k for st, sc in zip(FILM.starts, FILM.scenes) for k in (0.2, 0.45, 0.7, 0.9)]
        print(stills(FILM, ts, "output/preview_konz3", cols=8, scale=0.22))
    else:
        render(FILM, "output/gehirntest_konzentration_teil3.mp4")
