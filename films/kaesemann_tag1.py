"""Käsemann wird reich - Tag 1 (Pfandflaschen -> 1,25 €).

The talking character is cut out of the uploaded clip (rembg) and placed into drawn, animated scenes
with a running balance counter, word-by-word subtitles, overlays and SFX. The original voice is kept.

Storyboard (stills):  python3 -m films.kaesemann_tag1 storyboard SRC.mp4 WORDS.json OUT.png
Full video:           python3 -m films.kaesemann_tag1 render SRC.mp4 WORDS.json OUT.mp4
"""
import json
import math
import os
import random
import subprocess
import sys
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from engine import sfx
from engine.gfx import H, SS, W, Canvas, back_out, ease, ease_in, ease_out, lerp, prog
from films.illusions import ding

SRC_W, SRC_H, FPS = 768, 1152, 25
VOICE_END = 59.44
DUR = 62.5
RED, YEL, GOLD, WHITE, INK = (232, 38, 52), (255, 214, 0), (255, 196, 40), (255, 255, 255), (16, 16, 20)
GREEN = (46, 200, 96)

FEET, FACE = (420.0, 1100.0), (392.0, 250.0)   # anchor points in the source frame
BASE_S = 0.96                                  # output px per source px

# key moments (s), taken from the word timestamps
MILLION, KEIN_JOB, KEIN_GELD, VERPACKUNG = 4.5, 8.04, 8.98, 10.52
MOMENT, FLASCHE1, NOCH = 12.48, 15.26, 17.4
DREI, VIER, FUENF, VERMOEGEN = 18.44, 19.12, 20.10, 22.36
AB, CUT = 23.56, 24.25
REIN = [26.70, 28.34, 29.06, 29.82]
LETZTE, REJECT, DOCH = 31.12, 31.7, 33.22
BON, EURO125, START, NURNOCH = 35.12, 36.3, 39.22, 40.34
EUCH, KOMMENTARE, FOLGT = 48.08, 50.84, 56.62

FIX = {"Bonn": "Bon"}


# ------------------------------------------------------------------ subtitles
def load_words(path):
    raw = [w for s in json.load(open(path))["segments"] for w in s["words"]]
    out = []
    for w in raw:
        txt = w["w"].strip()
        if out and txt[:1] in ",." and txt[1:2].isdigit():          # "1" ",25" -> "1,25"
            out[-1]["w"] += txt
            out[-1]["e"] = w["e"]
            continue
        if out and out[-1]["w"] == "Konto" and txt == "Stand":
            out[-1]["w"] = "Kontostand"
            out[-1]["e"] = w["e"]
            continue
        out.append({"w": FIX.get(txt.rstrip("!?.,"), txt.rstrip("!?.,")) + txt[len(txt.rstrip("!?.,")):],
                    "s": w["s"], "e": w["e"]})
    return out


def chunks(words, max_words=3, max_chars=15):
    out, cur = [], []
    for w in words:
        cur.append(w)
        txt = " ".join(x["w"] for x in cur)
        if len(cur) >= max_words or len(txt) >= max_chars or w["w"][-1:] in ".,!?":
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    res = []
    for k, ch in enumerate(out):
        nxt = out[k + 1][0]["s"] if k + 1 < len(out) else VOICE_END
        res.append((ch[0]["s"], min(nxt, ch[-1]["e"] + 0.5), ch))
    return res


def draw_subs(c, t, subs, y=1210):
    for s, e, ch in subs:
        if not (s <= t < e):
            continue
        size = 68
        texts = [w["w"].upper() for w in ch]
        widths = [c.text_w(x, size * 1.1) for x in texts]
        gap = 24
        total = sum(widths) + gap * (len(texts) - 1)
        if total > 840:
            k = 840 / total
            size, widths, gap, total = size * k, [x * k for x in widths], gap * k, 840
        x = 490 - total / 2
        pop = back_out(prog(t, s, s + 0.12))
        for w, tw, txt in zip(ch, widths, texts):
            active = w["s"] <= t < max(w["e"], w["s"] + 0.15)
            sz = int(size * (1.1 if active else 1.0) * (0.85 + 0.15 * pop))
            c.text(x + tw / 2, y, txt, sz, YEL if active else WHITE, stroke=9, stroke_fill=INK, shake=False)
            x += tw + gap


# ------------------------------------------------------------------ backgrounds (cached, supersampled)
_bg = {}


