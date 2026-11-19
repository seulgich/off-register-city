#!/usr/bin/env python3
"""Fix one arrangement of the page and lay every sign out for the risograph, exactly as it reads on screen.

    python3 tools/build_signs.py [path/to/Found-Letters-Tool] [--seed N] [--lh PX]

Seed 427 is the page's arrangement. Other seeds make other shuffles of the same signs, saved with -seedN in the name.

Run tools/build_print.py first (it chooses the letters). This script then
- picks one letter for every character, the way the page does (same slope from noise to sure words),
  and saves it as data/composition.json, so the page opens on that arrangement;
- sets all signs, line by line and word by word, on 11 x 17 sheets at 600 dpi, packed into the lowest free spot in reading order,
  shrinking the letter height until everything fits on SHEETS sheets;
- writes print/signs-print.pdf, one PNG per sheet, and print/signs-layout.json (where every word sits).
"""
import json, os, sys, random, collections
from PIL import Image, ImageOps, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import argparse
ap = argparse.ArgumentParser()
ap.add_argument('tool', nargs='?', default='~/Documents/Found-Letters-Tool')
ap.add_argument('--seed', type=int, default=427, help='another seed = another shuffle of the letters')
ap.add_argument('--lh', type=int, default=0, help='letter height in px at 600 dpi (0 = the largest that fits)')
args = ap.parse_args()
TOOL = os.path.abspath(os.path.expanduser(args.tool))
DPI = 600
PAGE_W, PAGE_H = 11 * DPI, 17 * DPI
SHEETS = 3
EDGE = int(.2 * DPI)             # the riso cannot print right to the edge
MARK = int(.18 * DPI)            # corner squares for straightening the scans
THR = .5
NEAR, TOP = 10, {5: 6, 6: 3}     # same as app.js
SEED = args.seed
TAG = '' if SEED == 427 else f'-seed{SEED}'   # seed 427 is the page's own arrangement
FALL = {'–': '-', '•': '.', 'ñ': 'n', '’': "'"}

L = json.load(open(os.path.join(HERE, 'print', 'layout.json')))
G, SRC = L['G'], L['src']
tones = json.load(open(os.path.join(HERE, 'data', 'signs.json'), encoding='utf8'))
signs = [(t['level'], g) for t in tones for g in t['signs']]

def glyph(ch):
    if ch in G: return G[ch]
    if FALL.get(ch) in G: return G[FALL[ch]]
    return G.get(ch.swapcase())

# one arrangement, picked the way the page picks
random.seed(SEED)
comp = []
for k, (lv, lines) in enumerate(signs):
    p = k / (len(signs) - 1); out = []
    for line in lines:
        words = []
        for w in line.split(' '):
            if not w: continue
            ids = []
            for ch in w:
                lst = glyph(ch)
                if not lst: continue
                c = sorted(lst, key=lambda a: -a[1])[:TOP[lv]] if lv in TOP else sorted(lst, key=lambda a: abs(a[1] - p))[:NEAR]
                ids.append(random.choice(c)[0])
            if ids: words.append(ids)
        out.append(words)
    comp.append(out)
json.dump({'seed': SEED, 'signs': comp}, open(os.path.join(HERE, 'data', f'composition{TAG}.json'), 'w'), separators=(',', ':'))

# letter widths per unit height, from the source boxes (box + 15% pad, as cut)
def padded(i):
    _, x, y, w, h = SRC[i]; pad = max(2, round(min(w, h) * .15)); return x - pad, y - pad, w + 2 * pad, h + 2 * pad
aspect = {}
for s in comp:
    for line in s:
        for wd in line:
            for i in wd:
                if i not in aspect: _, _, w, h = padded(i); aspect[i] = w / h

area = (EDGE, EDGE + MARK + int(.04 * DPI), PAGE_W - EDGE, PAGE_H - EDGE - MARK - int(.04 * DPI))   # top and bottom bands keep the corner squares and the label

def measure(LH):
    """Each sign as rows of words. A line keeps its break; only a line wider than the sheet wraps, at a word, as on a narrow screen."""
    gap, space, lgap = LH * .08, LH * .35, LH * .2
    maxw = area[2] - area[0] - LH * .6
    blocks = []
    for s in comp:
        rows = []
        for li, line in enumerate(s):
            row = []; x = 0
            for wi, wd in enumerate(line):
                ww = sum(aspect[i] * LH for i in wd) + gap * (len(wd) - 1)
                if row and x + space + ww > maxw: rows.append((row, x)); row = []; x = 0
                if row: x += space
                row.append((li, wi, x, ww)); x += ww
            rows.append((row, x))
        bw = max([r[1] for r in rows] + [1]); bh = len(rows) * LH + (len(rows) - 1) * lgap
        blocks.append((rows, bw, bh))
    return blocks

def place(sky, w, h, bottom):
    """Skyline packing: the lowest, then leftmost, spot where a block of w x h fits."""
    best = None
    for i in range(len(sky)):
        x = sky[i][0]
        if x + w > area[2]: break
        y = 0; j = i; right = x + w
        while j < len(sky) and sky[j][0] < right:
            y = max(y, sky[j][1]); j += 1
        if y + h <= bottom and (best is None or (y, x) < (best[1], best[0])): best = (x, y)
    return best

def put(sky, x, y, w, h):
    right = x + w; new = []
    for sx, sy, sw in sky:
        if sx + sw <= x or sx >= right: new.append((sx, sy, sw)); continue
        if sx < x: new.append((sx, sy, x - sx))
        if sx + sw > right: new.append((right, sy, sx + sw - right))
    new.append((x, y + h, w)); new.sort()
    return new

