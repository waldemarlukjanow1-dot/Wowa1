"""'Finde den Fehler' Teil 2 - cat theme, with a cheeky cat (top right) that keeps distracting you.

Render:  python3 -m films.finde_den_fehler_katze
Preview: python3 -m films.finde_den_fehler_katze --sheet
"""
import math
import random
import sys

import numpy as np

from engine import sfx
from engine.gfx import INK, back_out, ease, ease_in, ease_out, lerp, prog
from engine.render import Film, Scene, render, stills
from films.illusions import BG, CX, GOLD, WHITE, ding, drone, follow_cta, text_block

RED = (230, 50, 60)
GRID = (90, 640, 880, 1440)
REVEAL = 2.6
ORANGE = (240, 150, 60)
ORANGE_D = (196, 104, 34)
PINK = (245, 140, 160)

# ------------------------------------------------------------------ sounds
def meow(d=0.65, pitch=1.0):
    t = sfx.tt(d)
    k = t / d
    f0 = pitch * (520 + 380 * np.sin(np.pi * np.clip(k * 1.2, 0, 1)) - 120 * k)
    f0 = f0 * (1 + 0.02 * np.sin(2 * np.pi * 6 * t))
    ph = 2 * np.pi * np.cumsum(f0) / sfx.SR
    x = np.zeros_like(t)
    for h in range(1, 9):
        fh = f0 * h
        # vowel-ish formants: "iiii-aaaa-uuu" sweep
        form = np.exp(-((fh - lerp(2600, 900, k)) / 700) ** 2) + 0.6 * np.exp(-((fh - 700) / 400) ** 2)
        x += np.sin(ph * h) * form / h ** 0.3
    e = np.minimum(1, t / 0.06) * np.minimum(1, (d - t) / 0.18)
    return sfx.norm(x * e) * 0.9


def purr(d=1.2):
    t = sfx.tt(d)
    x = sfx.band(sfx.noise(d), 40, 400) * (0.5 + 0.5 * np.sin(2 * np.pi * 24 * t)) ** 2
    return sfx.fade(sfx.norm(x) * 0.6, 0.1, 0.3)


# ------------------------------------------------------------------ mascot cat
CAT = (985, 590)
CAT_R = 104


def speech_right(c, txt, a, y=540, right=850, tip=(905, 610)):
    """Speech bubble whose tail points to the cat on the right."""
    if a <= 0:
        return
    size = 40
    w = c.text_w(txt, size) + 56
    h = size + 40
    x1 = right
    x0 = x1 - w
    al = int(255 * a)
    c.poly([(x1 - 70, y + h / 2 - 4), (x1 - 24, y + h / 2 - 4), tip], fill=(255, 255, 255, al),
           outline=(*INK, al), w=5)
    c.rect(x0, y - h / 2, x1, y + h / 2, fill=(255, 255, 255, al), outline=(*INK, al), w=5, r=26)
    c.poly([(x1 - 66, y + h / 2 - 8), (x1 - 28, y + h / 2 - 8), (tip[0] - 6, tip[1] - 8)], fill=(255, 255, 255, al))
    c.text((x0 + x1) / 2, y + 2, txt, size, (*INK, al))