def bg_street():
    if "street" in _bg:
        return _bg["street"]
    c = Canvas()
    c.vgrad(0, 1300, (150, 205, 250), (225, 240, 255))
    c.circle(860, 520, 70, fill=(255, 236, 150))
    rnd = random.Random(4)
    x = -40
    while x < W:
        w, h = rnd.uniform(160, 260), rnd.uniform(380, 700)
        col = rnd.choice([(244, 196, 160), (200, 214, 236), (236, 220, 170), (214, 190, 220)])
        c.rect(x, 1300 - h, x + w - 14, 1300, fill=col)
        for j in range(int(h / 90)):
            for i in range(int(w / 70)):
                c.rect(x + 22 + i * 64, 1300 - h + 40 + j * 90, x + 56 + i * 64, 1300 - h + 90 + j * 90,
                       fill=(255, 255, 255, 150))
        x += w
    c.rect(0, 1300, W, 1350, fill=(170, 170, 178))
    c.rect(0, 1350, W, H, fill=(196, 196, 204))
    for i in range(0, W, 180):
        c.line([(i, 1350), (i + 60, H)], (176, 176, 186), 4, cap=False)
    c.line([(120, 1350), (120, 760)], (70, 74, 84), 14)                    # street lamp
    c.ellipse(150, 760, 50, 16, fill=(70, 74, 84))
    _bg["street"] = c.img.copy()
    return _bg["street"]


def bg_market():
    if "market" in _bg:
        return _bg["market"]
    c = Canvas()
    c.vgrad(0, 1320, (246, 240, 226), (232, 224, 206))
    for x in range(60, W, 240):
        c.rect(x, 140, x + 140, 160, fill=(255, 255, 240))
        c.glow(x + 70, 160, 90, (255, 250, 220), 0.4, rings=4)
    rnd = random.Random(9)
    for shelf_y in (560, 760, 960, 1160):
        c.rect(380, shelf_y, 1080, shelf_y + 18, fill=(150, 150, 160))
        x = 390
        while x < 1070:
            w = rnd.uniform(40, 80)
            h = rnd.uniform(90, 170)
            col = rnd.choice([(230, 80, 70), (70, 140, 230), (250, 200, 60), (90, 190, 110), (240, 150, 60),
                              (200, 110, 200)])
            c.rect(x, shelf_y - h, x + w - 6, shelf_y, fill=col, r=6)
            x += w
    c.rect(400, 380, 1080, 450, fill=(214, 40, 52))
    c.text(740, 417, "SUPERMARKT", 50, WHITE)
    c.rect(0, 1320, W, H, fill=(214, 214, 220))
    for i in range(0, W, 120):
        c.line([(i, 1320), (i, H)], (196, 196, 204), 3, cap=False)
    _bg["market"] = c.img.copy()
    return _bg["market"]


def bg_blur(name):
    key = name + "_blur"
    if key not in _bg:
        _bg[key] = (bg_market() if name == "market" else bg_street()).filter(ImageFilter.GaussianBlur(22))
    return _bg[key]


# ------------------------------------------------------------------ props
def bottle(c, x, y, s=1.0, ang=0.0, a=255):
    """Plastic deposit bottle standing at (x, y) = bottom centre."""
    r = math.radians(ang)

    def P(u, v):
        return (x + (u * math.cos(r) - v * math.sin(r)) * s, y + (u * math.sin(r) + v * math.cos(r)) * s)

    body = [P(-26, 0), P(26, 0), P(28, -110), P(14, -140), P(10, -160), P(-10, -160), P(-14, -140), P(-28, -110)]
    c.poly(body, fill=(170, 230, 210, int(220 * a / 255)))
    c.poly([P(-27, -40), P(27, -40), P(28, -85), P(-28, -85)], fill=(40, 120, 220, a))
    c.poly([P(-11, -160), P(11, -160), P(11, -176), P(-11, -176)], fill=(30, 90, 200, a))
    c.line([P(-14, -20), P(-14, -100)], (255, 255, 255, int(140 * a / 255)), 5 * s)


def automat(c, light=None):
    c.rect(60, 760, 340, 1440, fill=(236, 238, 242), outline=(150, 154, 164), w=6, r=20)
    c.rect(60, 760, 340, 840, fill=(40, 150, 90), r=20)
    c.text(200, 801, "PFAND", 44, WHITE)
    c.circle(200, 980, 62, fill=(40, 42, 50))
    c.circle(200, 980, 42, fill=(20, 20, 24))
    col = {"green": GREEN, "red": RED}.get(light, (120, 124, 134))
    if light:
        c.glow(200, 880, 70, col, 1.2)
    c.circle(200, 880, 18, fill=col)
    c.rect(110, 1130, 290, 1150, fill=(40, 42, 50), r=6)                    # receipt slot


def coin(c, x, y, r=26, a=255):
    c.circle(x, y, r, fill=(*GOLD, a))
    c.circle(x, y, r * 0.72, outline=(220, 150, 20, a), w=3)
    c.text(x, y + 1, "€", int(r * 1.1), (180, 110, 10, a))


