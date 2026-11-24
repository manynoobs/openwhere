"""Build the "How long shops last" heat surface.

    python pipeline/heat.py      # after export.py

For every street-level sign history that started after the first 2016 file (so its start is
known), take how long it stayed listed. Histories still listed today are censored: they count
as "lasted at least this long". Around each point of the map, a Kaplan-Meier estimate weighted
by distance (Gaussian, sigma about 150 m) gives:

  value   share of new shops still listed three years after they opened  (colour)
  median  years until half of them stopped being listed, where that point is reached
  n       how many shops the estimate rests on (sum of weights)

The colour scale is centred on Hong Kong's own three-year figure: yellow is typical, green
means shops last longer than that, red shorter. Where the estimate rests on few shops the
colour fades toward white, so paler means less data. Nothing is drawn more than about 45 m
from a shop.

Hong Kong is cut into 4 km tiles. Writes one image per tile with shops,
web/public/data/heat/<col>_<row>.png, a sparse heat/grid.json for hover readouts, and the
tile bounds and colour stops into meta.json.
"""
import json
import math
import warnings
from datetime import date

import numpy as np
from PIL import Image

from export import DISTRICTS
from ingest import ROOT

OUT = ROOT / "web" / "public" / "data"
TILE = 4096.0  # metres (web mercator) per tile
SIZE = 512  # image side per tile, a power of two so every WebGL path can draw it
GRID = 128  # estimate grid per tile (32 m cells); the image is a smooth upsample of it
READ = 64  # metres per cell of the hover readout grid
SIGMA = 150.0
NEAR = 45.0
MARGIN = 500.0
HORIZON = 36  # months: "still listed after three years"
N_FULL = 15.0  # shops at which the colour reaches full strength
N_MIN = 3.0  # below this, nothing is drawn
R = 6378137.0
# green = shops last, red = they do not (the map pin colours, read as stability)
RAMP = ["#D92D20", "#FF8A3A", "#FFCE3A", "#B4D335", "#3FBF6F"]


def merc(lon, lat):
    return R * math.radians(lon), R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def unmerc(x, y):
    return math.degrees(x / R), math.degrees(2 * math.atan(math.exp(y / R)) - math.pi / 2)


def months_between(a, b):
    a, b = date.fromisoformat(a), date.fromisoformat(b)
    return (b.year - a.year) * 12 + (b.month - a.month)


def load():
    xs, ys, dur, event, shop_xy = [], [], [], [], []
    for line in open(ROOT / "data" / "histories.jsonl"):
        r = json.loads(line)
        if r["dist"] not in DISTRICTS or r["lat"] is None or not r["street_level"]:
            continue
        x, y = merc(r["lon"], r["lat"])
        shop_xy.append((x, y))
        for h in r["sign_histories"]:
            if h["listed_before_2016"]:
                continue
            xs.append(x)
            ys.append(y)
            dur.append(months_between(h["first_seen"], h["last_seen"]) + 1)
            event.append(0 if h["listed_in_latest_snapshot"] else 1)
    return np.array(xs), np.array(ys), np.array(dur), np.array(event), np.array(shop_xy)


def hex_rgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)


def box(a, k, axis):
    """Moving-window sum along one axis, half-width k cells."""
    pad = [(k + 1, k) if i == axis else (0, 0) for i in range(a.ndim)]
    c = np.cumsum(np.pad(a, pad), axis=axis)
    return np.take(c, range(2 * k + 1, c.shape[axis]), axis=axis) - np.take(c, range(0, c.shape[axis] - 2 * k - 1), axis=axis)


def estimate(P, hx, hy, onehot, deaths_by_t, T):
    """Kaplan-Meier around each point of P, weighted by distance to each history."""
    surv3 = np.full(len(P), np.nan)
    median = np.full(len(P), np.nan)
    n_eff = np.zeros(len(P))
    if not len(hx):
        return surv3, median, n_eff
    for s in range(0, len(P), 2048):
        p = P[s:s + 2048]
        d2 = (p[:, :1] - hx[None, :]) ** 2 + (p[:, 1:] - hy[None, :]) ** 2
        w = np.exp(-d2 / (2 * SIGMA ** 2))
        w[d2 > (3 * SIGMA) ** 2] = 0
        n_eff[s:s + 2048] = w.sum(1)
        at = (w @ onehot)[:, ::-1].cumsum(1)[:, ::-1]  # weight still at risk at month t
        dead = w @ deaths_by_t
        with np.errstate(invalid="ignore", divide="ignore"):
            hz = np.where(at > 1e-9, dead / at, 0.0)
        S = np.cumprod(1 - hz, axis=1)
        surv3[s:s + 2048] = S[:, min(HORIZON, T - 1)]
        below = S <= 0.5
        median[s:s + 2048] = np.where(below.any(1), below.argmax(1) / 12.0, np.nan)
    return surv3, median, n_eff


