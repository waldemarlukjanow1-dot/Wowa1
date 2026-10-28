"""Optical illusion shorts: question -> countdown -> reveal with proof -> loop back.

Render all:   python3 -m films.illusions
Render one:   python3 -m films.illusions schach
Preview:      python3 -m films.illusions schach --sheet
"""
import math
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from engine import sfx
from engine.gfx import SS, W, H, Canvas, back_out, ease, ease_out, lerp, prog
from engine.render import Film, Scene, render, stills

BG = (16, 17, 22)
GOLD = (255, 200, 61)
WHITE = (255, 255, 255)
CX = 495          # horizontal centre of the content (shifted left, away from the like column)
DUR = 17.5
T_REVEAL = 8.0    # "AUFLÖSUNG"
T_BACK = 15.6     # reveal rewinds -> loops into the start


# ------------------------------------------------------------------ shared layout
def wrap(c, txt, size, maxw):
    if "\n" in txt:
        return txt.split("\n")
    words, lines, cur = txt.split(), [], ""
    for w in words:
        nxt = (cur + " " + w).strip()
        if c.text_w(nxt, size) > maxw and cur:
            lines.append(cur)
            cur = w
        else:
            cur = nxt
    return lines + [cur]


def text_block(c, lines, y, size, alpha=1.0, gap=1.18):
    """lines: [(text, colour), ...] centred at CX, first baseline-centre at y."""
    a = int(255 * alpha)
    for i, (txt, col) in enumerate(lines):
        c.text(CX, y + i * size * gap, txt, size, (*col, a), stroke=5, stroke_fill=BG)


def overlay_text(c, t, spec):
    T_REVEAL = spec.get("t_reveal", 8.0)
    T_BACK = spec.get("t_back", 15.6)
    T_COUNT = spec.get("t_count", T_REVEAL)
    q = spec.get("quiet")
    if q and q[0] <= t < q[1]:
        return
    q_in = ease_out(prog(t, 0.0, 0.35))
    q_out = 1 - ease(prog(t, T_REVEAL - 0.3, T_REVEAL))
    q_back = ease_out(prog(t, T_BACK + 0.9, T_BACK + 1.3))
    label_a = max(min(q_in, q_out), q_back)
    c.text(CX, 238, spec.get("label", "OPTISCHE TÄUSCHUNG"), 30, (*GOLD, int(255 * max(label_a, 0.0))))
    qa = max(min(q_in, q_out), q_back)
    if qa > 0:
        lines = [(l, WHITE) for l in wrap(c, spec["question"], 58, 820)]
        text_block(c, lines, 318 + (1 - qa) * 16, 58, qa)
    # countdown bar while the viewer looks
    if 1.0 <= t < T_COUNT:
        k = 1 - prog(t, 1.0, T_COUNT)
        y = 318 + 58 * 1.18 * (len(wrap(c, spec["question"], 58, 820)) - 1) + 62
        c.rect(CX - 300, y, CX + 300, y + 10, fill=(255, 255, 255, 40), r=5)
        c.rect(CX - 300, y, CX - 300 + 600 * k, y + 10, fill=(*GOLD, 230), r=5)
        n = int(math.ceil(T_COUNT - t))
        if n <= 3:
            p = (T_COUNT - t) % 1.0
            s = back_out(prog(1 - p, 0, 0.25))
            c.text(CX, 1395, str(n), int(120 * s) + 1, (*WHITE, 235), stroke=7, stroke_fill=BG)
    # reveal banner + answer
    if T_REVEAL <= t < T_BACK + 0.4:
        ba = ease_out(prog(t, T_REVEAL, T_REVEAL + 0.25)) * (1 - prog(t, T_BACK, T_BACK + 0.4))
        c.rect(CX - 210, 205, CX + 210, 268, fill=(*GOLD, int(255 * ba)), r=31)
        c.text(CX, 237, "AUFLÖSUNG", 36, (*BG, int(255 * ba)))
        aa = ease_out(prog(t, spec["t_answer"], spec["t_answer"] + 0.3)) * (1 - prog(t, T_BACK, T_BACK + 0.4))
        if aa > 0:
            text_block(c, spec["answer"], 330 + (1 - aa) * 16, 58, aa)


def sounds(spec, dur=DUR):
    T_REVEAL = spec.get("t_reveal", 8.0)
    T_BACK = spec.get("t_back", 15.6)
    T_COUNT = spec.get("t_count", T_REVEAL)
    s = [(0.0, sfx.whoosh(0.35), 0.5), (0.0, drone(dur), 0.35)]
    s += [(1.0 + k * 0.5, sfx.click(), 0.35) for k in range(int((T_COUNT - 1.0) / 0.5))]
    s += [(T_COUNT - n, sfx.beep(880, 0.12), 0.45) for n in (3, 2, 1)]
    s += spec.get("extra_snd", [])
    s += [(T_REVEAL, sfx.bass_hit(), 0.9), (T_REVEAL, sfx.whoosh(0.4), 0.5)]
    s += [(ts, sfx.whoosh(0.5), 0.45) for ts in spec["steps"]]
    s += [(spec["t_answer"], ding(), 0.7)]
    s += [(T_BACK, sfx.whoosh(0.6, False), 0.5)]
    return [x for x in s if x[0] < dur - 0.2]


def ding():
    return sfx.clang(1320, 1.6, 0.4) * 0.6 + sfx.clang(1980, 1.6, 0.2) * 0.3


def drone(d):
    t = sfx.tt(d)
    x = sum(np.sin(2 * np.pi * f * t + i) for i, f in enumerate((55, 82.4, 110.3)))
    x *= 0.6 + 0.4 * np.sin(2 * np.pi * 0.25 * t)
    return sfx.fade(sfx.norm(x) * 0.35, 1.0, 1.5)


def reveal_amount(t, a, b):
    """0 -> 1 between a and b, back to 0 when the video rewinds at T_BACK."""
    return ease(prog(t, a, b)) * (1 - ease(prog(t, T_BACK, T_BACK + 0.9)))