# ------------------------------------------------------------------ character placement
def char_state(t):
    """Returns dict(x, y, s, rot, sq, anchor_k, bg, visible)."""
    st = dict(x=470.0, y=1440.0, s=1.0, rot=0.0, sq=1.0, k=0.0)
    # scene 1: slide in
    if t < 0.7:
        st["x"] = lerp(-420, 470, back_out(prog(t, 0, 0.7)))
    # jumps
    for t0 in (MILLION - 0.1, FLASCHE1 - 0.1, DOCH):
        if t0 <= t < t0 + 0.65:
            p = prog(t, t0, t0 + 0.55)
            st["y"] -= 170 * math.sin(math.pi * min(1, p))
            if p >= 1:
                st["sq"] = 1 - 0.12 * math.sin(math.pi * prog(t, t0 + 0.55, t0 + 0.65))
    # scene 2: sad sway, slightly left
    if KEIN_JOB - 0.4 <= t < MOMENT:
        k = ease(prog(t, KEIN_JOB - 0.4, KEIN_JOB)) * (1 - ease(prog(t, MOMENT - 0.3, MOMENT)))
        st["x"] -= 70 * k
        st["rot"] = math.sin(t * 2.2) * 3 * k
        st["sq"] *= 1 - 0.04 * k
    # punch-in on "Moment" and whisper on "Vermögen"
    for t0, t1, amt in ((MOMENT - 0.1, MOMENT + 0.9, 1.0), (VERMOEGEN - 0.2, AB - 0.05, 1.0)):
        if t0 <= t < t1:
            st["k"] = ease_out(prog(t, t0, t0 + 0.2)) * (1 - ease(prog(t, t1 - 0.25, t1))) * amt
    # dash out / in
    if AB <= t < CUT:
        st["x"] = lerp(470, 1500, ease_in(prog(t, AB + 0.1, CUT)))
        st["rot"] = 8
    if CUT <= t < 25.0:
        st["x"] = lerp(-500, 640, ease_out(prog(t, CUT, 25.0)))
        st["rot"] = 8 * (1 - prog(t, CUT, 25.0))
    if 25.0 <= t < 46.3:
        st["x"] = 640
    # nervous shake
    if REJECT <= t < DOCH:
        st["x"] += math.sin(t * 60) * 7
        st["rot"] = math.sin(t * 47) * 2.5
    # close-up talk to camera
    if 46.3 <= t < 51.0:
        st["x"] = 640
        st["k"] = ease_out(prog(t, 46.3, 46.8)) * (1 - ease(prog(t, 50.6, 51.0)))
    # options: step aside right, smaller
    if 51.0 <= t < 56.6:
        p = ease_out(prog(t, 51.0, 51.4)) * (1 - ease(prog(t, 56.3, 56.6)))
        st["x"] = lerp(640, 760, p)
        st["s"] = lerp(1.0, 0.78, p)
    # wave
    if 56.6 <= t < VOICE_END:
        st["x"] = lerp(760, 470, ease_out(prog(t, 56.6, 57.0)))
        st["rot"] = math.sin(t * 7) * 6
    if t >= VOICE_END:
        st["x"], st["s"] = 470, 0.86
    return st


def place_character(c, cut, t):
    st = char_state(t)
    k = st["k"]
    s = BASE_S * st["s"] * lerp(1.0, 1.75, k)
    ax, ay = lerp(FEET[0], FACE[0], k), lerp(FEET[1], FACE[1], k)
    px, py = lerp(st["x"], 500, k), lerp(st["y"], 640, k)
    kx, ky = s * SS, s * SS * st["sq"]
    w, h = max(1, int(SRC_W * kx)), max(1, int(SRC_H * ky))
    im = cut.resize((w, h), Image.BICUBIC)
    fx, fy = ax * kx, ay * ky
    if st["rot"]:
        cx, cy = w / 2, h / 2
        im = im.rotate(st["rot"], resample=Image.BICUBIC, expand=True)
        r = math.radians(-st["rot"])
        dx, dy = fx - cx, fy - cy
        fx = im.width / 2 + dx * math.cos(r) - dy * math.sin(r)
        fy = im.height / 2 + dx * math.sin(r) + dy * math.cos(r)
    if k < 0.3:                                                     # ground shadow
        lift = 1440 - st["y"]
        c.ellipse(st["x"], 1452, 190 * st["s"] * (1 - lift / 600), 26 * st["s"], fill=(0, 0, 0, int(70 * (1 - k * 3))))
    c.img.paste(im, (int(px * SS - fx), int(py * SS - fy)), im)


# ------------------------------------------------------------------ overlays
def balance_at(t):
    b = 0.0
    for t0 in REIN:
        if t >= t0 + 0.35:
            b += 0.25
    if t >= DOCH + 0.1:
        b += 0.25
    return b


def bottles_found(t):
    return sum(1 for t0 in (FLASCHE1, NOCH, DREI, VIER, FUENF) if t >= t0)


