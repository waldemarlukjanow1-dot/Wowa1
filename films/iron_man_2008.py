"""Iron Man (2008) - in 1 Minute. Stick-figure summary, no voice, SFX only.

Render:  python3 -m films.iron_man_2008            (full video)
Preview: python3 -m films.iron_man_2008 --sheet    (contact sheet of stills)
"""
import math
import random
import sys

from engine import sfx
from engine.gfx import (INK, WHITE, arc_reactor, back_out, bolt, ease, ease_in, ease_out, explosion,
                        figure, flash, keys, lerp, lerp_c, muzzle, prog, smoke_puff, sparks, speech, bullet,
                        W, H)
from engine.render import Film, Scene, render, stills

GY = 1330  # ground line
GOLD = (255, 200, 61)
RED = (214, 36, 44)


# ------------------------------------------------------------------ shared bits
def header(c, t):
    c.text(540, 258, "IRON MAN (2008)", 68, WHITE, stroke=7, shake=False)
    c.text(540, 328, "in 1 Minute", 42, GOLD, stroke=6, shake=False)


def caption(c, txt, age):
    a = ease_out(prog(age, 0, 0.18))
    if a <= 0:
        return
    size = 40
    w = c.text_w(txt, size) + 64
    y = 418 + (1 - a) * 14
    c.no_shake()
    c.rect(540 - w / 2, y - 34, 540 + w / 2, y + 34, fill=(10, 10, 14, int(170 * a)), r=34)
    c.text(540, y + 1, txt, size, (255, 255, 255, int(255 * a)), shake=False)


def sky(c, top, bottom, ground, gy=GY):
    c.vgrad(0, gy, top, bottom)
    c.rect(0, gy, W, H, fill=ground)


def mountains(c, col, seed=3, x0=420, base=GY, h=300):
    rnd = random.Random(seed)
    x = x0
    while x < W + 100:
        w = rnd.uniform(180, 300)
        hh = rnd.uniform(0.55, 1.0) * h
        c.poly([(x - 40, base), (x + w * 0.5, base - hh), (x + w + 40, base)], fill=col)
        x += w * 0.7


def rocks_bg(c, seed, col, n=26, y0=480, y1=GY):
    rnd = random.Random(seed)
    for i in range(n):
        x = rnd.uniform(-40, W + 40)
        y = rnd.uniform(y0, y1)
        r = rnd.uniform(40, 120)
        pts = [(x + math.cos(a) * r * rnd.uniform(0.6, 1.1), y + math.sin(a) * r * rnd.uniform(0.4, 0.8))
               for a in [k * 6.283 / 7 for k in range(7)]]
        c.poly(pts, fill=col)


def missile(c, x, y, ang, L=130, w=26, flame=False, t=0.0):
    a = math.radians(ang)
    dx, dy = math.cos(a), math.sin(a)
    nx, ny = -dy, dx

    def P(u, v):
        return (x + dx * u + nx * v, y + dy * u + ny * v)

    if flame:
        fl = 40 + 14 * math.sin(t * 60)
        c.poly([P(-L / 2, -w * 0.4), P(-L / 2 - fl, 0), P(-L / 2, w * 0.4)], fill=(255, 170, 40, 230))
        c.poly([P(-L / 2, -w * 0.2), P(-L / 2 - fl * 0.55, 0), P(-L / 2, w * 0.2)], fill=(255, 245, 200))
    c.poly([P(-L / 2 + 8, -w / 2), P(-L / 2 - 10, -w), P(-L / 2 + 24, -w / 2)], fill=(90, 96, 104))
    c.poly([P(-L / 2 + 8, w / 2), P(-L / 2 - 10, w), P(-L / 2 + 24, w / 2)], fill=(90, 96, 104))
    c.poly([P(-L / 2, -w / 2), P(L / 2 - 26, -w / 2), P(L / 2 - 26, w / 2), P(-L / 2, w / 2)],
           fill=(232, 234, 238), outline=INK, w=3)
    c.poly([P(L / 2 - 26, -w / 2), P(L / 2, 0), P(L / 2 - 26, w / 2)], fill=RED, outline=INK, w=3)
    c.line([P(-L / 2 + 30, -w / 2), P(-L / 2 + 30, w / 2)], RED, 5, cap=False)


def rifle(c, hand, face, ang=0):
    a = math.radians(ang)
    dx, dy = math.cos(a) * face, math.sin(a)
    x, y = hand
    c.line([(x - dx * 55, y - dy * 55 + 8), (x + dx * 70, y + dy * 70)], (40, 34, 30), 9)
    c.line([(x - dx * 70, y - dy * 70 + 14), (x - dx * 40, y - dy * 40 + 4)], (110, 70, 40), 14)
    return (x + dx * 78, y + dy * 78)


def run_pose(t, f=2.6, A=42):
    s = math.sin(t * 6.283 * f)
    return dict(fl=(A * s, A * s - 55 * max(0, -s) - 10), bl=(-A * s, -A * s - 55 * max(0, s) - 10),
                fa=(-A * s * 0.9, -A * s * 0.9 + 75), ba=(A * s * 0.9, A * s * 0.9 + 75), lean=12)


def walk_pose(t, f=1.0, A=22):
    s = math.sin(t * 6.283 * f)
    return dict(fl=(A * s, A * s - 12 * max(0, -s)), bl=(-A * s, -A * s - 12 * max(0, s)),
                fa=(-A * s * 0.6 + 8, -A * s * 0.6 + 14), ba=(A * s * 0.6 - 8, A * s * 0.6 + 6), lean=3)


def podium(c, x, y=GY, label=True):
    c.poly([(x - 120, y - 210), (x + 120, y - 210), (x + 100, y), (x - 100, y)], fill=(70, 76, 90),
           outline=(30, 32, 40), w=5)
    c.rect(x - 130, y - 222, x + 130, y - 200, fill=(90, 96, 112), outline=(30, 32, 40), w=4)
    for dx in (-30, 30):
        c.line([(x + dx, y - 222), (x + dx * 0.6, y - 268)], (40, 40, 44), 5)
        c.ellipse(x + dx * 0.6, y - 274, 9, 13, fill=(30, 30, 34))
    if label:
        c.text(x, y - 110, "STARK", 34, (225, 230, 240))


def press_bg(c):
    c.vgrad(0, GY, (34, 64, 118), (18, 32, 64))
    c.rect(0, GY, W, H, fill=(26, 26, 34))
    for i in range(6):
        x = 90 + i * 180
        c.rect(x - 60, 560, x + 60, 1180, fill=(255, 255, 255, 12), r=10)


def photographers(c):
    for i, x in enumerate((60, 230, 640, 800)):
        y = 1400 + (i % 2) * 20
        c.ellipse(x, y + 80, 80, 60, fill=(12, 12, 18))
        c.circle(x, y, 38, fill=(12, 12, 18))
        c.rect(x + 20, y - 30, x + 70, y + 4, fill=(12, 12, 18), r=6)


def flashes(c, t, seed, rate=6.0, t0=0.0, t1=99.0, ys=(1360, 1385)):
    """Photographer camera flashes along the bottom edge of the stage."""
    photographers(c)
    if not (t0 <= t <= t1):
        return
    rnd = random.Random(seed + int(t * rate))
    k = (t * rate) % 1.0
    if k < 0.45:
        x = rnd.choice((60, 230, 640, 800)) + 50
        y = rnd.uniform(*ys)
        a = 1 - k / 0.45
        c.glow(x, y, 110, (255, 255, 255), 1.6 * a, rings=5)
        c.circle(x, y, 14, fill=(255, 255, 255, int(255 * a)))
        c.overlay((255, 255, 255), 0.12 * a)


