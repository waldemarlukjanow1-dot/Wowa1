"""Drawing helpers: supersampled canvas, easing, stick figures, common effects.

All coordinates are logical 1080x1920 (TikTok portrait). The canvas renders at
SS x resolution and is reduced at the end for smooth (anti-aliased) lines.
"""
import math
import random
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
SS = 2
FPS = 30

# TikTok safe zone (logical px). Keep text/important action inside.
SAFE_TOP = 190      # "Following | For You" bar
SAFE_BOTTOM = 1480  # caption / music ticker starts below this
SAFE_LEFT = 60
SAFE_RIGHT = 930    # like / comment / share column on the right

INK = (24, 24, 28)
WHITE = (255, 255, 255)

FONT_DIR = "/usr/share/fonts/opentype/inter/"


@lru_cache(maxsize=64)
def font(size, weight="Black"):
    return ImageFont.truetype(FONT_DIR + f"Inter-{weight}.otf", int(size * SS))


# ---------------------------------------------------------------- easing
def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def prog(t, a, b):
    """0..1 progress of t between a and b."""
    if b <= a:
        return 1.0 if t >= b else 0.0
    return clamp((t - a) / (b - a))


def ease(p):
    p = clamp(p)
    return p * p * (3 - 2 * p)


def ease_out(p):
    p = clamp(p)
    return 1 - (1 - p) ** 3


def ease_in(p):
    p = clamp(p)
    return p ** 3


def back_out(p):
    p = clamp(p)
    c = 1.9
    return 1 + (c + 1) * (p - 1) ** 3 + c * (p - 1) ** 2


def lerp(a, b, p):
    return a + (b - a) * p


def lerp_c(c0, c1, p):
    return tuple(int(round(lerp(a, b, p))) for a, b in zip(c0, c1))


def keys(t, frames):
    """Piecewise eased interpolation. frames = [(time, value_or_tuple), ...]."""
    if t <= frames[0][0]:
        return frames[0][1]
    for (t0, v0), (t1, v1) in zip(frames, frames[1:]):
        if t <= t1:
            p = ease(prog(t, t0, t1))
            if isinstance(v0, tuple):
                return tuple(lerp(a, b, p) for a, b in zip(v0, v1))
            return lerp(v0, v1, p)
    return frames[-1][1]


# ---------------------------------------------------------------- canvas
_bg_cache = {}