def ov_counter(c, t):
    b = balance_at(t)
    bump = 0.0
    for t0 in [x + 0.35 for x in REIN] + [DOCH + 0.1, EURO125]:
        if t0 <= t < t0 + 0.4:
            bump = 1 - prog(t, t0, t0 + 0.4)
    c.rect(36, 214, 410, 300, fill=(0, 0, 0, 170), r=43)
    coin(c, 84, 257, 28)
    zero = b == 0 and 1.9 < t < 3.2 and int(t * 6) % 2 == 0
    col = RED if zero else (GOLD if b >= 1.25 else WHITE)
    c.text(258, 259, f"{b:.2f} €".replace(".", ","), int(54 * (1 + 0.25 * bump)), col, shake=False)
    c.rect(36, 308, 410, 344, fill=(0, 0, 0, 150), r=18)
    c.text(156, 326, "Ziel: 1.000.000 €", 24, WHITE, shake=False)
    c.rect(282, 318, 398, 334, fill=(80, 80, 90), r=8)
    c.rect(282, 318, 286, 334, fill=GREEN if b > 0 else (80, 80, 90), r=2)
    if 15.0 <= t < CUT:
        n = bottles_found(t)
        pop = 1 + 0.2 * (1 - prog(t, FUENF, FUENF + 0.4)) if FUENF <= t < FUENF + 0.4 else 1
        c.rect(36, 354, 330, 410, fill=GREEN if n == 5 else (40, 150, 90, 220), r=28)
        bottle(c, 80, 400, 0.28)
        c.text(200, 383, f"Flaschen {n}/5" + (" ✓" if n == 5 else ""), int(32 * pop), WHITE, shake=False)


def ov_day(c, t):
    if t < KEIN_JOB - 0.5:
        c.rect(600, 214, 800, 290, fill=RED, r=38)
        c.text(700, 253, "TAG 1", 46, WHITE, shake=False)


def ov_scene1(c, t):
    if MILLION - 0.1 <= t < 6.3:
        p = back_out(prog(t, MILLION - 0.1, MILLION + 0.2))
        a = 1 - prog(t, 5.9, 6.3)
        c.text(490, 760, "1.000.000 €", int(130 * p) + 1, (*GOLD, int(255 * a)), stroke=10, stroke_fill=INK)
        rnd = random.Random(3)
        for i in range(26):
            x = rnd.uniform(60, 900)
            y = -60 + (t - MILLION) * rnd.uniform(500, 900) + rnd.uniform(-300, 0)
            if 190 < y < 1450:
                coin(c, x, y, 24, int(255 * a))


def ov_scene2(c, t):
    if KEIN_JOB - 0.5 <= t < MOMENT + 0.2:
        a = ease_out(prog(t, KEIN_JOB - 0.5, KEIN_JOB)) * (1 - prog(t, MOMENT, MOMENT + 0.2))
        x, y = 400, 330                                                     # rain cloud over the head
        for dx, dy, r in ((-70, 10, 55), (0, -20, 70), (70, 10, 55), (0, 25, 60)):
            c.circle(x + dx, y + dy, r, fill=(120, 130, 150, int(240 * a)))
        rnd = random.Random(int(t * 12))
        for i in range(10):
            rx = x + rnd.uniform(-110, 110)
            ry = y + 60 + ((t * 600 + i * 47) % 160)
            c.line([(rx, ry), (rx - 6, ry + 26)], (120, 170, 240, int(220 * a)), 4)
        for k, (t0, txt) in enumerate(((KEIN_JOB, "JOB"), (KEIN_GELD, "GELD"), (VERPACKUNG, "VERPACKUNG"))):
            p = back_out(prog(t, t0, t0 + 0.2))
            if p <= 0:
                continue
            yy = 640 + k * 120
            c.rect(600, yy - 46, 920, yy + 46, fill=(255, 255, 255, int(240 * a)), r=22)
            c.text(785, yy + 2, txt, int(34 * p) + 1, (*INK, int(255 * a)))
            c.circle(642, yy, 26 * p, fill=(*RED, int(255 * a)))
            c.text(642, yy + 2, "X", int(30 * p) + 1, (255, 255, 255, int(255 * a)))


GROUND_BOTTLES = [(FLASCHE1, 790, 1400), (NOCH, 170, 1400), (DREI, 870, 1420), (VIER, 250, 1425), (FUENF, 720, 1430)]


def ov_bottles(c, t):
    if not (MOMENT + 0.5 <= t < CUT):
        return
    first = MOMENT + 0.8
    for k, (t0, x, y) in enumerate(GROUND_BOTTLES):
        appear = first if k == 0 else t0 - 0.05
        if t < appear:
            continue
        p = back_out(prog(t, appear, appear + 0.25))
        if k == 0 and t < FLASCHE1:                                         # spotlight + sparkle
            c.poly([(x - 30, 190), (x + 30, 190), (x + 120, y), (x - 120, y)], fill=(255, 250, 200, 60))
            for j in range(4):
                a = t * 3 + j * 1.57
                c.circle(x + math.cos(a) * 60, y - 90 + math.sin(a) * 60, 6, fill=(255, 255, 255, 220))
        bottle(c, x, y, 0.95 * p, ang=(-12 if k % 2 else 10))