def shutters(times, gain=0.5):
    return [(tt_, sfx.shutter(), gain) for tt_ in times]


# ------------------------------------------------------------------ 1. title
def s_title(c, t):
    c.vgrad(0, H, (10, 10, 16), (34, 10, 14))
    p = ease_out(prog(t, 0.0, 0.6))
    flick = 1.0 if t > 0.6 else (0.5 + 0.5 * math.sin(t * 70)) * p
    x, y = 540, 820
    c.glow(x, y, 260, (120, 210, 255), 1.2 * flick, rings=8)
    c.circle(x, y, 150, fill=(60, 64, 72), outline=(20, 20, 24), w=8)
    c.circle(x, y, 120, fill=lerp_c((40, 50, 60), (160, 225, 255), flick))
    for i in range(10):
        a = math.radians(i * 36 + t * 30)
        c.line([(x + math.cos(a) * 70, y + math.sin(a) * 70), (x + math.cos(a) * 118, y + math.sin(a) * 118)],
               (60, 120, 160), 12)
    c.circle(x, y, 62, fill=lerp_c((60, 70, 80), (235, 250, 255), flick), outline=(60, 120, 160), w=6)
    s = back_out(prog(t, 0.55, 0.95))
    if s > 0:
        c.text(540, 1120, "IRON MAN", int(150 * s) + 1, RED, stroke=6, stroke_fill=GOLD)
    s2 = ease_out(prog(t, 0.85, 1.15))
    if s2 > 0:
        c.text(540, 1228, "(2008)", 58, (*GOLD, int(255 * s2)))
        c.text(540, 1318, "in 1 Minute", 66, (255, 255, 255, int(255 * s2)))
    flash(c, t, 0.58, 0.25, (200, 235, 255))


title_snd = [(0.0, sfx.powerup(0.6), 0.5), (0.0, sfx.hum(2.8), 0.35), (0.58, sfx.bass_hit(), 1.0),
             (2.55, sfx.whoosh(0.5), 0.6)]


# ------------------------------------------------------------------ 2. Jericho demo
TARGETS = [(610, GY - 30), (690, GY - 70), (760, GY - 40), (830, GY - 80), (880, GY - 30)]


def s_demo(c, t):
    c.shake(16 * (1 - prog(t, 2.5, 3.4)) if t > 2.5 else 0, t)
    sky(c, (246, 186, 112), (252, 230, 186), (222, 178, 108))
    mountains(c, (196, 140, 86), seed=4, x0=430, h=330)
    mountains(c, (176, 120, 72), seed=9, x0=520, h=220)
    # launcher crate
    c.rect(370, GY - 70, 520, GY, fill=(98, 110, 70), outline=INK, w=5, r=6)
    c.text(445, GY - 34, "JERICHO", 26, (240, 240, 230))
    # main missile
    if t < 0.9:
        missile(c, 450, GY - 110, -60, L=120)
    elif t < 1.9:
        p = ease_in(prog(t, 0.9, 1.9))
        x, y = lerp(450, 640, p), lerp(GY - 110, 700, p)
        for k in range(10):  # smoke trail
            q = max(0, p - k * 0.06)
            c.circle(lerp(450, 640, q), lerp(GY - 110, 700, q) + 20, 16 + k * 3,
                     fill=(250, 250, 250, max(0, 190 - k * 16)))
        missile(c, x, y, -60, L=120, flame=True, t=t)
    elif t < 2.5:
        p = ease_in(prog(t, 1.9, 2.5))
        for i, (tx, ty) in enumerate(TARGETS):
            x, y = lerp(640, tx, p), lerp(700, ty, p)
            ang = math.degrees(math.atan2(ty - 700, tx - 640))
            missile(c, x, y, ang, L=60, w=14, flame=True, t=t + i)
    for i, (tx, ty) in enumerate(TARGETS):
        explosion(c, tx, ty, t - 2.5 - i * 0.07, size=120 + 20 * (i % 2), seed=i + 3)
    # Tony with shades, showing off
    if t < 0.5:
        pose = dict(fa=(30, 20), ba=(-20, -10))
    elif t < 2.6:
        pose = dict(fa=(100, 105), ba=(-15, -5))
    else:
        pose = dict(fa=(125, 150), ba=(-125, -150))
    figure(c, 220, GY, "tony", face=1, pose=pose, shades=True, mouth="smile")


demo_snd = [(0.0, sfx.wind(5.0), 0.35), (0.9, sfx.rocket(1.2), 0.55), (0.9, sfx.whoosh(0.9), 0.5),
            (1.9, sfx.whoosh(0.5), 0.45), (2.5, sfx.boom(2.4), 1.0), (2.64, sfx.boom(2.0, 0.8), 0.6),
            (2.8, sfx.boom(2.0, 0.7), 0.5)]


# ------------------------------------------------------------------ 3. ambush
def humvee(c, x, y, shake=0.0, t=0.0):
    oy = math.sin(t * 80) * shake
    c.rect(x - 200, y - 130 + oy, x + 200, y - 30 + oy, fill=(110, 118, 78), outline=INK, w=6, r=12)
    c.poly([(x - 110, y - 130 + oy), (x - 70, y - 215 + oy), (x + 120, y - 215 + oy), (x + 150, y - 130 + oy)],
           fill=(110, 118, 78), outline=INK, w=6)
    c.poly([(x - 55, y - 140 + oy), (x - 30, y - 200 + oy), (x + 108, y - 200 + oy), (x + 128, y - 140 + oy)],
           fill=(170, 210, 230))
    for wx in (-125, 125):
        c.circle(x + wx, y - 30, 46, fill=(34, 34, 38))
        c.circle(x + wx, y - 30, 18, fill=(120, 120, 124))


