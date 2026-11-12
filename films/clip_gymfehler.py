"""TikTok edit of an uploaded talking-character video ("5 Gym-Fehler"): 9:16 reframe, punch-in zooms,
word-by-word subtitles, a progress tracker, animated illustration cards, STOPP moment, CTA - plus SFX.

Usage: python3 -m films.clip_gymfehler SOURCE.mp4 WORDS.json OUT.mp4
(WORDS.json = faster-whisper word timestamps: {"segments": [{"words": [{"w","s","e"}, ...]}, ...]})
"""
import json
import math
import random
import subprocess
import sys
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw

from engine import sfx
from engine.gfx import FPS as _FPS, H, SS, W, Canvas, back_out, ease, ease_out, lerp, prog
from films.illusions import ding

SRC_W, SRC_H, FPS = 768, 1152, 25
BASE = (60.0, 0.0, 648.0, 1152.0)            # 9:16 crop of the 2:3 source
FACE = (384.0, 240.0)                         # zoom focus (source px)
RED, YEL, WHITE, INK = (232, 38, 52), (255, 214, 0), (255, 255, 255), (16, 16, 20)
GREEN = (50, 200, 100)

ERRORS = [8.86, 17.96, 25.32, 33.58, 44.12]   # "Fehler 1..5"
STOPP = 39.74
CTA = 58.84
SHARE = 64.10
END = 67.88

PUNCH = [(7.62, 0.14)] + [(t, 0.12) for t in ERRORS] + [(42.28, 0.1), (55.72, 0.08)]


# ------------------------------------------------------------------ camera
def zoom_at(t):
    z = 1.0 + 0.05 * (t % 9.0) / 9.0                       # slow drift inside each beat
    for t0, amp in PUNCH:
        if t0 <= t < t0 + 1.2:
            z += amp * ease_out(prog(t, t0, t0 + 0.12)) * (1 - ease(prog(t, t0 + 0.5, t0 + 1.2)))
    if STOPP <= t < STOPP + 1.6:
        z += 0.32 * ease_out(prog(t, STOPP, STOPP + 0.1)) * (1 - ease(prog(t, STOPP + 0.9, STOPP + 1.6)))
    if t >= CTA:
        z = lerp(z, 1.0, ease(prog(t, CTA, CTA + 0.5)))
    return z


def shake_at(t):
    if STOPP <= t < STOPP + 0.6:
        k = 1 - prog(t, STOPP, STOPP + 0.6)
        return math.sin(t * 90) * 14 * k, math.cos(t * 70) * 10 * k
    return 0.0, 0.0


def crop_box(t):
    z = zoom_at(t)
    x0, y0, w, h = BASE
    fx, fy = FACE
    sx, sy = shake_at(t)
    cx, cy = fx - (fx - x0) / z + sx, fy - (fy - y0) / z + sy
    return (cx, cy, cx + w / z, cy + h / z)


# ------------------------------------------------------------------ subtitles
def chunks(words, max_words=3, max_chars=16):
    out, cur = [], []
    for w in words:
        cur.append(w)
        txt = " ".join(x["w"].strip() for x in cur)
        if len(cur) >= max_words or len(txt) >= max_chars or w["w"].strip()[-1:] in ".,!?":
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    res = []
    for k, ch in enumerate(out):
        start = ch[0]["s"]
        nxt = out[k + 1][0]["s"] if k + 1 < len(out) else END
        res.append((start, min(nxt, ch[-1]["e"] + 0.5), ch))
    return res


def draw_subs(c, t, subs):
    for s, e, ch in subs:
        if not (s <= t < e):
            continue
        size = 70
        texts = [w["w"].strip().upper() for w in ch]
        widths = [c.text_w(x, size * 1.1) for x in texts]
        gap = 24
        total = sum(widths) + gap * (len(texts) - 1)
        if total > 860:                                    # shrink long lines to stay on screen
            k = 860 / total
            size, widths, gap = size * k, [w_ * k for w_ in widths], gap * k
            total = 860
        x = 520 - total / 2
        pop = back_out(prog(t, s, s + 0.12))
        for w, tw, txt in zip(ch, widths, texts):
            active = w["s"] <= t < max(w["e"], w["s"] + 0.15)
            col = YEL if active else WHITE
            sz = int(size * (1.1 if active else 1.0) * (0.85 + 0.15 * pop))
            c.text(x + tw / 2, 1215, txt, sz, col, stroke=9, stroke_fill=INK, shake=False)
            x += tw + gap