# ------------------------------------------------------------------ 1. checker shadow (Adelson)
N = 5
SC = 120
SQ = 0.7
BCX, BCY = CX, 960
LIGHT = np.array([206.0, 206.0, 210.0])
SHADOW = 0.6
DARK = LIGHT * SHADOW            # identical to a light square in shadow
A_SQ, B_SQ = (1, 0), (2, 2)
SH_C, SH_A, SH_B = (580.0, 975.0), 300.0, 95.0


def board_pt(u, v):
    pu, pv = (u - N / 2) * SC, (v - N / 2) * SC
    return (BCX + (pu - pv) * 0.7071, BCY + (pu + pv) * 0.7071 * SQ)


def square_poly(i, j):
    return [board_pt(i, j), board_pt(i + 1, j), board_pt(i + 1, j + 1), board_pt(i, j + 1)]


def shadow_d(x, y):
    return ((x - SH_C[0]) / SH_A) ** 2 + ((y - SH_C[1]) / SH_B) ** 2


_cache = {}


def checker_image():
    if "checker" in _cache:
        return _cache["checker"]
    L = Canvas().layer()
    # slab thickness
    l, b, r = board_pt(0, N), board_pt(N, N), board_pt(N, 0)
    L.poly([l, b, (b[0], b[1] + 38), (l[0], l[1] + 38)], fill=(70, 72, 80))
    L.poly([b, r, (r[0], r[1] + 38), (b[0], b[1] + 38)], fill=(50, 52, 58))
    arr = np.array(L.img).astype(np.float32)
    ys, xs = np.mgrid[0:H * SS, 0:W * SS].astype(np.float32) / SS
    x, y = xs - BCX, (ys - BCY) / SQ
    pu = (x + y) * 0.7071 / SC + N / 2
    pv = (y - x) * 0.7071 / SC + N / 2
    inside = (pu >= 0) & (pu < N) & (pv >= 0) & (pv < N)
    parity = (np.floor(pu) + np.floor(pv)) % 2
    col = np.where(parity[..., None] == 0, LIGHT, DARK)
    d = shadow_d(xs, ys)
    sh = np.clip((d - 0.75) / (1.2 - 0.75), 0, 1)
    sh = sh * sh * (3 - 2 * sh)                       # smooth edge, flat core
    fac = (SHADOW + (1 - SHADOW) * sh)[..., None]
    col = col * fac
    arr[inside, :3] = col[inside]
    arr[inside, 3] = 255
    img = Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGBA")
    L.img, L.d = img, ImageDraw.Draw(img, "RGBA")
    # green cylinder casting the shadow
    cx0, cy0, rr, hh = 752, 952, 62, 250
    L.ellipse(cx0, cy0, rr, rr * SQ * 0.55, fill=(40, 108, 48))
    for k in range(int(rr * 2)):
        xx = cx0 - rr + k
        shade = 0.55 + 0.45 * math.sin(math.pi * (k / (rr * 2)) ** 0.8)
        L.line([(xx, cy0 - hh), (xx, cy0 - 4)], (int(60 * shade), int(160 * shade), int(72 * shade)), 1.2, cap=False)
    L.ellipse(cx0, cy0 - hh, rr, rr * SQ * 0.55, fill=(110, 200, 120))
    for sq, name in ((A_SQ, "A"), (B_SQ, "B")):
        p = board_pt(sq[0] + 0.5, sq[1] + 0.5)
        L.text(p[0], p[1] + 2, name, 58, (24, 24, 28))
    _cache["checker"] = L
    return L


def check_checker():
    """The whole point: B must sit fully inside the flat shadow core, A fully outside it."""
    assert all(shadow_d(*p) < 0.75 for p in square_poly(*B_SQ)), "B not in shadow core"
    assert all(shadow_d(*p) > 1.2 for p in square_poly(*A_SQ)), "A touches the shadow"


def draw_checker(c, t):
    c.fill(BG)
    c.paste(checker_image())
    dark = tuple(int(round(v)) for v in DARK)
    pa = board_pt(A_SQ[0] + 0.5, A_SQ[1] + 0.5)
    pb = board_pt(B_SQ[0] + 0.5, B_SQ[1] + 0.5)
    fade = reveal_amount(t, 10.0, 10.8)
    if fade > 0:
        c.overlay(BG, 0.92 * fade)
        for sq in (A_SQ, B_SQ):
            c.poly(square_poly(*sq), fill=dark)
    bar = reveal_amount(t, 8.4, 9.4)
    if bar > 0:
        # bar in the exact grey of both squares, grown from A to B
        w = 46
        ex = (lerp(pa[0], pb[0], bar), lerp(pa[1], pb[1], bar))
        dx, dy = pb[0] - pa[0], pb[1] - pa[1]
        n = math.hypot(dx, dy)
        nx, ny = -dy / n * w / 2, dx / n * w / 2
        c.poly([(pa[0] + nx, pa[1] + ny), (ex[0] + nx, ex[1] + ny), (ex[0] - nx, ex[1] - ny),
                (pa[0] - nx, pa[1] - ny)], fill=dark)
    if fade > 0 or bar > 0:
        for p, name in ((pa, "A"), (pb, "B")):
            c.text(p[0], p[1] + 2, name, 58, (24, 24, 28))
    if fade > 0.5:
        a = int(255 * ease(prog(fade, 0.5, 1)))
        c.text(CX, 1300, "exakt derselbe Grauton", 40, (*GOLD, a))


SCHACH = dict(
    slug="schach", question="Welches Feld ist dunkler:\nA oder B?",
    answer=[("Beide Felder haben", WHITE), ("die GLEICHE Farbe!", GOLD)],
    steps=[8.4, 10.0], t_answer=10.6, draw=draw_checker)


# ------------------------------------------------------------------ 2. café wall
TILE, ROW, MORTAR = 72, 66, 5
ROWS = 12
WALL_Y0 = 560
WALL_X0, WALL_X1 = CX - 6 * TILE, CX + 6 * TILE
OFFS = [0, 1, 2, 1]                 # zig-zag row shift, in thirds of a tile
MORTAR_C = (128, 128, 128)


