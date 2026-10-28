"""Timeline + parallel renderer: scenes -> frames -> ffmpeg (H.264 + AAC)."""
import os
import subprocess
import sys
from multiprocessing import Pool

from . import gfx
from .gfx import FPS, H, W, Canvas
from .sfx import Mixer

_film = None


class Scene:
    def __init__(self, dur, draw, caption=None, sounds=None, header=True, halo=None, zoom=1.2, ty=1390):
        self.dur = dur
        self.draw = draw          # draw(c, t)
        self.caption = caption    # str or [(t_from, str), ...]
        self.sounds = sounds or []  # [(t, signal, gain), ...]
        self.header = header
        self.halo = halo
        self.zoom = zoom
        self.ty = ty


class Film:
    def __init__(self, title, subtitle, scenes, header_fn=None, caption_fn=None):
        self.title = title
        self.subtitle = subtitle
        self.scenes = scenes
        self.header_fn = header_fn
        self.caption_fn = caption_fn
        self.starts = []
        acc = 0.0
        for s in scenes:
            self.starts.append(acc)
            acc += s.dur
        self.dur = acc

    def frame(self, i):
        t = i / FPS
        idx = 0
        for k, st in enumerate(self.starts):
            if t >= st:
                idx = k
        sc = self.scenes[idx]
        lt = t - self.starts[idx]
        c = Canvas()
        c.halo = sc.halo
        c.zoom = sc.zoom
        c.ty = sc.ty
        sc.draw(c, lt)
        c.no_shake()
        c.halo = None
        c.zoom = 1.0
        c.ty = c.zy
        if sc.header and self.header_fn:
            self.header_fn(c, t)
        cap = sc.caption
        if isinstance(cap, list):
            cur = None
            for ts, s in cap:
                if lt >= ts:
                    cur = (ts, s)
            cap = cur
        elif cap:
            cap = (0, cap)
        if cap and cap[1] and self.caption_fn:
            self.caption_fn(c, cap[1], lt - cap[0])
        return c.final()

    def audio(self, path):
        m = Mixer(self.dur)
        for st, sc in zip(self.starts, self.scenes):
            for (ts, sig, gain) in sc.sounds:
                m.add(st + ts, sig, gain)
        m.write(path)


def _init(film):
    global _film
    _film = film


def _render(i):
    return _film.frame(i).tobytes()


def render(film, out_path, workers=None, only=None):
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    wav = out_path.rsplit(".", 1)[0] + ".wav"
    film.audio(wav)
    n = int(round(film.dur * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
           "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
           "-profile:v", "high", "-movflags", "+faststart",
           "-c:a", "aac", "-b:a", "192k", "-shortest", out_path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    frames = range(n) if only is None else only
    with Pool(workers or os.cpu_count(), initializer=_init, initargs=(film,)) as pool:
        for k, data in enumerate(pool.imap(_render, frames, chunksize=4)):
            proc.stdin.write(data)
            if k % 60 == 0:
                print(f"\r  frame {k}/{n}", end="", file=sys.stderr, flush=True)
    proc.stdin.close()
    proc.wait()
    print(f"\r  done: {out_path}            ", file=sys.stderr)
    os.remove(wav)


def stills(film, times, out_dir, cols=4, scale=0.25):
    """Contact sheet for quick review."""
    from PIL import Image
    os.makedirs(out_dir, exist_ok=True)
    w, h = int(W * scale), int(H * scale)
    rows = (len(times) + cols - 1) // cols
    sheet = Image.new("RGB", (w * cols, h * rows), (0, 0, 0))
    for k, t in enumerate(times):
        im = film.frame(int(t * FPS))
        sheet.paste(im.resize((w, h)), ((k % cols) * w, (k // cols) * h))
    path = os.path.join(out_dir, "sheet.png")
    sheet.save(path)
    return path