# ------------------------------------------------------------------ overlays
CARD = (712, 236, 1040, 576)


def card(c, t, t0, t1):
    """White card top-right; returns (alpha, x-offset) or None."""
    if not (t0 <= t < t1):
        return None
    a = ease_out(prog(t, t0, t0 + 0.25)) * (1 - ease(prog(t, t1 - 0.25, t1)))
    dx = (1 - ease_out(prog(t, t0, t0 + 0.25))) * 360
    x0, y0, x1, y1 = CARD
    c.rect(x0 + dx + 8, y0 + 10, x1 + dx + 8, y1 + 10, fill=(0, 0, 0, int(90 * a)), r=30)
    c.rect(x0 + dx, y0, x1 + dx, y1, fill=(255, 255, 255, int(245 * a)), r=30)
    return a, dx


def card_title(c, a, dx, txt, col=INK):
    x0, y0, x1, y1 = CARD
    c.text((x0 + x1) / 2 + dx, y1 - 42, txt, 36, (*col, int(255 * a)))


def cx_card(dx):
    return (CARD[0] + CARD[2]) / 2 + dx


def ov_legday(c, t):
    r = card(c, t, 10.2, 14.3)
    if r:
        a, dx = r
        x = CARD[0] + 40 + dx
        for k, (txt, ok) in enumerate((("Brust", True), ("Arme", True), ("Beine", False))):
            y = CARD[1] + 60 + k * 74
            p = ease_out(prog(t, 10.4 + k * 0.6, 10.7 + k * 0.6))
            if k == 2:
                p = ease_out(prog(t, 12.8, 13.1))
            c.text(x + 80, y, txt, 46, (*INK, int(255 * a * p)), anchor="lm")
            col = GREEN if ok else RED
            c.circle(x + 30, y, 26, fill=(*col, int(255 * a * p)))
            c.text(x + 30, y + 2, "✓" if ok else "X", 34, (255, 255, 255, int(255 * a * p)), weight="Bold")
        card_title(c, a, dx, "Leg Day? NIE.", RED)
    r = card(c, t, 14.3, 17.9)
    if r:
        a, dx = r
        x, y = cx_card(dx), CARD[1] + 120
        c.glow(x, y, 100, (255, 230, 120), 0.8 * a)
        c.circle(x, y, 72, fill=(255, 225, 90, int(255 * a)))
        c.rect(x - 34, y + 62, x + 34, y + 100, fill=(150, 150, 160, int(255 * a)), r=6)
        for sx in (-1, 1):                                   # matchstick legs
            c.line([(x + sx * 18, y + 100), (x + sx * 24, y + 225)], (214, 170, 110, int(255 * a)), 9)
            c.circle(x + sx * 24, y + 228, 10, fill=(*RED, int(255 * a)))
        card_title(c, a, dx, "Glühbirne-Look")


def ov_weight(c, t):
    r = card(c, t, 19.1, 25.0)
    if r:
        a, dx = r
        x, y = cx_card(dx), CARD[1] + 135
        ang = math.radians(16 * math.sin(t * 7))
        ux, uy = math.cos(ang), math.sin(ang)
        c.line([(x - ux * 135, y - uy * 135), (x + ux * 135, y + uy * 135)], (80, 80, 90, int(255 * a)), 12)
        for s_ in (-1, 1):
            px, py = x + s_ * ux * 105, y + s_ * uy * 105
            c.ellipse(px, py, 26, 74, fill=(30, 30, 36, int(255 * a)))
        if int(t * 4) % 2 == 0 and t > 21.1:
            c.poly([(x, y - 118), (x - 34, y - 62), (x + 34, y - 62)], fill=(*YEL, int(255 * a)))
            c.text(x, y - 80, "!", 40, (*INK, int(255 * a)))
        card_title(c, a, dx, "ZU SCHWER", RED)