def draw_cafe(c, t):
    c.fill(BG)
    align = reveal_amount(t, 10.2, 11.4)
    for r in range(ROWS):
        y0 = WALL_Y0 + r * ROW
        off = OFFS[r % 4] * TILE / 3 * (1 - align)
        x = WALL_X0 - 2 * TILE + off
        k = 0
        while x < WALL_X1 + TILE:
            col = (12, 12, 12) if k % 2 == 0 else (245, 245, 245)
            if x + TILE > WALL_X0 and x < WALL_X1:
                c.rect(max(x, WALL_X0), y0, min(x + TILE, WALL_X1), y0 + ROW, fill=col)
            x += TILE
            k += 1
    for r in range(ROWS + 1):
        y = WALL_Y0 + r * ROW
        c.rect(WALL_X0, y - MORTAR / 2, WALL_X1, y + MORTAR / 2, fill=MORTAR_C)
    lines = reveal_amount(t, 8.4, 9.6)
    if lines > 0:
        for r in range(1, ROWS):
            y = WALL_Y0 + r * ROW
            p = ease_out(prog(lines * 1.4 - r * 0.03, 0, 1))
            if p > 0:
                c.line([(WALL_X0 - 10, y), (lerp(WALL_X0 - 10, WALL_X1 + 10, p), y)], (255, 40, 60, 235), 5)


CAFE = dict(
    slug="cafe", question="Sind diese Linien schief?",
    answer=[("Alle Linien sind", WHITE), ("PERFEKT gerade!", GOLD)],
    steps=[8.4, 10.2], t_answer=9.4, draw=draw_cafe)


# ------------------------------------------------------------------ 3. Ebbinghaus
ORANGE = (255, 138, 28)
R0 = 54
TOP, BOT = (CX, 770), (CX, 1215)


def draw_ebbinghaus(c, t):
    c.fill(BG)
    gone = reveal_amount(t, 8.4, 9.3)
    move = reveal_amount(t, 9.6, 10.8)
    for (cx, cy), n, rr, dist in ((TOP, 6, 98, R0 + 22 + 98), (BOT, 8, 27, R0 + 16 + 27)):
        if gone >= 1:
            continue
        for k in range(n):
            a = k * 2 * math.pi / n + 0.3
            d = dist * (1 + gone * 1.6)
            c.circle(cx + math.cos(a) * d, cy + math.sin(a) * d, rr * (1 - gone * 0.6),
                     fill=(150, 154, 166, int(255 * (1 - gone))))
    y_mid = 1000
    p_top = (lerp(TOP[0], CX - 120, move), lerp(TOP[1], y_mid, move))
    p_bot = (lerp(BOT[0], CX + 120, move), lerp(BOT[1], y_mid, move))
    if move > 0.6:
        a = int(255 * ease(prog(move, 0.6, 1)))
        for yy in (y_mid - R0, y_mid + R0):
            for k in range(14):
                x0 = CX - 260 + k * 38
                c.line([(x0, yy), (x0 + 22, yy)], (255, 255, 255, a), 4, cap=False)
    for p in (p_top, p_bot):
        c.circle(*p, R0, fill=ORANGE)


EBBING = dict(
    slug="kreise", question="Welcher orange Kreis\nist größer?",
    answer=[("Beide Kreise sind", WHITE), ("GENAU gleich groß!", GOLD)],
    steps=[8.4, 9.6], t_answer=10.6, draw=draw_ebbinghaus)


# ------------------------------------------------------------------ 4. Müller-Lyer
ML_LEN = 520
ML_Y = (800, 1170)


def draw_mueller(c, t):
    c.fill(BG)
    guides = reveal_amount(t, 8.4, 9.2)
    fins = 1 - reveal_amount(t, 9.6, 10.4)
    x0, x1 = CX - ML_LEN / 2, CX + ML_LEN / 2
    col = (235, 235, 240)
    for k, y in enumerate(ML_Y):
        c.line([(x0, y), (x1, y)], col, 12)
        if fins > 0:
            fc = (*col, int(255 * fins))
            d = 95 if k == 0 else -95      # top: fins point outward (>-<), bottom: inward (<->)
            for x, sgn in ((x0, -1), (x1, 1)):
                for dy in (-1, 1):
                    c.line([(x, y), (x + sgn * d * 0.75, y + dy * 85)], fc, 12)
    if guides > 0:
        a = int(255 * guides)
        top, bot = ML_Y[0] - 150, ML_Y[0] - 150 + (ML_Y[1] - ML_Y[0] + 300) * guides
        for x in (x0, x1):
            yy = top
            while yy < bot:
                c.line([(x, yy), (x, min(bot, yy + 24))], (*GOLD, a), 5, cap=False)
                yy += 40


MUELLER = dict(
    slug="linien", question="Welche Linie\nist länger?",
    answer=[("Beide Linien sind", WHITE), ("GLEICH lang!", GOLD)],
    steps=[8.4, 9.6], t_answer=9.4, draw=draw_mueller)


# ------------------------------------------------------------------ 5. Ponzo (railway)
PZ_LEN = 250
PZ_Y = (730, 1250)


def draw_ponzo(c, t):
    c.fill(BG)
    tracks = 1 - reveal_amount(t, 8.4, 9.2)
    move = reveal_amount(t, 9.6, 10.6)
    if tracks > 0:
        a = int(255 * tracks)
        top_y, bot_y = 540, 1440
        lt, rt, lb, rb = CX - 40, CX + 40, CX - 430, CX + 430
        y = bot_y
        gap = 70
        while y > top_y + 10:          # sleepers, closer together towards the horizon
            k = (y - top_y) / (bot_y - top_y)
            c.line([(lerp(lt, lb, k) - 20 * k, y), (lerp(rt, rb, k) + 20 * k, y)], (120, 92, 70, a), 4 + 14 * k)
            gap = 12 + 66 * k
            y -= gap
        for x0, x1 in ((lt, lb), (rt, rb)):
            c.line([(x0, top_y), (x1, bot_y)], (190, 196, 206, a), 12)
    ys = (lerp(PZ_Y[0], 940, move), lerp(PZ_Y[1], 1060, move))
    for y in ys:
        c.rect(CX - PZ_LEN / 2, y - 16, CX + PZ_LEN / 2, y + 16, fill=GOLD, r=4)
    if move > 0.6:
        a = int(255 * ease(prog(move, 0.6, 1)))
        for x in (CX - PZ_LEN / 2, CX + PZ_LEN / 2):
            yy = 860
            while yy < 1140:
                c.line([(x, yy), (x, yy + 22)], (255, 255, 255, a), 4, cap=False)
                yy += 38


