// Small geometry helpers for distances of a few hundred metres.
const R = 6371000;

/** straight-line metres between two lon/lat points */
export function metres(lon1: number, lat1: number, lon2: number, lat2: number) {
  const k = Math.cos((((lat1 + lat2) / 2) * Math.PI) / 180);
  const dx = (((lon2 - lon1) * Math.PI) / 180) * k;
  const dy = ((lat2 - lat1) * Math.PI) / 180;
  return R * Math.hypot(dx, dy);
}

export function circlePolygon(lon: number, lat: number, radius: number, steps = 72): GeoJSON.Polygon {
  const k = Math.cos((lat * Math.PI) / 180);
  const ring: [number, number][] = [];
  for (let i = 0; i <= steps; i++) {
    const a = (i / steps) * Math.PI * 2;
    ring.push([lon + ((radius * Math.cos(a)) / (R * k)) * (180 / Math.PI), lat + ((radius * Math.sin(a)) / R) * (180 / Math.PI)]);
  }
  return { type: "Polygon", coordinates: [ring] };
}