def main():
    hx, hy, dur, event, shops = load()
    print(f"{len(dur)} new sign histories, {event.sum()} no longer listed, {len(shops)} street-level shops")
    T = int(dur.max()) + 1
    onehot = np.zeros((len(dur), T))
    onehot[np.arange(len(dur)), dur] = 1.0
    deaths_by_t = onehot * event[:, None]

    # Hong Kong is cut into square tiles of TILE metres (web mercator), each estimated on a
    # GRID x GRID grid and drawn as its own SIZE x SIZE image. Tiles without shops are skipped.
    cell = TILE / GRID
    X0 = math.floor((shops[:, 0].min() - MARGIN) / TILE) * TILE
    Y1 = math.ceil((shops[:, 1].max() + MARGIN) / TILE) * TILE
    reach = 3 * SIGMA
    tiles = {}
    for sx, sy in shops:
        for dx in (-MARGIN, 0, MARGIN):
            for dy in (-MARGIN, 0, MARGIN):
                tiles[(int((sx + dx - X0) // TILE), int((Y1 - (sy + dy)) // TILE))] = True
    est = {}
    for (c, r) in sorted(tiles):
        x0, y1 = X0 + c * TILE, Y1 - r * TILE
        gx = x0 + (np.arange(GRID) + 0.5) * cell
        gy = y1 - (np.arange(GRID) + 0.5) * cell
        GX, GY = np.meshgrid(gx, gy)
        P = np.stack([GX.ravel(), GY.ravel()], 1)
        k = (hx > x0 - reach) & (hx < x0 + TILE + reach) & (hy > y1 - TILE - reach) & (hy < y1 + reach)
        sv, md, nn = estimate(P, hx[k], hy[k], onehot[k], deaths_by_t[k], T)
        est[(c, r)] = (sv.reshape(GRID, GRID), md.reshape(GRID, GRID), nn.reshape(GRID, GRID))
    print(f"{len(est)} tiles of {TILE / 1000:g} km")

    # colour stops centred on Hong Kong's own figure, so yellow means "typical", green better
    # and red worse; the ends sit where the well-supported cells reach
    at = onehot[:, ::-1].cumsum(1)[:, ::-1].sum(0)
    with np.errstate(invalid="ignore", divide="ignore"):
        hz = np.where(at > 0, deaths_by_t.sum(0) / at, 0.0)
    overall = float(np.cumprod(1 - hz)[min(HORIZON, T - 1)])
    centre = round(overall, 2)
    ok = np.concatenate([sv[nn >= 8] for sv, _, nn in est.values()])
    lo, hi = np.quantile(ok, [0.05, 0.95])
    half = max(0.1, math.ceil(max(centre - lo, hi - centre) * 20 - 1e-9) / 20)
    stops_v = [round(centre + k * half / 2, 3) for k in (-2, -1, 0, 1, 2)]
    stops = [[v, c] for v, c in zip(stops_v, RAMP)]
    cols = np.array([hex_rgb(c) for _, c in stops])

    def up(a):
        im = Image.fromarray(a.astype(np.float32), mode="F")
        return np.array(im.resize((SIZE, SIZE), Image.BILINEAR))

    heat_dir = OUT / "heat"
    heat_dir.mkdir(parents=True, exist_ok=True)
    for old in heat_dir.glob("*.png"):
        old.unlink()
    pix = TILE / SIZE
    k = max(1, int(round(NEAR / pix)))
    pad = 8 * k
    one = np.zeros((4 * k + 1, 4 * k + 1))
    one[2 * k, 2 * k] = 1.0  # a single shop, blurred the same way, sets the scale
    for _ in range(3):
        for axis in (0, 1):
            one = box(one, k, axis)
    out_tiles = []
    readout = {}
    for (c, r), (sv, md, nn) in est.items():
        x0, y1 = X0 + c * TILE, Y1 - r * TILE
        fill = float(np.nanmedian(sv)) if np.isfinite(sv).any() else centre
        v = up(np.nan_to_num(sv, nan=fill))
        n = up(nn)
        rgb = np.stack([np.interp(v, stops_v, cols[:, j]) for j in range(3)], -1)
        strength = 0.3 + 0.7 * np.clip((n - N_MIN) / (N_FULL - N_MIN), 0, 1)
        rgb = rgb * strength[..., None] + 255 * (1 - strength[..., None])  # paler = fewer shops to go on

        # draw only near shops; shops just outside the tile count, so edges join up
        near = np.zeros((SIZE + 2 * pad, SIZE + 2 * pad))
        px = ((shops[:, 0] - x0) / pix).astype(int) + pad
        py = ((y1 - shops[:, 1]) / pix).astype(int) + pad
        inside = (px >= 0) & (px < SIZE + 2 * pad) & (py >= 0) & (py < SIZE + 2 * pad)
        np.add.at(near, (py[inside], px[inside]), 1.0)
        for _ in range(3):  # three box passes approximate a Gaussian, so the edge is round
            for axis in (0, 1):
                near = box(near, k, axis)
        near = near[pad:pad + SIZE, pad:pad + SIZE]
        a_near = np.clip(near / one.max() * 1.6, 0, 1)
        alpha = np.where(n >= N_MIN, a_near * (0.5 + 0.3 * strength), 0)
        if alpha.max() < 1 / 255:
            continue
        img = np.dstack([rgb.clip(0, 255).astype(np.uint8), (alpha * 255).astype(np.uint8)])
        name = f"heat/{c}_{r}.png"
        Image.fromarray(img, "RGBA").save(OUT / name, optimize=True)
        nw, se = unmerc(x0, y1), unmerc(x0 + TILE, y1 - TILE)
        out_tiles.append({"image": name,
                          "bounds": [[nw[0], nw[1]], [se[0], nw[1]], [se[0], se[1]], [nw[0], se[1]]]})

        # readout: 2 x 2 blocks of the estimate grid, kept only where there is colour
        b = READ // int(cell)
        A = alpha.reshape(GRID, SIZE // GRID, GRID, SIZE // GRID).max((1, 3))
        for i in range(0, GRID, b):
            for j in range(0, GRID, b):
                if A[i:i + b, j:j + b].max() < 1 / 255 or nn[i:i + b, j:j + b].mean() < N_MIN:
                    continue
                gi = r * (GRID // b) + i // b
                gj = c * (GRID // b) + j // b
                with np.errstate(invalid="ignore"), warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    m = np.nanmean(md[i:i + b, j:j + b])
                readout[gi * 100000 + gj] = (round(float(np.nanmean(sv[i:i + b, j:j + b])), 3),
                                             None if math.isnan(m) else round(float(m), 1),
                                             int(round(float(nn[i:i + b, j:j + b].mean()))))
    for old in heat_dir.glob("grid*.json"):
        old.unlink()
    keys = sorted(readout)
    grid = {"x0": X0, "y1": Y1, "cell": READ, "stride": 100000, "i": keys,
            "v": [readout[i][0] for i in keys], "median": [readout[i][1] for i in keys], "n": [readout[i][2] for i in keys]}
    json.dump(grid, open(heat_dir / "grid.json", "w"), separators=(",", ":"))

    meta = json.load(open(OUT / "meta.json"))
    meta["heat"] = {
        "metric": "lifespan",
        "tiles": out_tiles,
        "stops": stops,
        "district": centre,
        "horizon_months": HORIZON,
        "sigma_m": SIGMA,
        "new_histories": int(len(dur)),
        "min_shops": N_MIN,
        "full_shops": N_FULL,
    }
    json.dump(meta, open(OUT / "meta.json", "w"), ensure_ascii=False, indent=1)
    print(f"{len(out_tiles)} tile images, {len(keys)} readout cells; stops {stops}")


if __name__ == "__main__":
    main()