def s_ambush(c, t):
    c.shake(22 * (1 - prog(t, 3.35, 3.9)) if t > 3.35 else (4 if 0.2 < t < 1.0 else 0), t)
    sky(c, (246, 186, 112), (252, 230, 186), (222, 178, 108))
    mountains(c, (196, 140, 86), seed=12, x0=-100, h=260)
    c.rect(0, GY, W, GY + 60, fill=(196, 156, 96))
    # rock cover
    c.poly([(700, GY), (730, GY - 120), (820, GY - 150), (900, GY - 90), (920, GY)], fill=(150, 112, 74),
           outline=INK, w=5)
    hv_shake = 4 if 0.2 < t < 1.1 else 0
    humvee(c, 300, GY, hv_shake, t)
    if t < 1.1:
        # Tony in the passenger seat
        hx, hy = 330, GY - 170
        c.circle(hx, hy, 26, fill=WHITE, outline=INK, w=5)
        c.chord(hx, hy, 27, 190, 370, (40, 30, 26))
        c.circle(hx + 12, hy - 2, 4, fill=INK)
        c.poly([(hx + 4, hy + 14), (hx + 18, hy + 14), (hx + 13, hy + 26), (hx + 8, hy + 26)], fill=(40, 30, 26))
    # gunfire from off-screen left
    for i, ts in enumerate((0.2, 0.32, 0.45, 0.6, 0.7, 0.85, 0.95)):
        age = t - ts
        if 0 <= age < 0.12:
            bullet(c, lerp(0, 160, age / 0.12), GY - 90 - i * 9, 1)
        if 0.1 <= age < 0.3:
            sparks(c, 120, GY - 90 - i * 9, age - 0.1, n=6, spread=60, seed=i)
    # Tony runs for cover
    if 1.1 <= t:
        p = ease(prog(t, 1.1, 1.8))
        x = lerp(470, 690, p)
        if t < 1.8:
            figure(c, x, GY, "tony", face=1, pose=run_pose(t), eyes="wide", mouth="o")
        else:
            look = t > 2.2
            figure(c, 690, GY, "tony", face=-1 if not look else -1,
                   pose=dict(fl=(80, -10), bl=(60, -40), fa=(60, 30), ba=(30, 10), lean=-20, lift=-45),
                   eyes="wide" if look else "open", mouth="o" if look else "flat")
    # missile drops next to him
    if 1.8 <= t < 3.35:
        p = ease_in(prog(t, 1.8, 2.1))
        x, y = lerp(700, 560, p), lerp(380, GY - 30, p)
        ang = lerp(120, 165, p) if p < 1 else 170
        if p < 1:
            missile(c, x, y, ang - 0, L=130)
        else:
            missile(c, 560, GY - 24, 172, L=150, w=30)
            c.text(565, GY - 76, "STARK INDUSTRIES", 22, INK)
            # blinking light synced with beeps
            for bt in BEEPS:
                if bt <= t < bt + 0.09:
                    c.glow(612, GY - 30, 50, (255, 40, 40), 1.6)
                    c.circle(612, GY - 30, 9, fill=(255, 60, 60))
        if 2.08 < t < 2.5:
            smoke_puff(c, 560, GY - 10, t - 2.08, 40, seed=5, col=(230, 200, 150))
    explosion(c, 560, GY - 60, t - 3.35, size=320, seed=11)
    if t >= 3.35:
        c.overlay((255, 255, 255), 1 - prog(t, 3.55, 3.9))
        c.overlay((0, 0, 0), prog(t, 3.9, 4.5))


BEEPS = [2.3, 2.62, 2.88, 3.08, 3.22]
ambush_snd = ([(0.0, sfx.wind(4.5), 0.3)] +
              [(ts, sfx.gunshot(), 0.55) for ts in (0.2, 0.32, 0.45, 0.6, 0.7, 0.85, 0.95)] +
              [(ts, sfx.ping(), 0.35) for ts in (0.3, 0.62, 0.9)] +
              [(1.8, sfx.whoosh(0.35), 0.6), (2.08, sfx.thud(), 0.8)] +
              [(b, sfx.beep(), 0.45) for b in BEEPS] +
              [(3.35, sfx.boom(3.0, 1.2), 1.1), (3.4, sfx.ringing(2.0), 0.5)])


# ------------------------------------------------------------------ 4. cave: captured
CAVE_HALO = (118, 92, 72)


def cave_bg(c, blue=0.0):
    c.vgrad(0, GY, (58, 42, 32), (36, 26, 20))
    rocks_bg(c, 5, (48, 34, 26), n=30)
    c.rect(0, GY, W, H, fill=(46, 34, 26))
    c.line([(760, 480), (760, 600)], (30, 22, 18), 4)
    c.glow(760, 640, 180, (255, 190, 90), 0.8)
    c.circle(760, 640, 22, fill=(255, 220, 140))
    if blue > 0:
        c.overlay((60, 140, 220), 0.12 * blue)


def battery(c, x, y):
    c.rect(x - 50, y - 60, x + 50, y, fill=(40, 42, 46), outline=(15, 15, 18), w=4, r=6)
    c.rect(x - 34, y - 72, x - 18, y - 60, fill=(200, 40, 40))
    c.rect(x + 18, y - 72, x + 34, y - 60, fill=(30, 30, 30))


def s_cave(c, t):
    cave_bg(c)
    if t < 2.3:
        # table with Tony lying on it, Yinsen watching
        c.rect(230, 1180, 720, 1205, fill=(120, 84, 52), outline=INK, w=4)
        c.rect(260, 1205, 280, GY, fill=(100, 70, 44))
        c.rect(670, 1205, 690, GY, fill=(100, 70, 44))
        battery(c, 470, GY)
        pts = figure(c, 300, 1178 - 34, "tony", face=1, rot=90, eyes="closed" if t < 1.1 else "wide",
                     mouth="flat" if t < 1.1 else "o", pose=dict(fa=(5, 5), ba=(-5, -5), fl=(0, 0), bl=(0, 0)))
        cx, cy = pts["chest"]
        c.line([(cx, cy), (cx - 40, cy + 120), (440, GY - 72)], (200, 40, 40), 4, cap=False)
        c.line([(cx + 6, cy), (cx - 10, cy + 110), (500, GY - 72)], (20, 20, 20), 4, cap=False)
        c.circle(cx, cy, 10, fill=(150, 150, 150), outline=INK, w=3)
        figure(c, 830, GY, "yinsen", face=-1, mouth="smile" if t > 1.3 else "flat",
               pose=dict(fa=(40, 60), ba=(-10, 0), lean=-8))
    else:
        lt = t - 2.3
        battery(c, 220, GY)
        shake_no = math.sin(lt * 30) * 9 if 0.7 < lt < 1.3 else 0
        nod = max(0, math.sin((lt - 2.4) * 18)) * 10 if 2.4 < lt < 3.1 else 0
        scared = lt > 1.6
        pts = figure(c, 330, GY, "tony", face=1, eyes="wide" if scared else "open",
                     mouth="frown" if lt > 0.6 else "flat",
                     pose=dict(fa=(20, 10), ba=(-10, -5), hdx=shake_no, hdy=nod))
        cx, cy = pts["chest"]
        c.line([(cx, cy), (cx - 30, cy + 140), (220, GY - 60)], (200, 40, 40), 4, cap=False)
        c.circle(cx, cy, 10, fill=(150, 150, 150), outline=INK, w=3)
        # leader shows a drawing of the missile
        lp = figure(c, 640, GY, "thug", face=-1, pose=dict(fa=(110, 95), ba=(-10, -5)), eyes="angry")
        hx, hy = lp["fh"]
        c.rect(hx - 110, hy - 100, hx + 30, hy + 10, fill=(240, 232, 210), outline=INK, w=4)
        missile(c, hx - 40, hy - 45, -30, L=90, w=18)
        # rifleman
        aim = ease(prog(lt, 1.4, 1.6))
        rp = figure(c, 820, GY, "thug", face=-1, eyes="angry",
                    pose=dict(fa=(lerp(40, 88, aim), lerp(70, 92, aim)), ba=(lerp(20, 60, aim), lerp(70, 95, aim))))
        rifle(c, rp["fh"], -1, lerp(40, 0, aim))


cave_snd = ([(0.0, sfx.cave(5.5), 0.6)] + [(ts, sfx.heartbeat(), 0.9) for ts in (0.1, 0.85, 1.6)] +
            [(0.5, sfx.drip(), 0.5), (2.0, sfx.drip(), 0.4), (2.3, sfx.whoosh(0.3), 0.25),
             (3.7, sfx.servo(0.15, 400), 0.4), (3.85, sfx.click(), 0.8), (3.95, sfx.click(), 0.6),
             (4.7, sfx.drip(), 0.4)])


# ------------------------------------------------------------------ 5. build
HITS = [0.35, 0.85, 1.35, 1.85]
STEPS5 = [4.2, 4.65, 5.1, 5.55]
CUTS5 = [GY, 1170, 1080, 1030, 960]


