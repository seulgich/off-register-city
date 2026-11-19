#!/usr/bin/env python3
"""Lay out the letters of Signage, Inverted as risograph sheets.

    python3 tools/build_print.py [path/to/Found-Letters-Tool]

Writes print/letters-print.pdf (letter size, 600 dpi, pure black and white, one page per sheet),
print/layout.json (where every letter sits on every sheet, for cutting the scans later)
and letters/letters-digital-*.webp + letters/letters.json (the same letters for the page, before the prints exist).

The same sheets are printed ten times, and each print lets one thing happen to the paper.
Every sheet carries four solid corner squares; tools/cut_scans.py uses them to straighten a scan.
"""
import json, glob, os, random, sys, collections
from PIL import Image, ImageOps, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.abspath(os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else '~/Documents/Found-Letters-Tool'))
DPI = 600
PAGE_W, PAGE_H = int(8.5 * DPI), int(11 * DPI)      # US letter
MARGIN = int(0.5 * DPI)                              # riso cannot print to the edge
MARK = int(0.25 * DPI)                               # corner squares
LH = int(0.2 * DPI)                                  # printed letter height: 0.2 in = 120 px
GAP_X, GAP_Y = int(0.04 * DPI), int(0.07 * DPI)      # white between letters, so each can be cut again
PER = 12                                             # instances per band and letter
THR = 0.5                                            # same threshold as the page and the tool
SEED = 9

tones = json.load(open(os.path.join(HERE, 'data', 'signs.json'), encoding='utf8'))
need = set(ch for t in tones for g in t['signs'] for l in g for ch in l if ch != ' ')
KR = {3: 0, 2: 1, 1: 2, 0: 3}   # Noise, Non-words, Unsure words, Sure words

by = collections.defaultdict(list)
for f in sorted(glob.glob(os.path.join(TOOL, 'readings', '*.json'))):
    d = json.load(open(f)); name = os.path.basename(f)[:-5]; ws = d['words']
    for ch, wi, k, q, x, y, w, h in d['letters']:
        if k not in KR or (ch not in need and ch.swapcase() not in need): continue
        if w < 4 or h < 6 or w > h * 1.6: continue
        conf = ws[wi][2] if wi is not None and 0 <= wi < len(ws) else 0
        by[(ch, KR[k])].append((name, x, y, w, h, conf, q))
if not by: sys.exit(f'No readings found in {TOOL}/readings')

random.seed(SEED)
G = {}; order = []; idx = {}
for ch in sorted(need):
    items = []
    for band in range(4):
        v = list(by[(ch, band)])
        if len(v) < PER // 2 and ch.swapcase() != ch: v += by[(ch.swapcase(), band)]
        if not v: continue
        v.sort(key=(lambda c: (c[6], c[5])) if band == 3 else (lambda c: (c[5], c[6])))
        n = len(v)
        take = [v[round(i * (n - 1) / (PER - 1))] for i in range(PER)] if n > PER else v
        if band == 3 and n > PER: take = take[:-8] + v[-8:]
        seen = set(); take = [c for c in take if not (c in seen or seen.add(c))]
        for j, c in enumerate(take):
            pv = (band + (j + .5) / len(take)) / 4
            if c[:5] not in idx: idx[c[:5]] = len(order); order.append(c)
            items.append([idx[c[:5]], round(pv, 4)])
    if items: G[ch] = items
print('letters', len(G), 'of', len(need), '| cuts', len(order), '| not found', sorted(need - set(G)))

# cut every letter from its original photograph at print height, grey
grey = [None] * len(order)
byp = collections.defaultdict(list)
for i, c in enumerate(order): byp[c[0]].append(i)
for name, ids in byp.items():
    im = ImageOps.exif_transpose(Image.open(os.path.join(TOOL, 'photos', name))).convert('L')
    for i in ids:
        _, x, y, w, h, _c, _q = order[i]; pad = max(2, round(min(w, h) * .15))
        p = im.crop((max(0, round(x - pad)), max(0, round(y - pad)), min(im.width, round(x + w + pad)), min(im.height, round(y + h + pad))))
        grey[i] = p.resize((max(1, round(p.width * LH / p.height)), LH), Image.LANCZOS)

