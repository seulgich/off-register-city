#!/usr/bin/env python3
"""Put a scan of a printed sign sheet back on the page.

    python3 tools/cut_sign_scans.py path/to/scan.jpg --sheet 1 [--seed 427]

The scan is straightened on its four corner squares, the paper is brought to white (the ink keeps its colour),
and every letter is cut out where print/signs-layout.json says it was printed, after a small search that follows
the riso's own drift word by word. The page then shows the scanned letters for every sign on that sheet, and a
random swap there takes the same letter from somewhere else on the scan.

Writes letters/riso-<seed>-<sheet>.webp (the straightened sheet) and adds it to letters/riso.json.
Run it again with a sharper scan (600 dpi if possible) and it replaces the old one.
"""
import argparse, json, os
import numpy as np
from PIL import Image, ImageOps
from scipy import ndimage

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument('scan')
ap.add_argument('--sheet', type=int, required=True, help='1, 2 or 3, as printed in the sheet header')
ap.add_argument('--seed', type=int, default=427)
ap.add_argument('--debug', action='store_true')
ap.add_argument('--dpi', type=int, help='working resolution of the cut sheet (default: the scan\'s own, up to 600)')
a = ap.parse_args()
TAG = '' if a.seed == 427 else f'-seed{a.seed}'
SI = a.sheet - 1

L = json.load(open(os.path.join(HERE, 'print', f'signs-layout{TAG}.json')))
SRC = json.load(open(os.path.join(HERE, 'print', 'layout.json')))['src']
G = json.load(open(os.path.join(HERE, 'letters', 'letters.json')))['G']
comp = json.load(open(os.path.join(HERE, 'data', f'composition{TAG}.json')))['signs']
tones = json.load(open(os.path.join(HERE, 'data', 'signs.json'), encoding='utf8'))
signs = [g for t in tones for g in t['signs']]
PW, PH = L['page']; MARK = L['mark']; LH = L['letter_height']
FALL = {'–': '-', '•': '.', 'ñ': 'n', '’': "'"}

def key(ch):                                   # the same lookup as glyph() in app.js
    if ch in G: return ch
    if FALL.get(ch) in G: return FALL[ch]
    return ch.swapcase() if ch.swapcase() in G else None

# 1. paper to white, ink keeps its colour
im = np.asarray(ImageOps.exif_transpose(Image.open(a.scan)).convert('RGB')).astype(float)
paper = np.median(im.reshape(-1, 3), axis=0)
im = np.clip(im / paper * 255, 0, 255)
im[im.min(axis=2) > 232] = 255                 # paper grain and dust
ink = 255 - im.min(axis=2)

# 2. the corner squares: in each corner of the scan, the spot where a square of the mark's size holds the most ink
#    (a box filter, so a pale or halftoned square is found as well as a solid one)
sc = np.hypot(*im.shape[:2]) / np.hypot(PW, PH)           # rough scan scale
Hs, Ws = im.shape[:2]; ms = max(3, int(MARK * sc))
fi = ndimage.uniform_filter(ink, ms); fo = ndimage.uniform_filter(ink, 3 * ms)
fill = fi - (fo * 9 - fi) / 8                    # ink in the square minus ink around it: letters have neighbours, the mark stands alone
found = []
for fx, fy in [(0, 0), (1, 0), (0, 1), (1, 1)]:
    x0, y0 = int(fx * Ws * .88), int(fy * Hs * .9); x1, y1 = x0 + int(Ws * .12), y0 + int(Hs * .1)
    win = fill[y0:y1, x0:x1]; yy, xx = np.unravel_index(np.argmax(win), win.shape)
    cy, cx = yy + y0, xx + x0; r = ms
    sub = ink[max(0, cy - r):cy + r, max(0, cx - r):cx + r]; w = np.where(sub > sub.max() * .4, sub, 0)
    my, mx = ndimage.center_of_mass(w)
    found.append((mx + max(0, cx - r), my + max(0, cy - r)))
page_pts = [(cx + MARK / 2, cy + MARK / 2) for cx, cy in L['corners']]
d = np.hypot(found[1][0] - found[0][0], found[1][1] - found[0][1]) / (page_pts[1][0] - page_pts[0][0])
S = min(1.0, round(d * 4) / 4 or .25)
if a.dpi: S = min(S, a.dpi / 600)           # work at the scan's own resolution: 0.25 = 150 dpi, 0.5 = 300, 1 = 600
print(f'scan at about {d * 600:.0f} dpi, working at {S * 600:.0f} dpi; corners', [tuple(round(v) for v in c) for c in found])

