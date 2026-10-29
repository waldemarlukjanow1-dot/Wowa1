"""Gehirn-Test: Konzentration Teil 2 - 6 new tests, fly + cat distractions.

Render:  python3 -m films.gehirntest_konzentration2
Preview: python3 -m films.gehirntest_konzentration2 --sheet
"""
import math
import random
import sys

from engine import sfx
from engine.gfx import INK, back_out, ease, ease_out, lerp, prog
from engine.render import Film, Scene, render, stills
from films.illusions import BG, CX, GOLD, WHITE, ding, drone, follow_cta, text_block
from films.finde_den_fehler_katze import cat, meow, purr, speech_right
from films.gehirntest_konzentration import (GREEN, RED, buzz, cat_say, count_snd, fly, fly_path, pop, swish, ui)

N_TESTS = 6
LBL = lambda k: f"TEST {k} / {N_TESTS}"
SC = lambda d, fn, snd: Scene(d, fn, None, snd, header=False, zoom=1.0, ty=1330.0)


def base_snd(d):
    return [(0.0, drone(d), 0.25), (0.0, sfx.whoosh(0.35), 0.4)]


def solve_snd(t):
    return [(t, ding(), 0.8), (t, sfx.bass_hit(), 0.5)]


# ------------------------------------------------------------------ 1. count the RED flashes
LAMP = (CX, 990)
FL_RED = (235, 40, 50)
DECOYS = [(250, 130, 40), (240, 90, 170), (60, 120, 255), (60, 200, 110), (245, 245, 245)]


def _flashes(seed=51, n=18, reds=7):
    rnd = random.Random(seed)
    cols = [FL_RED] * reds + [rnd.choice(DECOYS) for _ in range(n - reds)]
    rnd.shuffle(cols)
    out, t = [], 1.2
    for k, col in enumerate(cols):
        out.append((t, col))
        t += lerp(0.44, 0.26, k / (n - 1))
    return out, t


FLASHES, T1_END = _flashes()
T1_ASK = T1_END + 0.3
T1 = T1_ASK + 2.2


def s_flash(c, t):
    c.fill(BG)
    on = None
    for ts, col in FLASHES:
        if ts <= t < ts + 0.17:
            on = col
    c.circle(*LAMP, 190, fill=(40, 42, 52))
    if on and t < T1_ASK:
        c.glow(*LAMP, 330, on, 1.3)
        c.circle(*LAMP, 170, fill=on)
    else:
        c.circle(*LAMP, 170, fill=(70, 72, 84))
    if T1_ASK <= t < T1:
        c.text(*LAMP, "?", 200, WHITE)
    if t >= T1:
        # replay strip: every flash as a dot, the reds get numbered
        n = len(FLASHES)
        reds = 0
        for k, (_, col) in enumerate(FLASHES):
            x = CX - 400 + k * (800 / (n - 1))
            y = 1290
            red = col == FL_RED
            tk = T1 + 0.2 + k * 0.08
            if t < tk:
                continue
            if red:
                reds += 1
                c.circle(x, y, 22, fill=FL_RED)
                c.text(x, y - 52, str(reds), 34, GOLD)
            else:
                c.circle(x, y, 13, fill=col)
        c.text(*LAMP, "7", int(220 * back_out(prog(t, T1, T1 + 0.25))) + 1, FL_RED)
    p = fly_path(t, 2.6, 4.6, (-120, 700), (1200, 1250), 120, 21)
    if p:
        fly(c, *p, t, s=2.0)
    ui(c, t, 1, "NUR 3 % ZÄHLEN RICHTIG", "Wie oft leuchtet es ROT?", T1_ASK, T1, T1, "7 mal ROT!",
       "Orange und Pink zählen nicht ;)")
    cat_say(c, t, T1 + 1.2, T1 + 3.6, "Ich hab 9 gezählt...")


def flash_snd():
    s = base_snd(T1 + 4)
    s += [(ts, sfx.beep(1250, 0.08), 0.35) for ts, _ in FLASHES]      # identical blip for every colour
    s += [(2.6, buzz(2.0), 0.55), (T1_ASK, sfx.whoosh(0.3), 0.4)]
    s += [(T1 - n, sfx.beep(880, 0.12), 0.45) for n in (2, 1)] + solve_snd(T1)
    s += [(T1 + 1.4, meow(0.5, 1.0), 0.5)]
    return s


# ------------------------------------------------------------------ 2. bat and ball
T2 = 7.5


