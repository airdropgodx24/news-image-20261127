#!/usr/bin/env python3
"""news-image-20261127 entry.

Draws a 1024x1024 front-page style summary of the world news of
Friday 27 November 2026 and writes it as a PNG to /output/entry.png
(or $MAKEFUN_OUTPUT_DIR/entry.png outside the grader).

Python 3 standard library only. No network. The output is fully
deterministic: the same bytes on every run.
"""

import binascii
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- colours

def rgb(r, g, b):
    return bytes((r, g, b))

NAVY = rgb(14, 30, 51)        # page background
CREAM = rgb(247, 241, 227)    # card background / light text
INK = rgb(22, 34, 46)         # card text
GOLD = rgb(212, 172, 13)      # masthead accent
RED = rgb(192, 57, 43)

ACCENTS = [
    rgb(192, 57, 43),    # war red
    rgb(46, 109, 164),   # storm blue
    rgb(183, 121, 31),   # oil amber
    rgb(30, 122, 79),    # politics green
    rgb(108, 52, 131),   # economy purple
    rgb(93, 109, 126),   # migration slate
]

def tint(color, base=CREAM, keep=0.16):
    """A pale wash of `color` over `base`, for icon backings."""
    return bytes(int(c * keep + b * (1.0 - keep)) for c, b in zip(color, base))

# ------------------------------------------------------------------- font
# A hand-drawn 5x7 bitmap font, uppercase plus digits and punctuation.
# Each glyph is 7 rows of 5 pixels; '#' is ink, '.' is empty.