def s_build(c, t):
    blue = ease(prog(t, 3.4, 3.7))
    cave_bg(c, blue)
    if t < 2.3:
        # hammering at the workbench
        c.rect(180, 1170, 560, 1195, fill=(120, 84, 52), outline=INK, w=4)
        c.rect(200, 1195, 220, GY, fill=(100, 70, 44))
        c.rect(520, 1195, 540, GY, fill=(100, 70, 44))
        c.rect(380, 1140, 500, 1170, fill=(150, 154, 160), outline=INK, w=3)
        ph = (t % 0.5) / 0.5
        up = 160 - 110 * ease_in(min(1, ph / 0.7)) if ph < 0.7 else 50 + 110 * ease(prog(ph, 0.7, 1))
        pts = figure(c, 640, GY, "tony", face=-1, pose=dict(fa=(up, up - 20), ba=(40, 70), lean=10), mouth="flat")
        hx, hy = pts["fh"]
        a = math.radians(up - 20 - 90)
        hdx, hdy = -math.cos(a) * 1, math.sin(a)
        c.line([(hx, hy), (hx - math.sin(math.radians(up - 20)) * 50, hy + math.cos(math.radians(up - 20)) * 50)],
               (110, 70, 40), 9)
        head = (hx - math.sin(math.radians(up - 20)) * 55, hy + math.cos(math.radians(up - 20)) * 55)
        c.circle(*head, 16, fill=(90, 90, 96), outline=INK, w=3)
        for i, h in enumerate(HITS):
            sparks(c, 470, 1140, t - h, n=14, spread=150, seed=i)
        figure(c, 130, GY, "yinsen", face=1, pose=dict(fa=(60, 80), ba=(-10, 0)))
    elif t < 4.0:
        lt = t - 2.3
        raise_ = ease(prog(lt, 0.0, 0.4))
        bring = ease(prog(lt, 0.7, 1.1))
        pts = figure(c, 470, GY, "tony", face=1, mouth="smile" if lt > 1.2 else "flat",
                     reactor=lt > 1.1,
                     pose=dict(fa=(lerp(lerp(20, 150, raise_), 40, bring), lerp(lerp(10, 175, raise_), 150, bring)),
                               ba=(-15, -10)))
        if lt <= 1.1:
            arc_reactor(c, *pts["fh"], 16, 0.6 + 0.4 * math.sin(lt * 20) ** 2)
        figure(c, 760, GY, "yinsen", face=-1, mouth="smile" if lt > 1.2 else "o",
               eyes="wide" if lt > 1.1 else "open")
        flash(c, lt, 1.1, 0.3, (190, 235, 255))
    else:
        lt = t - 4.0
        # suit appears piece by piece on a stand while Tony works
        c.line([(720, GY), (720, 940)], (60, 50, 44), 8)
        cut = CUTS5[0]
        for i, st in enumerate(STEPS5):
            cut = lerp(cut, CUTS5[i + 1], ease_out(prog(t, st, st + 0.15)))
        L = c.layer()
        figure(L, 720, GY, "mk1", face=-1, s=1.05)
        c.paste(L, cut - 2, GY + 20)
        work = any(st <= t < st + 0.3 for st in STEPS5)
        figure(c, 430, GY, "tony", face=1, reactor=True, mouth="smile" if t > 5.7 else "flat",
               pose=dict(fa=(90 if work else 70, 100 if work else 60), ba=(20, 50), lean=6))
        for i, st in enumerate(STEPS5):
            sparks(c, 700, CUTS5[i + 1] + 10, t - st, n=14, spread=140, seed=20 + i)


build_snd = ([(0.0, sfx.cave(6.5), 0.5)] + [(h, sfx.clang(620 + i * 30, 0.8), 0.65) for i, h in enumerate(HITS)] +
             [(2.4, sfx.powerup(1.0), 0.35), (3.4, sfx.zap(0.35), 0.6), (3.4, sfx.hum(3.0, 110), 0.3),
              (3.4, sfx.bass_hit(), 0.4)] +
             [(st, sfx.clang(300 + i * 40, 0.9, 0.6), 0.7) for i, st in enumerate(STEPS5)] +
             [(st, sfx.zap(0.2), 0.3) for st in STEPS5])


# ------------------------------------------------------------------ 6. escape
THUGS6 = [690, 830]


def s_escape(c, t):
    sh = 14 * (1 - prog(t, 0.4, 0.9)) if 0.4 <= t < 0.9 else 0
    sh += 20 * (1 - prog(t, 3.4, 4.0)) if 3.4 <= t < 4.0 else 0
    c.shake(sh, t)
    sky(c, (246, 186, 112), (252, 230, 186), (222, 178, 108))
    mountains(c, (196, 140, 86), seed=21, x0=380, h=240)
    c.poly([(-20, 520), (260, 600), (380, 900), (420, GY), (-20, GY)], fill=(120, 86, 60), outline=INK, w=5)
    c.poly([(120, GY), (130, 1120), (200, 1060), (280, 1120), (290, GY)], fill=(30, 22, 18))
    # ammo crates
    if t < 3.4:
        for i, (x, w) in enumerate(((560, 90), (610, 70))):
            c.rect(x - w / 2, GY - 70 - i * 60, x + w / 2, GY - i * 60, fill=(120, 96, 54), outline=INK, w=4)
    explosion(c, 600, GY - 80, t - 3.4, size=260, seed=31)
    explosion(c, 205, 1200, t - 0.4, size=110, seed=7)
    # Yinsen lies near the cave
    figure(c, 330, GY - 34, "yinsen", face=1, rot=-90, eyes="closed", mouth="flat",
           pose=dict(fa=(170, 170), ba=(-20, -10)))
    # Mark I
    walk = ease(prog(t, 0.6, 2.0))
    x = lerp(205, 380, walk)
    lift = 0
    if t >= 4.0:
        lift = ease_in(prog(t, 4.0, 5.5)) * 1500 + 30 * ease(prog(t, 4.0, 4.2))
    if t < 2.0:
        pose = walk_pose(t, 0.9, 18) if t > 0.6 else dict()
    elif t < 3.4:
        pose = dict(fa=(90, 90), ba=(-10, 0))
    else:
        pose = dict(fa=(10, 5), ba=(-10, -5))
    pose = dict(pose)
    pose["lift"] = lift
    pts = figure(c, x, GY, "mk1", face=1, pose=pose, reactor=True)
    if t >= 4.0:
        for k, foot in enumerate(("ff", "bf")):
            fx, fy = pts[foot]
            fl = 70 + 20 * math.sin(t * 50 + k)
            c.poly([(fx - 16, fy + 8), (fx + 16, fy + 8), (fx, fy + fl)], fill=(255, 170, 40, 230))
            c.poly([(fx - 8, fy + 8), (fx + 8, fy + 8), (fx, fy + fl * 0.6)], fill=(255, 245, 200))
        smoke_puff(c, x, GY - 10, t - 4.0, 70, seed=4)
    # flamethrower
    if 2.3 <= t < 3.4:
        hx, hy = pts["fh"]
        reach = ease_out(prog(t, 2.3, 2.6)) * 520
        fl = math.sin(t * 40) * 14
        c.poly([(hx + 10, hy - 8), (hx + reach, hy - 70 + fl), (hx + reach + 30, hy + fl), (hx + reach, hy + 70 + fl),
                (hx + 10, hy + 8)], fill=(255, 130, 30, 220))
        c.poly([(hx + 10, hy - 4), (hx + reach * 0.75, hy - 34 + fl), (hx + reach * 0.8, hy + fl),
                (hx + reach * 0.75, hy + 34), (hx + 10, hy + 4)], fill=(255, 225, 120, 240))
    # thugs: fire, then flee
    for i, tx in enumerate(THUGS6):
        if t < 2.5:
            rp = figure(c, tx, GY, "thug", face=-1, eyes="angry", pose=dict(fa=(88, 92), ba=(60, 95)))
            m = rifle(c, rp["fh"], -1, 0)
            for k, ts in enumerate(SHOTS6):
                if k % 2 == i and 0 <= t - ts < 0.07:
                    muzzle(c, *m, -1)
        else:
            p = prog(t, 2.5, 3.4)
            figure(c, tx + ease_in(p) * 520, GY, "thug", face=1, eyes="wide", pose=run_pose(t, 3.2))
    for k, ts in enumerate(SHOTS6):
        age = t - ts
        if 0.06 <= age < 0.18 and t < 2.5:
            sparks(c, x + 10, GY - 230 + (k % 3) * 30, age - 0.06, n=6, spread=70, seed=k)