# pack the letters in reading order of the ranking, row by row, inside the marks
inner = (MARGIN + MARK + int(.1 * DPI), MARGIN + MARK + int(.1 * DPI), PAGE_W - MARGIN - MARK - int(.1 * DPI), PAGE_H - MARGIN - MARK - int(.1 * DPI))
pages = [[]]; boxes = [None] * len(order); x, y = inner[0], inner[1]
for i, p in enumerate(grey):
    if x + p.width > inner[2]: x = inner[0]; y += LH + GAP_Y
    if y + LH > inner[3]: pages.append([]); x, y = inner[0], inner[1]
    boxes[i] = [len(pages) - 1, x, y, p.width, LH]; pages[-1].append(i); x += p.width + GAP_X
print(len(pages), 'sheets')

font = ImageFont.load_default(size=int(.11 * DPI))
corners = lambda: [(MARGIN, MARGIN), (PAGE_W - MARGIN - MARK, MARGIN), (MARGIN, PAGE_H - MARGIN - MARK), (PAGE_W - MARGIN - MARK, PAGE_H - MARGIN - MARK)]
os.makedirs(os.path.join(HERE, 'print'), exist_ok=True)
sheets = []
for si, ids in enumerate(pages):
    S = Image.new('L', (PAGE_W, PAGE_H), 255); d = ImageDraw.Draw(S)
    for cx, cy in corners(): d.rectangle([cx, cy, cx + MARK - 1, cy + MARK - 1], fill=0)
    label = f'SIGNAGE, INVERTED   LETTERS {si + 1}/{len(pages)}   PRINT ____   VERB ______________'
    d.text((MARGIN + MARK + int(.1 * DPI), MARGIN + int(.06 * DPI)), label, fill=0, font=font)
    for i in ids:
        _, bx, by_, bw, bh = boxes[i]
        bw_ = grey[i].point(lambda v: 0 if v < THR * 255 else 255)
        S.paste(bw_, (bx, by_))
    sheets.append(S.convert('1'))
pdf = os.path.join(HERE, 'print', 'letters-print.pdf')
sheets[0].save(pdf, save_all=True, append_images=sheets[1:], resolution=DPI)
for si, S in enumerate(sheets): S.save(os.path.join(HERE, 'print', f'letters-print-{si + 1}.png'), dpi=(DPI, DPI))
json.dump({'dpi': DPI, 'page': [PAGE_W, PAGE_H], 'mark': MARK, 'corners': corners(), 'boxes': boxes, 'G': G, 'src': [list(c[:5]) for c in order]},
          open(os.path.join(HERE, 'print', 'layout.json'), 'w'), separators=(',', ':'))

# the same letters for the page, before the prints exist: one grey version, as 'digital'
H = 80; W = MAXH = 4096; sheet = 0; x = y = rowh = 0; rects = []; groups = [[]]
small = [g.resize((max(1, round(g.width * H / g.height)), H), Image.LANCZOS) for g in grey]
for p in small:
    if x + p.width > W: x = 0; y += rowh + 2; rowh = 0
    if y + p.height > MAXH: sheet += 1; groups.append([]); x = y = rowh = 0
    rects.append([sheet, x, y, p.width, p.height]); groups[sheet].append(len(rects) - 1); x += p.width + 2; rowh = max(rowh, p.height)
os.makedirs(os.path.join(HERE, 'letters'), exist_ok=True)
for si, ids in enumerate(groups):
    hh = max(rects[i][2] + rects[i][4] for i in ids); A = Image.new('L', (W, hh), 255)
    for i in ids: A.paste(small[i], (rects[i][1], rects[i][2]))
    A.save(os.path.join(HERE, 'letters', f'letters-digital-{si}.webp'), 'WEBP', quality=86, method=5)
json.dump({'R': rects, 'G': G, 'sheets': len(groups), 'versions': [{'name': 'digital', 'files': [f'letters-digital-{i}.webp' for i in range(len(groups))], 'R': rects}]},
          open(os.path.join(HERE, 'letters', 'letters.json'), 'w'), separators=(',', ':'))
print('wrote print/letters-print.pdf, print/layout.json and letters/letters.json')