def s_ball(c, t):
    c.fill(BG)
    # bat + ball
    c.line([(CX - 300, 1000), (CX - 40, 760)], (196, 140, 86), 46)
    c.line([(CX - 300, 1000), (CX - 250, 954)], (120, 80, 46), 30)
    c.circle(CX + 170, 900, 70, fill=(245, 245, 245))
    c.arc(CX + 120, 900, 60, 300, 60, RED, 5)
    c.arc(CX + 220, 900, 60, 120, 240, RED, 5)
    lines = [("Schläger + Ball = 1,10 €", WHITE), ("Der Schläger kostet", WHITE), ("1 € MEHR als der Ball.", GOLD)]
    if t < T2:
        text_block(c, lines, 1150, 50, ease_out(prog(t, 0.3, 0.6)))
    else:
        p = back_out(prog(t, T2, T2 + 0.25))
        c.text(CX, 1150, "5 Cent", int(120 * p) + 1, GOLD)
        a = ease_out(prog(t, T2 + 0.5, T2 + 0.8))
        c.text(CX, 1250, "10 Cent", 60, (*RED, int(255 * a)))
        c.line([(CX - 120, 1250), (CX + 120, 1250)], (*RED, int(255 * a)), 8)
        b = ease_out(prog(t, T2 + 1.0, T2 + 1.3))
        text_block(c, [("0,05 € + 1,05 € = 1,10 €", WHITE)], 1350, 44, b)
    ui(c, t, 2, LBL(2), "Was kostet der Ball?", 0.6, T2, T2, "Der Ball kostet 5 Cent!", "Nicht 10 Cent :)")
    cat_say(c, t, 3.0, 5.6, "Easy. 10 Cent!")


def ball_snd():
    return base_snd(T2 + 4) + count_snd(0.6, T2) + [(3.3, meow(0.5, 1.15), 0.5)] + solve_snd(T2) + \
        [(T2 + 0.5, sfx.zap(0.2), 0.3)]


# ------------------------------------------------------------------ 3. which number is missing (1-30)
MISSING = 23
NBOX = (110, 640, 860, 1420)


def _numbers(seed=53):
    """Jittered 5x6 grid (one cell left empty) so numbers never overlap but still look scattered."""
    rnd = random.Random(seed)
    cols, rows = 5, 6
    cw, ch = (NBOX[2] - NBOX[0]) / cols, (NBOX[3] - NBOX[1]) / rows
    cells = [(i, j) for j in range(rows) for i in range(cols)]
    rnd.shuffle(cells)
    nums = [n for n in range(1, 31) if n != MISSING]
    out = []
    for n, (i, j) in zip(nums, cells):
        x = NBOX[0] + cw * (i + 0.5) + rnd.uniform(-0.22, 0.22) * cw
        y = NBOX[1] + ch * (j + 0.5) + rnd.uniform(-0.22, 0.22) * ch
        size = rnd.randint(56, 84)
        col = rnd.choice(((245, 245, 245), (255, 200, 61), (130, 200, 255), (255, 150, 170), (150, 230, 160)))
        out.append((x, y, n, size, col))
    return out


NUMS = _numbers()
T3 = 9.0
FLY_ON = [p for p in NUMS if p[2] == 8][0]


def s_missing(c, t):
    c.fill(BG)
    solved = ease(prog(t, T3, T3 + 0.3))
    for x, y, n, size, col in NUMS:
        c.text(x, y, str(n), size, (*col, int(255 * (1 - 0.7 * solved))))
    fx, fy = FLY_ON[0], FLY_ON[1]
    p = fly_path(t, 2.0, 3.2, (1200, 700), (fx, fy), 60, 31)
    if p:
        fly(c, *p, t, s=2.0)
    elif 3.2 <= t < 6.4:
        fly(c, fx + math.sin(t * 9) * 4, fy, t, ang=90 + math.sin(t * 3) * 30, flying=False, s=2.0)
    else:
        p = fly_path(t, 6.4, 7.8, (fx, fy), (-150, 1500), 80, 32)
        if p:
            fly(c, *p, t, s=2.0)
    if t >= T3:
        k = back_out(prog(t, T3, T3 + 0.3))
        c.circle(CX, 1030, 130 * k, fill=(*GOLD, 235))
        c.text(CX, 1034, str(MISSING), int(130 * k) + 1, BG)
    ui(c, t, 3, LBL(3), "Welche Zahl von 1 bis 30\nfehlt?", 0.4, T3, T3, "Die 23 fehlt!", "Wie schnell warst du?")