SHOTS6 = [1.0, 1.15, 1.3, 1.45, 1.6, 1.75, 1.9, 2.05, 2.2]
escape_snd = ([(0.0, sfx.wind(5.6), 0.25), (0.4, sfx.boom(1.8, 0.8), 0.8)] +
              [(ts, sfx.step_heavy(), 0.9) for ts in (0.85, 1.35, 1.85)] +
              [(ts, sfx.gunshot(), 0.5) for ts in SHOTS6] + [(ts + 0.06, sfx.ping(), 0.4) for ts in SHOTS6[::2]] +
              [(2.3, sfx.flame(1.1), 0.9), (3.4, sfx.boom(2.5, 1.1), 1.0), (4.0, sfx.rocket(1.6), 0.8)])


# ------------------------------------------------------------------ 7. crash + rescue
def heli(c, x, y, t):
    c.line([(x + 60, y), (x + 230, y - 20)], (64, 74, 54), 18)
    c.rect(x + 220, y - 50, x + 240, y + 6, fill=(64, 74, 54))
    c.ellipse(x, y, 110, 58, fill=(78, 90, 64), outline=INK, w=5)
    c.ellipse(x - 50, y - 8, 50, 34, fill=(170, 210, 230))
    c.line([(x, y - 58), (x, y - 78)], INK, 6)
    w = 230 * abs(math.sin(t * 40)) + 40
    c.ellipse(x, y - 80, w, 8, fill=(30, 30, 30, 140))
    c.line([(x - 60, y + 70), (x + 70, y + 70)], INK, 6)
    c.line([(x - 30, y + 56), (x - 30, y + 70)], INK, 5)
    c.line([(x + 40, y + 56), (x + 40, y + 70)], INK, 5)


def s_crash(c, t):
    c.shake(18 * (1 - prog(t, 0.6, 1.0)) if 0.6 <= t < 1.0 else 0, t)
    c.vgrad(0, GY, (250, 200, 130), (253, 236, 200))
    c.poly([(0, GY), (0, GY - 60), (300, GY - 100), (650, GY - 40), (1080, GY - 90), (1080, GY)], fill=(232, 192, 124))
    c.rect(0, GY, W, H, fill=(222, 178, 108))
    if t < 0.6:
        p = ease_in(prog(t, 0, 0.6))
        figure(c, lerp(900, 480, p), lerp(500, GY, p), "mk1", face=-1, rot=lerp(-60, -100, p))
    else:
        rnd = random.Random(2)
        for i in range(7):
            x = 480 + rnd.uniform(-220, 220)
            c.rect(x - 22, GY - 26, x + 22, GY, fill=(128, 133, 140), outline=(70, 72, 78), w=4, r=4)
        smoke_puff(c, 480, GY - 30, t - 0.6, 90, seed=3, col=(232, 205, 160))
        up = ease(prog(t, 0.9, 1.4))
        wave = t > 1.9
        figure(c, 480, GY, "tony", face=1 if wave else -1,
               pose=dict(fa=(lerp(60, 165 + 10 * math.sin(t * 14), 1 if wave else 0), 175 if wave else 60),
                         ba=(-10, -5), lift=lerp(-140, 0, up), lean=lerp(60, 0, up)),
               mouth="grin" if wave else "o", eyes="open")
        if t > 1.5:
            p = ease_out(prog(t, 1.5, 2.4))
            heli(c, lerp(1250, 740, p), lerp(640, 800, p), t)


crash_snd = [(0.0, sfx.whoosh(0.6), 0.6), (0.6, sfx.thud(), 1.0), (0.6, sfx.boom(1.2, 0.6), 0.6),
             (0.0, sfx.wind(3.0), 0.25), (1.3, sfx.heli(1.8), 0.9)]


# ------------------------------------------------------------------ 8. press conference
def s_press(c, t):
    press_bg(c)
    c.text(500, 655, "STARK INDUSTRIES", 54, (255, 255, 255, 50))
    up = back_out(prog(t, 0.3, 0.6))
    pts = figure(c, 470, GY, "tony", face=1, mouth="flat",
                 pose=dict(fa=(lerp(20, 150, up), lerp(10, 170, up)), ba=(-10, -5)), reactor=True)
    podium(c, 470)
    if up > 0.05:
        hx, hy = pts["fh"]
        x0, y0 = hx - 120, hy - 170
        c.rect(x0, y0, x0 + 240, y0 + 160, fill=WHITE, outline=INK, w=6, r=8)
        missile(c, x0 + 120, y0 + 80, -20, L=150, w=26)
        if t > 0.7:
            k = ease_out(prog(t, 0.7, 0.9))
            c.line([(x0 + 20, y0 + 20), (lerp(x0 + 20, x0 + 220, k), lerp(y0 + 20, y0 + 140, k))], RED, 16)
            if t > 0.85:
                k2 = ease_out(prog(t, 0.85, 1.05))
                c.line([(x0 + 220, y0 + 20), (lerp(x0 + 220, x0 + 20, k2), lerp(y0 + 20, y0 + 140, k2))], RED, 16)
    angry = t > 1.3
    figure(c, 810, GY, "obadiah", face=-1, s=1.08, eyes="angry" if angry else "open",
           pose=dict(fa=(10, 5), ba=(-10, -5)))
    flashes(c, t, 3, rate=4.0, t0=0.1, t1=3.5)


press_snd = (shutters([0.1, 0.35, 0.6, 0.85, 1.6, 1.85, 2.35, 2.6, 3.1], 0.45) +
             [(0.72, sfx.whoosh(0.2), 0.3), (0.88, sfx.whoosh(0.2), 0.3), (1.3, sfx.bass_hit(), 0.55),
              (0.0, sfx.room(3.5), 0.4)])


# ------------------------------------------------------------------ 9. workshop
STEPS9 = [3.4, 3.85, 4.3, 4.75]
CUTS9 = [GY, 1180, 1100, 1040, 960]


def workshop_bg(c):
    c.vgrad(0, GY, (78, 90, 108), (52, 60, 72))
    c.rect(-200, 560, W + 200, 640, fill=(34, 38, 46))
    for x in range(-60, W + 100, 140):
        c.rect(x, 640, x + 70, 656, fill=(220, 235, 255, 120))
    c.rect(0, GY, W, H, fill=(96, 102, 114))
    c.line([(0, GY), (W, GY)], (60, 64, 74), 6)
    # hot rod silhouette
    c.rect(700, 1180, 1080, 1270, fill=(40, 44, 54), r=30)
    c.circle(760, 1280, 40, fill=(26, 28, 34))
    c.circle(1000, 1280, 40, fill=(26, 28, 34))