def ov_plan(c, t):
    r = card(c, t, 26.7, 32.7)
    if r:
        a, dx = r
        rnd = random.Random(int(t * 6))
        names = ["Brust", "Bauch", "Beine", "Cardio", "Arme", "Yoga?", "Rücken", "???", "Pause"]
        for k in range(6):
            i, j = k % 2, k // 2
            x = CARD[0] + 90 + i * 150 + dx
            y = CARD[1] + 60 + j * 74
            c.rect(x - 66, y - 28, x + 66, y + 28, fill=(235, 238, 245, int(255 * a)), r=10)
            c.text(x, y + 1, rnd.choice(names), 30, (*INK, int(255 * a)))
        card_title(c, a, dx, "KEIN PLAN", RED)


def ov_banana(c, t):
    r = card(c, t, 34.6, 39.6)
    if r:
        a, dx = r
        x, y = cx_card(dx), CARD[1] + 150
        c.arc(x, y - 90, 130, 40, 140, (*YEL, int(255 * a)), 46)
        c.arc(x, y - 90, 130, 40, 140, (220, 180, 0, int(255 * a)), 8)
        for ang in (40, 140):
            px = x + math.cos(math.radians(ang)) * 130
            py = y - 90 + math.sin(math.radians(ang)) * 130
            c.circle(px, py, 12, fill=(110, 80, 30, int(255 * a)))
        if t > 37.0:
            k = ease_out(prog(t, 37.0, 37.3))
            c.line([(x - 90 * k, y - 60), (x + 90 * k, y + 60)], (*RED, int(200 * a)), 9)
            c.line([(x + 90 * k, y - 60), (x - 90 * k, y + 60)], (*RED, int(200 * a)), 9)
        card_title(c, a, dx, "ZU WENIG ESSEN", RED)


def ov_quit(c, t):
    r = card(c, t, 45.5, 50.1)
    if r:
        a, dx = r
        for k in range(3):
            x0 = CARD[0] + 40 + dx
            y = CARD[1] + 60 + k * 70
            p = ease(prog(t, 45.7 + k * 0.6, 46.2 + k * 0.6))
            c.text(x0, y, f"W{k + 1}", 34, (*INK, int(255 * a)), anchor="lm")
            c.rect(x0 + 60, y - 16, x0 + 260, y + 16, fill=(230, 232, 238, int(255 * a)), r=8)
            c.rect(x0 + 60, y - 16, x0 + 60 + 200 * p, y + 16, fill=(*GREEN, int(255 * a)), r=8)
        if t > 48.4:
            k = back_out(prog(t, 48.4, 48.7))
            c.rect(cx_card(dx) - 140 * k, CARD[1] + 250 - 34, cx_card(dx) + 140 * k, CARD[1] + 250 + 34,
                   fill=(*RED, int(255 * a)), r=10)
            c.text(cx_card(dx), CARD[1] + 252, "AUFGEHÖRT", int(40 * k) + 1, (255, 255, 255, int(255 * a)))
    r = card(c, t, 53.8, 58.8)
    if r:
        a, dx = r
        x0, y0 = CARD[0] + 40 + dx, CARD[1] + 250
        c.line([(x0, CARD[1] + 40), (x0, y0), (x0 + 250, y0)], (*INK, int(255 * a)), 5, cap=False)
        p = ease(prog(t, 54.0, 57.0))
        pts = []
        for k in range(int(40 * p) + 2):
            u = k / 40
            pts.append((x0 + 250 * u, y0 - 190 * (u ** 2.4)))
        if len(pts) > 1:
            c.line(pts, (*GREEN, int(255 * a)), 9)
        card_title(c, a, dx, "DRANBLEIBEN!", GREEN)