def cat(c, t, talk=0.0, mood="sly", slide=1.0):
    x = lerp(1250, CAT[0], ease_out(slide)) + math.sin(t * 2.2) * 4
    y = CAT[1] + math.sin(t * 3.1) * 3
    r = CAT_R
    # tail swishing behind
    sw = math.sin(t * 2.8) * 30
    c.line([(x + 40, y + 120), (x + 10, y + 40 + sw * 0.3), (x - 30 + sw, y - 40)], ORANGE_D, 26)
    # ears (with twitch)
    tw = 8 * max(0, math.sin(t * 1.7)) ** 20
    for sx in (-1, 1):
        ex = x + sx * r * 0.55
        c.poly([(ex - 42, y - r * 0.55), (ex + sx * 14, y - r * 1.25 - (tw if sx < 0 else 0)), (ex + 42, y - r * 0.6)],
               fill=ORANGE, outline=INK, w=5)
        c.poly([(ex - 22, y - r * 0.62), (ex + sx * 10, y - r * 1.05 - (tw if sx < 0 else 0)), (ex + 22, y - r * 0.64)],
               fill=PINK)
    c.circle(x, y, r, fill=ORANGE, outline=INK, w=6)
    for k in (-1, 0, 1):   # forehead stripes
        c.line([(x + k * 26, y - r * 0.92), (x + k * 20, y - r * 0.6)], ORANGE_D, 9)
    # eyes: blink every ~2.7 s, look left at the grid
    blink = (t % 2.7) < 0.12
    for sx in (-1, 1):
        exx, eyy = x + sx * 40 - 6, y - 12
        if mood == "happy":
            c.arc(exx, eyy + 8, 18, 200, 340, INK, 6)
        elif blink:
            c.line([(exx - 18, eyy), (exx + 18, eyy)], INK, 6)
        else:
            c.ellipse(exx, eyy, 20, 24, fill=(250, 240, 120), outline=INK, w=4)
            c.ellipse(exx - 6, eyy, 7, 17, fill=INK)
            c.circle(exx - 1, eyy - 9, 4, fill=WHITE)
        if mood == "sly":
            c.line([(exx - 22, eyy - 26 + sx * 4), (exx + 22, eyy - 26 - sx * 4)], INK, 5)
    # muzzle, nose, mouth
    c.poly([(x - 14, y + 18), (x + 2, y + 18), (x - 6, y + 30)], fill=PINK, outline=INK, w=3)
    if talk > 0:
        c.ellipse(x - 6, y + 50, 16, 8 + 14 * talk, fill=(120, 30, 40), outline=INK, w=4)
    else:
        c.arc(x - 18, y + 34, 12, 20, 160, INK, 4)
        c.arc(x + 6, y + 34, 12, 20, 160, INK, 4)
    for sx in (-1, 1):
        for k in (-1, 0, 1):
            c.line([(x + sx * 36 - 6, y + 32 + k * 9), (x + sx * 110 - 6, y + 26 + k * 18)], INK, 3, cap=False)
    # paws hanging over the top of the grid
    for px in (x - 70, x + 20):
        c.ellipse(px, y + r + 18, 34, 22, fill=ORANGE, outline=INK, w=5)
        for k in (-1, 0, 1):
            c.line([(px + k * 11, y + r + 30), (px + k * 11, y + r + 38)], INK, 3)


def paw_swipe(c, p):
    """Big paw that sweeps over the grid (p: 0 -> 1 -> 0)."""
    if p <= 0:
        return
    x = lerp(1250, 470, ease_out(p))
    y = 1010
    c.line([(x + 40, y + 10), (1250, y - 30)], ORANGE, 120)
    c.line([(x + 40, y + 10), (1250, y - 30)], ORANGE_D, 6, cap=False)
    c.ellipse(x, y, 110, 90, fill=ORANGE, outline=INK, w=7)
    c.ellipse(x - 10, y + 18, 46, 36, fill=PINK)
    for k, (dx, dy) in enumerate(((-70, -40), (-30, -70), (20, -72), (62, -44))):
        c.circle(x + dx, y + dy, 20, fill=PINK)


# ------------------------------------------------------------------ grid icons
def fish(c, x, y, s, face=1, a=255):
    col = (110, 190, 250, a)
    c.ellipse(x + face * 0.04 * s, y, 0.3 * s, 0.17 * s, fill=col)
    tx = x - face * 0.24 * s
    c.poly([(tx + face * 0.04 * s, y), (tx - face * 0.16 * s, y - 0.14 * s), (tx - face * 0.16 * s, y + 0.14 * s)], fill=col)
    c.circle(x + face * 0.18 * s, y - 0.04 * s, 0.035 * s, fill=(20, 20, 30, a))