class Canvas:
    def __init__(self):
        self.img = Image.new("RGB", (W * SS, H * SS), (0, 0, 0))
        self.d = ImageDraw.Draw(self.img, "RGBA")
        self.ox = 0.0
        self.oy = 0.0
        self.halo = None  # outline colour behind figures on dark scenes
        self.zoom = 1.0   # stage camera zoom around (zx, zy)
        self.zx, self.zy = 500.0, 1330.0
        self.ty = 1330.0  # screen y where stage y == zy lands

    # coordinates -------------------------------------------------------
    def p(self, x, y):
        z = self.zoom
        return ((self.zx + (x + self.ox - self.zx) * z) * SS, (self.ty + (y + self.oy - self.zy) * z) * SS)

    def shake(self, amount, t):
        if amount <= 0:
            return
        self.ox = math.sin(t * 91.0) * amount + math.sin(t * 57.0) * amount * 0.5
        self.oy = math.cos(t * 77.0) * amount + math.sin(t * 43.0) * amount * 0.4

    def no_shake(self):
        self.ox = self.oy = 0.0

    # primitives --------------------------------------------------------
    def line(self, pts, col, w, cap=True):
        pp = [self.p(*q) for q in pts]
        w = w * self.zoom
        self.d.line(pp, fill=col, width=max(1, int(w * SS)), joint="curve")
        if cap:
            r = w * SS / 2
            for (x, y) in (pp[0], pp[-1]):
                self.d.ellipse((x - r, y - r, x + r, y + r), fill=col)

    def circle(self, x, y, r, fill=None, outline=None, w=0):
        X, Y = self.p(x, y)
        z = self.zoom
        R = r * SS * z
        self.d.ellipse((X - R, Y - R, X + R, Y + R), fill=fill, outline=outline,
                       width=int(w * SS * z) if outline else 0)

    def ellipse(self, x, y, rx, ry, fill=None, outline=None, w=0):
        X, Y = self.p(x, y)
        z = self.zoom * SS
        self.d.ellipse((X - rx * z, Y - ry * z, X + rx * z, Y + ry * z), fill=fill,
                       outline=outline, width=int(w * z) if outline else 0)

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, w=0, r=0):
        a = self.p(x0, y0)
        b = self.p(x1, y1)
        box = (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
        z = self.zoom * SS
        if r:
            self.d.rounded_rectangle(box, radius=r * z, fill=fill, outline=outline,
                                     width=int(w * z) if outline else 0)
        else:
            self.d.rectangle(box, fill=fill, outline=outline, width=int(w * z) if outline else 0)

    def poly(self, pts, fill=None, outline=None, w=0):
        pp = [self.p(*q) for q in pts]
        self.d.polygon(pp, fill=fill)
        if outline and w:
            self.line(pts + [pts[0]], outline, w, cap=False)

    def arc(self, x, y, r, a0, a1, col, w):
        X, Y = self.p(x, y)
        R = r * SS * self.zoom
        self.d.arc((X - R, Y - R, X + R, Y + R), a0, a1, fill=col, width=int(w * SS * self.zoom))

    def pie(self, x, y, r, a0, a1, fill):
        X, Y = self.p(x, y)
        R = r * SS * self.zoom
        self.d.pieslice((X - R, Y - R, X + R, Y + R), a0, a1, fill=fill)

    def chord(self, x, y, r, a0, a1, fill):
        X, Y = self.p(x, y)
        R = r * SS * self.zoom
        self.d.chord((X - R, Y - R, X + R, Y + R), a0, a1, fill=fill)

    def text(self, x, y, s, size, fill=WHITE, anchor="mm", stroke=0, stroke_fill=INK,
             weight="Black", shake=True):
        X, Y = self.p(x, y) if shake else (x * SS, y * SS)
        z = self.zoom if shake else 1.0
        self.d.text((X, Y), s, font=font(max(1, int(size * z)), weight), fill=fill, anchor=anchor,
                    stroke_width=int(stroke * SS * z), stroke_fill=stroke_fill)

    def text_w(self, s, size, weight="Black"):
        return self.d.textlength(s, font=font(size, weight)) / SS

    def fill(self, col):
        self.d.rectangle((0, 0, W * SS, H * SS), fill=col)

    def vgrad(self, y0, y1, c0, c1):
        """Vertical gradient band (cached as an image strip)."""
        y0 = self.ty + (y0 - self.zy) * self.zoom
        y1 = self.ty + (y1 - self.zy) * self.zoom
        key = (y0, y1, c0, c1)
        strip = _bg_cache.get(key)
        if strip is None:
            h = max(1, int((y1 - y0) * SS))
            strip = Image.new("RGB", (W * SS, h))
            dd = ImageDraw.Draw(strip)
            for i in range(h):
                dd.line([(0, i), (W * SS, i)], fill=lerp_c(c0, c1, i / max(1, h - 1)))
            _bg_cache[key] = strip
        self.img.paste(strip, (0, int(y0 * SS)))

    def overlay(self, col, alpha):
        if alpha <= 0:
            return
        self.d.rectangle((0, 0, W * SS, H * SS), fill=(*col[:3], int(clamp(alpha) * 255)))

    def glow(self, x, y, r, col, strength=1.0, rings=7):
        for i in range(rings, 0, -1):
            k = i / rings
            a = int(50 * strength * (1 - k) + 6 * strength)
            self.circle(x, y, r * (0.35 + k), fill=(*col, min(255, a)))

    def layer(self):
        """Transparent canvas with the same transform, for wipes/reveals."""
        L = Canvas.__new__(Canvas)
        L.img = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
        L.d = ImageDraw.Draw(L.img, "RGBA")
        L.ox, L.oy, L.halo = self.ox, self.oy, self.halo
        L.zoom, L.zx, L.zy, L.ty = self.zoom, self.zx, self.zy, self.ty
        return L

    def paste(self, L, y0=0, y1=H):
        y0 = self.ty + (y0 - self.zy) * self.zoom
        y1 = self.ty + (y1 - self.zy) * self.zoom
        box = (0, int(max(0, y0) * SS), W * SS, int(min(H, y1) * SS))
        if box[3] <= box[1]:
            return
        reg = L.img.crop(box)
        self.img.paste(reg, box[:2], reg)

    def final(self):
        return self.img.reduce(SS)


# ---------------------------------------------------------------- figures
def _dir(a, face):
    r = math.radians(a)
    return (math.sin(r) * face, math.cos(r))


def _rot(pt, ang, cx, cy):
    if not ang:
        return pt
    r = math.radians(ang)
    x, y = pt[0] - cx, pt[1] - cy
    return (cx + x * math.cos(r) - y * math.sin(r), cy + x * math.sin(r) + y * math.cos(r))


STAND = dict(fa=(15, 10), ba=(-15, -10), fl=(10, 0), bl=(-10, 0), lean=0)

SUITS = {
    "mk1": dict(col=(128, 133, 140), dark=(70, 72, 78), w=26, accent=(160, 165, 170)),
    "mk2": dict(col=(200, 206, 214), dark=(110, 116, 124), w=20, accent=(230, 234, 240)),
    "mk3": dict(col=(196, 30, 40), dark=(110, 14, 20), w=20, accent=(236, 180, 58)),
    "monger": dict(col=(78, 84, 92), dark=(36, 38, 44), w=30, accent=(110, 116, 124)),
}


def figure(c, x, y, kind="plain", s=1.0, face=1, pose=None, rot=0, eyes="open",
           mouth="flat", shades=False, reactor=False, reactor_power=1.0, visor=0.0,
           head_tilt=0, alpha=255):
    """Draw a stick figure with feet anchored at (x, y). Returns key points.

    pose angles (deg): 0 = pointing down, 90 = forward (facing dir), 180 = up.
    fa/ba = front/back arm (upper, lower), fl/bl = legs (thigh, shin).
    visor: for suits 0 = face open, 1 = faceplate closed.
    """
    P = dict(STAND)
    if pose:
        P.update(pose)
    suit = SUITS.get(kind)
    big = kind in ("obadiah",)
    hr = 34 * s
    torso = 120 * s
    ua, la = 68 * s, 64 * s
    th, sh = 76 * s, 74 * s
    lift = P.get("lift", 0) * s

    def add(a, v, l):
        return (a[0] + v[0] * l, a[1] + v[1] * l)

    hip = (x, y - (th + sh) * 0.985 - lift)
    tv = (math.sin(math.radians(P["lean"])) * face, -math.cos(math.radians(P["lean"])))
    neck = add(hip, tv, torso)
    shoulder = add(hip, tv, torso * 0.9)
    head = add(neck, tv, hr + 6 * s)
    head = (head[0] + P.get("hdx", 0) * face * s, head[1] + P.get("hdy", 0) * s)

    def limb(base, ang):
        k = add(base, _dir(ang[0], face), ua if base is shoulder else th)
        e = add(k, _dir(ang[1], face), la if base is shoulder else sh)
        return k, e

    fe, fh = limb(shoulder, P["fa"])
    be, bh = limb(shoulder, P["ba"])
    fk, ff = limb(hip, P["fl"])
    bk, bf = limb(hip, P["bl"])
    chest = add(hip, tv, torso * 0.72)

    pts = dict(hip=hip, neck=neck, shoulder=shoulder, head=head, fe=fe, fh=fh, be=be, bh=bh,
               fk=fk, ff=ff, bk=bk, bf=bf, chest=chest)
    if rot:
        pts = {k: _rot(v, rot, x, y) for k, v in pts.items()}
    pts["hr"] = hr

    ink = (*INK, alpha)
    if suit:
        w = suit["w"] * s
        col, dark = (*suit["col"], alpha), (*suit["dark"], alpha)
        acc = (*suit["accent"], alpha)

        def seg(a, b, cc=col, ww=w):
            if c.halo:
                c.line([a, b], c.halo, ww + 12 * s)
            c.line([a, b], dark, ww + 6 * s)
            c.line([a, b], cc, ww)

        seg(pts["shoulder"], pts["be"]); seg(pts["be"], pts["bh"], acc if kind == "mk3" else col)
        seg(pts["hip"], pts["bk"]); seg(pts["bk"], pts["bf"], acc if kind == "mk3" else col)
        seg(pts["hip"], pts["neck"], col, w * 1.7)
        if kind == "mk3":
            mid = ((pts["hip"][0] * 0.6 + pts["neck"][0] * 0.4), (pts["hip"][1] * 0.6 + pts["neck"][1] * 0.4))
            c.line([pts["hip"], mid], acc, w * 0.8)
        seg(pts["hip"], pts["fk"]); seg(pts["fk"], pts["ff"], acc if kind == "mk3" else col)
        seg(pts["shoulder"], pts["fe"]); seg(pts["fe"], pts["fh"], acc if kind == "mk3" else col)
        # head
        hx, hy = pts["head"]
        if kind in ("mk1", "monger"):
            hw = hr * (1.05 if kind == "mk1" else 0.9)
            if c.halo:
                c.rect(hx - hw - 6, hy - hw - 6, hx + hw + 6, hy + hw + 6, fill=c.halo, r=10 * s)
            c.rect(hx - hw, hy - hw, hx + hw, hy + hw, fill=col, outline=dark, w=5 * s, r=8 * s)
            ex = hx + face * hw * 0.25
            eye_c = (180, 230, 255, alpha) if kind == "monger" else (40, 40, 44, alpha)
            c.rect(ex - hw * 0.55, hy - hw * 0.25, ex + hw * 0.55, hy - hw * 0.05, fill=eye_c)
            if kind == "monger":
                c.glow(ex, hy - hw * 0.15, hw * 0.7, (150, 220, 255), 0.6, rings=4)
        else:
            if c.halo:
                c.circle(hx, hy, hr + 6 * s, fill=c.halo)
            c.circle(hx, hy, hr, fill=col, outline=dark, w=4 * s)
            if visor > 0:
                # gold faceplate slides down from the top
                fp = (*SUITS["mk3"]["accent"], alpha) if kind == "mk3" else acc
                cx = hx + face * hr * 0.28
                top = hy - hr * 0.75
                bot = lerp(top, hy + hr * 0.8, visor)
                c.rect(cx - hr * 0.55, top, cx + hr * 0.55, bot, fill=fp, r=10 * s)
                if visor >= 0.99:
                    ey = hy - hr * 0.2
                    for dx in (-0.25, 0.25):
                        c.rect(cx + hr * dx - 9 * s, ey - 3.5 * s, cx + hr * dx + 9 * s, ey + 3.5 * s,
                               fill=(230, 250, 255, alpha))
                    c.glow(cx, ey, hr * 0.8, (170, 230, 255), 0.5, rings=4)
            else:
                _face(c, pts["head"], hr, face, eyes, mouth, s, alpha)
                if kind in ("mk2", "mk3"):
                    _tony_hair(c, pts["head"], hr, face, s, alpha)
        if reactor:
            arc_reactor(c, *pts["chest"], 11 * s * (1.4 if kind == "monger" else 1), reactor_power)
        return pts

    lw = (12 if big else 9) * s
    if c.halo:
        for a, b in (("shoulder", "be"), ("be", "bh"), ("hip", "bk"), ("bk", "bf"),
                     ("hip", "neck"), ("hip", "fk"), ("fk", "ff"), ("shoulder", "fe"), ("fe", "fh")):
            c.line([pts[a], pts[b]], c.halo, lw + 8 * s)
        c.circle(*pts["head"], hr + 7 * s, fill=c.halo)
    c.line([pts["shoulder"], pts["be"], pts["bh"]], ink, lw)
    c.line([pts["hip"], pts["bk"], pts["bf"]], ink, lw)
    if kind == "obadiah":
        # dark business suit
        sx, sy = pts["neck"]
        hx_, hy_ = pts["hip"]
        c.poly([(sx - 30 * s, sy + 4 * s), (sx + 30 * s, sy + 4 * s), (hx_ + 26 * s, hy_ + 8 * s),
                (hx_ - 26 * s, hy_ + 8 * s)], fill=(52, 54, 62, alpha))
        c.poly([(sx - 6 * s, sy + 6 * s), (sx + 6 * s, sy + 6 * s), (sx, sy + 46 * s)], fill=(235, 235, 235, alpha))
    elif kind == "pepper":
        sx, sy = pts["neck"]
        hx_, hy_ = pts["hip"]
        c.poly([(sx - 10 * s, sy + 6 * s), (sx + 10 * s, sy + 6 * s), (hx_ + 34 * s, hy_ + 34 * s),
                (hx_ - 34 * s, hy_ + 34 * s)], fill=(60, 110, 190, alpha))
    else:
        c.line([pts["hip"], pts["neck"]], ink, lw)
    c.line([pts["hip"], pts["fk"], pts["ff"]], ink, lw)
    _head(c, pts, kind, hr, face, eyes, mouth, s, shades, alpha)
    c.line([pts["shoulder"], pts["fe"], pts["fh"]], ink, lw)
    if reactor:
        arc_reactor(c, *pts["chest"], 9 * s, reactor_power)
    return pts


def _tony_hair(c, head, hr, face, s, alpha):
    hx, hy = head
    c.chord(hx, hy, hr + 2 * s, 180 + (10 if face > 0 else -10), 360 + (10 if face > 0 else -10),
            (40, 30, 26, alpha))


def _face(c, head, hr, face, eyes, mouth, s, alpha):
    hx, hy = head
    ex = hx + face * hr * 0.3
    ey = hy - hr * 0.08
    sp = hr * 0.32
    ink = (*INK, alpha)
    for dx in (-sp, sp):
        X = ex + dx
        if eyes == "closed":
            c.line([(X - 6 * s, ey), (X + 6 * s, ey)], ink, 3.5 * s)
        elif eyes == "wide":
            c.circle(X, ey, 8 * s, fill=(255, 255, 255, alpha), outline=ink, w=3 * s)
            c.circle(X + face * 2 * s, ey, 3.8 * s, fill=ink)
        elif eyes == "x":
            c.line([(X - 5 * s, ey - 5 * s), (X + 5 * s, ey + 5 * s)], ink, 3 * s)
            c.line([(X - 5 * s, ey + 5 * s), (X + 5 * s, ey - 5 * s)], ink, 3 * s)
        else:
            c.circle(X, ey, 4.6 * s, fill=ink)
        if eyes == "angry":
            c.line([(X - 8 * s, ey - 13 * s + (4 * s if dx * face > 0 else -2 * s) * 1),
                    (X + 8 * s, ey - 13 * s + (-2 * s if dx * face > 0 else 4 * s))], ink, 3.5 * s)
    my = hy + hr * 0.42
    mx = ex
    if mouth == "smile":
        c.arc(mx, my - 12 * s, 13 * s, 30, 150, ink, 3.5 * s)
    elif mouth == "grin":
        c.chord(mx, my - 6 * s, 13 * s, 0, 180, ink)
    elif mouth == "frown":
        c.arc(mx, my + 8 * s, 12 * s, 210, 330, ink, 3.5 * s)
    elif mouth == "o":
        c.circle(mx, my, 6 * s, fill=ink)
    elif mouth != "none":
        c.line([(mx - 9 * s, my), (mx + 9 * s, my)], ink, 3.5 * s)


def _head(c, pts, kind, hr, face, eyes, mouth, s, shades, alpha):
    hx, hy = pts["head"]
    ink = (*INK, alpha)
    if kind == "pepper":
        # long strawberry-blond hair behind head
        c.ellipse(hx - face * 6 * s, hy + 18 * s, hr * 1.15, hr * 1.45, fill=(232, 140, 62, alpha))
    c.circle(hx, hy, hr, fill=(255, 255, 255, alpha), outline=ink, w=6 * s)
    if kind == "thug":
        # head wrap: cloth over head and lower face, eye slot open
        cloth = (120, 52, 40, alpha)
        c.chord(hx, hy, hr - 2 * s, 175, 365, cloth)
        c.chord(hx, hy, hr - 2 * s, 20, 160, cloth)
        _face(c, pts["head"], hr, face, eyes, "none", s, alpha)
        c.circle(hx, hy, hr, outline=ink, w=6 * s)
        return
    _face(c, pts["head"], hr, face, eyes, mouth, s, alpha)
    if kind == "tony":
        _tony_hair(c, pts["head"], hr, face, s, alpha)
        # goatee
        gx = hx + face * hr * 0.3
        gy = hy + hr * 0.62
        c.poly([(gx - 11 * s, gy - 4 * s), (gx + 11 * s, gy - 4 * s), (gx + 3 * s, gy + 16 * s),
                (gx - 3 * s, gy + 16 * s)], fill=(40, 30, 26, alpha))
        c.line([(gx - 14 * s, gy - 10 * s), (gx + 14 * s, gy - 10 * s)], (40, 30, 26, alpha), 4 * s)
    elif kind == "yinsen":
        c.chord(hx, hy, hr + 1, 190, 350, (150, 150, 150, alpha))
        ex = hx + face * hr * 0.3
        ey = hy - hr * 0.08
        for dx in (-hr * 0.32, hr * 0.32):
            c.circle(ex + dx, ey, 10 * s, outline=ink, w=3 * s)
        c.line([(ex - hr * 0.32 + 10 * s, ey), (ex + hr * 0.32 - 10 * s, ey)], ink, 3 * s)
        c.chord(hx + face * 4 * s, hy + 4 * s, hr - 4 * s, 30, 150, (150, 150, 150, alpha))
        _face(c, pts["head"], hr, face, "none", mouth, s, alpha)
    elif kind == "obadiah":
        c.chord(hx + face * 2 * s, hy + 2 * s, hr - 3 * s, 15, 165, (205, 205, 205, alpha))
        mx = hx + face * hr * 0.3
        c.line([(mx - 9 * s, hy + hr * 0.38), (mx + 9 * s, hy + hr * 0.38)], ink, 3.5 * s)
    elif kind == "pepper":
        c.chord(hx, hy, hr + 2 * s, 185 - face * 15, 355 - face * 15, (232, 140, 62, alpha))
    elif kind == "soldier":
        c.chord(hx, hy, hr + 3 * s, 180, 360, (82, 98, 60, alpha))
        c.line([(hx, hy - 2 * s), (hx + face * (hr + 16 * s), hy - 2 * s)], (82, 98, 60, alpha), 6 * s)
    if shades:
        ex = hx + face * hr * 0.3
        ey = hy - hr * 0.08
        c.rect(ex - hr * 0.62, ey - 8 * s, ex + hr * 0.62, ey + 8 * s, fill=(20, 20, 24, alpha), r=6 * s)


# ---------------------------------------------------------------- effects
def arc_reactor(c, x, y, r, power=1.0):
    if power <= 0.02:
        c.circle(x, y, r, fill=(70, 74, 80), outline=(30, 30, 34), w=2)
        return
    c.glow(x, y, r * 3.2, (120, 210, 255), 0.9 * power, rings=6)
    c.circle(x, y, r, fill=lerp_c((70, 74, 80), (215, 245, 255), power), outline=(40, 120, 170), w=2)
    c.circle(x, y, r * 0.45, fill=(255, 255, 255, int(255 * power)))


def explosion(c, x, y, age, size=160, seed=1):
    """Cartoon explosion that starts at age=0 and fades by ~1.4 s."""
    if age < 0 or age > 1.6:
        return
    rnd = random.Random(seed)
    grow = ease_out(prog(age, 0, 0.28))
    fade = 1 - prog(age, 0.35, 1.5)
    # smoke
    for i in range(9):
        a = rnd.uniform(0, 6.28)
        d = rnd.uniform(0.3, 0.8) * size * (0.6 + age * 0.8)
        rr = size * rnd.uniform(0.35, 0.6) * (0.7 + age * 0.6)
        g = rnd.randint(70, 110)
        c.circle(x + math.cos(a) * d, y + math.sin(a) * d * 0.7 - age * 60, rr,
                 fill=(g, g, g, int(170 * fade)))
    core = 1 - prog(age, 0.1, 0.8)
    if core > 0:
        c.circle(x, y, size * grow * 1.0, fill=(255, 120, 30, int(240 * core)))
        c.circle(x, y, size * grow * 0.72, fill=(255, 200, 60, int(250 * core)))
        c.circle(x, y, size * grow * 0.42, fill=(255, 250, 220, int(255 * core)))
    # debris sparks
    for i in range(10):
        a = rnd.uniform(3.4, 6.0)
        sp = rnd.uniform(250, 520)
        dx = math.cos(a) * sp * age
        dy = math.sin(a) * sp * age + 500 * age * age
        if age < 0.9:
            c.circle(x + dx, y + dy, 5, fill=(255, 180, 60, int(255 * (1 - age / 0.9))))


def muzzle(c, x, y, face, size=26):
    pts = []
    for i in range(10):
        a = math.radians(i * 36)
        r = size if i % 2 == 0 else size * 0.45
        pts.append((x + math.cos(a) * r * 1.5 * face + face * size * 0.6, y + math.sin(a) * r))
    c.poly(pts, fill=(255, 220, 90, 240))
    c.circle(x + face * size * 0.6, y, size * 0.35, fill=(255, 255, 230))


def bullet(c, x, y, face, length=46):
    c.line([(x, y), (x - face * length, y)], (255, 230, 120, 230), 5)


def sparks(c, x, y, t, n=10, spread=110, seed=0, col=(255, 210, 90)):
    if t < 0:
        return
    rnd = random.Random(seed)
    for i in range(n):
        a = rnd.uniform(-3.0, -0.1)
        sp = rnd.uniform(0.5, 1.0) * spread
        life = rnd.uniform(0.25, 0.45)
        if t > life:
            continue
        k = t / life
        x1 = x + math.cos(a) * sp * k
        y1 = y + math.sin(a) * sp * k + 120 * k * k
        x0 = x + math.cos(a) * sp * max(0, k - 0.25)
        y0 = y + math.sin(a) * sp * max(0, k - 0.25)
        c.line([(x0, y0), (x1, y1)], (*col, int(255 * (1 - k))), 4)


def smoke_puff(c, x, y, age, size=40, seed=0, col=(235, 235, 235)):
    if age < 0 or age > 1.2:
        return
    rnd = random.Random(seed)
    k = age / 1.2
    for i in range(5):
        dx = rnd.uniform(-1, 1) * size * (0.5 + k)
        dy = rnd.uniform(-1, 0.4) * size * (0.5 + k)
        c.circle(x + dx, y + dy - k * 30, size * (0.5 + k * 0.8), fill=(*col, int(200 * (1 - k))))


def flash(c, t, t0, dur=0.35, col=(255, 255, 255)):
    if t0 <= t <= t0 + dur:
        c.overlay(col, 1 - prog(t, t0, t0 + dur))


def bolt(c, x0, y0, x1, y1, seed, col=(170, 230, 255), w=6, segs=9):
    rnd = random.Random(seed)
    pts = [(x0, y0)]
    for i in range(1, segs):
        k = i / segs
        pts.append((lerp(x0, x1, k) + rnd.uniform(-28, 28), lerp(y0, y1, k) + rnd.uniform(-18, 18)))
    pts.append((x1, y1))
    c.line(pts, (*col, 110), w * 3, cap=False)
    c.line(pts, (240, 250, 255), w, cap=False)


def speech(c, x, y, txt, size=46, tail=(0, 60), alpha=1.0):
    """Speech bubble centered at (x, y). tail = offset of the pointer tip."""
    if alpha <= 0:
        return
    w = c.text_w(txt, size) + 56
    h = size + 44
    a = int(255 * alpha)
    tx, ty = x + tail[0], y + tail[1]
    c.poly([(x - 30, y + h / 2 - 4), (x + 10, y + h / 2 - 4), (tx, ty)], fill=(255, 255, 255, a),
           outline=(*INK, a), w=5)
    c.rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, fill=(255, 255, 255, a), outline=(*INK, a), w=5, r=28)
    c.poly([(x - 26, y + h / 2 - 8), (x + 6, y + h / 2 - 8), (tx, ty - 8)], fill=(255, 255, 255, a))
    c.text(x, y + 2, txt, size, fill=(*INK, a))