def ov_tracker(c, t):
    if t < ERRORS[0] or t >= CTA:
        return
    n = sum(1 for e in ERRORS if t >= e)
    c.rect(36, 214, 330, 282, fill=(0, 0, 0, 150), r=34)
    c.text(118, 249, "FEHLER", 30, WHITE, shake=False)
    for k in range(5):
        x = 200 + k * 26
        on = k < n
        cur = k == n - 1
        r = 10 + (3 * math.sin(t * 8) if cur else 0)
        c.circle(x, 248, r, fill=RED if on else (90, 90, 100))


def ov_badges(c, t):
    for k, t0 in enumerate(ERRORS):
        if t0 <= t < t0 + 1.25:
            p = back_out(prog(t, t0, t0 + 0.2))
            a = 1 - prog(t, t0 + 1.0, t0 + 1.25)
            w, h = 470 * p, 150 * p
            c.rect(520 - w / 2, 860 - h / 2, 520 + w / 2, 860 + h / 2, fill=(*RED, int(250 * a)), r=30)
            c.text(520, 864, f"FEHLER #{k + 1}", int(86 * p) + 1, (255, 255, 255, int(255 * a)))


def ov_hook(c, t):
    if t < 3.8:
        a = 1 - prog(t, 3.4, 3.8)
        p = 0.75 + 0.25 * back_out(prog(t, 0.0, 0.3))      # fully readable on frame 0 (thumbnail)
        c.text(520, 800, "5 GYM-FEHLER", int(104 * p) + 1, (*YEL, int(255 * a)), stroke=10, stroke_fill=INK)
        c.text(520, 915, "die JEDER macht", int(70 * p) + 1, (255, 255, 255, int(255 * a)), stroke=9,
               stroke_fill=INK)


def ov_stopp(c, t):
    if STOPP <= t < STOPP + 0.35:
        c.overlay(RED, 0.45 * (1 - prog(t, STOPP, STOPP + 0.35)))
    if STOPP <= t < 40.5:
        p = back_out(prog(t, STOPP, STOPP + 0.15))
        c.text(520, 860, "STOPP!", int(190 * p) + 1, RED, stroke=12, stroke_fill=WHITE)
    if 40.44 <= t < 43.9:
        a = ease_out(prog(t, 40.44, 40.7)) * (1 - prog(t, 43.6, 43.9))
        pulse = 1 + 0.05 * math.sin(t * 10)
        w = 640 * pulse
        c.rect(520 - w / 2, 800, 520 + w / 2, 920, fill=(*INK, int(220 * a)), r=26)
        c.text(520, 862, "DER GRÖSSTE FEHLER", int(56 * pulse), (*YEL, int(255 * a)))


def ov_cta(c, t):
    if t < CTA:
        return
    a = ease_out(prog(t, CTA, CTA + 0.3))
    c.rect(80, 700, 960, 1010, fill=(0, 0, 0, int(170 * a)), r=36)
    c.text(520, 770, "Welchen Fehler machst DU?", 52, (255, 255, 255, int(255 * a)))
    for k in range(5):
        x = 240 + k * 140
        p = back_out(prog(t, CTA + 0.4 + k * 0.15, CTA + 0.6 + k * 0.15))
        bob = math.sin(t * 5 + k) * 6
        c.circle(x, 900 + bob, 52 * p + 1, fill=RED)
        c.text(x, 904 + bob, str(k + 1), int(60 * p) + 1, WHITE)
    if t >= SHARE:
        b = ease_out(prog(t, SHARE, SHARE + 0.3))
        c.rect(120, 1040, 900, 1130, fill=(*YEL, int(255 * b)), r=30)
        c.text(510, 1086, "Schick's deinem Gym-Partner!", 46, (*INK, int(255 * b)))
        k = ease_out(prog(t, SHARE + 0.3, SHARE + 0.8)) + 0.04 * math.sin(t * 9)
        x0, y0, x1, y1 = 840, 1150, lerp(840, 975, k), lerp(1150, 1470, k)
        c.line([(x0, y0), (x1, y1)], (*YEL, int(255 * b)), 16)
        ang = math.atan2(y1 - y0, x1 - x0)
        for s_ in (-1, 1):
            c.line([(x1, y1), (x1 - math.cos(ang + s_ * 0.5) * 50, y1 - math.sin(ang + s_ * 0.5) * 50)],
                   (*YEL, int(255 * b)), 16)