def catface(c, x, y, s, sleep=False, whiskers=3, a=255):
    col, ink = (*ORANGE, a), (*INK, a)
    r = 0.3 * s
    for sx in (-1, 1):
        ex = x + sx * r * 0.6
        c.poly([(ex - r * 0.4, y - r * 0.55), (ex + sx * r * 0.12, y - r * 1.25), (ex + r * 0.4, y - r * 0.6)], fill=col)
    c.circle(x, y, r, fill=col)
    for sx in (-1, 1):
        ex, ey = x + sx * r * 0.42, y - r * 0.12
        if sleep:
            c.arc(ex, ey - r * 0.1, r * 0.18, 30, 150, ink, max(2, s * 0.035))
        else:
            c.circle(ex, ey, r * 0.13, fill=ink)
    c.circle(x, y + r * 0.2, r * 0.09, fill=(*PINK, a))
    for sx, n in ((-1, whiskers), (1, 3)):
        for k in range(n):
            dy = (k - 1) * r * 0.18
            c.line([(x + sx * r * 0.3, y + r * 0.3 + dy * 0.4), (x + sx * r * 1.05, y + r * 0.22 + dy)], ink,
                   max(1.6, s * 0.018), cap=False)


def wool(c, x, y, s, col, a=255):
    r = 0.32 * s
    c.circle(x, y, r, fill=(*col, a))
    dark = tuple(int(v * 0.7) for v in col)
    for k in range(3):
        c.arc(x - r * 0.2 + k * r * 0.2, y, r * (0.9 - k * 0.15), 200 + k * 20, 320 + k * 15, (*dark, a), max(2, s * 0.03))
    c.line([(x + r * 0.8, y + r * 0.5), (x + r * 1.3, y + r * 0.9)], (*col, a), max(2, s * 0.03))


def icon_level(lv, q, cols, rows, normal, odd, t_find, seed, lines, react, paw=None):
    return dict(kind="icon", lv=lv, q=q, cols=cols, rows=rows, normal=normal, odd=odd, t_find=t_find, seed=seed,
                lines=lines, react=react, paw=paw)


def text_level(lv, q, cols, rows, txt, odd, size, t_find, seed, lines, react, weight="Bold", paw=None):
    return dict(kind="text", lv=lv, q=q, cols=cols, rows=rows, txt=txt, oddtxt=odd, size=size, weight=weight,
                t_find=t_find, seed=seed, lines=lines, react=react, paw=paw)


WOOL = (220, 60, 110)
WOOL_ODD = (228, 74, 98)

LEVELS = [
    icon_level(1, "Finde den falschen Fisch!", 6, 9, lambda c, x, y, s, a: fish(c, x, y, s, 1, a),
               lambda c, x, y, s, a: fish(c, x, y, s, -1, a), 6.0, 21,
               [(1.0, "Psst... ich lenk dich ab!")], "Zu einfach!"),
    icon_level(2, "Welche Katze schläft?", 6, 8, lambda c, x, y, s, a: catface(c, x, y, s, a=a),
               lambda c, x, y, s, a: catface(c, x, y, s, sleep=True, a=a), 7.0, 22,
               [(1.2, "Ich schlafe NIE!"), (4.3, "...fast nie.")], "Verpetzt!"),
    text_level(3, "Finde das MAIU!", 5, 13, "MIAU", "MAIU", 44, 8.0, 23,
               [(1.2, "MIAU MIAU MIAU"), (4.6, "Schon Kopfweh?")], "MAIU ist kein Wort!"),
    icon_level(4, "Finde das andere Wollknäuel!", 6, 8, lambda c, x, y, s, a: wool(c, x, y, s, WOOL, a),
               lambda c, x, y, s, a: wool(c, x, y, s, WOOL_ODD, a), 7.0, 24,
               [(0.9, "Schau mal, ein Vogel!"), (4.6, "Hoppla. Ich war das nicht.")], "Mein Knäuel!", paw=(2.4, 3.9)),
    text_level(5, "Finde das ß!", 9, 12, "B", "ß", 60, 8.0, 25,
               [(1.2, "Ich hab's längst gefunden."), (4.8, "Du nicht? Hihi.")], "Glück gehabt."),
    icon_level(6, "Welcher Katze fehlt\nein Barthaar?", 6, 8, lambda c, x, y, s, a: catface(c, x, y, s, a=a),
               lambda c, x, y, s, a: catface(c, x, y, s, whiskers=2, a=a), 9.0, 26,
               [(1.2, "Das schafft eh keiner."), (5.0, "Nicht auf MICH gucken!")], "Respekt, wenn du's hattest!"),
]