def ov_treasure(c, t):
    if VERMOEGEN - 0.2 <= t < AB:
        a = ease_out(prog(t, VERMOEGEN - 0.2, VERMOEGEN + 0.2)) * (1 - prog(t, AB - 0.25, AB))
        c.glow(500, 700, 520, (255, 210, 80), 0.8 * a)
        rnd = random.Random(int(t * 10))
        for i in range(12):
            c.circle(rnd.uniform(80, 900), rnd.uniform(300, 1300), rnd.uniform(4, 9), fill=(255, 240, 160, int(230 * a)))


def ov_dash(c, t):
    if AB + 0.05 <= t < 25.0:
        rnd = random.Random(int(t * 20))
        for i in range(9):
            y = rnd.uniform(500, 1400)
            x = rnd.uniform(0, 900)
            c.line([(x, y), (x - 220, y)], (255, 255, 255, 170), 6)


def ov_automat(c, t):
    if not (CUT <= t < 46.3):
        return
    light = None
    for t0 in REIN + [DOCH]:
        if t0 + 0.3 <= t < t0 + 0.9:
            light = "green"
    if REJECT <= t < DOCH:
        light = "red" if int(t * 5) % 2 == 0 else None
    if DOCH <= t < DOCH + 1.4:
        light = "green"
    automat(c, light)
    # bottles flying into the slot
    for t0 in REIN + [LETZTE, DOCH - 0.35]:
        if t0 - 0.05 <= t < t0 + 0.35:
            p = ease_in(prog(t, t0 - 0.05, t0 + 0.35))
            bottle(c, lerp(560, 200, p), lerp(1000, 1060, p), lerp(0.8, 0.3, p), ang=lerp(0, -80, p))
    if REJECT <= t < REJECT + 0.6:                                            # spat back out
        p = ease_out(prog(t, REJECT, REJECT + 0.6))
        bottle(c, lerp(200, 420, p), lerp(1000, 1440, p) - math.sin(math.pi * p) * 160, 0.8, ang=lerp(-80, 200, p))
    if REJECT + 0.6 <= t < DOCH - 0.35:
        bottle(c, 420, 1440, 0.8, ang=90)
    if REJECT <= t < DOCH:
        c.rect(70, 650, 330, 730, fill=RED, r=20)
        c.text(200, 691, "FEHLER", 44, WHITE)
    if DOCH <= t < BON:                                                        # confetti
        rnd = random.Random(7)
        for i in range(60):
            x = rnd.uniform(40, 920)
            y = 200 + (t - DOCH) * rnd.uniform(300, 700) + rnd.uniform(-200, 100)
            col = rnd.choice([RED, YEL, GREEN, (70, 140, 240), (240, 120, 200)])
            if 200 < y < 1450:
                c.rect(x, y, x + 14, y + 22, fill=col)
    if BON <= t < EURO125 + 0.2:                                               # receipt printing
        h = 260 * ease(prog(t, BON, BON + 1.0))
        c.rect(118, 1140, 282, 1140 + h, fill=(252, 252, 248), outline=(200, 200, 200), w=2)
        if h > 120:
            c.text(200, 1190, "PFAND", 28, INK)
            c.text(200, 1240, "1,25 €", 34, INK)


def ov_receipt(c, t):
    if EURO125 <= t < START + 0.8:
        p = back_out(prog(t, EURO125, EURO125 + 0.35))
        a = 1 - prog(t, START + 0.4, START + 0.8)
        x0, y0 = 490 - 230 * p, 560
        c.glow(490, 760, 300, (255, 220, 120), 0.7 * a)
        c.rect(x0, y0, 490 + 230 * p, y0 + 420 * p, fill=(252, 252, 246, int(250 * a)), r=12)
        if p > 0.6:
            al = int(255 * a)
            c.text(490, y0 + 60, "PFANDBON", 44, (*INK, al))
            c.line([(330, y0 + 110), (650, y0 + 110)], (*INK, al), 3, cap=False)
            c.text(490, y0 + 170, "5 x 0,25 €", 40, (*INK, al))
            c.line([(330, y0 + 225), (650, y0 + 225)], (*INK, al), 3, cap=False)
            c.text(490, y0 + 300, "1,25 €", 92, (*GREEN, al))