PONZO = dict(
    slug="gleise", question="Welcher gelbe Balken\nist länger?",
    answer=[("Beide Balken sind", WHITE), ("GLEICH lang!", GOLD)],
    steps=[8.4, 9.6], t_answer=10.4, draw=draw_ponzo)


# ------------------------------------------------------------------ 6. Zöllner
ZB = (CX - 400, 590, CX + 400, 1390)   # box


def clip_line(px, py, dx, dy, box):
    """Clip the infinite line p + s*d to box; returns two points or None (Liang-Barsky)."""
    x0, y0, x1, y1 = box
    lo, hi = -1e9, 1e9
    for p, q in ((-dx, px - x0), (dx, x1 - px), (-dy, py - y0), (dy, y1 - py)):
        if abs(p) < 1e-9:
            if q < 0:
                return None
            continue
        r = q / p
        if p < 0:
            lo = max(lo, r)
        else:
            hi = min(hi, r)
    if lo > hi:
        return None
    return (px + dx * lo, py + dy * lo), (px + dx * hi, py + dy * hi)


def draw_zoellner(c, t):
    c.fill(BG)
    hatch = 1 - reveal_amount(t, 8.4, 9.4)
    guide = reveal_amount(t, 9.6, 10.4)
    d = (0.7071, 0.7071)
    cxm, cym = (ZB[0] + ZB[2]) / 2, (ZB[1] + ZB[3]) / 2
    for k in range(-4, 5):
        off = k * 130
        px, py = cxm - d[1] * off, cym + d[0] * off          # shift along the normal
        seg = clip_line(px, py, *d, ZB)
        if not seg:
            continue
        (ax, ay), (bx, by) = seg
        col = (240, 240, 245)
        if guide > 0:
            col = (lerp(240, 255, guide), lerp(240, 200, guide), lerp(245, 61, guide))
        c.line([(ax, ay), (bx, by)], tuple(int(v) for v in col), 8)
        if hatch > 0:
            L = math.hypot(bx - ax, by - ay)
            s_ = 30.0
            while s_ < L - 30:
                hx, hy = ax + d[0] * s_, ay + d[1] * s_
                if k % 2 == 0:
                    a0, a1 = (hx - 34, hy), (hx + 34, hy)
                else:
                    a0, a1 = (hx, hy - 34), (hx, hy + 34)
                c.line([a0, a1], (240, 240, 245, int(255 * hatch)), 6)
                s_ += 46


ZOELLNER = dict(
    slug="parallel", question="Laufen diese Linien\nparallel?",
    answer=[("JA! Alle Linien sind", WHITE), ("PERFEKT parallel!", GOLD)],
    steps=[8.4, 9.6], t_answer=9.6, draw=draw_zoellner)


# ------------------------------------------------------------------ 7. scintillating grid
GRID_N, GRID_SP = 9, 92


def draw_grid(c, t):
    c.fill((0, 0, 0))
    lines = 1 - reveal_amount(t, 8.4, 9.4)
    span = GRID_SP * (GRID_N - 1)
    x0, y0 = CX - span / 2, 985 - span / 2
    if lines > 0:
        g = int(105 * lines)
        for i in range(GRID_N):
            c.rect(x0 + i * GRID_SP - 7, y0 - 40, x0 + i * GRID_SP + 7, y0 + span + 40, fill=(g, g, g))
            c.rect(x0 - 40, y0 + i * GRID_SP - 7, x0 + span + 40, y0 + i * GRID_SP + 7, fill=(g, g, g))
    for i in range(GRID_N):
        for j in range(GRID_N):
            c.circle(x0 + i * GRID_SP, y0 + j * GRID_SP, 11.5, fill=WHITE)


GRID = dict(
    slug="punkte", question="Wie viele SCHWARZE\nPunkte siehst du?",
    answer=[("KEINEN! Alle Punkte", WHITE), ("sind WEISS!", GOLD)],
    steps=[8.4], t_answer=9.2, draw=draw_grid)


# ------------------------------------------------------------------ 8. contrast bar
CB = (CX - 425, 590, CX + 425, 1380)
BAR_G = (128, 128, 128)


def draw_contrast(c, t):
    c.fill(BG)
    flat = reveal_amount(t, 8.4, 9.6)
    x0, y0, x1, y1 = CB
    step = 4
    x = x0
    while x < x1:
        k = (x - x0) / (x1 - x0)
        v = lerp(lerp(0, 255, k), 128, 0)            # black -> white gradient
        v = lerp(v, 60, flat)                         # reveal: background goes flat
        c.rect(x, y0, x + step + 1, y1, fill=(int(v), int(v), int(v)))
        x += step
    c.rect(x0 + 40, 940, x1 - 40, 1030, fill=BAR_G)
    out = reveal_amount(t, 9.8, 10.4)
    if out > 0:
        c.rect(x0 + 34, 934, x1 - 34, 1036, outline=(*GOLD, int(255 * out)), w=6)


CONTRAST = dict(
    slug="balken", question="Ist der Balken überall\ngleich grau?",
    answer=[("JA! Der Balken ist", WHITE), ("ÜBERALL gleich grau!", GOLD)],
    steps=[8.4, 9.8], t_answer=9.8, draw=draw_contrast)


# ------------------------------------------------------------------ 9. top hat (vertical-horizontal)
HAT_W, HAT_Y = 420, 1230          # brim width == total hat height


def draw_hat(c, t):
    c.fill(BG)
    x0, x1 = CX - HAT_W / 2, CX + HAT_W / 2
    top = HAT_Y - HAT_W
    crown = (235, 235, 240)
    c.rect(CX - 115, top, CX + 115, HAT_Y - 20, fill=crown)
    c.rect(CX - 115, HAT_Y - 110, CX + 115, HAT_Y - 60, fill=(214, 36, 44))
    c.rect(x0, HAT_Y - 30, x1, HAT_Y, fill=crown, r=10)
    rot = ease(prog(t, 6.9, 8.0))
    if rot > 0:
        # a gold copy of the brim swings up next to the hat
        a = math.radians(-90 * rot)
        px, py = x1 + 40, HAT_Y
        L = HAT_W
        ex, ey = px - math.cos(a) * L, py + math.sin(a) * L
        c.line([(px, py), (ex, ey)], (*GOLD, 235), 26)
    if t > 8.1:
        a = int(255 * ease(prog(t, 8.1, 8.5)))
        for yy in (top, HAT_Y):
            xx = x0 - 30
            while xx < x1 + 90:
                c.line([(xx, yy), (xx + 22, yy)], (255, 255, 255, a), 4, cap=False)
                xx += 38