def odd_cell(L):
    rnd = random.Random(L["seed"])
    while True:
        i, j = rnd.randrange(L["cols"]), rnd.randrange(L["rows"])
        near_cat = i >= L["cols"] - 2 and j <= 1
        if not near_cat and 0 < i < L["cols"] - 1 or (not near_cat and L["cols"] <= 5):
            return i, j


def cell_xy(L, i, j):
    x0, y0, x1, y1 = GRID
    cw, ch = (x1 - x0) / L["cols"], (y1 - y0) / L["rows"]
    return x0 + cw * (i + 0.5), y0 + ch * (j + 0.5), cw, ch


def draw_grid(c, t, L):
    T = L["t_find"]
    solved = ease(prog(t, T, T + 0.35))
    oi, oj = odd_cell(L)
    for i in range(L["cols"]):
        for j in range(L["rows"]):
            x, y, cw, ch = cell_xy(L, i, j)
            odd = (i, j) == (oi, oj)
            a = 255 if odd else int(255 * (1 - 0.75 * solved))
            if L["kind"] == "text":
                col = GOLD if odd and solved > 0 else WHITE
                c.text(x, y, L["oddtxt"] if odd else L["txt"], L["size"], (*col, a), weight=L["weight"])
            else:
                (L["odd"] if odd else L["normal"])(c, x, y, min(cw, ch * 1.25), a)
    if solved > 0:
        x, y, cw, ch = cell_xy(L, oi, oj)
        r = max(cw, ch) * 0.6 * (2.2 - 1.2 * back_out(prog(t, T, T + 0.4)))
        c.circle(x, y, r, outline=(*RED, int(255 * solved)), w=9)


def draw_level(c, t, L):
    c.fill(BG)
    T = L["t_find"]
    (L.get("draw") or draw_grid)(c, t, L)
    if L["paw"]:
        a, b = L["paw"]
        p = ease(prog(t, a, a + 0.45)) * (1 - ease(prog(t, b - 0.45, b)))
        paw_swipe(c, p)
    # UI
    a_in = ease_out(prog(t, 0, 0.3))
    label = "NUR 1 % SCHAFFEN LEVEL 6" if L["lv"] == 1 else f"LEVEL {L['lv']} / 6"
    c.text(CX - 40, 238, label, 32, (*GOLD, int(255 * a_in)))
    if t < T:
        lines = L["q"].split("\n")
        text_block(c, [(l, WHITE) for l in lines], 318, 56 if len(lines) > 1 else 58, a_in)
        k = 1 - prog(t, 0.3, T)
        late = T - t < 3
        y = 318 + 66 * len(lines) + 10
        c.rect(CX - 340, y, CX + 240, y + 12, fill=(255, 255, 255, 40), r=6)
        c.rect(CX - 340, y, CX - 340 + 580 * k, y + 12, fill=(*(RED if late else GOLD), 235), r=6)
    else:
        a = ease_out(prog(t, T, T + 0.3))
        text_block(c, [(L.get("solved", "Hast du es gefunden?"), WHITE)], 322, 58, a)
        c.text(CX - 40, 400, L.get("sub", "Schreib deine Zeit in die Kommentare"), 32, (*GOLD, int(255 * a)))
    # the cat + what it says
    say, age = None, 0.0
    for ts, txt in L["lines"]:
        if ts <= t < ts + 2.3 and t < T:
            say, age = txt, t - ts
    if T + 0.4 <= t:
        say, age = L["react"], t - T - 0.4
    talk = max(0.0, math.sin(age * 14)) * (1 - prog(age, 0.5, 0.7)) if say else 0.0
    cat(c, t, talk, "happy" if t >= T else "sly", slide=prog(t, 0, 0.45) if L["lv"] == 1 else 1.0)
    if say:
        fade_in = ease_out(prog(age, 0, 0.2))
        fade_out = 1 - prog(age, 2.0, 2.3) if t < T else 1.0
        speech_right(c, say, fade_in * fade_out, y=520 if t < T else 500)


