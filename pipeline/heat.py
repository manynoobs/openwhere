"""Build the "Change heat" surface: store changes per street-level shop, smoothed.

    python pipeline/heat.py      # after export.py

For each year, on a 512 x 512 grid in Web Mercator over the district (about 10 m cells):
  value = Σ w · changes so far  ÷  Σ w · shops listed so far,   w = Gaussian, σ ≈ 100 m
Dividing by shops keeps a dense street from glowing just because it holds more shops.
Cells with fewer than about five shops nearby fade to transparent.

Writes web/public/data/heat/<year>.png (one RGBA image per year), heat/grid.json (a coarse
grid of values and shop counts for hover readouts) and the image bounds and colour stops
into meta.json.
"""
import json
import math

import numpy as np
from PIL import Image

from ingest import ROOT

OUT = ROOT / "web" / "public" / "data"
YEARS = list(range(2016, 2027))
SIZE = 512  # image side in pixels; a power of two so every WebGL path can draw it
SIGMA = 100.0
MARGIN = 500.0
NEAR = 45.0  # metres: the wash is drawn only within about this distance of a shop
R = 6378137.0


def merc(lon, lat):
    return R * math.radians(lon), R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def unmerc(x, y):
    return math.degrees(x / R), math.degrees(2 * math.atan(math.exp(y / R)) - math.pi / 2)


def box_blur(a, r, axis):
    """Moving-window mean along one axis with half-width r cells (edges zero-padded)."""
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad), axis=axis)
    hi = np.take(c, range(2 * r + 1, c.shape[axis]), axis=axis)
    lo = np.take(c, range(0, c.shape[axis] - 2 * r - 1), axis=axis)
    return (hi - lo) / (2 * r + 1)


def gauss(a, sigma_cells):
    # three box passes approximate a Gaussian; box half-width from the standard formula
    r = max(1, int(round((math.sqrt(12 * sigma_cells ** 2 / 3 + 1) - 1) / 2)))
    for axis in (0, 1):
        for _ in range(3):
            a = box_blur(a, r, axis)
    return a


def hex_rgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)


def colour(v, stops):
    xs = [s[0] for s in stops]
    cols = np.array([hex_rgb(s[1]) for s in stops])
    out = np.zeros(v.shape + (3,))
    for ch in range(3):
        out[..., ch] = np.interp(v, xs, cols[:, ch])
    return out


def main():
    gj = json.load(open(OUT / "units.geojson"))
    pts = [f for f in gj["features"] if f["properties"]["sl"] == 1]
    xy = np.array([merc(*f["geometry"]["coordinates"]) for f in pts])
    x0, y0 = xy.min(0) - MARGIN
    x1, y1 = xy.max(0) + MARGIN
    # square grid centred on the shops, so the image is SIZE x SIZE
    side = max(x1 - x0, y1 - y0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    x0, x1, y0, y1 = cx - side / 2, cx + side / 2, cy - side / 2, cy + side / 2
    CELL = side / SIZE
    w = h = SIZE
    col = ((xy[:, 0] - x0) / CELL).astype(int)
    row = ((y1 - xy[:, 1]) / CELL).astype(int)  # image rows run north to south
    sig = SIGMA / CELL
    # shops within ~1σ of a cell carry about this much summed Gaussian weight each
    per_shop = 1.0 / (2 * math.pi * sig ** 2)

    fields = {}
    for yi, year in enumerate(YEARS):
        listed = np.array([f["properties"]["l"][yi] != "0" for f in pts])
        chg = np.array([int(f["properties"]["c"][yi]) for f in pts], dtype=float)
        n = np.zeros((h, w))
        c = np.zeros((h, w))
        np.add.at(n, (row[listed], col[listed]), 1.0)
        np.add.at(c, (row[listed], col[listed]), chg[listed])
        n_s, c_s = gauss(n, sig), gauss(c, sig)
        # colour only where shops actually are: shops within ~NEAR metres of the cell
        near = gauss(n, NEAR / CELL) * (2 * math.pi * (NEAR / CELL) ** 2)
        with np.errstate(invalid="ignore", divide="ignore"):
            rate = np.where(n_s > 1e-9, c_s / n_s, 0.0)
        fields[year] = (rate, n_s / per_shop, near)

    # colour stops from the final year's distribution where enough shops are nearby
    rate26, n26, _ = fields[YEARS[-1]]
    valid = rate26[n26 >= 5]
    q = np.quantile(valid, [0.1, 0.5, 0.8, 0.95, 0.995])
    stops_v = [round(float(v), 2) for v in q]
    for i in range(1, len(stops_v)):  # keep strictly increasing after rounding
        stops_v[i] = max(stops_v[i], stops_v[i - 1] + 0.02)
    # the badge colours, so the wash and the badges read as one scale (grey = calm, red = hot)
    ramp = ["#DADDE3", "#5CC6BA", "#FFC53D", "#FF8A3D", "#E5372B"]
    stops = [[v, c] for v, c in zip(stops_v, ramp)]

    (OUT / "heat").mkdir(parents=True, exist_ok=True)
    for year, (rate, n, near) in fields.items():
        rgb = colour(rate, stops)
        # opacity: fades in with shop density (3 → 6 shops), stays on the streets with shops,
        # and rises with the value so calm areas stay light
        a_n = np.clip((n - 3) / 3, 0, 1)
        a_near = np.clip(near / 1.0, 0, 1)
        a_v = np.interp(rate, [stops_v[0], stops_v[2], stops_v[4]], [0.3, 0.55, 0.75])
        alpha = (a_n * a_near * a_v * 255).astype(np.uint8)
        img = np.dstack([rgb.astype(np.uint8), alpha])
        Image.fromarray(img, "RGBA").save(OUT / "heat" / f"{year}.png", optimize=True)

    # coarse readout grid for hover (about 80 m): value and shops nearby, per year
    k = 8
    gh, gw = h // k, w // k
    grid = {"x0": x0, "y1": y1, "cell": CELL * k, "w": gw, "h": gh, "years": {}}
    for year, (rate, n, _) in fields.items():
        r = rate[: gh * k, : gw * k].reshape(gh, k, gw, k).mean((1, 3))
        nn = n[: gh * k, : gw * k].reshape(gh, k, gw, k).mean((1, 3))
        grid["years"][str(year)] = {
            "v": [round(float(v), 2) if m >= 5 else None for v, m in zip(r.ravel(), nn.ravel())],
            "n": [int(round(float(m))) for m in nn.ravel()],
        }
    json.dump(grid, open(OUT / "heat" / "grid.json", "w"), separators=(",", ":"))

    nw, se = unmerc(x0, y1), unmerc(x0 + w * CELL, y1 - h * CELL)
    meta = json.load(open(OUT / "meta.json"))
    meta["heat"] = {
        "bounds": [[nw[0], nw[1]], [se[0], nw[1]], [se[0], se[1]], [nw[0], se[1]]],
        "years": YEARS,
        "stops": stops,
        "sigma_m": SIGMA,
        "min_shops": 5,
    }
    json.dump(meta, open(OUT / "meta.json", "w"), ensure_ascii=False, indent=1)
    print(f"heat {w}x{h} cells, stops {stops}")


if __name__ == "__main__":
    main()