def missing_snd():
    return base_snd(T3 + 4) + count_snd(0.4, T3) + [(2.0, buzz(1.2), 0.55), (6.4, buzz(1.4), 0.55)] + solve_snd(T3)


# ------------------------------------------------------------------ 4. picture memory
T4_SHOW = (0.5, 3.7)
T4_ASK, T4 = 7.0, 10.0
DOOR = (60, 200, 110)
OPTS4 = [("Rot", (235, 50, 60)), ("Blau", (60, 120, 255)), ("Grün", (60, 200, 110))]
ANS4 = 2


def picture(c):
    c.rect(110, 640, 880, 1400, fill=(120, 190, 240), r=30)                 # sky
    c.rect(110, 1210, 880, 1400, fill=(90, 170, 90), r=30)                   # grass
    c.circle(770, 760, 60, fill=(255, 220, 70))                              # sun
    c.rect(220, 930, 520, 1220, fill=(236, 214, 180))                        # house
    c.poly([(190, 940), (370, 790), (550, 940)], fill=(170, 60, 50))         # roof
    c.rect(330, 1080, 410, 1220, fill=DOOR)                                  # door
    c.rect(250, 980, 310, 1040, fill=(170, 220, 250))
    c.rect(440, 980, 500, 1040, fill=(170, 220, 250))
    c.rect(590, 1150, 820, 1220, fill=(60, 120, 255), r=18)                  # car
    c.rect(630, 1100, 770, 1155, fill=(60, 120, 255), r=14)
    for x in (630, 780):
        c.circle(x, 1225, 26, fill=(30, 30, 34))
    c.line([(700, 1000), (690, 1100)], (60, 60, 60), 3)                     # balloon
    c.ellipse(700, 960, 40, 50, fill=(235, 50, 60))


def s_picmem(c, t):
    c.fill(BG)
    if T4_SHOW[0] <= t < T4_SHOW[1]:
        picture(c)
        k = 1 - prog(t, T4_SHOW[0], T4_SHOW[1])
        c.rect(CX - 300, 1440, CX - 300 + 600 * k, 1452, fill=GOLD, r=6)
    elif T4_SHOW[1] <= t < T4_ASK:
        c.text(CX, 960, "Kurze Ablenkung...", 56, (255, 255, 255, 120))
        p = fly_path(t, T4_SHOW[1], T4_ASK, (1200, 1300), (-150, 760), 150, 41)
        if p:
            fly(c, *p, t, s=2.4)
    if t >= T4_ASK:
        for k, (name, col) in enumerate(OPTS4):
            y = 800 + k * 200
            a = ease_out(prog(t, T4_ASK + k * 0.12, T4_ASK + k * 0.12 + 0.25))
            good, bad = t >= T4 and k == ANS4, t >= T4 and k != ANS4
            dim = 0.35 if bad else 1
            c.rect(CX - 360, y - 70, CX + 360, y + 70, fill=(*(GREEN if good else (30, 34, 46)), int(255 * a * dim)), r=26)
            c.text(CX - 280, y + 2, "ABC"[k], 64, (*GOLD, int(255 * a * dim)))
            c.rect(CX - 160, y - 40, CX - 80, y + 40, fill=(*col, int(255 * a * dim)), r=12)
            c.text(CX + 90, y + 2, name, 70, (*WHITE, int(255 * a * dim)))
    cat_say(c, t, 4.0, 6.7, "Ich mag rote Ballons.")
    q = "Merk dir das Bild!" if t < T4_ASK else "Welche Farbe hatte\ndie TÜR?"
    ui(c, t, 4, LBL(4), q, T4_ASK if t >= T4_ASK else T4_SHOW[0], T4 if t >= T4_ASK else T4_SHOW[1], T4,
       "Die Tür war GRÜN!", "Hattest du A, B oder C?")


def picmem_snd():
    s = base_snd(T4 + 3) + [(T4_SHOW[0], pop(), 0.8), (T4_SHOW[1], sfx.whoosh(0.3, False), 0.4),
                            (T4_SHOW[1], buzz(T4_ASK - T4_SHOW[1]), 0.6), (4.3, meow(0.5, 1.05), 0.5),
                            (T4_ASK, sfx.whoosh(0.35), 0.5)]
    return s + count_snd(T4_ASK, T4) + solve_snd(T4)


# ------------------------------------------------------------------ 5. number sequence
SEQ5 = ["2", "6", "12", "20", "30", "?"]
T5 = 6.5