def dum_e(c, x, tipx, tipy):
    c.rect(x - 50, GY - 40, x + 50, GY, fill=(60, 64, 72), outline=INK, w=4)
    ex, ey = x + 10, GY - 230
    c.line([(x, GY - 40), (ex, ey)], (240, 200, 60), 18)
    c.line([(ex, ey), (tipx, tipy)], (240, 200, 60), 14)
    c.circle(ex, ey, 14, fill=(60, 64, 72))
    c.rect(tipx - 14, tipy - 30, tipx + 14, tipy + 10, fill=(200, 30, 30), r=4)


def s_workshop(c, t):
    hit = 1.75
    c.shake(16 * (1 - prog(t, hit, hit + 0.4)) if hit <= t < hit + 0.4 else
            (10 * (1 - prog(t, 2.25, 2.5)) if 2.25 <= t < 2.5 else 0), t)
    c.halo = (126, 138, 156)
    workshop_bg(c)
    if t < 3.2:
        if t < 1.4:
            lift = 40 + 26 * math.sin(t * 9) + 12 * math.sin(t * 23)
            rot = 8 * math.sin(t * 5)
        elif t < hit:
            lift = lerp(60, 330, ease_in(prog(t, 1.4, hit)))
            rot = 0
        else:
            lift = lerp(330, 0, ease_in(prog(t, hit + 0.1, 2.25)))
            rot = lerp(0, 90, ease(prog(t, hit + 0.05, 2.25)))
        if t < 2.25:
            pts = figure(c, 520, GY, "mk2", face=1, rot=rot, visor=1.0, reactor=True,
                         pose=dict(fa=(-20, -15), ba=(-30, -20), lift=lift))
            for k, n in enumerate(("fh", "bh", "ff", "bf")):
                fx, fy = pts[n]
                fl = (50 if n in ("ff", "bf") else 34) * (1.8 if 1.4 <= t < hit else 1) + 10 * math.sin(t * 60 + k)
                c.poly([(fx - 12, fy + 6), (fx + 12, fy + 6), (fx, fy + fl)], fill=(140, 210, 255, 220))
                c.poly([(fx - 6, fy + 6), (fx + 6, fy + 6), (fx, fy + fl * 0.6)], fill=(240, 250, 255))
        else:
            figure(c, 360, GY - 30, "mk2", face=1, rot=90, visor=1.0, reactor=True)
        dum_e(c, 160, lerp(230, 300, ease(prog(t, 2.3, 2.5))), lerp(GY - 200, GY - 160, ease(prog(t, 2.3, 2.5))))
        if t > 2.45:
            smoke_puff(c, 470, GY - 60, (t - 2.45) * 0.8, 70, seed=8)
            smoke_puff(c, 560, GY - 50, (t - 2.55) * 0.8, 60, seed=9)
        if hit <= t < hit + 0.25:
            sparks(c, 520, 650, t - hit, n=16, spread=160, seed=4)
    else:
        dum_e(c, 160, 230, GY - 200)
        cut = CUTS9[0]
        for i, st in enumerate(STEPS9):
            cut = lerp(cut, CUTS9[i + 1], ease_out(prog(t, st, st + 0.15)))
        tpose = dict(fa=(80, 85), ba=(-80, -85))
        figure(c, 540, GY, "tony", face=1, pose=tpose, reactor=True, mouth="smile")
        L = c.layer()
        visor = ease(prog(t, 5.25, 5.5))
        figure(L, 540, GY, "mk3", face=1, pose=tpose, reactor=True, visor=max(visor, 0.001) if t > 5.25 else 0,
               mouth="smile")
        c.paste(L, cut - 2, GY + 30)
        for i, st in enumerate(STEPS9):
            sparks(c, 540, CUTS9[i + 1] + 4, t - st, n=12, spread=120, seed=40 + i, col=(255, 235, 170))
        if t > 5.55:
            flash(c, t, 5.6, 0.3, (255, 240, 200))


workshop_snd = ([(0.0, sfx.room(6.2, 60), 0.4), (0.0, sfx.rocket(1.4), 0.35), (1.4, sfx.rocket(0.4), 0.7),
                 (1.75, sfx.clang(240, 1.0), 0.9), (1.75, sfx.thud(), 0.9), (2.25, sfx.thud(), 1.0),
                 (2.25, sfx.clang(300, 0.8, 0.5), 0.6), (2.45, sfx.extinguisher(0.8), 0.6)] +
                [(st, sfx.servo(0.2, 600 + 80 * i), 0.5) for i, st in enumerate(STEPS9)] +
                [(st + 0.15, sfx.clang(700, 0.4, 0.5), 0.5) for st in STEPS9] +
                [(5.25, sfx.servo(0.25, 900), 0.5), (5.5, sfx.click(), 0.8), (5.55, sfx.powerup(0.6), 0.55),
                 (5.6, sfx.bass_hit(), 0.6)])


# ------------------------------------------------------------------ 10. first mission
NIGHT_HALO = (118, 120, 156)


def night_bg(c):
    c.vgrad(0, GY, (16, 20, 44), (44, 44, 84))
    rnd = random.Random(1)
    for i in range(40):
        c.circle(rnd.uniform(0, W), rnd.uniform(480, 1000), rnd.uniform(1.5, 3.5), fill=(255, 255, 230, 200))
    c.circle(820, 620, 60, fill=(245, 240, 210))
    for x, w, h in ((0, 220, 260), (230, 180, 200), (430, 240, 300), (690, 200, 220), (900, 200, 280)):
        c.rect(x, GY - h, x + w, GY, fill=(70, 60, 64))
        c.rect(x + w * 0.4, GY - h + 50, x + w * 0.4 + 40, GY - h + 100, fill=(255, 200, 110, 160))
    c.rect(0, GY, W, H, fill=(58, 50, 50))


def s_gulmira(c, t):
    c.shake(14 * (1 - prog(t, 0.55, 0.85)) if 0.55 <= t < 0.85 else 0, t)
    night_bg(c)
    # villagers
    for i, x in enumerate((140, 250)):
        figure(c, x, GY, "plain", face=1, s=0.85, eyes="wide" if t < 1.8 else "open",
               mouth="o" if t < 1.8 else "smile", pose=dict(fa=(170, 175), ba=(-170, -175)))
    # Iron Man lands
    land = ease_in(prog(t, 0.0, 0.55))
    crouch = 1 - ease(prog(t, 0.75, 1.0))
    if t < 0.55:
        pose = dict(fa=(-20, -15), ba=(-30, -20), lift=lerp(1200, 0, land))
    else:
        pose = dict(fl=(lerp(10, 95, crouch), lerp(0, -10, crouch)), bl=(lerp(-10, 10, crouch), lerp(0, -90, crouch)),
                    lean=lerp(0, 30, crouch), lift=lerp(0, -70, crouch),
                    fa=(lerp(15, 30, crouch), lerp(10, 0, crouch)) if t < 0.95 else (90, 90),
                    ba=(-10, -5))
    pts = figure(c, 420, GY, "mk3", face=1, visor=1.0, reactor=True, pose=pose)
    if 0.5 < t < 1.0:
        smoke_puff(c, 420, GY - 20, (t - 0.5) * 1.2, 80, seed=2, col=(150, 140, 140))
    # thugs get blasted away
    for i, (tx, bt) in enumerate(((640, 1.0), (820, 1.25))):
        if t < bt:
            rp = figure(c, tx, GY, "thug", face=-1, eyes="angry", pose=dict(fa=(70, 80), ba=(50, 85)))
            rifle(c, rp["fh"], -1, 20)
        else:
            p = ease_out(prog(t, bt, bt + 0.6))
            figure(c, tx + p * 600, GY - math.sin(p * 3.14) * 220, "thug", face=-1, eyes="x", rot=p * 200,
                   pose=dict(fa=(160, 170), ba=(140, 160), fl=(40, 20), bl=(-30, -10)))
        if bt - 0.25 <= t < bt + 0.15 and t > 0.95:
            hx, hy = pts["fh"]
            g = prog(t, bt - 0.25, bt)
            c.glow(hx + 12, hy, 60, (180, 230, 255), 1.5 * g)
            if t >= bt:
                k = 1 - prog(t, bt, bt + 0.15)
                c.line([(hx + 10, hy), (tx - 20, GY - 220)], (200, 240, 255, int(230 * k)), 26 * k + 4)
                c.line([(hx + 10, hy), (tx - 20, GY - 220)], (255, 255, 255, int(255 * k)), 8)