def level_sounds(L):
    T = L["t_find"]
    s = [(0.0, sfx.whoosh(0.35), 0.5), (0.0, drone(T + REVEAL), 0.25)]
    s += [(k, sfx.click(), 0.35) for k in range(1, int(T))]
    s += [(T - n, sfx.beep(880, 0.12), 0.45) for n in (3, 2, 1)]
    s += [(T, ding(), 0.8), (T, sfx.bass_hit(), 0.4)]
    for k, (ts, _) in enumerate(L["lines"]):
        s.append((ts, meow(0.45 + 0.1 * (k % 2), 1.0 + 0.12 * ((L["lv"] + k) % 3)), 0.55))
    s.append((T + 0.4, purr(1.6), 0.6))
    s += L.get("extra_snd", [])
    if L["paw"]:
        s += [(L["paw"][0], sfx.whoosh(0.45), 0.7), (L["paw"][0], meow(0.7, 0.85), 0.6),
              (L["paw"][1] - 0.45, sfx.whoosh(0.4, False), 0.5)]
    return s


def draw_outro(c, t):
    c.fill(BG)
    a = ease_out(prog(t, 0, 0.3))
    text_block(c, [("Bei welchem Level hat", WHITE), ("dich die Katze erwischt?", WHITE)], 860, 62, a)
    b = ease_out(prog(t, 0.5, 0.8))
    text_block(c, [("1  2  3  4  5  6", GOLD)], 1060, 76, b)
    c.text(CX, 1170, "Schick das einem Katzen-Fan!", 40, (*WHITE, int(220 * b)))
    cat(c, t + 3, talk=0.0, mood="happy")
    speech_right(c, "Bis morgen!", ease_out(prog(t, 0.3, 0.5)), y=520)
    f = ease_out(prog(t, 1.6, 2.0))
    if f > 0:
        follow_cta(c, f, "FOLGEN für Teil 3")


def make():
    scenes = []
    for L in LEVELS:
        scenes.append(Scene(L["t_find"] + REVEAL, lambda c, t, L=L: draw_level(c, t, L), None, level_sounds(L),
                            header=False, zoom=1.0, ty=1330.0))
    scenes.append(Scene(4.5, draw_outro, None, [(0.0, sfx.whoosh(0.4), 0.5), (0.3, meow(0.6, 1.1), 0.6)],
                        header=False, zoom=1.0, ty=1330.0))
    return Film("Finde den Fehler 2", "Katze", scenes)


FILM = make()

if __name__ == "__main__":
    print(f"duration {FILM.dur:.1f}s")
    if "--sheet" in sys.argv:
        ts = [st + k for st, sc in zip(FILM.starts, FILM.scenes) for k in (1.6, 3.2, sc.dur - 1.0)]
        print(stills(FILM, ts, "output/preview_katze", cols=7, scale=0.24))
    else:
        render(FILM, "output/finde_den_fehler_teil2_katze.mp4")
