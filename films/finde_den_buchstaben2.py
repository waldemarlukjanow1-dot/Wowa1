"""'Finde den Buchstaben' Teil 2 - 8 new, meaner letter walls.

Render:  python3 -m films.finde_den_buchstaben2
Preview: python3 -m films.finde_den_buchstaben2 --sheet
"""
import sys

from engine.render import render, stills
from films.finde_den_buchstaben import lv, make

LEVELS = [
    lv("Finde das Ü!", "U", "Ü", 11, 16, 58, 5.0, 81),
    lv("Finde das F!", "E", "F", 11, 17, 54, 6.0, 82),
    lv("Finde die 5!", "S", "5", 12, 17, 52, 6.0, 83, fly_at=(1.8, 3.8)),
    lv("Finde das G!", "C", "G", 12, 18, 50, 6.0, 84),
    lv("Finde das W!", "VV", "W", 9, 18, 48, 7.0, 85, cat_line=(2.0, 4.6, "Zu viele Vs... mir ist schwindelig.")),
    lv("Finde die 6!", "b", "6", 13, 19, 46, 7.0, 86, fly_at=(2.4, 4.6)),
    lv("Finde die NULL!", "O", "0", 13, 19, 46, 8.0, 87),
    lv("Finde das rn!", "m", "rn", 11, 20, 44, 8.0, 88, weight="Medium", fly_at=(3.0, 5.4)),
]

FILM = make(LEVELS, hook="NUR 1 % SCHAFFEN LEVEL 8", cat_txt="Level 8 hat mich fertig gemacht.",
            cta="FOLGEN für Teil 3")

if __name__ == "__main__":
    print(f"duration {FILM.dur:.1f}s")
    if "--sheet" in sys.argv:
        ts = [st + k for st, sc in zip(FILM.starts, FILM.scenes) for k in (1.0, sc.dur - 0.6)]
        print(stills(FILM, ts, "output/preview_buchst2", cols=6, scale=0.25))
    else:
        render(FILM, "output/finde_den_buchstaben_teil2.mp4")
