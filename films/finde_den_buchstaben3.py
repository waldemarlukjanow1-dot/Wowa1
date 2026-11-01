"""'Finde den Buchstaben' Teil 3 - letters, numbers and whole words (TIKTOK vs TIKT0K finale).

Render:  python3 -m films.finde_den_buchstaben3
Preview: python3 -m films.finde_den_buchstaben3 --sheet
"""
import sys

from engine.render import render, stills
from films.finde_den_buchstaben import lv, make

LEVELS = [
    lv("Finde das Ä!", "A", "Ä", 11, 16, 58, 5.0, 91),
    lv("Finde die 7!", "1", "7", 12, 17, 54, 6.0, 92),
    lv("Finde das K!", "X", "K", 12, 17, 52, 6.0, 93, fly_at=(1.8, 3.8)),
    lv("Finde das Q!", "O", "Q", 12, 18, 50, 6.0, 94),
    lv("Finde HUND!", "HUHN", "HUND", 5, 18, 42, 7.0, 95, cat_line=(2.0, 4.6, "HUND?! Wo?! Ich hau ab.")),
    lv("Finde das ß!", "B", "ß", 13, 19, 46, 7.0, 96, fly_at=(2.4, 4.6)),
    lv("Finde das große i!", "l", "I", 14, 20, 44, 8.0, 97, weight="Medium"),
    lv("Finde TIKTOK!", "TIKT0K", "TIKTOK", 4, 20, 40, 8.0, 98, fly_at=(3.0, 5.4)),
]

FILM = make(LEVELS, hook="99 % SCHEITERN AN LEVEL 8", cat_txt="TIKT0K... TIKTOK... Hilfe!",
            cta="FOLGEN für Teil 4")

if __name__ == "__main__":
    print(f"duration {FILM.dur:.1f}s")
    if "--sheet" in sys.argv:
        ts = [st + k for st, sc in zip(FILM.starts, FILM.scenes) for k in (1.0, sc.dur - 0.6)]
        print(stills(FILM, ts, "output/preview_buchst3", cols=6, scale=0.25))
    else:
        render(FILM, "output/finde_den_buchstaben_teil3.mp4")
