"""Optical illusion shorts: question -> countdown -> reveal with proof -> loop back.

Render all:   python3 -m films.illusions
Render one:   python3 -m films.illusions schach
Preview:      python3 -m films.illusions schach --sheet
"""
import math
import sys

import numpy as np
from PIL import Image, ImageDraw

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
    if 1.0 <= t < T_REVEAL:
        k = 1 - prog(t, 1.0, T_REVEAL)
        y = 318 + 58 * 1.18 * (len(wrap(c, spec["question"], 58, 820)) - 1) + 62
        c.rect(CX - 300, y, CX + 300, y + 10, fill=(255, 255, 255, 40), r=5)
        c.rect(CX - 300, y, CX - 300 + 600 * k, y + 10, fill=(*GOLD, 230), r=5)
        n = int(math.ceil(T_REVEAL - t))
        if n <= 3:
            p = (T_REVEAL - t) % 1.0
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
    s = [(0.0, sfx.whoosh(0.35), 0.5), (0.0, drone(dur), 0.35)]
    s += [(1.0 + k * 0.5, sfx.click(), 0.35) for k in range(int((T_REVEAL - 1.0) / 0.5))]
    s += [(T_REVEAL - n, sfx.beep(880, 0.12), 0.45) for n in (3, 2, 1)]
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


# ------------------------------------------------------------------ build
ALL = [SCHACH, CAFE, EBBING, MUELLER]
SEG = 14.0                      # per illusion inside the 60 s compilation
COMP = [CAFE, MUELLER, EBBING, SCHACH]


def draw_intro(c, t):
    c.fill(BG)
    s = back_out(prog(t, 0.05, 0.4))
    c.text(CX, 820, "4", int(300 * s) + 1, GOLD, stroke=8, stroke_fill=BG)
    a = int(255 * ease_out(prog(t, 0.3, 0.6)))
    c.text(CX, 1010, "optische Täuschungen", 62, (*WHITE, a))
    b = int(255 * ease_out(prog(t, 0.9, 1.2)))
    c.text(CX, 1110, "Schaffst du alle?", 62, (*GOLD, b))


def draw_outro(c, t):
    c.fill(BG)
    a = ease_out(prog(t, 0.0, 0.3))
    text_block(c, [("Wie viele hattest", WHITE), ("du richtig?", WHITE)], 860, 70, a)
    b = ease_out(prog(t, 0.5, 0.8))
    text_block(c, [("0 / 1 / 2 / 3 / 4", GOLD)], 1080, 70, b)
    c.text(CX, 1220, "Schreib es in die Kommentare!", 40, (*WHITE, int(200 * b)))


def make_compilation():
    scenes = [Scene(2.5, draw_intro, None, [(0.0, sfx.whoosh(0.4), 0.5), (0.05, sfx.bass_hit(), 0.9),
                                            (0.9, ding(), 0.5)], header=False, zoom=1.0, ty=1330.0)]
    for i, spec in enumerate(COMP):
        sp = dict(spec, label=f"OPTISCHE TÄUSCHUNG  {i + 1}/{len(COMP)}")

        def draw(c, t, sp=sp):
            sp["draw"](c, t)
            overlay_text(c, t, sp)

        scenes.append(Scene(SEG, draw, None, sounds(sp, SEG), header=False, zoom=1.0, ty=1330.0))
    scenes.append(Scene(1.5, draw_outro, None, [(0.0, sfx.whoosh(0.4), 0.5), (0.5, sfx.click(), 0.6)],
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
        film = make_compilation()
        print(f"duration {film.dur:.1f}s")
        if "--sheet" in sys.argv:
            print(stills(film, [1.5] + [2.5 + i * SEG + k for i in range(4) for k in (3, 9, 12)] + [59.5],
                         "output/preview_comp", cols=7, scale=0.22))
        else:
            render(film, "output/optische_taeuschungen_60s.mp4")
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