HAT = dict(
    slug="hut", question="Ist der Hut höher\nals breit?", seg=11.0, t_reveal=6.5,
    answer=[("Der Hut ist GENAU so", WHITE), ("hoch wie breit!", GOLD)],
    steps=[6.9], t_answer=8.1, draw=draw_hat)


# ------------------------------------------------------------------ 10. confetti / colour assimilation
STRIPE = 9
STRIPES = [(236, 32, 52), (20, 190, 80), (40, 90, 255)]
BALL = (196, 196, 196)
BALLS = [(CX - 250, 700, 0), (CX + 60, 640, 1), (CX + 300, 790, 2), (CX - 120, 900, 2), (CX + 180, 1010, 0),
         (CX - 300, 1080, 1), (CX + 330, 1200, 1), (CX - 60, 1180, 0), (CX - 280, 1300, 2), (CX + 90, 1330, 2)]
BR = 68
BOX = (CX - 420, 560, CX + 420, 1420)


def draw_confetti(c, t):
    c.fill(BG)
    plain = ease(prog(t, 8.4, 9.4))
    x0, y0, x1, y1 = BOX
    y = y0
    k = 0
    while y < y1:
        c.rect(x0, y, x1, y + STRIPE, fill=STRIPES[k % 3])
        y += STRIPE
        k += 1
    for bx, by, g in BALLS:
        c.circle(bx, by, BR, fill=BALL)
        if plain < 1:
            col = (*STRIPES[g], int(255 * (1 - plain)))
            # the stripes of one colour run OVER the ball -> it takes on that colour
            y = y0 + g * STRIPE
            while y < y1:
                yc0, yc1 = max(y, by - BR), min(y + STRIPE, by + BR)
                if yc1 > yc0:
                    ym = (yc0 + yc1) / 2
                    hw = math.sqrt(max(0, BR * BR - (ym - by) ** 2))
                    c.rect(bx - hw, yc0, bx + hw, yc1, fill=col)
                y += 3 * STRIPE


CONFETTI = dict(
    slug="kugeln", question="Wie viele ROTE\nKugeln siehst du?", seg=12.0, t_reveal=8.0,
    answer=[("KEINE! Alle Kugeln", WHITE), ("sind GRAU!", GOLD)],
    steps=[8.4], t_answer=9.2, draw=draw_confetti)


# ------------------------------------------------------------------ 11. rotating snakes (peripheral drift)
SN_C = [(CX - 205, 790), (CX + 205, 790), (CX - 205, 1200), (CX + 205, 1200)]
SN_R = 200
SN_MOVE = [(12, 12, 12), (40, 70, 200), (250, 250, 250), (250, 210, 30)]   # black, blue, white, yellow
SN_STILL = [(12, 12, 12), (130, 130, 130), (250, 250, 250), (130, 130, 130)]


def snakes_image(cols):
    key = ("snakes", tuple(cols))
    if key in _cache:
        return _cache[key]
    L = Canvas().layer()
    props = [0.14, 0.36, 0.14, 0.36]
    for di, (cx, cy) in enumerate(SN_C):
        L.circle(cx, cy, SN_R + 6, fill=(60, 60, 66))
        rings = 6
        for ri in range(rings):
            r = SN_R - ri * (SN_R - 30) / rings
            n = 28 - ri * 3
            flip = (ri + di) % 2
            off = ri * 7.0
            for k in range(n):
                a = off + k * 360 / n
                order = range(4) if not flip else range(3, -1, -1)
                for j in order:
                    span = 360 / n * props[j]
                    L.pie(cx, cy, r, a, a + span + 0.4, cols[j])
                    a += span
        L.circle(cx, cy, 30, fill=(60, 60, 66))
    _cache[key] = L
    return L


def draw_snakes(c, t):
    c.fill(BG)
    still = ease(prog(t, 8.4, 9.4))
    if still <= 0:
        c.paste(snakes_image(SN_MOVE))
    elif still >= 1:
        c.paste(snakes_image(SN_STILL))
    else:
        a, b = snakes_image(SN_MOVE).img, snakes_image(SN_STILL).img
        L = Canvas().layer()
        L.img = Image.blend(a, b, still)
        c.paste(L)


SNAKES = dict(
    slug="bewegung", question="Das ist ein STANDBILD.\nWarum dreht es sich?", seg=12.0, t_reveal=8.0,
    answer=[("Es dreht sich NICHT!", WHITE), ("Dein Gehirn erfindet es.", GOLD)],
    steps=[8.4], t_answer=9.2, draw=draw_snakes)


# ------------------------------------------------------------------ 12. afterimage flag (finale)
FL = (CX - 410, 985 - 246, CX + 410, 985 + 246)
FLAG_REAL = [(16, 16, 16), (221, 0, 0), (255, 206, 0)]
FLAG_NEG = [tuple(255 - v for v in col) for col in FLAG_REAL]
T_STARE, T_WHITE = 12.0, 15.0


def flag(c, box, cols, alpha=255):
    x0, y0, x1, y1 = box
    h = (y1 - y0) / 3
    for i, col in enumerate(cols):
        c.rect(x0, y0 + i * h, x1, y0 + (i + 1) * h + (1 if i < 2 else 0), fill=(*col, alpha))


def draw_afterimage(c, t):
    if t < T_STARE:
        c.fill(BG)
        flag(c, FL, FLAG_NEG)
        c.circle(CX, 985, 15, fill=(0, 0, 0))
        c.circle(CX, 985, 9, fill=(255, 30, 30))
    elif t < T_WHITE:
        c.fill((250, 250, 250))
        c.circle(CX, 985, 9, fill=(0, 0, 0))
    else:
        c.fill(BG)
        a = ease_out(prog(t, T_WHITE + 0.9, T_WHITE + 1.4))
        sm = lambda cx: (cx - 190, 1020 - 114, cx + 190, 1020 + 114)
        flag(c, sm(CX - 215), FLAG_NEG, int(255 * a))
        b = ease_out(prog(t, T_WHITE + 1.6, T_WHITE + 2.1))
        flag(c, sm(CX + 215), FLAG_REAL, int(255 * b))
        if b > 0:
            c.text(CX - 215, 1190, "gezeigt", 36, (*WHITE, int(200 * a)))
            c.text(CX + 215, 1190, "gesehen", 36, (*GOLD, int(255 * b)))