gulmira_snd = [(0.0, sfx.night(2.6), 0.5), (0.0, sfx.whoosh(0.55), 0.6), (0.55, sfx.thud(), 1.0),
               (0.55, sfx.clang(220, 0.6, 0.4), 0.5), (0.72, sfx.repulsor(), 0.8), (0.97, sfx.repulsor(), 0.8)]


# ------------------------------------------------------------------ 10b. the real villain
def s_villain(c, t):
    c.vgrad(0, GY, (70, 16, 18), (26, 8, 10))
    c.rect(0, GY, W, H, fill=(22, 8, 10))
    c.glow(540, 760, 380, (255, 70, 60), 0.5)
    shake = math.sin(t * 22) * 8 if 0.4 < t < 1.4 else 0
    figure(c, 380, GY, "obadiah", face=1, s=1.08, eyes="angry", mouth="grin",
           pose=dict(fa=(75, 85 + shake), ba=(-10, -5)))
    figure(c, 690, GY, "thug", face=-1, eyes="angry", pose=dict(fa=(75, 85 - shake), ba=(-10, -5)))
    # suitcase of money
    c.rect(560, GY - 90, 680, GY, fill=(30, 30, 34), outline=(200, 200, 200), w=4, r=8)
    c.text(620, GY - 44, "$", 54, (110, 200, 110))


villain_snd = [(0.0, sfx.bass_hit(2.0), 0.9), (0.0, sfx.hum(2.0, 41), 0.6), (0.6, sfx.whoosh(0.4, False), 0.2)]


# ------------------------------------------------------------------ 11. heart stolen
def living_bg(c):
    c.vgrad(0, GY, (214, 196, 168), (184, 164, 136))
    c.rect(0, GY, W, H, fill=(132, 108, 84))
    c.rect(560, 560, 920, 900, fill=(60, 110, 160), outline=(60, 50, 40), w=8)   # window/ocean
    c.rect(560, 760, 920, 900, fill=(40, 80, 130))


def s_heart(c, t):
    living_bg(c)
    # couch
    c.rect(330, 1120, 760, 1260, fill=(150, 60, 50), outline=INK, w=5, r=20)
    c.rect(330, 1250, 760, 1300, fill=(130, 50, 42), outline=INK, w=5, r=10)
    # small table with glass case (Pepper's gift)
    c.rect(90, 1170, 290, 1190, fill=(110, 80, 56), outline=INK, w=4)
    c.rect(180, 1190, 200, GY, fill=(110, 80, 56))
    have = t < 3.3
    c.rect(140, 1080, 240, 1170, fill=(200, 230, 245, 90), outline=(80, 110, 130), w=4)
    if have:
        arc_reactor(c, 190, 1130, 18, 0.25)
    # Tony
    lost = t > 1.3
    if t < 2.2:
        pts = figure(c, 470, GY, "tony", face=1, eyes="wide", mouth="o",
                     pose=dict(fl=(90, 0), bl=(80, 0), lift=-70, fa=(10, 10), ba=(-10, -5)),
                     reactor=True, reactor_power=0.0 if lost else 1.0)
        if lost and t < 2.2:
            cx, cy = pts["chest"]
            c.circle(cx, cy, 12, fill=(20, 20, 24))
    else:
        crawl = ease(prog(t, 2.2, 3.1))
        reach = ease(prog(t, 3.1, 3.4))
        back = t > 3.5
        x = lerp(760, 610, crawl)
        figure(c, x, GY - 24, "tony", face=-1, rot=-90, eyes="wide" if not back else "open",
               mouth="o" if not back else "smile", reactor=True, reactor_power=1.0 if back else 0.0,
               pose=dict(fa=(lerp(60, 150, reach), lerp(70, 160, reach)), ba=(20, 10),
                         fl=(-abs(math.sin(t * 9)) * 15, -35), bl=(-abs(math.cos(t * 9)) * 15, -35)))
        if back:
            flash(c, t, 3.5, 0.3, (190, 235, 255))
    # Obadiah
    if t < 2.8:
        pull = ease(prog(t, 0.8, 1.3))
        leave = ease_in(prog(t, 1.9, 2.8))
        op = figure(c, 700 + leave * 500, GY, "obadiah", face=-1 if leave == 0 else 1, s=1.08, eyes="angry",
                    mouth="grin" if pull > 0.5 else "flat",
                    pose=dict(fa=(lerp(70, lerp(100, 150, pull), 1), lerp(80, lerp(100, 170, pull), 1)),
                              ba=(30, 70), lean=lerp(20, 0, pull)))
        hx, hy = op["fh"]
        if t < 0.8:
            c.rect(hx - 18, hy - 14, hx + 18, hy + 14, fill=(40, 40, 46), r=4)
            if int(t * 10) % 2 == 0:
                c.circle(hx, hy - 20, 6, fill=(255, 60, 60))
        if lost:
            arc_reactor(c, hx, hy, 14, 1.0)


heart_snd = ([(0.0, sfx.room(4.5, 50), 0.4), (0.05, sfx.zap(0.7), 0.4), (0.05, sfx.beep(2400, 0.6), 0.15),
              (1.3, sfx.servo(0.3, 300), 0.5), (1.3, sfx.bass_hit(), 0.5)] +
             [(ts, sfx.heartbeat(), g) for ts, g in ((0.2, 0.8), (1.6, 0.6), (2.5, 0.45), (3.3, 0.35))] +
             [(3.45, sfx.click(), 0.8), (3.5, sfx.powerup(0.5), 0.5), (3.5, sfx.hum(1.0, 110), 0.25)])


# ------------------------------------------------------------------ 12. showdown
def rooftop_bg(c, glow=0.0):
    c.vgrad(0, GY, (10, 14, 34), (34, 40, 78))
    rnd = random.Random(4)
    x = -20
    while x < W:
        w = rnd.uniform(70, 150)
        h = rnd.uniform(150, 420)
        c.rect(x, GY - h, x + w - 8, GY, fill=(22, 26, 46))
        for k in range(int(h / 50)):
            if rnd.random() < 0.5:
                c.rect(x + 14, GY - h + 20 + k * 50, x + 30, GY - h + 34 + k * 50, fill=(255, 220, 140, 120))
        x += w
    c.rect(0, GY, W, H, fill=(50, 54, 64))
    c.glow(540, GY + 10, 260, (120, 210, 255), 0.6 + glow)
    c.ellipse(540, GY + 8, 200, 34, fill=lerp_c((120, 200, 240), (240, 252, 255), glow), outline=(40, 60, 80), w=6)