def s_seq(c, t):
    c.fill(BG)
    xs = [CX - 375 + k * 150 for k in range(6)]
    for k, (x, n) in enumerate(zip(xs, SEQ5)):
        a = ease_out(prog(t, 0.3 + k * 0.15, 0.55 + k * 0.15))
        last = k == 5
        fill = GOLD if last and t >= T5 else (30, 34, 46)
        c.rect(x - 64, 940, x + 64, 1080, fill=(*fill, int(255 * a)), r=20)
        txt = "42" if last and t >= T5 else n
        c.text(x, 1012, txt, 66, (*(BG if last and t >= T5 else WHITE), int(255 * a)))
        if t >= T5 and k < 5:
            b = ease_out(prog(t, T5 + 0.2 + k * 0.2, T5 + 0.4 + k * 0.2))
            c.arc(x + 75, 940, 62, 200, 340, (*GOLD, int(255 * b)), 5)
            c.text(x + 75, 850, f"+{(k + 2) * 2}", 40, (*GOLD, int(255 * b)))
    cat_say(c, t, 2.0, 4.6, "40? 50? Pizza?")
    ui(c, t, 5, LBL(5), "Welche Zahl\nkommt als Nächstes?", 0.6, T5, T5, "Die Lösung ist 42!",
       "+4  +6  +8  +10  +12")


def seq_snd():
    return base_snd(T5 + 4) + count_snd(0.6, T5) + [(2.3, meow(0.45, 1.2), 0.5)] + solve_snd(T5) + \
        [(T5 + 0.2 + k * 0.2, sfx.click(), 0.5) for k in range(5)]


# ------------------------------------------------------------------ 6. shell game with 4 cups (finale)
CUPS_X = [CX - 330, CX - 110, CX + 110, CX + 330]
TY = 1180
SH0 = 2.4
SW6 = [(0, 1, 0.55), (2, 3, 0.52), (1, 2, 0.5), (0, 3, 0.5), (1, 3, 0.46), (0, 2, 0.44), (2, 3, 0.42), (0, 1, 0.4),
       (1, 2, 0.38), (0, 3, 0.38), (1, 3, 0.36), (0, 2, 0.34), (2, 3, 0.33), (0, 1, 0.32), (1, 2, 0.32), (0, 3, 0.32)]
BALL = 2
T6_ASK = SH0 + sum(d for *_, d in SW6) + 0.2
T6 = T6_ASK + 2.6


def cups_at(t):
    slot = [0, 1, 2, 3]
    tt = SH0
    for a, b, d in SW6:
        ca, cb = slot.index(a), slot.index(b)
        if t < tt:
            break
        if t < tt + d:
            p = ease(prog(t, tt, tt + d))
            xy = {k: (CUPS_X[slot[k]], 0.0) for k in range(4)}
            xy[ca] = (lerp(CUPS_X[a], CUPS_X[b], p), -math.sin(math.pi * p) * 80)
            xy[cb] = (lerp(CUPS_X[b], CUPS_X[a], p), math.sin(math.pi * p) * 45)
            return xy, slot
        slot[ca], slot[cb] = b, a
        tt += d
    return {k: (CUPS_X[slot[k]], 0.0) for k in range(4)}, slot


def cup4(c, x, y, lift=0.0):
    y = y - lift * 170
    c.ellipse(x, TY + 6, 80, 15, fill=(0, 0, 0, 90))
    c.poly([(x - 74, y), (x + 74, y), (x + 46, y - 170), (x - 46, y - 170)], fill=(60, 120, 230))
    c.rect(x - 74, y - 22, x + 74, y, fill=(40, 90, 190))
    c.rect(x - 56, y - 120, x + 56, y - 104, fill=(240, 240, 240))
    c.ellipse(x, y - 170, 46, 10, fill=(100, 150, 240))