LABEL_H = int(.11 * DPI)
starts = {}   # first sign of each tone -> (level, tone name, number of signs)
_k = 0
for t in tones:
    starts[_k] = (t['level'], t['tone'], len(t['signs'])); _k += len(t['signs'])

def pack(LH):
    """Signs go in reading order, each into the lowest free spot, so the gaps fill up.
    Each tone starts on a new band under its label, as on the page."""
    blocks = measure(LH); gx, gy = LH * .6, LH * .5
    fresh = lambda: [(area[0], area[1], area[2] - area[0])]
    pages = [[]]; labels = [[]]; sky = fresh()
    for bi, (rows, bw, bh) in enumerate(blocks):
        if bi in starts:
            y0 = max(sy for _, sy, _ in sky) if pages[-1] else area[1]
            if y0 > area[1]: y0 += gy
            if y0 + LABEL_H + gy + bh > area[3]: pages.append([]); labels.append([]); y0 = area[1]
            labels[-1].append((starts[bi], area[0], y0))
            sky = [(area[0], y0 + LABEL_H + gy * .6, area[2] - area[0])]
        w, h = bw + gx, bh + gy
        spot = place(sky, w, h, area[3] + gy)
        if spot is None:
            pages.append([]); labels.append([]); sky = fresh(); spot = place(sky, w, h, area[3] + gy)
            if spot is None: return blocks, [[]] * (SHEETS + 1), None   # a sign wider than the sheet: smaller letters
        pages[-1].append((bi, spot[0], spot[1])); sky = put(sky, spot[0], spot[1], w, h)
    return blocks, pages, labels

LH = args.lh or .2 * DPI
while True:
    blocks, pages, labels = pack(LH)
    if len(pages) <= SHEETS: break
    LH -= 1
print(f'letter height {LH / DPI:.3f} in ({LH:.0f} px at {DPI} dpi), {len(pages)} sheets')

# cut letters from the originals at print height, grey, then threshold like the page
need = sorted(aspect)
byp = collections.defaultdict(list)
for i in need: byp[SRC[i][0]].append(i)
LHp = int(round(LH)); cut = {}
for name, ids in byp.items():
    im = ImageOps.exif_transpose(Image.open(os.path.join(TOOL, 'photos', name))).convert('L')
    for i in ids:
        x, y, w, h = padded(i)
        p = im.crop((max(0, round(x)), max(0, round(y)), min(im.width, round(x + w)), min(im.height, round(y + h))))
        cut[i] = p.resize((max(1, round(LHp * aspect[i])), LHp), Image.LANCZOS).point(lambda v: 0 if v < THR * 255 else 255)

font = ImageFont.load_default(size=int(.09 * DPI))
corners = [(EDGE, EDGE), (PAGE_W - EDGE - MARK, EDGE), (EDGE, PAGE_H - EDGE - MARK), (PAGE_W - EDGE - MARK, PAGE_H - EDGE - MARK)]
words = []   # [sign, line, word, sheet, x, y, w, h]
label_pos = []   # [sheet, x, y, text]
out = []
for si, pl in enumerate(pages):
    S = Image.new('L', (PAGE_W, PAGE_H), 255); d = ImageDraw.Draw(S)
    for cx, cy in corners: d.rectangle([cx, cy, cx + MARK - 1, cy + MARK - 1], fill=0)
    d.text((EDGE + MARK + int(.1 * DPI), EDGE + int(.03 * DPI)), f'SIGNAGE, INVERTED   SIGNS {si + 1}/{len(pages)}   SEED {SEED}   PRINT ____   VERB ______________', fill=0, font=font)
    for (lv, name, n), lx, ly in labels[si]:
        d.text((lx, ly), f'{lv} / 6   {name.upper()}   {n} SIGNS', fill=0, font=font); label_pos.append([si, int(lx), int(ly), f'{lv} / 6   {name.upper()}   {n} SIGNS'])
    for bi, bx, by in pl:
        rows, bw, bh = blocks[bi]
        for ri, (row, _) in enumerate(rows):
            ly = by + ri * LH * 1.2
            for li, wi, wx, ww in row:
                x = bx + wx
                for k, i in enumerate(comp[bi][li][wi]):
                    if k: x += LH * .08
                    S.paste(cut[i], (int(round(x)), int(round(ly)))); x += aspect[i] * LH
                words.append([bi, li, wi, si, int(bx + wx), int(ly), int(ww + 1), LHp])
    out.append(S.convert('1'))
os.makedirs(os.path.join(HERE, 'print'), exist_ok=True)
out[0].save(os.path.join(HERE, 'print', f'signs-print{TAG}.pdf'), save_all=True, append_images=out[1:], resolution=DPI)
for si, S in enumerate(out): S.save(os.path.join(HERE, 'print', f'signs-print{TAG}-{si + 1}.png'), dpi=(DPI, DPI))
json.dump({'dpi': DPI, 'page': [PAGE_W, PAGE_H], 'mark': MARK, 'corners': corners, 'letter_height': LHp, 'seed': SEED, 'words': words, 'labels': label_pos, 'edge': EDGE},
          open(os.path.join(HERE, 'print', f'signs-layout{TAG}.json'), 'w'), separators=(',', ':'))
print(f'wrote print/signs-print{TAG}.pdf, print/signs-layout{TAG}.json, data/composition{TAG}.json')
