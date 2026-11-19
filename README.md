# Off-Register City

A scroll website of 168 street signs from Lafayette, Classon and DeKalb Avenues in Brooklyn, sorted by tone from prohibitions to personal notes.

Every letter is cut from my own photographs of the street, wherever a text reader (OCR) believed it saw a letter. On the street, the strictest words are the biggest and clearest. Here the hierarchy is turned over: prohibitions are set in the letters the machine doubted most, and only the personal notes can be read.

The page was printed on a risograph (three 11 × 17 in sheets, the ink running from red through yellow, green, blue and brown to pink) and the scans were put back into the site. Each word on screen is cut from the scan, with its halftone dots and the drift of the drums. Now and then a letter is taken again from another spot where the same letter was printed, and over time the colours stain and mix.

Rest the pointer on a sign to read what it says.

Seulgi Choei, 2026

## View it

Open the published site, or run it locally (the letters are read from image files, so the page needs a small local server):

```
python3 serve.py
```

then visit http://127.0.0.1:5502. Add `?mix` to the address to open the page as it looks after a long time, with every letter already mixed.

## Files

| Path | What it is |
| --- | --- |
| `index.html`, `style.css`, `app.js` | the page |
| `data/signs.json` | the 168 signs, line by line, in six tones |
| `data/composition.json` | which letter was chosen for every character (the printed arrangement) |
| `data/order.json` | the order the signs are shown in, so the printed colours run on down the page |
| `letters/riso-427-*.webp`, `letters/riso.json` | the three scanned risograph sheets and where every letter sits on them |
| `letters/letters-digital-0.webp`, `letters/letters.json` | the digital letters cut from the photographs, ranked by how sure the machine was |
| `fonts/` | Overpass (SIL Open Font License) |
| `tools/` | the scripts that chose the letters, laid out the print sheets and cut the scans back in |

## Tones

| | Tone | Signs |
| --- | --- | --- |
| 1 | Prohibitions | 32 |
| 2 | Punitive Warnings | 15 |
| 3 | Administrative Regulations | 21 |
| 4 | Informational / Neutral | 84 |
| 5 | Softened Requests | 11 |
| 6 | Emotional / Personal Tone | 5 |