OVERLAYS = [ov_legday, ov_weight, ov_plan, ov_banana, ov_quit, ov_tracker, ov_badges, ov_hook, ov_stopp, ov_cta]

# ------------------------------------------------------------------ render
_subs = None


def _init(subs):
    global _subs
    _subs = subs


def render_frame(args):
    i, raw = args
    t = i / FPS
    src = Image.frombytes("RGB", (SRC_W, SRC_H), raw)
    big = src.resize((W * SS, H * SS), Image.BICUBIC, box=crop_box(t))
    c = Canvas.__new__(Canvas)
    c.img = big
    c.d = ImageDraw.Draw(big, "RGBA")
    c.ox = c.oy = 0.0
    c.halo = None
    c.zoom, c.zx, c.zy, c.ty = 1.0, 500.0, 1330.0, 1330.0
    for ov in OVERLAYS:
        ov(c, t)
    draw_subs(c, t, _subs)
    return c.final().tobytes()


def scratch():
    d = 0.45
    return sfx.norm(sfx.band(sfx.noise(d), 200, 3000) * np.abs(np.sin(2 * np.pi * sfx.tt(d) * (18 - 30 * sfx.tt(d))))
                    * sfx.env(d, 0.005, 0.2)) * 0.9


def build_audio(src, out):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", src, "-ac", "1", "-ar", str(sfx.SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    voice = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    mix = np.zeros(len(voice) + sfx.SR * 2)
    mix[:len(voice)] += voice * 1.0
    ev = [(0.0, sfx.bass_hit(), 0.35), (0.0, sfx.whoosh(0.4), 0.25)]
    ev += [(t, sfx.whoosh(0.35), 0.3) for t in ERRORS] + [(t + 0.05, sfx.bass_hit(), 0.22) for t in ERRORS]
    ev += [(t0, sfx.whoosh(0.3), 0.18) for t0 in (10.2, 14.3, 19.1, 26.7, 34.6, 45.5, 53.8)]
    ev += [(STOPP - 0.05, scratch(), 0.5), (STOPP, sfx.bass_hit(), 0.4), (36.3, sfx.zap(0.2), 0.15),
           (48.4, sfx.thud(), 0.3), (CTA, ding(), 0.3)] + [(CTA + 0.4 + k * 0.15, sfx.click(), 0.3) for k in range(5)]
    ev += [(SHARE, sfx.whoosh(0.4), 0.25)]
    for t0, sig, g in ev:
        o = int(t0 * sfx.SR)
        n = min(len(sig), len(mix) - o)
        mix[o:o + n] += sig[:n] * g
    mix = mix[:len(voice)]
    mix = mix / max(1e-6, np.max(np.abs(mix))) * 0.95
    data = (np.stack([mix, mix], 1) * 32767).astype(np.int16)
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sfx.SR)
        w.writeframes(data.tobytes())


def main(src, words_json, out, only=None):
    words = [w for s in json.load(open(words_json))["segments"] for w in s["words"]]
    subs = chunks(words)
    wav = out.rsplit(".", 1)[0] + "_audio.wav"
    build_audio(src, wav)
    dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags",
                            "+faststart", out], stdin=subprocess.PIPE)
    fsize = SRC_W * SRC_H * 3
    i = 0
    with Pool(initializer=_init, initargs=(subs,)) as pool:
        while True:
            batch = []
            for _ in range(48):
                raw = dec.stdout.read(fsize)
                if len(raw) < fsize:
                    break
                batch.append((i, raw))
                i += 1
            if not batch:
                break
            if only is not None:
                batch = [b for b in batch if b[0] in only]
            for data in pool.map(render_frame, batch):
                enc.stdin.write(data)
            print(f"\r  frame {i}", end="", file=sys.stderr, flush=True)
    enc.stdin.close()
    enc.wait()
    print(f"\n  done: {out}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