# 3. straighten: output (page * S) -> scan
A, b = [], []
for (X, Y), (x, y) in zip(page_pts, found):
    X, Y = X * S, Y * S
    A += [[X, Y, 1, 0, 0, 0, -x * X, -x * Y], [0, 0, 0, X, Y, 1, -y * X, -y * Y]]; b += [x, y]
coef = np.linalg.solve(np.array(A), np.array(b))
OW, OH = round(PW * S), round(PH * S)
sheet = Image.fromarray(im.astype(np.uint8)).transform((OW, OH), Image.PERSPECTIVE, tuple(coef), Image.BICUBIC, fillcolor=(255, 255, 255))
A_ink = (255 - np.asarray(sheet).min(axis=2)) / 255

# 4. where each word was meant to be (the 600 dpi sheet), and where the riso put it
src_png = os.path.join(HERE, 'print', f'signs-print{TAG}-{a.sheet}.png')
E = np.asarray(Image.open(src_png).convert('L').resize((OW, OH), Image.BOX)) < 128
E = E.astype(float)

def aspect(i):
    _, x, y, w, h = SRC[i]; pad = max(2, round(min(w, h) * .15)); return (w + 2 * pad) / (h + 2 * pad)

R, K, P, signs_out, offs = [], [], [], {}, []
r = max(2, round(LH * S * .25))
for bi, li, wi, si, x, y, w, h in L['words']:
    if si != SI: continue
    X0, Y0, X1, Y1 = int(x * S), int(y * S), int((x + w) * S) + 1, int((y + h) * S) + 1
    e = E[Y0:Y1, X0:X1]; best = (-1, 0, 0)
    if e.sum():
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if Y0 + dy < 0 or X0 + dx < 0 or Y1 + dy > OH or X1 + dx > OW: continue
                v = (A_ink[Y0 + dy:Y1 + dy, X0 + dx:X1 + dx] * e).sum()
                if v > best[0]: best = (v, dx, dy)
    _, dx, dy = best; offs.append((dx, dy))
    ids = comp[bi][li][wi]
    chars = [c for c in [c for c in signs[bi][li].split(' ') if c and any(key(q) for q in c)][wi] if key(c)]
    assert len(chars) == len(ids), (bi, li, wi)
    lx = x; out = []
    for k, (i, ch) in enumerate(zip(ids, chars)):
        if k: lx += LH * .08
        lw = round(LH * aspect(i))
        X = round(lx) * S + dx; Y = y * S + dy
        out.append(len(R)); R.append([0, round(X, 2), round(Y, 2), round(lw * S, 2), round(h * S, 2)])
        K.append(key(ch)); P.append(round(bi / (len(signs) - 1), 4))
        lx += aspect(i) * LH
    signs_out.setdefault(str(bi), {}).setdefault(str(li), {})[str(wi)] = out

# signs as [line][word] lists of crop numbers
packed = {}
for bi, ls in signs_out.items():
    lines = [[ls.get(str(li), {}).get(str(wi), []) for wi in range(len(comp[int(bi)][li]))] for li in range(len(comp[int(bi)]))]
    packed[bi] = lines

name = f'riso-{a.seed}-{a.sheet}'
os.makedirs(os.path.join(HERE, 'letters'), exist_ok=True)
sheet.save(os.path.join(HERE, 'letters', name + '.webp'), quality=92, method=6)
jp = os.path.join(HERE, 'letters', 'riso.json')
J = json.load(open(jp)) if os.path.exists(jp) else {'sheets': []}
J['sheets'] = [s for s in J['sheets'] if s['name'] != name] + [{'name': name, 'file': name + '.webp', 'seed': a.seed, 'sheet': a.sheet,
               'dpi': round(S * 600), 'R': R, 'K': K, 'P': P, 'signs': packed}]
json.dump(J, open(jp, 'w'), separators=(',', ':'), ensure_ascii=False)
o = np.array(offs)
print(f'{name}: {len(packed)} signs, {len(R)} letters; drift per word dx {o[:,0].mean():+.1f} dy {o[:,1].mean():+.1f} px (max {abs(o).max()})')

if a.debug:
    from PIL import ImageDraw
    dbg = sheet.copy(); dd = ImageDraw.Draw(dbg)
    for f, X, Y, w, h in R: dd.rectangle([X, Y, X + w, Y + h], outline=(0, 120, 255))
    dbg.save('/tmp/' + name + '-boxes.png')