def s_showdown(c, t):
    beam = ease(prog(t, 1.8, 2.0)) * (1 - prog(t, 3.3, 3.5))
    c.shake(8 if 0.3 <= t < 0.5 else (6 * beam if beam > 0 else (22 * (1 - prog(t, 3.5, 4.1)) if 3.5 <= t < 4.1 else 0)), t)
    c.halo = NIGHT_HALO
    rooftop_bg(c, beam * 0.4)
    # Pepper at the console (left)
    c.rect(70, GY - 110, 170, GY, fill=(70, 74, 86), outline=INK, w=4)
    press = 1.55 <= t < 1.9
    figure(c, 230, GY, "pepper", face=-1, eyes="wide" if t > 1.8 else "open", mouth="o" if t > 1.8 else "flat",
           pose=dict(fa=(lerp(30, 80, 1 if press else 0), lerp(20, 80, 1 if press else 0)), ba=(-10, -5)))
    c.circle(150, GY - 110, 10, fill=(255, 60, 60) if press else (140, 30, 30))
    # Iron Monger
    fall = ease_in(prog(t, 3.3, 3.6))
    if t < 3.6:
        mx = lerp(760, 560, ease(prog(t, 1.0, 1.6)))
        punch = ease(prog(t, 0.15, 0.32)) * (1 - ease(prog(t, 0.6, 0.9)))
        jitter = math.sin(t * 70) * 10 * beam
        figure(c, mx + jitter, GY + fall * 400, "monger", face=-1, s=1.55, reactor=True,
               pose=dict(fa=(lerp(30, 95, punch), lerp(20, 95, punch)), ba=(-15, -10), lean=lerp(0, 18, punch)))
    # Iron Man
    if t < 1.2:
        knock = ease_out(prog(t, 0.32, 0.6))
        x = lerp(380, 300, knock)
        blast = 0.8 <= t < 1.05
        pts = figure(c, x, GY, "mk3", face=1, visor=1.0, reactor=True, rot=-12 * knock * (1 - prog(t, 0.6, 0.8)),
                     pose=dict(fa=(90, 90) if t > 0.65 else (30, 20), ba=(-20, -10)))
        if blast:
            hx, hy = pts["fh"]
            k = 1 - prog(t, 0.8, 1.05)
            c.line([(hx + 10, hy), (700, hy - 60)], (200, 240, 255, int(220 * k)), 30 * k + 4)
            c.line([(hx + 10, hy), (700, hy - 60)], WHITE, 8)
    else:
        up = ease_out(prog(t, 1.2, 1.6))
        hover = 8 * math.sin(t * 6)
        pts = figure(c, lerp(300, 330, up), GY, "mk3", face=1, visor=1.0, reactor=True,
                     pose=dict(fa=(-20, -15), ba=(-30, -20), lift=lerp(0, 380, up) + hover))
        for k, n in enumerate(("ff", "bf", "fh", "bh")):
            fx, fy = pts[n]
            fl = 40 + 10 * math.sin(t * 60 + k)
            c.poly([(fx - 10, fy + 6), (fx + 10, fy + 6), (fx, fy + fl)], fill=(140, 210, 255, 220))
    # reactor beam
    if beam > 0:
        w = 150 * beam
        c.rect(540 - w, 0, 540 + w, GY, fill=(150, 220, 255, int(140 * beam)))
        c.rect(540 - w * 0.4, 0, 540 + w * 0.4, GY, fill=(240, 250, 255, int(220 * beam)))
        for k in range(4):
            seed = int(t * 20) * 10 + k
            bolt(c, 540, GY, 540 + random.Random(seed).uniform(-300, 300), 600 + k * 120, seed)
    if 3.5 <= t:
        explosion(c, 540, GY - 120, t - 3.5, size=380, seed=13)
        c.overlay(WHITE, 1 - prog(t, 3.5, 3.9))


showdown_snd = ([(0.0, sfx.night(5.0), 0.3), (0.0, sfx.step_heavy(), 0.9), (0.32, sfx.clang(200, 1.2, 0.5), 1.0),
                 (0.32, sfx.thud(), 0.8), (0.52, sfx.repulsor(), 0.8), (1.2, sfx.rocket(1.0), 0.4),
                 (1.6, sfx.click(), 1.0), (1.62, sfx.powerup(0.4), 0.5), (1.8, sfx.hum(1.6, 90), 0.6)] +
                [(ts, sfx.zap(0.35), 0.7) for ts in (1.8, 2.1, 2.4, 2.7, 3.0)] +
                [(3.5, sfx.boom(3.0, 1.3), 1.2), (3.5, sfx.bass_hit(), 0.6)])


# ------------------------------------------------------------------ 13. "I am Iron Man"
def s_end(c, t):
    press_bg(c)
    c.text(500, 660, "STARK INDUSTRIES", 54, (255, 255, 255, 50))
    figure(c, 470, GY, "tony", face=1, mouth="smile" if t > 1.6 else "flat", reactor=True,
           pose=dict(fa=(40, 70), ba=(-10, -5)))
    podium(c, 470)
    a = back_out(prog(t, 0.7, 0.95))
    if a > 0:
        speech(c, 520, 820, "Ich bin Iron Man.", size=int(50 * min(1, a)) + 1, tail=(-40, 150), alpha=min(1, a))
    flashes(c, t, 9, rate=3.0, t0=0.0, t1=1.0)
    flashes(c, t, 11, rate=9.0, t0=1.05, t1=3.2)


end_snd = (shutters([0.15, 0.6]) + [(0.0, sfx.room(3.2), 0.4), (1.0, sfx.bass_hit(), 0.9)] +
           shutters([1.05 + k / 9 for k in range(19)], 0.4))


# ------------------------------------------------------------------ film
FILM = Film("IRON MAN (2008)", "in 1 Minute", [
    Scene(3.0, s_title, None, title_snd, header=False, zoom=1.0, ty=GY),
    Scene(5.0, s_demo, "Afghanistan", demo_snd),
    Scene(4.5, s_ambush, "Hinterhalt", ambush_snd),
    Scene(5.5, s_cave, "Gefangen", cave_snd, halo=CAVE_HALO),
    Scene(6.5, s_build, [(0, "Er baut heimlich…"), (2.3, "…einen Arc-Reaktor"), (4.0, "…und eine Rüstung")],
          build_snd, halo=CAVE_HALO),
    Scene(5.6, s_escape, "Die Flucht", escape_snd),
    Scene(3.0, s_crash, "Gerettet", crash_snd),
    Scene(3.5, s_press, "Schluss mit Waffen!", press_snd, halo=(92, 120, 168)),
    Scene(6.2, s_workshop, [(0, "Malibu: Upgrade"), (3.2, "Mark III")], workshop_snd),
    Scene(2.6, s_gulmira, "Erster Einsatz", gulmira_snd, halo=NIGHT_HALO),
    Scene(2.0, s_villain, "Obadiah steckt dahinter", villain_snd, halo=(120, 52, 52)),
    Scene(4.5, s_heart, "Verrat", heart_snd),
    Scene(5.0, s_showdown, "Showdown", showdown_snd),
    Scene(3.2, s_end, None, end_snd, halo=(92, 120, 168)),
], header_fn=header, caption_fn=caption)


if __name__ == "__main__":
    if "--sheet" in sys.argv:
        ts = [float(a) for a in sys.argv[sys.argv.index("--sheet") + 1:]] or \
             [st + sc.dur * k for st, sc in zip(FILM.starts, FILM.scenes) for k in (0.3, 0.75)]
        print(stills(FILM, ts, "output/preview", cols=7, scale=0.2))
    else:
        print(f"duration {FILM.dur:.1f}s")
        render(FILM, "output/iron_man_2008_in_1_minute.mp4")
