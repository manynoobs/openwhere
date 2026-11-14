"""Build the "How long shops last" heat surface.

    python pipeline/heat.py      # after export.py

For every street-level sign history that started after the first 2016 file (so its start is
known), take how long it stayed listed. Histories still listed today are censored: they count
as "lasted at least this long". Around each point of the map, a Kaplan-Meier estimate weighted
by distance (Gaussian, sigma about 150 m) gives:

  value   share of new shops still listed three years after they opened  (colour)
  median  years until half of them stopped being listed, where that point is reached
  n       how many shops the estimate rests on (sum of weights)

Green means shops last, red means they do not. Where the estimate rests on few shops the
colour fades toward white, so paler means less data. Nothing is drawn more than about 45 m
from a shop.

Writes web/public/data/heat/lifespan.png, heat/grid.json (for hover readouts) and the image
bounds and colour stops into meta.json.
"""
import json
import math
from datetime import date

import numpy as np
from PIL import Image

from export import DISTRICTS
from ingest import ROOT

OUT = ROOT / "web" / "public" / "data"
SIZE = 512  # output image side, a power of two so every WebGL path can draw it
GRID = 128  # estimate grid; the image is a smooth upsample of it
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


def main():
    hx, hy, dur, event, shops = load()
    print(f"{len(dur)} new sign histories, {event.sum()} no longer listed")
    x0, y0 = shops.min(0) - MARGIN
    x1, y1 = shops.max(0) + MARGIN
    side = max(x1 - x0, y1 - y0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    x0, y1 = cx - side / 2, cy + side / 2
    cell = side / GRID

    gx = x0 + (np.arange(GRID) + 0.5) * cell
    gy = y1 - (np.arange(GRID) + 0.5) * cell
    GX, GY = np.meshgrid(gx, gy)
    P = np.stack([GX.ravel(), GY.ravel()], 1)

    T = int(dur.max()) + 1
    onehot = np.zeros((len(dur), T))
    onehot[np.arange(len(dur)), dur] = 1.0
    deaths_by_t = onehot * event[:, None]

    surv3 = np.full(len(P), np.nan)
    median = np.full(len(P), np.nan)
    n_eff = np.zeros(len(P))
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

    surv3 = surv3.reshape(GRID, GRID)
    median = median.reshape(GRID, GRID)
    n_eff = n_eff.reshape(GRID, GRID)

    # colour stops from the spread of well-supported cells, rounded to 5 points
    ok = n_eff >= 8
    q = np.quantile(surv3[ok], [0.05, 0.25, 0.5, 0.75, 0.95])
    stops_v = [round(float(v) * 20) / 20 for v in q]
    for i in range(1, len(stops_v)):
        stops_v[i] = round(max(stops_v[i], stops_v[i - 1] + 0.05), 2)
    stops = [[v, c] for v, c in zip(stops_v, RAMP)]

    def up(a):
        im = Image.fromarray(a.astype(np.float32), mode="F")
        return np.array(im.resize((SIZE, SIZE), Image.BILINEAR))

    v = up(np.nan_to_num(surv3, nan=float(np.nanmedian(surv3))))
    n = up(n_eff)
    cols = np.array([hex_rgb(c) for _, c in stops])
    rgb = np.stack([np.interp(v, stops_v, cols[:, k]) for k in range(3)], -1)
    strength = 0.3 + 0.7 * np.clip((n - N_MIN) / (N_FULL - N_MIN), 0, 1)
    rgb = rgb * strength[..., None] + 255 * (1 - strength[..., None])  # paler = fewer shops to go on

    # draw only near shops
    pix = side / SIZE
    near = np.zeros((SIZE, SIZE))
    np.add.at(near, (((y1 - shops[:, 1]) / pix).astype(int).clip(0, SIZE - 1),
                     ((shops[:, 0] - x0) / pix).astype(int).clip(0, SIZE - 1)), 1.0)
    k = max(1, int(round(NEAR / pix)))
    one = np.zeros((4 * k + 1, 4 * k + 1))
    one[2 * k, 2 * k] = 1.0  # a single shop, blurred the same way, sets the scale
    for _ in range(3):  # three box passes approximate a Gaussian, so the edge is round
        for axis in (0, 1):
            near = box(near, k, axis)
            one = box(one, k, axis)
    a_near = np.clip(near / one.max() * 1.6, 0, 1)
    alpha = np.where(n >= N_MIN, a_near * (0.5 + 0.3 * strength), 0)
    img = np.dstack([rgb.clip(0, 255).astype(np.uint8), (alpha * 255).astype(np.uint8)])

    (OUT / "heat").mkdir(parents=True, exist_ok=True)
    for old in (OUT / "heat").glob("20*.png"):
        old.unlink()  # per-year change-rate images from the earlier heat measure
    Image.fromarray(img, "RGBA").save(OUT / "heat" / "lifespan.png", optimize=True)

    sv, md, nn = surv3.ravel(), median.ravel(), n_eff.ravel()
    grid = {"x0": x0, "y1": y1, "cell": cell, "w": GRID, "h": GRID,
            "v": [None if nn[i] < N_MIN else round(float(sv[i]), 3) for i in range(len(sv))],
            "median": [None if nn[i] < N_MIN or math.isnan(md[i]) else round(float(md[i]), 1) for i in range(len(md))],
            "n": [int(round(float(x))) for x in nn]}
    json.dump(grid, open(OUT / "heat" / "grid.json", "w"), separators=(",", ":"))

    nw, se = unmerc(x0, y1), unmerc(x0 + side, y1 - side)
    meta = json.load(open(OUT / "meta.json"))
    meta["heat"] = {
        "metric": "lifespan",
        "image": "heat/lifespan.png",
        "bounds": [[nw[0], nw[1]], [se[0], nw[1]], [se[0], se[1]], [nw[0], se[1]]],
        "stops": stops,
        "horizon_months": HORIZON,
        "sigma_m": SIGMA,
        "new_histories": int(len(dur)),
        "min_shops": N_MIN,
        "full_shops": N_FULL,
    }
    json.dump(meta, open(OUT / "meta.json", "w"), ensure_ascii=False, indent=1)
    print(f"stops {stops}")


if __name__ == "__main__":
    main()