def ov_goal(c, t):
    if NURNOCH - 0.3 <= t < 46.3:
        a = ease_out(prog(t, NURNOCH - 0.3, NURNOCH)) * (1 - prog(t, 46.0, 46.3))
        al = int(255 * a)
        c.rect(70, 560, 910, 980, fill=(16, 16, 22, int(235 * a)), r=36)
        c.text(490, 625, "ZIEL: 1.000.000 €", 50, (*WHITE, al))
        c.rect(120, 690, 860, 740, fill=(70, 70, 82, al), r=25)
        c.rect(120, 690, 126, 740, fill=(*GREEN, al), r=3)
        if t > NURNOCH + 0.8:                                                  # magnifier on the tiny progress
            p = back_out(prog(t, NURNOCH + 0.8, NURNOCH + 1.1))
            c.circle(200, 715, 70 * p, outline=(*YEL, al), w=8)
            c.line([(250, 765), (290, 805)], (*YEL, al), 12)
            c.text(420, 790, "0,000125 %", int(44 * p) + 1, (*YEL, al))
        rem = 999998.75
        shown = rem * ease_out(prog(t, NURNOCH, 44.5))
        s = f"{shown:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        c.text(490, 900, f"Noch {s} €", 52, (*RED, al))


def ov_question(c, t):
    if EUCH - 0.4 <= t < 51.0:
        a = ease_out(prog(t, EUCH - 0.4, EUCH)) * (1 - prog(t, 50.7, 51.0))
        c.rect(150, 1300, 830, 1400, fill=(*YEL, int(255 * a)), r=40)
        c.text(490, 1351, "Was soll ich machen?", 50, (*INK, int(255 * a)))


OPTIONS = [("A", "Brötchen weiterverkaufen"), ("B", "Weiter Pfand sammeln"), ("C", "Limo-Stand bauen")]


def ov_options(c, t):
    if not (KOMMENTARE <= t < FOLGT):
        return
    a = 1 - prog(t, FOLGT - 0.3, FOLGT)
    for k, (letter, txt) in enumerate(OPTIONS):
        p = back_out(prog(t, KOMMENTARE + 0.3 + k * 0.25, KOMMENTARE + 0.55 + k * 0.25))
        if p <= 0:
            continue
        y = 640 + k * 150
        c.rect(50, y - 60, 50 + 560 * p, y + 60, fill=(255, 255, 255, int(245 * a)), r=30)
        c.circle(100, y, 40 * p, fill=(*RED, int(255 * a)))
        c.text(100, y + 2, letter, int(48 * p) + 1, (255, 255, 255, int(255 * a)))
        if p > 0.5:
            c.text(158, y + 2, txt, 34, (*INK, int(255 * a)), anchor="lm")
    if t > KOMMENTARE + 1.2:
        b = ease_out(prog(t, KOMMENTARE + 1.2, KOMMENTARE + 1.5)) * a
        c.text(330, 1100, "...oder eigene Idee!", 40, (*YEL, int(255 * b)), stroke=6, stroke_fill=INK)
        arrow(c, (760, 1090), (930, 1290), b, t)


def arrow(c, p0, p1, a, t):
    k = 0.04 * math.sin(t * 9)
    x1, y1 = lerp(p0[0], p1[0], 1 + k), lerp(p0[1], p1[1], 1 + k)
    c.line([p0, (x1, y1)], (*YEL, int(255 * a)), 16)
    ang = math.atan2(y1 - p0[1], x1 - p0[0])
    for s_ in (-1, 1):
        c.line([(x1, y1), (x1 - math.cos(ang + s_ * 0.5) * 55, y1 - math.sin(ang + s_ * 0.5) * 55)],
               (*YEL, int(255 * a)), 16)


def ov_follow(c, t):
    if FOLGT <= t < VOICE_END:
        p = back_out(prog(t, FOLGT, FOLGT + 0.3))
        c.rect(490 - 270 * p, 540, 490 + 270 * p, 630, fill=RED, r=45)
        c.text(490, 586, "FOLGEN für Tag 2", int(48 * p) + 1, WHITE)
        arrow(c, (780, 700), (935, 1000), ease_out(prog(t, FOLGT + 0.3, FOLGT + 0.6)), t)


def ov_end(c, t):
    if t >= VOICE_END:
        a = ease_out(prog(t, VOICE_END, VOICE_END + 0.4))
        c.overlay((0, 0, 0), 0.35 * a)
        p = back_out(prog(t, VOICE_END + 0.1, VOICE_END + 0.4))
        c.text(490, 1120, "TAG 2:", int(80 * p) + 1, (*YEL, int(255 * a)), stroke=9, stroke_fill=INK)
        c.text(490, 1225, "IHR entscheidet!", int(84 * p) + 1, (255, 255, 255, int(255 * a)), stroke=9,
               stroke_fill=INK)
        c.text(490, 1330, "A, B oder C?", int(64 * p) + 1, (*YEL, int(255 * a)), stroke=8, stroke_fill=INK)


# ------------------------------------------------------------------ frame
def scene_bg(t):
    if t < CUT:
        return bg_street()
    if 46.6 <= t < 50.8:
        return bg_blur("market")
    if t >= VOICE_END:
        return bg_blur("street")
    return bg_market()