def s_shell4(c, t):
    c.fill(BG)
    c.rect(-50, TY, 1130, TY + 22, fill=(110, 80, 56), r=8)
    xy, slot = cups_at(t)
    show = ease(prog(t, 0.4, 0.8)) * (1 - ease(prog(t, 1.6, 2.0)))
    end = ease(prog(t, T6 + 0.1, T6 + 0.5))
    bx = xy[BALL][0]
    if show > 0.05 or end > 0.05:
        c.circle(bx, TY - 30, 30, fill=GOLD)
        if end > 0.3:
            c.glow(bx, TY - 30, 110, (255, 220, 120), end)
    for k in range(4):
        x, dy = xy[k]
        cup4(c, x, TY + dy, max(show, end) if k == BALL else 0.0)
    # the fly lands on cup 0 and rides along, then escapes
    rx, rdy = xy[0]
    if 4.0 <= t < 4.9:
        p = fly_path(t, 4.0, 4.9, (1200, 700), (rx, TY + rdy - 182), 50, 61)
        fly(c, *p, t, s=1.8)
    elif 4.9 <= t < 7.4:
        fly(c, rx, TY + rdy - 182, t, ang=-90 + math.sin(t * 4) * 20, flying=False, s=1.8)
    else:
        p = fly_path(t, 7.4, 8.6, (rx, TY + rdy - 182), (-150, 600), 90, 62)
        if p:
            fly(c, *p, t, s=1.8)
    if t >= T6_ASK - 0.1:
        a = ease_out(prog(t, T6_ASK - 0.1, T6_ASK + 0.2))
        for s_ in range(4):
            c.circle(CUPS_X[s_], TY + 110, 40, fill=(255, 255, 255, int(235 * a)))
            c.text(CUPS_X[s_], TY + 112, str(s_ + 1), 50, (*BG, int(255 * a)))
    cat_say(c, t, 6.2, 8.6, "Ich hab nur die Fliege gesehen!")
    ui(c, t, 6, "FINALE · 4 BECHER", "Wo ist die Kugel?", T6_ASK, T6, T6,
       f"Becher {cups_at(99.0)[1][BALL] + 1}!", "Schreib 1, 2, 3 oder 4")


def shell4_snd():
    s = base_snd(T6 + 3.2) + [(0.4, swish(), 0.6), (1.6, sfx.thud(), 0.4)]
    tt = SH0
    for a, b, d in SW6:
        s += [(tt, sfx.whoosh(min(0.4, d)), 0.45), (tt + d * 0.9, sfx.thud(), 0.25)]
        tt += d
    s += [(4.0, buzz(0.9), 0.6), (7.4, buzz(1.2), 0.6), (6.5, meow(0.6, 0.9), 0.6)]
    s += [(T6 - n, sfx.beep(880, 0.12), 0.45) for n in (2, 1)] + solve_snd(T6) + [(T6 + 0.1, swish(), 0.5)]
    return s


# ------------------------------------------------------------------ outro
def s_outro(c, t):
    c.fill(BG)
    a = ease_out(prog(t, 0, 0.3))
    text_block(c, [("Wie viele hattest", WHITE), ("du richtig?", WHITE)], 860, 70, a)
    b = ease_out(prog(t, 0.5, 0.8))
    text_block(c, [("0 / 1 / 2 / 3 / 4 / 5 / 6", GOLD)], 1060, 58, b)
    c.text(CX, 1160, "Markiere jemanden, der das nicht schafft", 34, (*WHITE, int(220 * b)))
    cat(c, t + 3, talk=0.0, mood="happy")
    speech_right(c, "Ich hatte 6. Okay... 2.", ease_out(prog(t, 0.3, 0.5)), y=520)
    f = ease_out(prog(t, 1.6, 2.0))
    if f > 0:
        follow_cta(c, f, "FOLGEN für Teil 3")


def make():
    scenes = [
        SC(T1 + 3.8, s_flash, flash_snd()),
        SC(T2 + 3.6, s_ball, ball_snd()),
        SC(T3 + 3.0, s_missing, missing_snd()),
        SC(T4 + 2.8, s_picmem, picmem_snd()),
        SC(T5 + 3.4, s_seq, seq_snd()),
        SC(T6 + 3.4, s_shell4, shell4_snd()),
        SC(4.5, s_outro, [(0.0, sfx.whoosh(0.4), 0.5), (0.3, meow(0.6, 1.1), 0.6), (0.6, purr(1.5), 0.5)]),
    ]
    return Film("Gehirn-Test Konzentration 2", "6 Tests", scenes)


FILM = make()

if __name__ == "__main__":
    print(f"duration {FILM.dur:.1f}s")
    if "--sheet" in sys.argv:
        ts = [st + sc.dur * k for st, sc in zip(FILM.starts, FILM.scenes) for k in (0.2, 0.45, 0.7, 0.9)]
        print(stills(FILM, ts, "output/preview_konz2", cols=8, scale=0.22))
    else:
        render(FILM, "output/gehirntest_konzentration_teil2.mp4")