FONT = {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".####", "#....", "#....", "#....", "#....", "#....", ".####"],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"],
    "J": ["..###", "....#", "....#", "....#", "....#", "#...#", ".###."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"],
    "X": ["#...#", ".#.#.", "..#..", "..#..", "..#..", ".#.#.", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
    "0": [".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", "#####"],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": [".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."],
    " ": [".....", ".....", ".....", ".....", ".....", ".....", "....."],
    ".": [".....", ".....", ".....", ".....", ".....", ".##..", ".##.."],
    ",": [".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."],
    ":": [".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."],
    ";": [".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."],
    "'": ["..#..", "..#..", ".#...", ".....", ".....", ".....", "....."],
    "!": ["..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."],
    "?": [".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."],
    "-": [".....", ".....", ".....", "#####", ".....", ".....", "....."],
    "+": [".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."],
    "/": ["....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."],
    "(": ["...##", "..#..", ".#...", ".#...", ".#...", "..#..", "...##"],
    ")": ["##...", "..#..", "...#.", "...#.", "...#.", "..#..", "##..."],
    "$": ["..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."],
    "%": ["##..#", "##.#.", "...#.", "..#..", ".#...", "#..##", "#..##"],
    "|": ["..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "&": [".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".###."],
    '"': [".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", "....."],
}

GLYPH_W = 5
GLYPH_H = 7
ADVANCE = 6  # glyph width plus one blank column, in font units

def text_width(text, scale):
    if not text:
        return 0
    return len(text) * ADVANCE * scale - scale

def wrap(text, max_chars):
    """Greedy word wrap to lines of at most max_chars characters."""
    lines = []
    current = ""
    for word in text.split():
        trial = word if not current else current + " " + word
        if len(trial) <= max_chars:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

# ----------------------------------------------------------------- canvas

class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg * (w * h))

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = color * (x1 - x0)
        for yy in range(y0, y1):
            start = (yy * self.w + x0) * 3
            self.px[start:start + len(row)] = row

    def fill_circle(self, cx, cy, r, color):
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, color)

    def fill_polygon(self, points, color):
        ys = [p[1] for p in points]
        n = len(points)
        for y in range(min(ys), max(ys) + 1):
            scan = y + 0.5
            nodes = []
            for i in range(n):
                x0, y0 = points[i]
                x1, y1 = points[(i + 1) % n]
                if y0 == y1:
                    continue
                if (y0 <= scan < y1) or (y1 <= scan < y0):
                    t = (scan - y0) / (y1 - y0)
                    nodes.append(x0 + t * (x1 - x0))
            nodes.sort()
            for i in range(0, len(nodes) - 1, 2):
                xa = int(round(nodes[i]))
                xb = int(round(nodes[i + 1]))
                if xb > xa:
                    self.fill_rect(xa, y, xb - xa, 1, color)

    def line(self, x0, y0, x1, y1, color, thick=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        half = thick // 2
        while True:
            self.fill_rect(x - half, y - half, thick, thick, color)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def outline_rect(self, x, y, w, h, color, thick=1):
        self.fill_rect(x, y, w, thick, color)
        self.fill_rect(x, y + h - thick, w, thick, color)
        self.fill_rect(x, y, thick, h, color)
        self.fill_rect(x + w - thick, y, thick, h, color)

    def text(self, x, y, s, scale, color):
        cx = x
        for ch in s:
            glyph = FONT.get(ch, FONT["?"])
            for row_i, row in enumerate(glyph):
                for col_i, cell in enumerate(row):
                    if cell == "#":
                        self.fill_rect(cx + col_i * scale, y + row_i * scale,
                                       scale, scale, color)
            cx += ADVANCE * scale

    def centered_text(self, y, s, scale, color):
        x = (self.w - text_width(s, scale)) // 2
        self.text(x, y, s, scale, color)

# -------------------------------------------------------------------- PNG

def _chunk(kind, data):
    body = kind + data
    return (struct.pack(">I", len(data)) + body +
            struct.pack(">I", binascii.crc32(body) & 0xFFFFFFFF))

def png_bytes(cv):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.px[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" +
            _chunk(b"IHDR", ihdr) +
            _chunk(b"IDAT", zlib.compress(bytes(raw), 9)) +
            _chunk(b"IEND", b""))

# ------------------------------------------------------------------ icons
# Simple geometric pictograms drawn inside a 56x56 box at (x, y).

def icon_bolt(cv, x, y, color):
    pts = [(x + 32, y + 3), (x + 14, y + 30), (x + 25, y + 30),
           (x + 19, y + 53), (x + 43, y + 24), (x + 31, y + 24)]
    cv.fill_polygon(pts, color)

def icon_storm(cv, x, y, color):
    cv.fill_circle(x + 19, y + 24, 9, color)
    cv.fill_circle(x + 29, y + 17, 12, color)
    cv.fill_circle(x + 40, y + 24, 8, color)
    cv.fill_rect(x + 11, y + 24, 36, 9, color)
    for rx in (17, 27, 37):
        cv.line(x + rx, y + 39, x + rx - 4, y + 50, color, 3)

def icon_barrel(cv, x, y, color):
    # an oil drop: round belly under a pointed top
    cv.fill_circle(x + 28, y + 36, 14, color)
    cv.fill_polygon([(x + 16, y + 34), (x + 40, y + 34), (x + 28, y + 6)], color)
    cv.fill_circle(x + 23, y + 38, 4, tint(color))

def icon_ballot(cv, x, y, color):
    cv.outline_rect(x + 12, y + 20, 32, 30, color, 4)
    cv.fill_rect(x + 19, y + 12, 18, 5, color)
    cv.line(x + 19, y + 34, x + 26, y + 42, color, 5)
    cv.line(x + 26, y + 42, x + 39, y + 26, color, 5)

def icon_note_barred(cv, x, y, color):
    cv.outline_rect(x + 7, y + 15, 42, 26, color, 3)
    cv.fill_circle(x + 28, y + 28, 7, color)
    cv.fill_circle(x + 28, y + 28, 4, tint(color))
    cv.line(x + 9, y + 46, x + 47, y + 10, RED, 5)

def icon_arrow_down(cv, x, y, color):
    pts = [(x + 22, y + 6), (x + 34, y + 6), (x + 34, y + 28),
           (x + 45, y + 28), (x + 28, y + 47), (x + 11, y + 28),
           (x + 22, y + 28)]
    cv.fill_polygon(pts, color)
    cv.fill_rect(x + 11, y + 51, 34, 3, color)

ICONS = [icon_bolt, icon_storm, icon_barrel,
         icon_ballot, icon_note_barred, icon_arrow_down]

# ---------------------------------------------------------------- stories
# The six verified stories of Friday 27 November 2026.

STORIES = [
    {
        "tag": "EUROPE | WAR",
        "headline": "UKRAINE WARNS OF NEW MASS STRIKE",
        "summary": ("Zelenskyy warns of a mass strike on the power grid. "
                    "Five died in overnight strikes. Trump urges Putin to "
                    "pull back; EU split over $49bn loan."),
    },
    {
        "tag": "USA | WEATHER",
        "headline": "THANKSGIVING STORM HITS EAST",
        "summary": ("A major storm leaves 900,000+ homes without power and "
                    "cancels 400+ flights. Macy's parade is postponed for "
                    "the first time in 100 years."),
    },
    {
        "tag": "MIDDLE EAST | ENERGY",
        "headline": "TANKERS MINED IN HORMUZ",
        "summary": ("Two tankers are mined in the Strait of Hormuz; Brent "
                    "crude settles near $96.57. A strike on the Jazan "
                    "refinery kills one worker."),
    },
    {
        "tag": "OCEANIA | POLITICS",
        "headline": "NZ COALITION ONE SEAT SHORT",
        "summary": ("Final results give the coalition 65 of 130 seats, one "
                    "short of a majority. It now needs the Opportunity "
                    "Party to govern."),
    },
    {
        "tag": "SOUTH AMERICA | ECONOMY",
        "headline": "ARGENTINA BARS MONEY PRINTING",
        "summary": ("The Chamber of Deputies votes 141-0 to bar the "
                    "central bank from printing money to fund government "
                    "spending."),
    },
    {
        "tag": "EUROPE | MIGRATION",
        "headline": "UK NET MIGRATION AT 77,000",
        "summary": ("Net migration falls to 77,000 in the year to June "
                    "2026, the lowest since 1997 outside the pandemic, "
                    "official figures show."),
    },
]

# ----------------------------------------------------------------- layout

CARD_W = 470
CARD_H = 256
GRID_X = (32, 522)
GRID_Y = (158, 430, 702)

def draw_card(cv, x, y, story, accent, icon):
    cv.fill_rect(x, y, CARD_W, CARD_H, CREAM)
    cv.fill_rect(x, y, 8, CARD_H, accent)

    # region tag pill
    tag = story["tag"]
    pill_w = text_width(tag, 2) + 20
    cv.fill_rect(x + 22, y + 14, pill_w, 28, accent)
    cv.text(x + 32, y + 21, tag, 2, CREAM)

    # pictogram in a tinted square, top right
    ix = x + CARD_W - 18 - 56
    iy = y + 10
    cv.fill_rect(ix, iy, 56, 56, tint(accent))
    icon(cv, ix, iy, accent)

    # headline, up to two lines
    hy = y + 78
    for line in wrap(story["headline"], 17)[:2]:
        cv.text(x + 22, hy, line, 4, INK)
        hy += 38

    # summary
    sy = y + 156
    for line in wrap(story["summary"].upper(), 35)[:5]:
        cv.text(x + 22, sy, line, 2, INK)
        sy += 19

def draw_page():
    cv = Canvas(W, H, NAVY)

    # masthead
    cv.centered_text(38, "WORLD NEWS", 3, GOLD)
    cv.centered_text(70, "FRIDAY, 27 NOVEMBER 2026", 6, CREAM)
    cv.fill_rect(32, 128, 960, 4, CREAM)
    cv.fill_rect(32, 138, 960, 2, CREAM)

    # story grid
    for i, story in enumerate(STORIES):
        x = GRID_X[i % 2]
        y = GRID_Y[i // 2]
        draw_card(cv, x, y, story, ACCENTS[i], ICONS[i])

    # footer
    foot = "THE DAY IN SIX STORIES"
    fx = (W - text_width(foot, 2)) // 2
    cv.fill_rect(32, 978, fx - 52, 2, GOLD)
    cv.fill_rect(fx + text_width(foot, 2) + 20, 978, 992 - (fx + text_width(foot, 2) + 20), 2, GOLD)
    cv.text(fx, 972, foot, 2, CREAM)

    return cv

def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = png_bytes(draw_page())
    with open(os.path.join(out_dir, "entry.png"), "wb") as fh:
        fh.write(data)

if __name__ == "__main__":
    main()