def post_afterimage(c, t):
    if T_STARE <= t < T_WHITE:
        a = int(255 * ease_out(prog(t, T_STARE + 0.1, T_STARE + 0.4)))
        c.text(CX, 330, "Weiter auf den Punkt", 58, (*BG, a))
        c.text(CX, 398, "schauen... und blinzeln!", 58, (*BG, a))


AFTER = dict(
    slug="flagge", question="Starre 12 Sekunden auf\nden ROTEN PUNKT!", seg=20.0,
    t_count=T_STARE, t_reveal=T_WHITE, t_back=99.0, quiet=(T_STARE, T_WHITE),
    answer=[("Du hast Schwarz-Rot-Gold", WHITE), ("auf WEISS gesehen!", GOLD)],
    steps=[T_WHITE + 0.9, T_WHITE + 1.6], t_answer=T_WHITE + 0.3, draw=draw_afterimage, post=post_afterimage,
    extra_snd=[(T_STARE, sfx.whoosh(0.3), 0.3), (T_STARE, sfx.beep(660, 0.25), 0.4)])


def draw_intro3(c, t, comp):
    c.fill(BG)
    s = back_out(prog(t, 0.05, 0.4))
    c.text(CX, 780, "ACHTUNG", int(120 * s) + 1, (214, 36, 44), stroke=8, stroke_fill=BG)
    a = ease_out(prog(t, 0.4, 0.7))
    text_block(c, [("Diese 4 Täuschungen", WHITE), ("sind richtig GEMEIN", GOLD)], 950, 62, a)
    b = int(255 * ease_out(prog(t, 1.2, 1.5)))
    c.text(CX, 1150, "Fast jeder fällt rein…", 44, (*WHITE, b))


def draw_outro3(c, t):
    c.fill(BG)
    a = ease_out(prog(t, 0.0, 0.3))
    text_block(c, [("Schick das jemandem,", WHITE), ("der IMMER alles", WHITE), ("besser weiß!", GOLD)], 860, 64, a)
    b = int(255 * ease_out(prog(t, 0.8, 1.1)))
    c.text(CX, 1150, "Wie viele hast du geschafft?", 42, (*WHITE, b))


# ------------------------------------------------------------------ 13. stepping feet (motion)
SF_BOX = (CX - 420, 600, CX + 420, 1380)
SF_STRIPE = 30
SF_BAR = 120
SF_SPEED = 170.0


def draw_steps(c, t):
    c.fill(BG)
    x0, y0, x1, y1 = SF_BOX
    plain = ease(prog(t, 7.4, 8.2))
    c.rect(x0, y0, x1, y1, fill=(128, 128, 128))
    if plain < 1:
        a = 1 - plain
        x = x0
        k = 0
        while x < x1:
            v = 0 if k % 2 == 0 else 255
            v = int(lerp(v, 128, plain))
            c.rect(x, y0, min(x1, x + SF_STRIPE), y1, fill=(v, v, v))
            x += SF_STRIPE
            k += 1
    span = (x1 - x0) - SF_BAR
    pos = (t * SF_SPEED) % (2 * span)
    pos = pos if pos < span else 2 * span - pos          # ping-pong at constant speed
    bx = x0 + pos
    c.rect(bx, 830, bx + SF_BAR, 900, fill=(255, 226, 40))
    c.rect(bx, 1080, bx + SF_BAR, 1150, fill=(20, 30, 120))
    if t > 8.4:
        a = int(255 * ease(prog(t, 8.4, 8.8)))
        c.line([(bx + SF_BAR / 2, 800), (bx + SF_BAR / 2, 1180)], (255, 40, 60, a), 5)


STEPS = dict(
    slug="schritte", label="99 % SEHEN ES FALSCH", question="Welcher Balken\nist schneller?", seg=11.0,
    t_reveal=7.0, answer=[("Beide sind GLEICH schnell", WHITE), ("und laufen GLEICHMÄSSIG!", GOLD)],
    steps=[7.4], t_answer=8.2, draw=draw_steps)


# ------------------------------------------------------------------ 14. Shepard tables
TU = (95.0, -290.0)        # long edge of the table top
TV = (150.0, 34.0)         # short edge
TA_C, TB_C = (CX - 175, 870), (CX + 130, 1210)


def _rot(v, deg):
    a = math.radians(deg)
    return (v[0] * math.cos(a) - v[1] * math.sin(a), v[0] * math.sin(a) + v[1] * math.cos(a))