BEHIND = [ov_bottles, ov_automat]          # drawn before the character
FRONT = [ov_scene1, ov_scene2, ov_treasure, ov_dash, ov_receipt, ov_goal, ov_question, ov_options, ov_follow, ov_end,
         ov_counter, ov_day]


def compose(t, cut, subs):
    c = Canvas.__new__(Canvas)
    c.img = scene_bg(t).copy()
    c.d = ImageDraw.Draw(c.img, "RGBA")
    c.ox = c.oy = 0.0
    c.halo = None
    c.zoom, c.zx, c.zy, c.ty = 1.0, 500.0, 1330.0, 1330.0
    if 12.4 <= t < 12.75 or REJECT <= t < REJECT + 0.25:
        c.ox = math.sin(t * 90) * 12
    for ov in BEHIND:
        ov(c, t)
    place_character(c, cut, t)
    for ov in FRONT:
        ov(c, t)
    for t0 in (MOMENT - 0.05, DOCH):                                            # white flash
        if t0 <= t < t0 + 0.2:
            c.overlay(WHITE, 0.5 * (1 - prog(t, t0, t0 + 0.2)))
    c.no_shake()
    draw_subs(c, t, subs)
    return c.final()


# ------------------------------------------------------------------ cutout
_session = None


def cutout(rgb):
    global _session
    from rembg import new_session, remove
    if _session is None:
        _session = new_session("isnet-general-use")
    return remove(rgb, session=_session)


def src_frame(src, t):
    t = min(t, VOICE_END - 0.05)
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", src, "-frames:v", "1", "-f",
                          "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return Image.frombytes("RGB", (SRC_W, SRC_H), raw)


# ------------------------------------------------------------------ storyboard
BOARD = [
    (0.9, "1 · 0–6 s", "Rutscht ins Bild · TAG 1 · Konto 0,00 €"),
    (4.9, "1 · Million", "Sprung · 1.000.000 € + Münzregen"),
    (10.9, "2 · 6–12 s", "Regenwolke · JOB/GELD/VERPACKUNG ✗"),
    (12.7, "3 · Moment!", "Kratzer + Zoom · Flasche im Spotlight"),
    (15.5, "3 · Pfandflasche!", "Freudensprung · Flaschen 1/5"),
    (21.0, "4 · 3, 4, 5", "Flaschen ploppen auf · Zähler 5/5 ✓ wird grün"),
    (22.9, "4 · Vermögen", "Flüster-Zoom · Goldglanz"),
    (24.6, "5 · Supermarkt", "Rennt rein · Speed-Lines"),
    (28.6, "6 · Rein, rein…", "Flasche → Automat · Konto zählt hoch"),
    (32.3, "6 · Die will er nicht", "Rotes Licht · FEHLER · Zittern"),
    (33.6, "7 · Doch!", "Grün · Sprung · Konfetti"),
    (37.2, "8 · 1,25 €", "Pfandbon groß · Konto gold"),
    (43.3, "9 · Noch 999.998,75 €", "Ziel-Balken mit Lupe: 0,000125 %"),
    (49.0, "10 · Was mache ich?", "Nah an die Kamera · Hintergrund unscharf"),
    (53.5, "11 · Kommentare", "A / B / C + Pfeil zum Kommentar-Knopf"),
    (57.6, "12 · Folgt mir", "Winkt · FOLGEN für Tag 2 · Pfeil zum Profil"),
    (61.0, "13 · Endbild (neu)", "TAG 2: IHR entscheidet! A, B oder C?"),
]


