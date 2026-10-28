"""Procedural sound effects (no voices) and a simple timeline mixer."""
import wave

import numpy as np

SR = 44100
_rng = np.random.default_rng(7)


def _n(d):
    return int(SR * d)


def tt(d):
    return np.arange(_n(d)) / SR


def noise(d):
    return _rng.uniform(-1, 1, _n(d))


def band(x, lo=0.0, hi=None, order=2):
    """FFT band filter with soft (Butterworth-like) slopes."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = np.ones_like(f)
    if hi:
        g *= 1 / np.sqrt(1 + (f / hi) ** (2 * order))
    if lo:
        g *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** (2 * order))
    return np.fft.irfft(X * g, len(x))


def env(d, a=0.005, decay=0.2, hold=0.0):
    t = tt(d)
    e = np.minimum(1, t / max(a, 1e-4))
    rel = np.clip(t - a - hold, 0, None)
    return e * np.exp(-rel / decay)


def norm(x, peak=1.0):
    m = np.max(np.abs(x)) or 1
    return x / m * peak


def chirp(f0, f1, d, curve=1.0):
    t = tt(d)
    k = (t / d) ** curve
    f = f0 + (f1 - f0) * k
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def fade(x, fi=0.01, fo=0.05):
    n = len(x)
    a, b = min(n, _n(fi)), min(n, _n(fo))
    x = x.copy()
    if a:
        x[:a] *= np.linspace(0, 1, a)
    if b:
        x[-b:] *= np.linspace(1, 0, b)
    return x


def echo(x, delay=0.18, fb=0.4, n=4):
    out = np.zeros(len(x) + _n(delay) * n)
    for i in range(n + 1):
        o = _n(delay) * i
        out[o:o + len(x)] += x * (fb ** i)
    return out


# ------------------------------------------------------------------ library
def boom(d=2.2, size=1.0):
    n = band(noise(d), hi=180 * size + 60) * env(d, 0.004, 0.5 * size)
    sub = chirp(70, 28, d, 0.5) * env(d, 0.002, 0.45 * size)
    crack = band(noise(d), lo=800) * env(d, 0.001, 0.05)
    return norm(norm(n) * 1.0 + sub * 0.9 + norm(crack) * 0.35)


def bass_hit(d=1.6):
    return norm(chirp(90, 38, d, 0.4) * env(d, 0.002, 0.35) + band(noise(d), hi=300) * env(d, 0.001, 0.04) * 0.6)


def whoosh(d=0.6, up=True):
    x = noise(d)
    t = tt(d)
    out = np.zeros_like(x)
    # sweep by blending a few bands
    bands = [(200, 600), (500, 1500), (1200, 3500), (2500, 7000)]
    for i, (lo, hi) in enumerate(bands):
        k = i / (len(bands) - 1)
        centre = (t / d) if up else 1 - t / d
        w = np.exp(-((centre - k) ** 2) / 0.08)
        out += band(x, lo, hi) * w
    e = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 1.5
    return norm(out * e)


def gunshot():
    d = 0.5
    return norm(band(noise(d), 300, 6000) * env(d, 0.0005, 0.035) + band(noise(d), hi=200) * env(d, 0.001, 0.09) * 1.5)


def beep(f=1800, d=0.09):
    return fade(np.sin(2 * np.pi * f * tt(d)) * 0.8, 0.003, 0.01)


def ringing(d=2.5):
    t = tt(d)
    return np.sin(2 * np.pi * 3900 * t) * np.exp(-t / (d * 0.5)) * np.minimum(1, t / 0.05) * 0.35


def heartbeat():
    d = 0.7
    one = np.sin(2 * np.pi * 52 * tt(0.18)) * env(0.18, 0.004, 0.05)
    out = np.zeros(_n(d))
    out[:len(one)] += one
    o = _n(0.22)
    out[o:o + len(one)] += one * 0.7
    return norm(band(out, hi=200))


def drip():
    d = 0.25
    x = chirp(1200, 2600, d, 0.3) * env(d, 0.001, 0.03)
    return norm(echo(x, 0.13, 0.35, 5)) * 0.5


def clang(f=520, d=1.0, bright=1.0):
    t = tt(d)
    parts = [(1, 1.0), (2.76, 0.6), (5.4, 0.4 * bright), (8.93, 0.25 * bright), (1.5, 0.3)]
    x = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * (3 + r * 1.5)) for r, a in parts)
    hit = band(noise(d), lo=1500) * env(d, 0.0005, 0.01)
    return norm(x + hit * 0.8)


def zap(d=0.4):
    t = tt(d)
    sq = np.sign(np.sin(2 * np.pi * 120 * t)) * 0.4
    crack = band(noise(d), lo=2000) * (_rng.uniform(0, 1, len(t)) > 0.92)
    return norm((sq + crack * 2) * env(d, 0.003, d * 0.5))


def hum(d=2.0, f=60):
    t = tt(d)
    x = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2 * t) + 0.25 * np.sin(2 * np.pi * f * 3 * t)
    return fade(norm(x) * 0.6, 0.15, 0.3)


def powerup(d=1.2):
    x = chirp(180, 1400, d, 1.6) * 0.6 + chirp(360, 2800, d, 1.6) * 0.25
    return fade(x * np.minimum(1, tt(d) / d * 1.4), 0.02, 0.15)


def ping():
    d = 0.35
    return norm(chirp(4200, 2400, d, 0.5) * env(d, 0.001, 0.08)) * 0.6


def step_heavy():
    d = 0.5
    return norm(band(noise(d), hi=140) * env(d, 0.002, 0.08) * 1.2 + clang(160, d, 0.3) * 0.35)


def flame(d=1.0):
    x = band(noise(d), 80, 1400)
    flick = 0.7 + 0.3 * np.sin(2 * np.pi * 9 * tt(d)) * _rng.uniform(0.6, 1, 1)
    return fade(norm(x * flick), 0.05, 0.25)


def rocket(d=1.5):
    x = band(noise(d), 40, 2500)
    return fade(norm(x), 0.08, 0.5)


def thud():
    d = 0.6
    return norm(band(noise(d), hi=160) * env(d, 0.002, 0.12) + chirp(90, 40, d) * env(d, 0.001, 0.12))


def heli(d=3.0, rate=11.0):
    t = tt(d)
    chop = (0.5 + 0.5 * np.sin(2 * np.pi * rate * t)) ** 6
    x = band(noise(d), 50, 400) * chop
    return fade(norm(x), 0.6, 0.6)


def shutter():
    d = 0.18
    c1 = band(noise(d), 1500, 8000) * env(d, 0.0005, 0.008)
    out = c1.copy()
    o = _n(0.07)
    out[o:] += c1[:-o] * 0.8
    return norm(out) * 0.7


def repulsor():
    d = 0.7
    whine = chirp(500, 2600, 0.3, 1.5) * 0.5
    blast = band(noise(0.4), 200, 5000) * env(0.4, 0.002, 0.1)
    out = np.zeros(_n(d))
    out[:len(whine)] += whine * np.linspace(0.2, 1, len(whine))
    o = _n(0.28)
    out[o:o + len(blast)] += norm(blast) + chirp(160, 60, 0.4) * env(0.4, 0.001, 0.1)
    return norm(out)


def servo(d=0.25, f=700):
    t = tt(d)
    x = np.sign(np.sin(2 * np.pi * (f + 300 * t / d) * t)) * 0.25 + band(noise(d), 1000, 4000) * 0.15
    return fade(x, 0.01, 0.04)


def click():
    d = 0.06
    return norm(band(noise(d), 2000, 9000) * env(d, 0.0003, 0.006)) * 0.6


def extinguisher(d=0.9):
    return fade(norm(band(noise(d), 1500, 9000)) * 0.6, 0.02, 0.2)


def wind(d):
    t = tt(d)
    x = band(noise(d), 100, 900)
    m = 0.6 + 0.4 * np.sin(2 * np.pi * 0.35 * t) * np.sin(2 * np.pi * 0.13 * t + 1)
    return fade(norm(x * m) * 0.5, 0.4, 0.4)


def cave(d):
    t = tt(d)
    drone = band(noise(d), 30, 150) * 0.6 + np.sin(2 * np.pi * 55 * t) * 0.08
    return fade(norm(drone) * 0.5, 0.3, 0.3)


def room(d, f=50):
    return fade(norm(hum(d, f) * 0.3 + band(noise(d), 60, 300) * 0.4) * 0.4, 0.2, 0.2)


def night(d):
    t = tt(d)
    cr = np.sin(2 * np.pi * 4300 * t) * ((np.sin(2 * np.pi * 14 * t) > 0.6) * (np.sin(2 * np.pi * 0.7 * t) > 0))
    return fade(norm(band(noise(d), 80, 500)) * 0.35 + cr * 0.05, 0.3, 0.3)


# ------------------------------------------------------------------ mixer
class Mixer:
    def __init__(self, dur):
        self.buf = np.zeros(_n(dur) + SR * 4)
        self.dur = dur

    def add(self, t, sig, gain=1.0):
        o = max(0, _n(t))
        n = min(len(sig), len(self.buf) - o)
        if n > 0:
            self.buf[o:o + n] += sig[:n] * gain

    def write(self, path):
        x = self.buf[:_n(self.dur)]
        # gentle soft-clip limiter
        x = np.tanh(x * 1.1) * 0.92
        x = x / max(1e-6, np.max(np.abs(x))) * 0.89
        data = (np.stack([x, x], 1) * 32767).astype(np.int16)
        with wave.open(path, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(data.tobytes())