def top_poly(cen, deg):
    u, v = _rot(TU, deg), _rot(TV, deg)
    cx, cy = cen
    return [(cx + sx * u[0] / 2 + sy * v[0] / 2, cy + sx * u[1] / 2 + sy * v[1] / 2)
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def table(c, cen, deg):
    pts = top_poly(cen, deg)
    # legs from the three lowest corners
    for p in sorted(pts, key=lambda q: q[1])[1:]:
        c.line([p, (p[0], p[1] + 150)], (70, 46, 30), 16)
    # table thickness: the visible lower edges
    low = sorted(range(4), key=lambda i: pts[i][1])[-1]
    for nb in ((low + 1) % 4, (low + 3) % 4):
        a, b = pts[low], pts[nb]
        c.poly([a, b, (b[0], b[1] + 24), (a[0], a[1] + 24)], fill=(120, 80, 46))
    c.poly(pts, fill=(204, 148, 92), outline=(90, 60, 36), w=4)


def draw_tables(c, t):
    c.fill(BG)
    table(c, TA_C, 0)
    table(c, TB_C, -90)
    m = ease(prog(t, 8.4, 10.0))
    if m > 0:
        cen = (lerp(TA_C[0], TB_C[0], m), lerp(TA_C[1], TB_C[1], m))
        pts = top_poly(cen, -90 * m)
        c.poly(pts, fill=(*GOLD, 110))
        c.line(pts + [pts[0]], (*GOLD, 255), 6, cap=False)


TABLES = dict(
    slug="tische", label="FAST NIEMAND SCHAFFT DAS", question="Welche Tischplatte\nist länger?", seg=12.0,
    t_reveal=8.0, answer=[("Beide Platten sind", WHITE), ("EXAKT gleich groß!", GOLD)],
    steps=[8.4], t_answer=10.0, draw=draw_tables)


# ------------------------------------------------------------------ 15. Troxler fading
TX_BOX = (CX - 420, 575, CX + 420, 1395)
TX_COLS = [(255, 150, 175), (150, 210, 255), (180, 245, 160), (255, 225, 140), (215, 175, 255), (140, 240, 220)]


def troxler_image():
    if "troxler" in _cache:
        return _cache["troxler"]
    x0, y0, x1, y1 = TX_BOX
    w, h = int((x1 - x0) * SS), int((y1 - y0) * SS)
    im = Image.new("RGB", (w, h), (196, 196, 202))
    d = ImageDraw.Draw(im)
    for k, col in enumerate(TX_COLS):
        a = k * math.pi / 3 + 0.5
        cx, cy = (w / 2 + math.cos(a) * 270 * SS, h / 2 + math.sin(a) * 270 * SS)
        r = 115 * SS
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
    im = im.filter(ImageFilter.GaussianBlur(55 * SS))
    _cache["troxler"] = im
    return im


def draw_troxler(c, t):
    c.fill(BG)
    x0, y0 = TX_BOX[0], TX_BOX[1]
    c.img.paste(troxler_image(), (int(x0 * SS), int(y0 * SS)))
    cx, cy = (TX_BOX[0] + TX_BOX[2]) / 2, (TX_BOX[1] + TX_BOX[3]) / 2
    c.line([(cx - 22, cy), (cx + 22, cy)], (20, 20, 24), 6)
    c.line([(cx, cy - 22), (cx, cy + 22)], (20, 20, 24), 6)


TROXLER = dict(
    slug="verschwinden", label="DAS IST KEIN FAKE",
    question="Starre 10 Sek. auf das\nKREUZ. Was passiert?", seg=15.0,
    t_count=11.0, t_reveal=11.0,
    answer=[("Dein Gehirn hat die", WHITE), ("Farben GELÖSCHT!", GOLD)],
    steps=[], t_answer=11.6, draw=draw_troxler)


# ------------------------------------------------------------------ 16. spiral motion aftereffect (finale)
SP_C, SP_R = (CX, 985), 410
SP_STARE, SP_STILL = 13.0, 16.5
_sp = {}


def _spiral_grid():
    if not _sp:
        n = int(2 * SP_R * SS)
        ys, xs = np.mgrid[0:n, 0:n].astype(np.float32)
        x, y = xs - n / 2, ys - n / 2
        r = np.sqrt(x * x + y * y) + 1
        _sp["theta"], _sp["logr"] = np.arctan2(y, x), np.log(r)
        _sp["mask"] = Image.fromarray(((r < n / 2) * 255).astype(np.uint8), "L")
        _sp["n"] = n
    return _sp


def draw_spiral(c, t):
    c.fill(BG)
    g = _spiral_grid()
    pos = (int((SP_C[0] - SP_R) * SS), int((SP_C[1] - SP_R) * SS))
    if t < SP_STARE:
        ph = g["theta"] * 4 + g["logr"] * 7 - t * 7.0
        v = (np.sin(ph) > 0).astype(np.uint8) * 235 + 10
        im = Image.fromarray(np.stack([v, v, v], -1), "RGB")
        c.img.paste(im, pos, g["mask"])
        c.circle(*SP_C, 12, fill=(255, 30, 30))
    else:
        # static picture: viewers' brains keep "moving" it after the spiral
        key = "spiral_still"
        if key not in _cache:
            n = g["n"]
            im = Image.new("RGB", (n, n), (245, 245, 245))
            d = ImageDraw.Draw(im)
            step = n / 12
            for i in range(12):
                for j in range(12):
                    if (i + j) % 2 == 0:
                        d.rectangle((i * step, j * step, (i + 1) * step, (j + 1) * step), fill=(40, 120, 220))
            _cache[key] = im
        c.img.paste(_cache[key], pos, g["mask"])
        c.circle(*SP_C, 12, fill=(255, 30, 30))


def post_spiral(c, t):
    if SP_STARE <= t < SP_STILL:
        a = int(255 * ease_out(prog(t, SP_STARE + 0.05, SP_STARE + 0.35)))
        text_block(c, [("Weiter auf den Punkt!", WHITE), ("Siehst du das?", GOLD)], 318, 58, a / 255)


SPIRAL = dict(
    slug="spirale", label="NICHT WEGSCHAUEN",
    question="Starre 12 Sek. auf\nden ROTEN PUNKT!", seg=20.0,
    t_count=SP_STARE, t_reveal=SP_STILL, t_back=99.0, quiet=(SP_STARE, SP_STILL),
    answer=[("Das Bild steht STILL!", WHITE), ("Schau jetzt auf deine Hand", GOLD)],
    steps=[], t_answer=SP_STILL + 0.5, draw=draw_spiral, post=post_spiral,
    extra_snd=[(SP_STARE, sfx.whoosh(0.3), 0.4), (SP_STARE, sfx.beep(660, 0.25), 0.4)])


def draw_outro4(c, t):
    c.fill(BG)
    a = ease_out(prog(t, 0.0, 0.3))
    text_block(c, [("Schick das jemandem", WHITE), ("und sag NICHTS!", GOLD)], 880, 66, a)
    b = int(255 * ease_out(prog(t, 0.6, 0.9)))
    c.text(CX, 1080, "Bei welcher bist du", 44, (*WHITE, b))
    c.text(CX, 1140, "reingefallen? 1, 2, 3 oder 4?", 44, (*WHITE, b))


# ------------------------------------------------------------------ build
ALL = [SCHACH, CAFE, EBBING, MUELLER, PONZO, ZOELLNER, GRID, CONTRAST, HAT, CONFETTI, SNAKES, AFTER, STEPS, TABLES, TROXLER, SPIRAL]
SEG = 14.0                      # per illusion inside the 60 s compilation
COMPS = {
    "1": dict(cta="FOLGEN für Teil 2", items=[CAFE, MUELLER, EBBING, SCHACH], top="optische Täuschungen", outro_dur=4.0,
              out="optische_taeuschungen_60s"),
    "2": dict(cta="FOLGEN für Teil 3", items=[PONZO, ZOELLNER, GRID, CONTRAST], top="NEUE Täuschungen", part="TEIL 2", outro_dur=4.0,
              out="optische_taeuschungen_teil2_60s"),
    "3": dict(cta="FOLGEN für Teil 4", items=[HAT, CONFETTI, SNAKES, AFTER], intro=draw_intro3, outro=draw_outro3,
              intro_dur=2.5, outro_dur=5.0, out="optische_taeuschungen_teil3_gemein_60s"),
    "4": dict(cta="FOLGEN für Teil 5", items=[STEPS, TABLES, TROXLER, SPIRAL], intro_dur=0, outro=draw_outro4, outro_dur=4.5,
              out="optische_taeuschungen_teil4_viral_60s"),
}


def draw_intro(c, t, comp):
    c.fill(BG)
    if comp.get("part"):
        c.text(CX, 640, comp["part"], 44, (*WHITE, int(200 * ease_out(prog(t, 0, 0.3)))))
    s = back_out(prog(t, 0.05, 0.4))
    c.text(CX, 820, "4", int(300 * s) + 1, GOLD, stroke=8, stroke_fill=BG)
    a = int(255 * ease_out(prog(t, 0.3, 0.6)))
    c.text(CX, 1010, comp["top"], 62, (*WHITE, a))
    b = int(255 * ease_out(prog(t, 0.9, 1.2)))
    c.text(CX, 1110, "Schaffst du alle?", 62, (*GOLD, b))


def follow_cta(c, a, txt="FOLGEN für mehr"):
    """'Follow for more' pill shown at the end of every video."""
    w = c.text_w(txt, 42) + 90
    c.rect(CX - w / 2, 1290, CX + w / 2, 1370, fill=(214, 36, 44, int(255 * a)), r=40)
    c.text(CX, 1331, txt, 42, (*WHITE, int(255 * a)))


def draw_outro(c, t):
    c.fill(BG)
    a = ease_out(prog(t, 0.0, 0.3))
    text_block(c, [("Wie viele hattest", WHITE), ("du richtig?", WHITE)], 860, 70, a)
    b = ease_out(prog(t, 0.5, 0.8))
    text_block(c, [("0 / 1 / 2 / 3 / 4", GOLD)], 1080, 70, b)
    c.text(CX, 1220, "Schreib es in die Kommentare!", 40, (*WHITE, int(200 * b)))


def make_compilation(comp):
    COMP = comp["items"]
    intro = comp.get("intro", draw_intro)
    scenes = [Scene(comp.get("intro_dur", 2.5), lambda c, t: intro(c, t, comp), None, [(0.0, sfx.whoosh(0.4), 0.5), (0.05, sfx.bass_hit(), 0.9),
                                            (0.9, ding(), 0.5)], header=False, zoom=1.0, ty=1330.0)]
    if not comp.get("intro_dur", 2.5):
        scenes = []
    for i, spec in enumerate(COMP):
        sp = dict(spec, label=f"OPTISCHE TÄUSCHUNG  {i + 1}/{len(COMP)}")
        if spec.get("label"):
            sp["label"] = spec["label"] + f"  ·  {i + 1}/{len(COMP)}"

        def draw(c, t, sp=sp):
            sp["draw"](c, t)
            overlay_text(c, t, sp)
            if sp.get("post"):
                sp["post"](c, t)

        seg = sp.get("seg", SEG)
        scenes.append(Scene(seg, draw, None, sounds(sp, seg), header=False, zoom=1.0, ty=1330.0))
    outro = comp.get("outro", draw_outro)
    def outro_cta(c, t, outro=outro):
        outro(c, t)
        a = ease_out(prog(t, 1.6, 2.0))
        if a > 0:
            follow_cta(c, a, comp.get("cta", "FOLGEN für mehr"))

    scenes.append(Scene(comp.get("outro_dur", 4.0), outro_cta, None, [(0.0, sfx.whoosh(0.4), 0.5), (0.5, sfx.click(), 0.6)],
                        header=False, zoom=1.0, ty=1330.0))
    return Film("Optische Täuschungen", "60s", scenes)


def make(spec):
    def draw(c, t):
        spec["draw"](c, t)
        overlay_text(c, t, spec)

    return Film("Optische Täuschung", spec["slug"],
                [Scene(DUR, draw, None, sounds(spec), header=False, zoom=1.0, ty=1330.0)])


if __name__ == "__main__":
    check_checker()
    if "--compilation" in sys.argv:
        key = sys.argv[sys.argv.index("--compilation") + 1] if len(sys.argv) > sys.argv.index("--compilation") + 1 \
            and not sys.argv[sys.argv.index("--compilation") + 1].startswith("--") else "1"
        comp = COMPS[key]
        film = make_compilation(comp)
        print(f"duration {film.dur:.1f}s")
        if "--sheet" in sys.argv:
            st = film.starts
            o = 1 if comp.get("intro_dur", 2.5) else 0
            print(stills(film, [0.2] + [st[i + o] + k * film.scenes[i + o].dur for i in range(4) for k in (0.3, 0.62, 0.8, 0.95)] + [59.5],
                         f"output/preview_comp{key}", cols=7, scale=0.22))
        else:
            render(film, f"output/{comp['out']}.mp4")
        sys.exit()
    names = [a for a in sys.argv[1:] if not a.startswith("--")]
    specs = [s for s in ALL if not names or s["slug"] in names]
    for spec in specs:
        film = make(spec)
        if "--sheet" in sys.argv:
            print(stills(film, [0.5, 4.0, 7.5, 8.6, 9.5, 11.0, 13.0, 16.0, 17.3],
                         f"output/preview_{spec['slug']}", cols=9, scale=0.25))
        else:
            render(film, f"output/optische_taeuschung_{spec['slug']}.mp4")