def storyboard(src, words, out):
    from engine.gfx import font
    subs = chunks(load_words(words))
    tw, th, cap = 360, 640, 120
    cols = 4
    rows = (len(BOARD) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * 16, rows * (th + cap) + (rows + 1) * 16), (24, 24, 30))
    d = ImageDraw.Draw(sheet)
    f1, f2 = font(9.5, "Black"), font(8, "Bold")
    for k, (t, title, desc) in enumerate(BOARD):
        cut = cutout(src_frame(src, t))
        im = compose(t, cut, subs).resize((tw, th), Image.LANCZOS)
        x = 16 + (k % cols) * (tw + 16)
        y = 16 + (k // cols) * (th + cap + 16)
        sheet.paste(im, (x, y))
        d.rectangle((x, y + th, x + tw, y + th + cap), fill=(36, 36, 44))
        d.text((x + 12, y + th + 12), f"{title}  ({t:.1f} s)", font=f1, fill=(255, 214, 0))
        for j, line in enumerate(desc.split(" · ")):
            d.text((x + 12, y + th + 44 + j * 24), "• " + line, font=f2, fill=(235, 235, 240))
        print(f"  {title}", file=sys.stderr)
    sheet.save(out)
    return out


# ------------------------------------------------------------------ full render
_subs = None


def _init(subs):
    global _subs
    _subs = subs


def _render(args):
    i, cut_path = args
    cut = Image.open(cut_path).convert("RGBA")
    return compose(i / FPS, cut, _subs).tobytes()


def build_audio(src, out):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", src, "-ac", "1", "-ar", str(sfx.SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    voice = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    mix = np.zeros(int(DUR * sfx.SR) + sfx.SR)
    mix[:len(voice)] += voice
    kaching = sfx.clang(1800, 0.5, 0.8) * 0.5
    kaching[:len(sfx.beep(2400, 0.06))] += sfx.beep(2400, 0.06) * 0.4
    sad = sfx.fade(sfx.chirp(330, 220, 1.2, 1.0) * 0.6, 0.02, 0.3)
    ev = [(0.0, sfx.whoosh(0.5), 0.4), (MILLION, kaching, 0.6), (MILLION, sfx.bass_hit(), 0.3),
          (KEIN_JOB, sad, 0.25), (MOMENT, sfx.whoosh(0.3), 0.3), (MOMENT - 0.05, sfx.zap(0.2), 0.25),
          (FLASCHE1, sfx.bass_hit(), 0.25), (AB, sfx.whoosh(0.6), 0.45), (CUT, sfx.whoosh(0.5), 0.35),
          (REJECT, sfx.beep(220, 0.5), 0.45), (DOCH, ding(), 0.5), (EURO125, kaching, 0.6),
          (NURNOCH + 0.8, sad, 0.25), (KOMMENTARE, sfx.whoosh(0.4), 0.3), (FOLGT, sfx.whoosh(0.4), 0.3),
          (VOICE_END, sfx.bass_hit(), 0.6)]
    ev += [(t0, sfx.click(), 0.4) for t0 in (FLASCHE1, NOCH, DREI, VIER, FUENF)]
    ev += [(t0 + 0.35, sfx.beep(1600, 0.1), 0.35) for t0 in REIN + [DOCH - 0.25]]
    ev += [(t0 + 0.4, kaching, 0.3) for t0 in REIN]
    ev += [(BON + k * 0.12, sfx.click(), 0.25) for k in range(8)]
    ev += [(VOICE_END - 0.2 + k * 0.06, sfx.click(), 0.2) for k in range(25)]       # drum roll
    for t0, sig, g in ev:
        o = int(t0 * sfx.SR)
        n = min(len(sig), len(mix) - o)
        mix[o:o + n] += sig[:n] * g
    mix = mix[:int(DUR * sfx.SR)]
    mix = mix / max(1e-6, np.max(np.abs(mix))) * 0.95
    data = (np.stack([mix, mix], 1) * 32767).astype(np.int16)
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sfx.SR)
        w.writeframes(data.tobytes())


def render_video(src, words, out, workdir):
    subs = chunks(load_words(words))
    cutdir = os.path.join(workdir, "cut")
    os.makedirs(cutdir, exist_ok=True)
    n_src = int(VOICE_END * FPS)
    n = int(DUR * FPS)
    # 1) cut out every source frame once (cached on disk)
    todo = [k for k in range(n_src) if not os.path.exists(os.path.join(cutdir, f"{k:05d}.png"))]
    if todo:
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, os.path.join(workdir, "src_%05d.png")],
                       check=True)
        with Pool(4, initializer=_cut_init) as pool:
            for k, _ in enumerate(pool.imap_unordered(_cut_one, [(workdir, cutdir, i) for i in todo])):
                if k % 50 == 0:
                    print(f"\r  cutout {k}/{len(todo)}", end="", file=sys.stderr, flush=True)
    wav = out.rsplit(".", 1)[0] + "_audio.wav"
    build_audio(src, wav)
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags",
                            "+faststart", out], stdin=subprocess.PIPE)
    jobs = [(i, os.path.join(cutdir, f"{min(i, n_src - 1):05d}.png")) for i in range(n)]
    with Pool(initializer=_init, initargs=(subs,)) as pool:
        for k, data in enumerate(pool.imap(_render, jobs, chunksize=8)):
            enc.stdin.write(data)
            if k % 100 == 0:
                print(f"\r  frame {k}/{n}", end="", file=sys.stderr, flush=True)
    enc.stdin.close()
    enc.wait()
    os.remove(wav)
    print(f"\n  done: {out}", file=sys.stderr)


def _cut_init():
    os.environ.setdefault("OMP_NUM_THREADS", "1")


def _cut_one(args):
    workdir, cutdir, i = args
    im = Image.open(os.path.join(workdir, f"src_{i + 1:05d}.png")).convert("RGB")
    cutout(im).save(os.path.join(cutdir, f"{i:05d}.png"))
    return i


if __name__ == "__main__":
    mode, src, words, out = sys.argv[1:5]
    if mode == "storyboard":
        print(storyboard(src, words, out))
    else:
        render_video(src, words, out, os.path.dirname(os.path.abspath(words)))
