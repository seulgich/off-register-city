#!/usr/bin/env python3
"""Set the original sign words, as the website shows them on hover, on the same sheets as the found letters.

    python3 tools/build_text.py                 # SEED 427, the screen
    python3 tools/build_text.py --seed 1013     # pairs with signs-print-seed1013.pdf

Reads print/signs-layout[-seedN].json (made by tools/build_signs.py) and writes print/signs-text[-seedN].pdf
and one PNG per sheet. Like the website's hover text, every line is Overpass 300 at 16/28 of the letter
height, with .02em letter spacing and a line pitch of 1.2 x the letter height, starting where the sign's
found letters start. The corner squares are the same, so the sheet can be printed over signs-print.pdf
as a second drum, or on its own.
"""
import argparse, json, os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument('--seed', type=int, default=427)
ap.add_argument('--weight', type=int, default=300)
ap.add_argument('--scale', type=float, default=16 / 28, help='text size / letter height (website: 16px / 28px)')
ap.add_argument('--labels', action='store_true', help='also print the tone names (they are already on signs-print)')
a = ap.parse_args()
sfx = '' if a.seed == 427 else f'-seed{a.seed}'

L = json.load(open(os.path.join(HERE, 'print', f'signs-layout{sfx}.json')))
G = json.load(open(os.path.join(HERE, 'letters', 'letters.json')))['G']
tones = json.load(open(os.path.join(HERE, 'data', 'signs.json'), encoding='utf8'))
signs = [g for t in tones for g in t['signs']]
PW, PH = L['page']; MARK = L['mark']; LH = L['letter_height']; DPI = L['dpi']; EDGE = L.get('edge', int(.2 * DPI))
FALL = {'–': '-', '•': '.', 'ñ': 'n', '’': "'"}

def has(ch): return ch in G or FALL.get(ch) in G or ch.swapcase() in G

def font(size, weight):
    f = ImageFont.truetype(os.path.join(HERE, 'fonts', 'Overpass[wght].ttf'), size)
    f.set_variation_by_axes([weight]); return f

SIZE = round(LH * a.scale)
F = font(SIZE, a.weight)
ASC, DESC = F.getmetrics()
PITCH = LH * 1.2
BASE = (PITCH - (ASC + DESC)) / 2 + ASC        # CSS half-leading: where the baseline sits in a line box
TRACK = .02 * SIZE

def set_line(d, x, y, text):
    for ch in text:                             # letter by letter, for the .02em spacing
        d.text((x, y + BASE), ch, fill=0, font=F, anchor='ls')
        x += F.getlength(ch) + TRACK

# Which sheet row each word landed on. A sign line that was too wide for the sheet was wrapped
# by build_signs, so one line of the sign can become two rows here, just as in the found letters.
rows = {}
for bi, li, wi, si, x, y, w, h in L['words']:
    rows.setdefault((bi, li, si, y), []).append((wi, x))

nsheets = max(wd[3] for wd in L['words']) + 1
pages = []
small = font(int(.09 * DPI), a.weight)
for si in range(nsheets):
    S = Image.new('L', (PW, PH), 255); d = ImageDraw.Draw(S)
    for cx, cy in L['corners']: d.rectangle([cx, cy, cx + MARK - 1, cy + MARK - 1], fill=0)
    d.text((EDGE + MARK + int(.1 * DPI), EDGE + int(.03 * DPI)),
           f'OFF-REGISTER CITY   TEXT {si + 1}/{nsheets}   SEED {L["seed"]}   PRINT ____   VERB ______________',
           fill=0, font=small)
    if a.labels:
        for s, x, y, text in L.get('labels', []):
            if s == si: d.text((x, y), text, fill=0, font=small)
    pages.append(S)

for bi, sign in enumerate(signs):
    for li, line in enumerate(sign):
        toks = line.split(' ')
        kept = [i for i, t in enumerate(toks) if t and any(has(c) for c in t)]   # the words the sheets hold
        mine = sorted((k for k in rows if k[0] == bi and k[1] == li), key=lambda k: (k[2], k[3]))
        for n, k in enumerate(mine):
            ws = sorted(rows[k]); first, last = ws[0][0], ws[-1][0]
            t0 = 0 if n == 0 else kept[first]                     # a word with no letters stays with its neighbours
            t1 = len(toks) - 1 if n == len(mine) - 1 else kept[last]
            text = ' '.join(t for t in toks[t0:t1 + 1] if t)
            set_line(ImageDraw.Draw(pages[k[2]]), ws[0][1], k[3], text)

out = [p.point(lambda v: 0 if v < 128 else 255).convert('1') for p in pages]
pdf = os.path.join(HERE, 'print', f'signs-text{sfx}.pdf')
out[0].save(pdf, save_all=True, append_images=out[1:], resolution=DPI)
for i, p in enumerate(out): p.save(os.path.join(HERE, 'print', f'signs-text{sfx}-{i + 1}.png'), dpi=(DPI, DPI))
print('wrote', pdf, f'text {SIZE}px = {SIZE / DPI * 72:.1f}pt, weight {a.weight}')
